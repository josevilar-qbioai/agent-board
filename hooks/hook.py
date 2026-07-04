#!/usr/bin/env python3
"""
hook.py — hook unificado del ciclo de vida + PUERTA (gobernada por policy.json).

Uso (desde hooks.json):  python3 hook.py <Evento>
  SessionStart / Stop  -> proyecta el ciclo de vida (crea/cierra tarjeta)
  PreToolUse           -> consulta la MISMA politica que el gate MCP y aplica
                          allow / deny / ask. Asi gobierna tambien los MCP de
                          terceros que no puedes modificar (tool = mcp__srv__op).

Decision por politica (mcp/policy.json), compartida con la puerta del servidor:
  allow -> permissionDecision allow (no molesta)
  deny  -> permissionDecision deny
  ask   -> tarjeta en el tablero y espera Aprobar/Denegar
  (ninguna regla casa) -> no interfiere; deja el flujo normal de Claude Code

Si no hay policy.json (o falta el modulo), cae a una lista simple por env:
  AGENT_BOARD_GATED  (def "Write,Edit,Bash")

Fallback seguro: sin broker o por timeout en un 'ask' -> prompt nativo (no auto-aprueba).
Config: AGENT_BOARD_BROKER, AGENT_BOARD_GATE_TIMEOUT, MCP_USER_ROLE.
"""
import sys, os, json, time, urllib.request

BROKER = os.environ.get("AGENT_BOARD_BROKER", "http://127.0.0.1:8787").rstrip("/")
GATE_TIMEOUT = int(os.environ.get("AGENT_BOARD_GATE_TIMEOUT", "300"))
ROLE = os.environ.get("MCP_USER_ROLE")
STATE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "board", "board-state.json"))

# politica compartida con la puerta MCP
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp"))
    from agentboard_gate import decide_rule, _load_policy
    HAVE_POLICY = True
except Exception:
    HAVE_POLICY = False
    GATED = set(t.strip() for t in os.environ.get("AGENT_BOARD_GATED", "Write,Edit,Bash").split(",") if t.strip())

# quota agregada (ADR-0008): determinar localmente si la tool esta sujeta a cuota
try:
    from quota import match_quotas as _match_quotas
except Exception:
    _match_quotas = None

# hash de operacion (ADR-0007): re-verificacion en el punto de efecto
try:
    from canonical import op_hash
except Exception:
    import hashlib
    def op_hash(tool, payload=None):
        blob = json.dumps({"tool": tool or "", "payload": payload or {}},
                          sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

def _post(path, payload, t=4):
    req = urllib.request.Request(BROKER + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=t) as r:
        return json.loads(r.read() or b"{}")

def _get(path, t=4):
    with urllib.request.urlopen(BROKER + path, timeout=t) as r:
        return json.loads(r.read() or b"{}")

def read_stdin():
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    try: return json.loads(raw) if raw.strip() else {}
    except Exception: return {}

def emit(obj): print(json.dumps(obj))

def file_fallback(event, sid, tool, prompt):
    try:
        try:
            with open(STATE_FILE) as f: s = json.load(f)
        except Exception:
            s = {"agents": [], "stats": {"spawned": 0, "done": 0, "failed": 0, "tokens": 0},
                 "archived": 0, "nextId": 1, "order": 0}
        card = next((a for a in s["agents"] if a.get("sid") == sid), None)
        if event == "SessionStart" and not card:
            s["agents"].append({"sid": sid, "id": s["nextId"], "order": s["order"], "kind": "implementer",
                "col": "working", "job": (prompt or "sesion " + sid[:6])[:90], "model": "opus",
                "wt": "wt/" + sid[:6], "tokens": 0, "target": 20000, "elapsed": 0,
                "mut": False, "parentId": None, "last": "sesion iniciada", "verdict": None})
            s["nextId"] += 1; s["order"] += 1; s["stats"]["spawned"] += 1
        elif event == "PreToolUse" and card:
            card["last"] = "tool: " + tool; card["tokens"] += 600
        elif event == "Stop" and card:
            card["col"] = "done"; card["verdict"] = "ok"; card["last"] = "completado"
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w") as f: json.dump(s, f)
        os.replace(tmp, STATE_FILE)
    except Exception:
        pass

def gate_via_board(sid, tool, tool_input):
    """ask -> tarjeta + espera. Devuelve el JSON del hook.
    La aprobacion se liga al hash del payload (ADR-0007): si el contenido que se va a
    ejecutar no coincide con el aprobado, se deniega (anti-replay/TOCTOU)."""
    try:
        resp = _post("/api/request", {"session_id": sid, "tool_name": tool,
                                      "summary": "Permiso: " + tool, "tool_input": tool_input})
        rid = resp.get("req_id")
        expected_hash = resp.get("payload_hash")
        deadline = time.time() + GATE_TIMEOUT
        decision = "pending"
        while time.time() < deadline:
            time.sleep(1.5)
            decision = _get(f"/api/decision?req_id={rid}").get("status", "pending")
            if decision in ("allow", "deny"): break
        if decision == "allow":
            # re-verificacion en el punto de efecto: el contenido debe ser EXACTAMENTE
            # el aprobado. Si difiere (manipulado tras aprobar), denegar.
            if expected_hash and op_hash(tool, tool_input) != expected_hash:
                return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": "Payload cambiado tras la aprobacion (binding roto)"}}
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                    "permissionDecision": "allow", "permissionDecisionReason": "Aprobado en el tablero"}}
        if decision == "deny":
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                    "permissionDecision": "deny", "permissionDecisionReason": "Denegado en el tablero"}}
        return {}   # timeout/expired/unknown -> prompt nativo (no auto-aprueba)
    except Exception:
        return {}   # broker caido -> prompt nativo

