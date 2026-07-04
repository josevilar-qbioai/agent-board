#!/usr/bin/env python3
"""
test_quota.py — pruebas e2e de la contabilidad agregada (ADR-0008) contra el broker.

Arranca un broker con una policy.json temporal que define quotas estrechas y
comprueba, via /api/account, que:
  1. acumular hasta el limite permite; pasarse deniega (troceo, #11).
  2. el bloque grande (count alto de una vez) tambien se caza.
  3. cubos por dimension independientes (otro agente no comparte contador).
  4. mode 'check' NO registra; 'commit' registra solo si allow; 'force' registra siempre.
  5. on_exceed 'ask' devuelve 'ask' en vez de 'deny'.
  6. la ventana deslizante libera cuota al caducar.

Ejecuta:  python3 tests/test_quota.py
"""
import os, sys, json, time, socket, subprocess, urllib.request, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEST_POLICY = {
    "default": "ask", "rules": [],
    "quotas": [
        {"name": "del", "tool": "*delete*", "key": ["agent"], "window": 2,
         "limit": 3, "amount_field": "count", "on_exceed": "deny"},
        {"name": "dep", "tool": "*deploy*", "key": ["workflow"], "window": 3600,
         "limit": 2, "on_exceed": "ask"},
    ],
}


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def post(base, path, payload):
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=4) as r:
        return json.loads(r.read() or b"{}")


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=4) as r:
        return json.loads(r.read() or b"{}")


def account(base, tool, payload, agent="", workflow="", mode="commit"):
    return post(base, "/api/account", {"tool": tool, "payload": payload,
                                       "ctx": {"agent": agent, "workflow": workflow}, "mode": mode})


def wait_up(base, tries=50):
    for _ in range(tries):
        try:
            get(base, "/api/state"); return True
        except Exception:
            time.sleep(0.1)
    return False


def main():
    port = free_port(); base = f"http://127.0.0.1:{port}"; tmp = tempfile.mkdtemp()
    pol = os.path.join(tmp, "policy.json")
    with open(pol, "w") as f:
        json.dump(TEST_POLICY, f)
    env = dict(os.environ, AGENT_BOARD_PORT=str(port), AGENT_BOARD_OP_TOKEN="tk",
               AGENT_BOARD_STATE=os.path.join(tmp, "state.json"), AGENT_BOARD_POLICY=pol)
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "hooks", "broker.py")],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    failures = []
    def check(name, cond):
        print(("  ok  " if cond else " FAIL ") + name)
        if not cond: failures.append(name)
    try:
        assert wait_up(base), "el broker no arranco"
        TOOL = "mcp__db__delete_rows"

        # 1. acumular 1+1+1 = 3 (limite 3) -> permite; el 4o -> deny
        check("1a 1er borrado allow", account(base, TOOL, {"count": 1}, agent="a1")["decision"] == "allow")
        check("1b 2o borrado allow",  account(base, TOOL, {"count": 1}, agent="a1")["decision"] == "allow")
        check("1c 3er borrado allow", account(base, TOOL, {"count": 1}, agent="a1")["decision"] == "allow")
        r4 = account(base, TOOL, {"count": 1}, agent="a1")
        check("1d 4o borrado deny (troceo cazado)", r4["decision"] == "deny" and not r4["recorded"])

        # 2. bloque grande de una vez supera el limite
        rb = account(base, TOOL, {"count": 9}, agent="b1")
        check("2 bloque grande deny", rb["decision"] == "deny")

        # 3. otro agente no comparte cubo
        check("3 otro agente allow", account(base, TOOL, {"count": 1}, agent="zz")["decision"] == "allow")

        # 4. mode 'check' no registra; 'force' registra aunque exceda
        before = account(base, TOOL, {"count": 1}, agent="a1", mode="check")
        check("4a check sobre a1 sigue deny y no registra", before["decision"] == "deny" and not before["recorded"])
        forced = account(base, TOOL, {"count": 1}, agent="zz", mode="force")
        check("4b force registra aunque la cuota lo permitiese o no", forced["recorded"] is True)

        # 5. on_exceed 'ask': 2 permitidos, el 3o pide aprobacion
        check("5a deploy 1 allow", account(base, "mcp__deploy__prod", {}, workflow="w1")["decision"] == "allow")
        check("5b deploy 2 allow", account(base, "mcp__deploy__prod", {}, workflow="w1")["decision"] == "allow")
        check("5c deploy 3 -> ask", account(base, "mcp__deploy__prod", {}, workflow="w1")["decision"] == "ask")

        # 6. ventana: tras 2s (window=2), a1 vuelve a tener cuota
        time.sleep(2.2)
        check("6 ventana liberada -> allow", account(base, TOOL, {"count": 1}, agent="a1")["decision"] == "allow")

    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()

    print()
    if failures:
        print(f"FALLARON {len(failures)}: {failures}"); sys.exit(1)
    print("TODAS LAS COMPROBACIONES PASARON")


if __name__ == "__main__":
    main()
