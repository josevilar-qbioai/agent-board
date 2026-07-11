#!/usr/bin/env python3
"""
broker.py — servidor local que coordina la aprobacion de doble via.

Sirve el tablero y mantiene un unico estado, PERSISTIDO en disco (atomico):
  - los hooks de Claude Code (POST /api/event, POST /api/request, GET /api/decision)
  - el tablero HTML (GET /api/state para pintar, POST /api/decide al pulsar boton)

Arranca:  python3 hooks/broker.py     (sirve en http://127.0.0.1:8787)
Abre:     http://127.0.0.1:8787/agent-board.html?feed=/api/state

Persistencia:
  AGENT_BOARD_STATE  ruta del fichero de estado (def board/broker-state.json)
  El estado se restaura al arrancar y se vuelca en background cada ~1s si hay
  cambios; las decisiones (/api/decide) se vuelcan de inmediato.
"""
import json, os, sys, threading, time, secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# canonical.op_hash: fuente unica del hash de operacion (ADR-0007). Fallback inline
# por si el modulo no es importable, para no acoplar el arranque del broker.
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp"))
    from canonical import op_hash
except Exception:
    import hashlib
    def op_hash(tool, payload=None):
        blob = json.dumps({"tool": tool or "", "payload": payload or {}},
                          sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

# quota: contabilidad agregada en ventana deslizante (ADR-0008). Opcional: si no se
# puede importar, el broker funciona igual pero sin enforcement de cuotas.
try:
    import quota as _quota
except Exception:
    _quota = None

# audit: cadena append-only tamper-evident (ADR-0006). El broker audita las decisiones
# del operador en la MISMA cadena que el gate (serializada por flock).
try:
    import audit as _audit_mod
except Exception:
    _audit_mod = None

# cost: coste en € por (modelo, tokens) y clase local|foundational. Permite cuotas de
# COSTE (no de tokens a secas), distinguiendo modelos locales de fundacionales.
try:
    import cost as _cost
    _PRICES = _cost.load_prices()
except Exception:
    _cost = None
    _PRICES = None

AUDIT_PATH = os.environ.get("AGENT_BOARD_AUDIT",
                            os.path.join(os.path.dirname(__file__), "..", "mcp", "gate-audit.log"))
# Guardar el payload COMPLETO en la auditoria (ademas de summary + payload_hash). Sirve
# para construir el dataset {contexto, decision_humana} (evals / juicio capturado). Por
# defecto NO: minimizacion de datos, el payload puede contener contenido sensible.
AUDIT_FULL_PAYLOAD = os.environ.get("AGENT_BOARD_AUDIT_FULL_PAYLOAD", "").strip().lower() \
    in ("1", "true", "yes", "on")
# Identificador de despliegue/tenant (unidad). Se estampa en cada entrada para poder
# FEDERAR varias instalaciones hacia un log central sin ambiguedad de procedencia.
DEPLOYMENT = (os.environ.get("AGENT_BOARD_DEPLOYMENT") or "").strip() or None

def audit_event(**entry):
    if DEPLOYMENT and "deployment" not in entry:
        entry["deployment"] = DEPLOYMENT
    if _audit_mod:
        _audit_mod.append(entry, AUDIT_PATH)

PORT = int(os.environ.get("AGENT_BOARD_PORT", "8787"))
BOARD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "board"))
STATE_PATH = os.environ.get("AGENT_BOARD_STATE", os.path.join(BOARD_DIR, "broker-state.json"))
POLICY_PATH = os.environ.get("AGENT_BOARD_POLICY",
                             os.path.join(os.path.dirname(__file__), "..", "mcp", "policy.json"))
# config.json del proyecto: fuente ÚNICA de los perfiles (agentes/unidades). El tablero
# lo carga por /api/config, así no se duplica (embebido solo como fallback offline).
CONFIG_PATH = os.environ.get("AGENT_BOARD_CONFIG",
                             os.path.join(os.path.dirname(__file__), "..", "config.json"))

def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}
# TTL (s) de una peticion 'ask' pendiente y de su decision (ADR-0007).
REQUEST_TTL = int(os.environ.get("AGENT_BOARD_REQUEST_TTL", "300"))


