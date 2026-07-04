#!/usr/bin/env python3
"""
test_audit.py — pruebas de la auditoria hash-chain (ADR-0006).

Comprueba, a nivel de modulo (rapido) y e2e contra el broker:
  1. una cadena recien escrita verifica OK.
  2. alterar una entrada rompe la cadena en esa linea.
  3. borrar una entrada intermedia rompe la cadena.
  4. e2e: una decision del operador deja una entrada encadenada y verificable.

Ejecuta:  python3 tests/test_audit.py
"""
import os, sys, json, time, socket, subprocess, tempfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "mcp"))
import audit

failures = []
def check(name, cond):
    print(("  ok  " if cond else " FAIL ") + name)
    if not cond: failures.append(name)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def post(base, path, payload, token=None):
    h = {"Content-Type": "application/json"}
    if token: h["X-Operator-Token"] = token
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode(), headers=h)
    try:
        with urllib.request.urlopen(req, timeout=4) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, {}


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=4) as r:
        return json.loads(r.read() or b"{}")


def unit_tests():
    p = os.path.join(tempfile.mkdtemp(), "chain.log")
    for i in range(5):
        audit.append({"tool": f"t{i}", "decision": "allow", "source": "policy"}, p)
    ok, prob = audit.verify(p); check("1 cadena nueva integra", ok and prob is None)

    lines = open(p).read().splitlines()
    rec = json.loads(lines[2]); rec["decision"] = "deny"; lines[2] = json.dumps(rec)
    bad = p + ".tamper"; open(bad, "w").write("\n".join(lines) + "\n")
    ok, prob = audit.verify(bad)
    check("2 entrada alterada -> rota en su linea", (not ok) and prob and prob["line"] == 3)

    lines2 = open(p).read().splitlines(); del lines2[2]
    bad2 = p + ".del"; open(bad2, "w").write("\n".join(lines2) + "\n")
    ok, _ = audit.verify(bad2); check("3 entrada borrada -> cadena rota", not ok)


def e2e_test():
    port = free_port(); base = f"http://127.0.0.1:{port}"; tmp = tempfile.mkdtemp()
    auditlog = os.path.join(tmp, "audit.log")
    env = dict(os.environ, AGENT_BOARD_PORT=str(port), AGENT_BOARD_OP_TOKEN="tk",
               AGENT_BOARD_STATE=os.path.join(tmp, "s.json"), AGENT_BOARD_AUDIT=auditlog)
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "hooks", "broker.py")],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try: get(base, "/api/state"); break
            except Exception: time.sleep(0.1)
        _, r = post(base, "/api/request",
                    {"session_id": "s1", "tool_name": "Write", "tool_input": {"path": "a"}})
        rid, ph = r["req_id"], r["payload_hash"]
        code, _ = post(base, "/api/decide",
                       {"req_id": rid, "payload_hash": ph, "decision": "allow"}, token="tk")
        check("4a decide allow -> 200", code == 200)
        time.sleep(0.2)
        ok, prob = audit.verify(auditlog)
        check("4b la cadena del broker verifica", ok and prob is None)
        entries = [json.loads(l) for l in open(auditlog) if l.strip()]
        check("4c hay una entrada del operador ligada al payload_hash",
              any(e.get("source") == "operator" and e.get("payload_hash") == ph for e in entries))
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()


def main():
    unit_tests()
    e2e_test()
    print()
    if failures:
        print(f"FALLARON {len(failures)}: {failures}"); sys.exit(1)
    print("TODAS LAS COMPROBACIONES PASARON")


if __name__ == "__main__":
    main()
