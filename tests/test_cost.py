#!/usr/bin/env python3
"""
test_cost.py — coste por modelo (cost.py) + cuota de COSTE en el broker (ADR-0008 ext).

Comprueba:
  1. cost.py: € por (modelo, tokens), clase, default, match por subcadena.
  2. e2e: una cuota de coste con match_class='foundational' suma € de modelos caros y
     pide aprobación al exceder; los modelos LOCALES no consumen presupuesto.

Ejecuta:  python3 tests/test_cost.py
"""
import os, sys, json, time, socket, subprocess, tempfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "mcp"))
sys.path.insert(0, os.path.join(ROOT, "client"))
import cost
from agentboard_client import AgentBoard

failures = []
def check(name, cond):
    print(("  ok  " if cond else " FAIL ") + name)
    if not cond: failures.append(name)


def unit():
    P = cost.load_prices()
    check("1a opus 20k = 0.30€", abs(cost.cost_eur("opus", 20000, P) - 0.30) < 1e-9)
    check("1b local = 0€",       cost.cost_eur("mistral-local", 1_000_000, P) == 0.0)
    check("1c clase local",      cost.model_class("llama-local", P) == "local")
    check("1d clase foundational por subcadena", cost.model_class("gpt-4o-mini", P) == "foundational")
    check("1e default desconocido = 5€/Mtok", abs(cost.cost_eur("xxx", 1_000_000, P) - 5.0) < 1e-9)


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

def account(base, model, tokens, workflow="w1", mode="commit"):
    return post(base, "/api/account", {"tool": "llm_call", "payload": {},
                "ctx": {"workflow": workflow, "model": model, "tokens": tokens}, "mode": mode})


def e2e():
    # policy con una cuota de coste: max 1.0€ fundacional por ventana
    pol = {"default": "ask", "rules": [],
           "quotas": [{"name": "coste-found", "tool": "*", "key": ["workflow"], "window": 3600,
                       "limit": 1.0, "amount_field": "cost_eur", "match_class": "foundational",
                       "on_exceed": "ask"}]}
    port = free_port(); base = f"http://127.0.0.1:{port}"; tmp = tempfile.mkdtemp()
    pp = os.path.join(tmp, "policy.json"); json.dump(pol, open(pp, "w"))
    env = dict(os.environ, AGENT_BOARD_PORT=str(port), AGENT_BOARD_OP_TOKEN="tk",
               AGENT_BOARD_STATE=os.path.join(tmp, "s.json"), AGENT_BOARD_POLICY=pp)
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "hooks", "broker.py")],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try: get(base, "/api/state"); break
            except Exception: time.sleep(0.1)
        # opus a 15€/Mtok: 40k tok = 0.60€. Dos van bien (1.20€ > 1.0 -> el 2º excede)
        check("2a opus 40k (0.60€) allow", account(base, "opus", 40000)["decision"] == "allow")
        check("2b opus 40k de nuevo (acum 1.20€>1.0) -> ask", account(base, "opus", 40000)["decision"] == "ask")
        # un modelo LOCAL no consume presupuesto fundacional: aunque sean muchos tokens, allow
        check("2c local 5M tokens (0€) allow", account(base, "mistral-local", 5_000_000)["decision"] == "allow")
        # otro workflow tiene su propio cubo
        check("2d otro workflow opus 40k allow", account(base, "opus", 40000, workflow="w2")["decision"] == "allow")

        # 3. helper del cliente generico (enforcement de una linea)
        board = AgentBoard(broker=base, gate_timeout=3)
        check("3a client opus 0.60€ -> True", board.account_llm("opus", 40000, workflow="wc") is True)
        check("3b client opus de nuevo (>1.0) sin bloquear -> False",
              board.account_llm("opus", 40000, workflow="wc", block_on_ask=False) is False)
        check("3c client local 5M tok -> True", board.account_llm("mistral-local", 5_000_000, workflow="wc") is True)
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()


def cap_test():
    """Estado 'capped': una cuota de coste DENY marca la tarjeta del agente; al
    permitir de nuevo, se libera (col vuelve a working)."""
    pol = {"default": "ask", "rules": [],
           "quotas": [{"name": "coste-deny", "tool": "*", "key": ["agent"], "window": 3600,
                       "limit": 0.5, "amount_field": "cost_eur", "match_class": "foundational",
                       "on_exceed": "deny"}]}
    port = free_port(); base = f"http://127.0.0.1:{port}"; tmp = tempfile.mkdtemp()
    pp = os.path.join(tmp, "policy.json"); json.dump(pol, open(pp, "w"))
    env = dict(os.environ, AGENT_BOARD_PORT=str(port), AGENT_BOARD_OP_TOKEN="tk",
               AGENT_BOARD_STATE=os.path.join(tmp, "s.json"), AGENT_BOARD_POLICY=pp)
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "hooks", "broker.py")],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    def card(sid):
        st = get(base, "/api/state")
        return next((a for a in st["agents"] if a.get("sid") == sid), None)
    try:
        for _ in range(50):
            try: get(base, "/api/state"); break
            except Exception: time.sleep(0.1)
        sid = "ag1"
        post(base, "/api/event", {"event": "SessionStart", "session_id": sid, "prompt": "tarea cara", "model": "opus"})
        # opus 40k = 0.60€ > 0.5 limite -> deny -> tarjeta capped
        account(base, "opus", 40000, workflow=sid)  # ctx.agent? account usa workflow; necesito agent=sid
        post(base, "/api/account", {"tool": "llm_call", "payload": {},
             "ctx": {"agent": sid, "model": "opus", "tokens": 40000}, "mode": "commit"})
        c = card(sid)
        check("4a tarjeta marcada capped", bool(c) and c.get("col") == "capped" and c.get("capped") is True)
        # un modelo local (0€) permite -> libera
        post(base, "/api/account", {"tool": "llm_call", "payload": {},
             "ctx": {"agent": sid, "model": "mistral-local", "tokens": 5_000_000}, "mode": "commit"})
        c = card(sid)
        check("4b capped liberado al permitir", bool(c) and c.get("col") == "working" and not c.get("capped"))
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()


def main():
    unit(); e2e(); cap_test()
    print()
    if failures:
        print(f"FALLARON {len(failures)}: {failures}"); sys.exit(1)
    print("TODAS LAS COMPROBACIONES PASARON")


if __name__ == "__main__":
    main()