def load_quotas():
    """Lee la seccion 'quotas' de policy.json. Lista vacia si no hay o no es legible."""
    try:
        with open(POLICY_PATH) as f:
            return json.load(f).get("quotas", []) or []
    except Exception:
        return []


QUOTAS = load_quotas()
MAX_WINDOW = max([int(q.get("window", 3600)) for q in QUOTAS], default=3600)
# nombres de cuotas de COSTE (para marcar 'capped' la tarjeta cuando una de estas deniega)
COST_QUOTA_NAMES = {q.get("name") for q in QUOTAS
                    if q.get("amount_field") == "cost_eur" or q.get("match_class")}
ledger = _quota.QuotaLedger() if _quota else None
# Token de operador: SOLO necesario para aprobar/denegar (/api/decide) y resetear.
# El canal del agente (request/decision/event/state) NO lo requiere.
TOKEN = os.environ.get("AGENT_BOARD_OP_TOKEN") or secrets.token_urlsafe(16)
GATE_MSG = {"Write": "Permiso: escribir fichero", "Edit": "Permiso: editar fichero",
            "Bash": "Permiso: ejecutar comando"}

lock = threading.Lock()
_dirty = False

def empty_state():
    return {"agents": [], "stats": {"spawned": 0, "done": 0, "failed": 0, "tokens": 0},
            "archived": 0, "nextId": 1, "order": 0}

state = empty_state()
# requests: req_id(str, aleatorio) -> registro de una peticion 'ask' (ADR-0007).
#   {req_id, sid, card_id, tool, payload_hash, decision, created, decided_at, used}
# La decision se liga al payload_hash exacto, es de un solo uso y caduca (TTL).
requests = {}

# ---------- persistencia ----------
def load_state():
    global state, requests, ledger
    try:
        with open(STATE_PATH) as f:
            d = json.load(f)
        state = d.get("state") or empty_state()
        requests = d.get("requests") or {}
        if _quota:
            ledger = _quota.QuotaLedger.from_dict(d.get("counters") or {})
        print(f"estado restaurado: {len(state['agents'])} tarjetas, {len(requests)} peticiones")
    except FileNotFoundError:
        print("sin estado previo, arrancando vacio")
    except Exception as e:
        print(f"estado corrupto ({e}), arrancando vacio")

def flush(force=False):
    """Vuelca a disco de forma atomica. Llamar dentro del lock."""
    global _dirty
    if not (_dirty or force):
        return
    try:
        os.makedirs(os.path.dirname(STATE_PATH) or ".", exist_ok=True)
        tmp = STATE_PATH + ".tmp"
        counters = ledger.to_dict() if ledger else {}
        with open(tmp, "w") as f:
            json.dump({"state": state, "requests": requests, "counters": counters}, f)
        os.replace(tmp, STATE_PATH)
        _dirty = False
    except Exception:
        pass

def flusher():
    while True:
        time.sleep(1.0)
        with lock:
            flush()

def mark_dirty():
    global _dirty
    _dirty = True

# ---------- logica de estado ----------
def find(sid):
    for a in state["agents"]:
        if a.get("sid") == sid:
            return a
    return None

def new_card(sid, job="", kind="implementer", col="working", model="opus", last="", mut=False, parent=None, unit=None, profile=None):
    a = {"sid": sid, "id": state["nextId"], "order": state["order"], "kind": kind,
         "col": col, "job": str(job)[:90], "model": model, "wt": "wt/" + str(sid)[:6],
         "tokens": 0, "target": 20000, "elapsed": 0, "mut": mut,
         "parentId": parent, "last": last, "verdict": None,
         # unit/profile: dimensión de departamento para el análisis por unidad de las
         # decisiones humanas (se propaga a la auditoría al decidir).
         "unit": unit, "profile": profile,
         "reqId": None, "payloadHash": None, "note": "", "capped": False,
         "created_at": time.time()}
    state["nextId"] += 1; state["order"] += 1; state["stats"]["spawned"] += 1
    state["agents"].append(a)
    return a

