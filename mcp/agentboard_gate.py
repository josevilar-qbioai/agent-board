#!/usr/bin/env python3
"""
agentboard_gate.py — puerta DETERMINISTA para tools de un servidor MCP en Python.

Filosofia: el efecto no puede ocurrir sin pasar la puerta, porque la puerta vive
DENTRO de la tool. La decision es codigo (politica), no criterio del modelo:

    RBAC (tu capa)  ->  politica determinista  ->  [solo 'ask'] tablero  ->  auditoria

Uso minimo en tu servidor MCP:

    from agentboard_gate import gated, GateDenied

    @gated("disable_account")
    def disable_account(upn: str):
        ...  # esto SOLO se ejecuta si la politica permite o el operador aprueba

Decisiones posibles de la politica (mcp/policy.json):
    allow  -> ejecuta sin preguntar
    deny   -> lanza GateDenied (nunca ejecuta)
    ask    -> crea tarjeta en el tablero y BLOQUEA hasta Aprobar/Denegar

Si el bucket es 'ask' y el broker no responde -> FAIL-CLOSED (deny), salvo que
pongas AGENT_BOARD_FAIL_OPEN=1. Para un servidor, lo seguro es denegar.

Config por entorno:
    AGENT_BOARD_BROKER       (def http://127.0.0.1:8787)
    AGENT_BOARD_GATE_TIMEOUT (def 300)  seg de espera de aprobacion humana
    AGENT_BOARD_POLICY       (def junto a este fichero: policy.json)
    AGENT_BOARD_AUDIT        (def mcp/gate-audit.log)
    AGENT_BOARD_FAIL_OPEN    (def 0)  1 = permitir si no hay broker en 'ask'
    MCP_USER_ROLE            rol del principal (reutiliza el de tu server M365)
"""
import os, sys, json, time, uuid, fnmatch, urllib.request, asyncio, functools

BROKER = os.environ.get("AGENT_BOARD_BROKER", "http://127.0.0.1:8787").rstrip("/")
GATE_TIMEOUT = int(os.environ.get("AGENT_BOARD_GATE_TIMEOUT", "300"))
POLICY_PATH = os.environ.get("AGENT_BOARD_POLICY", os.path.join(os.path.dirname(__file__), "policy.json"))
AUDIT_PATH = os.environ.get("AGENT_BOARD_AUDIT", os.path.join(os.path.dirname(__file__), "gate-audit.log"))
FAIL_OPEN = os.environ.get("AGENT_BOARD_FAIL_OPEN", "0") == "1"

# hash de operacion (ADR-0007): mismo modulo que usa el broker, fuente unica
try:
    from canonical import op_hash
