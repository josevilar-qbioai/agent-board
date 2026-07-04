#!/usr/bin/env python3
"""
test_binding.py — pruebas e2e del binding de aprobacion (ADR-0007) contra el broker real.

Arranca un broker en un puerto efimero, con estado temporal y token fijo, y comprueba:
  1. req_id NO es adivinable (no secuencial, no entero).
  2. /api/decide exige token de operador.
  3. payload_hash distinto en /api/decide -> 409 (no se aprueba otro contenido).
  4. flujo feliz allow: el agente ve 'allow' y el hash local coincide.
  5. un solo uso + segunda decision sobre el mismo req_id -> 409 (no replay).
  6. deny se propaga como 'deny'.
  7. TTL: una peticion caduca -> 'expired' (no queda 'pending' para siempre).

Ejecuta:  python3 tests/test_binding.py
Sale con codigo 0 si todo pasa.
"""
import os, sys, json, time, socket, subprocess, urllib.request, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "mcp"))
from canonical import op_hash  # la misma fuente que usa el broker

TOKEN = "test-operator-token"


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def post(base, path, payload, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Operator-Token"] = token
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=4) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=4) as r:
        return r.status, json.loads(r.read() or b"{}")


def wait_up(base, tries=50):
    for _ in range(tries):
        try:
            get(base, "/api/state"); return True
        except Exception:
            time.sleep(0.1)
    return False


def main():
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    tmp = tempfile.mkdtemp()
    env = dict(os.environ, AGENT_BOARD_PORT=str(port), AGENT_BOARD_OP_TOKEN=TOKEN,
               AGENT_BOARD_STATE=os.path.join(tmp, "state.json"), AGENT_BOARD_REQUEST_TTL="2")
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "hooks", "broker.py")],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    failures = []
    def check(name, cond):
        print(("  ok  " if cond else " FAIL ") + name)
        if not cond: failures.append(name)
    try:
        assert wait_up(base), "el broker no arranco"

        # --- crea una peticion 'ask' ---
        tool, payload = "Write", {"path": "secrets.env", "content": "x"}
        _, r = post(base, "/api/request", {"session_id": "s1", "tool_name": tool, "tool_input": payload})
        rid, ph = r.get("req_id"), r.get("payload_hash")

        check("1a req_id presente", bool(rid))
        check("1b req_id NO es entero/secuencial", not str(rid).isdigit())
        check("1c payload_hash coincide con canonical.op_hash", ph == op_hash(tool, payload))

        # --- /api/decide exige token ---
        code, _ = post(base, "/api/decide", {"req_id": rid, "decision": "allow"})
        check("2 decide sin token -> 403", code == 403)

        # --- hash equivocado -> 409 (no aprueba otro contenido) ---
        code, _ = post(base, "/api/decide",
                       {"req_id": rid, "payload_hash": "deadbeef", "decision": "allow"}, token=TOKEN)
        check("3 payload_hash erroneo -> 409", code == 409)

        # --- flujo feliz allow con hash correcto ---
        code, _ = post(base, "/api/decide",
                       {"req_id": rid, "payload_hash": ph, "decision": "allow"}, token=TOKEN)
        check("4a decide allow correcto -> 200", code == 200)
        _, st = get(base, f"/api/decision?req_id={rid}")
        check("4b el agente ve 'allow'", st.get("status") == "allow")
        check("4c hash local coincide (binding)", op_hash(tool, payload) == ph)

        # --- no replay: segunda decision sobre el mismo req_id -> 409 ---
        code, _ = post(base, "/api/decide",
                       {"req_id": rid, "payload_hash": ph, "decision": "deny"}, token=TOKEN)
        check("5 segunda decision (replay) -> 409", code == 409)

        # --- deny se propaga ---
        _, r2 = post(base, "/api/request", {"session_id": "s2", "tool_name": tool, "tool_input": payload})
        rid2, ph2 = r2["req_id"], r2["payload_hash"]
        post(base, "/api/decide", {"req_id": rid2, "payload_hash": ph2, "decision": "deny"}, token=TOKEN)
        _, st2 = get(base, f"/api/decision?req_id={rid2}")
        check("6 deny se propaga", st2.get("status") == "deny")

        # --- TTL: peticion sin resolver caduca (TTL=2s) ---
        _, r3 = post(base, "/api/request", {"session_id": "s3", "tool_name": tool, "tool_input": payload})
        rid3 = r3["req_id"]
        time.sleep(2.3)
        _, st3 = get(base, f"/api/decision?req_id={rid3}")
        check("7a peticion caducada -> 'expired'", st3.get("status") == "expired")
        code, _ = post(base, "/api/decide",
                       {"req_id": rid3, "payload_hash": r3["payload_hash"], "decision": "allow"}, token=TOKEN)
        check("7b no se puede aprobar una caducada -> 409", code == 409)

    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()

    print()
    if failures:
        print(f"FALLARON {len(failures)} comprobaciones: {failures}")
        sys.exit(1)
    print("TODAS LAS COMPROBACIONES PASARON")


if __name__ == "__main__":
    main()