def on_event(d):
    ev = d.get("event"); sid = str(d.get("session_id") or "default")
    card = find(sid)
    if ev == "SessionStart":
        if not card:
            new_card(sid, job=d.get("prompt") or "sesion " + sid[:6],
                     kind=d.get("kind", "implementer"), model=d.get("model", "opus"),
                     parent=d.get("parent_id"), last="sesion iniciada",
                     unit=d.get("unit"), profile=d.get("profile"))
    elif ev == "PreToolUse" and card:
        card["last"] = "tool: " + str(d.get("tool_name") or "tool")
        card["tokens"] += 600; state["stats"]["tokens"] += 600
        card["last_activity"] = time.time()
    elif ev == "Usage" and card:
        # uso REAL reportado por el orquestador (cualquier proveedor): tokens y modelo.
        # El tablero calcula el coste € a partir de tokens+modelo (mcp/models.json).
        tk = int(d.get("tokens") or 0)
        card["tokens"] += tk; state["stats"]["tokens"] += tk
        if d.get("model"): card["model"] = d["model"]
        if d.get("action"): card["last"] = str(d["action"])[:90]
        card["last_activity"] = time.time()
    elif ev == "Stop" and card and card["col"] != "needs":
        card["col"] = "done"; card["verdict"] = "ok"; card["last"] = "completado"
        state["stats"]["done"] += 1
    mark_dirty()

def canonical_summary(tool, payload):
    """Resumen que ve el operador, COMPUESTO por el servidor desde campos validados
    (no del texto libre del agente). Cierra la amenaza #12: el payload no controla la
    prosa que induce a aprobar deprisa; solo aporta valores, truncados y etiquetados."""
    parts = []
    for k in sorted((payload or {}).keys())[:4]:
        v = str(payload[k]).replace("\n", " ")
        if len(v) > 40:
            v = v[:40] + "…"
        parts.append(f"{k}={v}")
    body = " · ".join(parts)
    return f"{tool}" + (f" — {body}" if body else "")

def on_request(d):
    """Crea una peticion 'ask' ligada al hash del payload. Devuelve {req_id, payload_hash}.
    req_id es aleatorio (no adivinable); la decision se atara a ESTE payload_hash."""
    sid = str(d.get("session_id") or "default")
    tool = d.get("tool_name") or "operacion"
    payload = d.get("tool_input") or {}
    ph = op_hash(tool, payload)
    safe = canonical_summary(tool, payload)               # #12: resumen del servidor
    note = str(d.get("summary") or "")[:80]               # texto libre del agente: secundario
    req_id = secrets.token_urlsafe(12)        # no secuencial, no adivinable (ADR-0007)
    card = find(sid) or new_card(sid, job=safe)
    if d.get("unit"): card["unit"] = d["unit"]           # dimensión de departamento
    if d.get("profile"): card["profile"] = d["profile"]
    card["col"] = "needs"; card["mut"] = True
    card["last"] = safe; card["note"] = note
    card["reqId"] = req_id; card["payloadHash"] = ph
    requests[req_id] = {"req_id": req_id, "sid": sid, "card_id": card["id"], "tool": tool,
                        "payload_hash": ph, "summary": safe, "decision": "pending",
                        "created": time.time(), "decided_at": None, "used": False,
                        # payload completo retenido SOLO si el operador lo activo (evals)
                        "payload": (payload if AUDIT_FULL_PAYLOAD else None)}
    mark_dirty()
    return {"req_id": req_id, "payload_hash": ph}

def on_account(d):
    """Contabilidad agregada / rate limit (ADR-0008). Evalua las quotas que casan con
    la tool y devuelve la decision. Llamar DENTRO del lock.
      mode: 'check' (no registra) | 'commit' (registra si allow) | 'force' (registra siempre)
    Si no hay modulo quota o no hay quotas -> allow (no interfiere)."""
    if not _quota or not QUOTAS:
        return {"decision": "allow", "hits": [], "recorded": False}
    tool = d.get("tool_name") or d.get("tool") or ""
    payload = d.get("tool_input") or d.get("payload") or {}
    ctx = dict(d.get("ctx") or {})
    # coste: si el contexto trae modelo y tokens, calcula € y clase para las cuotas
    # de coste (amount_field='cost_eur', match_class='foundational', ...).
    if _cost and ctx.get("model") is not None and ctx.get("tokens") is not None:
        ctx["cost_eur"] = _cost.cost_eur(ctx.get("model"), ctx.get("tokens"), _PRICES)
        ctx["model_class"] = _cost.model_class(ctx.get("model"), _PRICES)
    mode = d.get("mode", "commit")
    now = time.time()
    res = _quota.evaluate(QUOTAS, tool, payload, ctx, ledger, now, mode=mode)
    if res.get("recorded"):
        ledger.prune(MAX_WINDOW, now)
        mark_dirty()
    # refleja el estado 'capped' en la tarjeta del agente (col '⚡ Sin presupuesto'):
    # si una cuota de COSTE deniega -> capped; si vuelve a permitir -> se libera.
    sid = ctx.get("agent")
    card = find(sid) if sid else None
    if card is not None:
        cost_deny = any(h.get("decision") == "deny" and h.get("name") in COST_QUOTA_NAMES
                        for h in res.get("hits", []))
        if cost_deny:
            card["capped"] = True; card["col"] = "capped"
            card["last"] = "frenado: presupuesto de coste fundacional"
            mark_dirty()
        elif res.get("decision") == "allow" and card.get("capped"):
            card["capped"] = False; card["col"] = "working"
            card["last"] = "presupuesto liberado"
            mark_dirty()
    return res