except Exception:
    import hashlib
    def op_hash(tool, payload=None):
        blob = json.dumps({"tool": tool or "", "payload": payload or {}},
                          sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

# quota (ADR-0008): determinar localmente si una tool esta sujeta a cuota; la cuenta
# agregada la lleva el broker (estado compartido). Si el modulo falta, sin enforcement.
try:
    from quota import match_quotas as _match_quotas
except Exception:
    _match_quotas = None


class GateDenied(Exception):
    """La operacion fue denegada (por politica o por el operador)."""


# ---------- politica determinista ----------
_OPS = {
    "==": lambda a, b: a == b, "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b, "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
    "in": lambda a, b: a in b, "not_in": lambda a, b: a not in b,
    "startswith": lambda a, b: str(a).startswith(b),
    "glob": lambda a, b: fnmatch.fnmatch(str(a), b),
}

def _load_policy():
    try:
        with open(POLICY_PATH) as f:
            return json.load(f)
    except Exception:
        # por defecto: todo lo que llega a la puerta pide aprobacion (conservador)
        return {"default": "ask", "rules": []}

def _match_preds(preds, payload):
    """True solo si HAY condiciones y TODAS se cumplen. Sin condiciones -> False."""
    if not preds:
        return False
    for p in preds:
        val = payload.get(p.get("field"))
        op = _OPS.get(p.get("op"))
        if op is None or val is None:
            return False
        try:
            if not op(val, p.get("value")):
                return False
        except Exception:
            return False
    return True

def decide_rule(tool, payload, role=None):
    """Decision de la PRIMERA regla que casa: 'allow'|'deny'|'ask', o None si ninguna casa.
    None permite al llamante decidir el comportamiento por defecto (servidor: ask; hook: no interferir)."""
    pol = _load_policy()
    default = pol.get("default", "ask")
    for rule in pol.get("rules", []):
        if not fnmatch.fnmatch(tool, rule.get("tool", "")):
            continue
        roles = rule.get("roles")
        if roles is not None and role not in roles:
            return "deny"
        decision = rule.get("decision", default)
        if _match_preds(rule.get("deny_if"), payload):
            return "deny"
        if decision == "allow" and _match_preds(rule.get("ask_if"), payload):
            return "ask"
        return decision
    return None

def evaluate(tool, payload, role=None):
    """Como decide_rule pero aplica el 'default' de la politica si nada casa."""
    d = decide_rule(tool, payload, role)
    return d if d is not None else _load_policy().get("default", "ask")


# ---------- cliente minimo del broker (sin dependencias) ----------
def _post(path, payload, t=4):
    req = urllib.request.Request(BROKER + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=t) as r:
        return json.loads(r.read() or b"{}")

def _get(path, t=4):
    with urllib.request.urlopen(BROKER + path, timeout=t) as r:
        return json.loads(r.read() or b"{}")

def _ask_board(tool, payload, summary):
    """Crea tarjeta en el tablero y BLOQUEA hasta la decision. True=allow.
    La aprobacion se liga al hash del payload (ADR-0007): en el allow se re-verifica
    que el contenido es exactamente el aprobado antes de dejar pasar el efecto."""
    sid = uuid.uuid4().hex[:8]
    try:
        _post("/api/event", {"event": "SessionStart", "session_id": sid,
                             "prompt": summary, "kind": "auditor", "model": "n/a"})
        resp = _post("/api/request", {"session_id": sid, "tool_name": tool,
                                      "summary": summary, "tool_input": payload})
        rid = resp["req_id"]
        expected_hash = resp.get("payload_hash")
    except Exception:
        return None  # broker inaccesible
    deadline = time.time() + GATE_TIMEOUT
    while time.time() < deadline:
        time.sleep(1.5)
        try:
            st = _get(f"/api/decision?req_id={rid}").get("status", "pending")
        except Exception:
            continue
        if st == "allow":
            if expected_hash and op_hash(tool, payload) != expected_hash:
                return False  # payload cambiado tras aprobar -> denegar
            return True
        if st == "deny":
            return False
        if st in ("expired", "unknown"):
            return None  # sin decision firme -> que decida el fail-open/closed
    return None  # timeout


# ---------- auditoria (hash-chain, ADR-0006) ----------
try:
    from audit import append as _audit_append
except Exception:
    _audit_append = None

def _audit(tool, role, decision, source, summary, payload_hash=None):
    entry = {"tool": tool, "role": role, "decision": decision, "source": source,
             "summary": summary, "payload_hash": payload_hash}
    if _audit_append:
        _audit_append(entry, AUDIT_PATH)          # cadena tamper-evident
        return
    try:                                          # fallback: log plano
        with open(AUDIT_PATH, "a") as f:
            f.write(json.dumps({"ts": int(time.time()), **entry}) + "\n")
    except Exception:
        pass


# ---------- cuota agregada (ADR-0008) ----------
def _quota_applies(tool):
    """¿Hay alguna quota configurada que case con esta tool? (decision local, sin red)"""
    if not _match_quotas:
        return False
    try:
        quotas = _load_policy().get("quotas", []) or []
    except Exception:
        return False
    return bool(_match_quotas(quotas, tool))

def _quota_consult(tool, payload, mode):
    """Pregunta al broker por la cuenta agregada. mode: check|commit|force.
    Devuelve el dict del broker, o None si el broker no responde."""
    ctx = {"agent": os.environ.get("AGENT_BOARD_AGENT", ""),
           "workflow": os.environ.get("AGENT_BOARD_WORKFLOW", "")}
    try:
        return _post("/api/account", {"tool": tool, "payload": payload, "ctx": ctx, "mode": mode})
    except Exception:
        return None


# ---------- el chequeo (codigo, determinista) ----------
def check(tool, payload, role=None, summary=None):
    """Lanza GateDenied si no se permite. No devuelve nada si se permite."""
    role = role or os.environ.get("MCP_USER_ROLE")
    summary = summary or f"{tool}: " + ", ".join(f"{k}={v}" for k, v in list(payload.items())[:3])
    ph = op_hash(tool, payload)                         # ancla la auditoria al contenido
    def aud(decision, source):                          # cada decision queda en la cadena
        _audit(tool, role, decision, source, summary, payload_hash=ph)
    decision = evaluate(tool, payload, role)

    if decision == "deny":
        aud("deny", "policy")
        raise GateDenied(f"Politica deniega '{tool}'")

    if decision == "allow":
        # cuota agregada (ADR-0008): si la tool esta sujeta a cuota, el limite real es
        # el acumulado en la ventana. Cierra el troceo (#11) que la politica por-llamada
        # no ve. mode 'commit' registra solo si la cuenta queda en 'allow'.
        if _quota_applies(tool):
            q = _quota_consult(tool, payload, "commit")
            if q is None:
                if FAIL_OPEN:
                    aud("allow", "quota-fail-open"); return
                aud("deny", "quota-fail-closed")
                raise GateDenied(f"Cuota no verificable para '{tool}' (broker caido; fail-closed)")
            qd = q.get("decision", "allow")
            if qd == "deny":
                aud("deny", "quota")
                raise GateDenied(f"Cuota excedida para '{tool}'")
            if qd == "ask":
                if _ask_board(tool, payload, "Cuota excedida — " + summary) is True:
                    _quota_consult(tool, payload, "force")     # cuenta tras aprobacion
                    aud("allow", "quota-human"); return
                aud("deny", "quota-human")
                raise GateDenied(f"Cuota excedida y no aprobada para '{tool}'")
            # qd == 'allow' -> ya registrado por 'commit'
        aud("allow", "policy")
        return

    # decision == 'ask' -> tablero
    result = _ask_board(tool, payload, summary)
    if result is True:
        if _quota_applies(tool):
            _quota_consult(tool, payload, "force")             # tambien cuenta lo aprobado
        aud("allow", "human")
        return
    if result is False:
        aud("deny", "human")
        raise GateDenied(f"Operador deniega '{tool}'")
    # broker caido o timeout
    if FAIL_OPEN:
        aud("allow", "fail-open")
        return
    aud("deny", "fail-closed")
    raise GateDenied(f"Sin aprobacion para '{tool}' (broker caido/timeout; fail-closed)")


# ---------- decorador (sync y async) ----------
def gated(tool_name=None, summary=None):
    """Envuelve una tool MCP. El cuerpo SOLO corre si check() no lanza."""
    def deco(fn):
        name = tool_name or fn.__name__
        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def awrap(*a, **kw):
                s = summary(kw) if callable(summary) else summary
                await asyncio.to_thread(check, name, dict(kw), None, s)
                return await fn(*a, **kw)
            return awrap
        @functools.wraps(fn)
        def wrap(*a, **kw):
            s = summary(kw) if callable(summary) else summary
            check(name, dict(kw), None, s)
            return fn(*a, **kw)
        return wrap
    return deco