def _allow(reason):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "permissionDecision": "allow", "permissionDecisionReason": reason}}

def _deny(reason):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "permissionDecision": "deny", "permissionDecisionReason": reason}}

def _quota_applies(tool):
    if not _match_quotas:
        return False
    try:
        return bool(_match_quotas(_load_policy().get("quotas", []) or [], tool))
    except Exception:
        return False

def _account(sid, tool, tool_input, mode):
    ctx = {"agent": sid, "workflow": os.environ.get("AGENT_BOARD_WORKFLOW", "")}
    return _post("/api/account", {"tool": tool, "payload": tool_input, "ctx": ctx, "mode": mode})

def apply_quota_on_allow(sid, tool, tool_input, broker_up):
    """Politica permite. Si la tool esta sujeta a cuota (ADR-0008), aplica el limite
    agregado antes de dejar pasar. Cierra el troceo (#11) en el camino 'allow'."""
    if not _quota_applies(tool):
        return _allow("Permitido por politica")
    if not broker_up:
        # hay cuota pero no podemos contabilizar -> fail-closed (salvo FAIL_OPEN)
        if os.environ.get("AGENT_BOARD_FAIL_OPEN", "0") == "1":
            return _allow("Permitido (cuota no verificable; fail-open)")
        return _deny("Cuota no verificable (broker caido; fail-closed)")
    try:
        q = _account(sid, tool, tool_input, "commit")
    except Exception:
        if os.environ.get("AGENT_BOARD_FAIL_OPEN", "0") == "1":
            return _allow("Permitido (cuota no verificable; fail-open)")
        return _deny("Cuota no verificable (broker caido; fail-closed)")
    qd = q.get("decision", "allow")
    if qd == "deny":
        return _deny("Cuota excedida")
    if qd == "ask":
        out = gate_via_board(sid, tool, tool_input)
        if out.get("hookSpecificOutput", {}).get("permissionDecision") == "allow":
            try: _account(sid, tool, tool_input, "force")   # cuenta lo aprobado
            except Exception: pass
        return out
    return _allow("Permitido por politica")   # 'allow' ya registrado por 'commit'

def main():
    event = sys.argv[1] if len(sys.argv) > 1 else "Unknown"
    d = read_stdin()
    sid = str(d.get("session_id") or "default")
    tool = d.get("tool_name") or ""
    tool_input = d.get("tool_input") or {}
    prompt = d.get("prompt") or d.get("cwd") or ""

    broker_up = True
    try:
        _post("/api/event", {"event": event, "session_id": sid, "tool_name": tool, "prompt": prompt})
    except Exception:
        broker_up = False
        file_fallback(event, sid, tool, prompt)

    if event != "PreToolUse":
        emit({}); return

    # --- decision de la puerta ---
    if HAVE_POLICY:
        decision = decide_rule(tool, tool_input, ROLE)
        if decision is None:
            emit({}); return                               # tool no contemplada -> no interferir
        if decision == "allow":
            emit(apply_quota_on_allow(sid, tool, tool_input, broker_up)); return
        if decision == "deny":
            emit({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                  "permissionDecision": "deny", "permissionDecisionReason": "Denegado por politica"}}); return
        # ask
        emit({} if not broker_up else gate_via_board(sid, tool, tool_input)); return
    else:
        if tool in GATED:
            emit({} if not broker_up else gate_via_board(sid, tool, tool_input)); return
        emit({}); return

if __name__ == "__main__":
    main()