def decision_status(req_id):
    """Estado de una peticion para el canal del agente: pending|allow|deny|expired|unknown.
    Marca 'used' al entregar una decision firme (un solo uso por consumo)."""
    rec = requests.get(req_id)
    if not rec:
        return "unknown"
    if rec["decision"] == "pending":
        if time.time() - rec["created"] > REQUEST_TTL:
            rec["decision"] = "expired"; mark_dirty()
            return "expired"
        return "pending"
    # decision firme: caduca tambien, y se consume una vez
    if rec["decided_at"] and time.time() - rec["decided_at"] > REQUEST_TTL:
        return "expired"
    if rec["decision"] == "allow":
        rec["used"] = True; mark_dirty()      # one-time: el allow se consume al leerse
    return rec["decision"]

def on_purge_stale(max_age_s=300):
    """Elimina tarjetas en 'working' sin actividad en los últimos max_age_s segundos.
    Las mueve a 'done' con verdict='stale'. Devuelve la lista de sids purgados.
    Llamar DENTRO del lock.

    Heurística: usa last_activity (si existe) > created_at > purga incondicional.
    Nunca purga tarjetas con un gate pendiente (en 'needs' o con request pending)."""
    now = time.time()
    purged = []
    for card in state["agents"]:
        if card["col"] != "working":
            continue
        sid = card.get("sid", "")
        # No purgar si hay un gate pendiente asociado
        has_pending = any(r["sid"] == sid and r["decision"] == "pending"
                          for r in requests.values())
        if has_pending:
            continue
        # Determinar el último timestamp de actividad
        last_ts = card.get("last_activity") or card.get("created_at") or 0
        if last_ts and (now - last_ts) < max_age_s:
            continue  # todavía activa
        # Sin timestamp → tarjeta legacy sin marcas, purgar
        card["col"] = "done"
        card["verdict"] = "stale"
        card["last"] = f"purgado (inactivo >{max_age_s}s)"
        state["stats"]["done"] += 1
        purged.append(sid)
    if purged:
        mark_dirty()
        flush(force=True)
    return purged


def on_decide(req_id, decision, payload_hash=None):
    """Aplica una decision del operador, validando el binding (ADR-0007).
    Devuelve (codigo_http, cuerpo)."""
    rec = requests.get(req_id)
    if not rec:
        return 404, {"error": "req_id desconocido"}
    if rec["decision"] != "pending":
        return 409, {"error": f"peticion ya resuelta ({rec['decision']})"}
    if time.time() - rec["created"] > REQUEST_TTL:
        rec["decision"] = "expired"; flush(force=True)
        return 409, {"error": "peticion caducada (TTL)"}
    if payload_hash is not None and payload_hash != rec["payload_hash"]:
        return 409, {"error": "payload_hash no coincide; aprobacion no ligada a este contenido"}
    if decision not in ("allow", "deny"):
        return 400, {"error": "decision invalida"}
    rec["decision"] = decision; rec["decided_at"] = time.time()
    card = None
    for a in state["agents"]:
        if a["id"] == rec["card_id"]:
            card = a
            if decision == "allow":
                a["col"] = "working"; a["last"] = "aprobado en el tablero"; a["mut"] = False
            else:
                a["col"] = "done"; a["verdict"] = "fail"; a["last"] = "denegado por operador"
                state["stats"]["failed"] += 1
            break
    # auditoria tamper-evident de la decision del operador (ADR-0006). Si el operador
    # activo AGENT_BOARD_AUDIT_FULL_PAYLOAD, el payload completo queda ligado a la
    # decision humana en la MISMA cadena (par {contexto, decision} para evals).
    # Ademas se enriquece con la dimension de UNIDAD/DEPARTAMENTO (+ agente, modelo,
    # coste) para poder analizar el juicio humano de forma agregada por area.
    meta = {}
    if card:
        for k in ("sid", "kind", "model", "unit", "profile"):
            if card.get(k) is not None:
                meta[k] = card.get(k)
        if _cost and card.get("model") is not None:
            meta["cost_eur"] = _cost.cost_eur(card.get("model"), card.get("tokens") or 0, _PRICES)
    extra = {"payload": rec.get("payload")} \
        if (AUDIT_FULL_PAYLOAD and rec.get("payload") is not None) else {}
    audit_event(tool=rec.get("tool"), role="operator", decision=decision, source="operator",
                summary=rec.get("summary"), payload_hash=rec.get("payload_hash"), req_id=req_id,
                **meta, **extra)
    flush(force=True)  # las decisiones se persisten de inmediato
    return 200, {"ok": True}

# ---------- HTTP ----------
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store"); self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path == "/api/state":
            with lock: self._send(200, dict(state)); return
        if u.path == "/api/decision":
            rid = q.get("req_id", [""])[0]
            with lock: self._send(200, {"status": decision_status(rid)}); return
        if u.path == "/api/config":
            c = load_config()
            self._send(200, {"project": c.get("project"), "active_profile": c.get("active_profile"),
                             "profiles": c.get("profiles", {}), "wip_limit": c.get("wip_limit"),
                             "columns": c.get("columns")}); return
        rel = u.path.lstrip("/") or "agent-board.html"
        path = os.path.normpath(os.path.join(BOARD_DIR, rel))
        if path.startswith(BOARD_DIR) and os.path.isfile(path):
            ctype = "text/html" if path.endswith(".html") else "application/octet-stream"
            with open(path, "rb") as f: self._send(200, f.read(), ctype); return
        self._send(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try: d = json.loads(self.rfile.read(n) or b"{}")
        except Exception: d = {}
        u = urlparse(self.path)
        # canal de operador: aprobar/resetear exige token (el agente no lo tiene)
        if u.path in ("/api/decide", "/api/reset", "/api/purge-stale"):
            if self.headers.get("X-Operator-Token") != TOKEN:
                self._send(403, {"error": "operator token required"}); return
        with lock:
            if u.path == "/api/event": on_event(d); self._send(200, {"ok": True}); return
            if u.path == "/api/account": self._send(200, on_account(d)); return
            if u.path == "/api/request": self._send(200, on_request(d)); return
            if u.path == "/api/decide":
                code, body = on_decide(d.get("req_id"), d.get("decision"), d.get("payload_hash"))
                self._send(code, body); return
            if u.path == "/api/reset":
                global state, requests, ledger
                state = empty_state(); requests = {}
                if _quota: ledger = _quota.QuotaLedger()
                flush(force=True)
                self._send(200, {"ok": True}); return
            if u.path == "/api/purge-stale":
                max_age = int(d.get("max_age_s", 300))
                purged = on_purge_stale(max_age)
                self._send(200, {"ok": True, "purged": purged, "count": len(purged)}); return
        self._send(404, {"error": "not found"})

if __name__ == "__main__":
    load_state()
    threading.Thread(target=flusher, daemon=True).start()
    op_url = f"http://127.0.0.1:{PORT}/agent-board.html?feed=/api/state#token={TOKEN}"
    print(f"agent-board broker en http://127.0.0.1:{PORT}  (estado: {STATE_PATH})")
    print(f"TOKEN de operador (necesario para aprobar/denegar): {TOKEN}")
    print(f"Abre el tablero CON el token (no compartas esta URL):\n  {op_url}")
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
    except KeyboardInterrupt:
        with lock: flush(force=True)
        print("\nestado guardado, broker detenido")
