#!/usr/bin/env python3
"""
test_providers.py — capa multi-proveedor + reporte de tokens reales al tablero.

Comprueba:
  1. provider_of() enruta cada modelo al proveedor correcto.
  2. generate() en modo simulado (sin keys) devuelve texto y tokens > 0.
  3. e2e: report_usage() incrementa los tokens de la tarjeta en el broker y fija el modelo.

Ejecuta:  python3 tests/test_providers.py
"""
import os, sys, json, time, socket, subprocess, tempfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "client"))
import providers
from agentboard_client import AgentBoard

failures = []
def check(name, cond):
    print(("  ok  " if cond else " FAIL ") + name)
    if not cond: failures.append(name)

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def get(base, path):
    with urllib.request.urlopen(base + path, timeout=4) as r:
        return json.loads(r.read() or b"{}")


def unit():
    check("1a gpt-4o -> openai", providers.provider_of("gpt-4o") == "openai")
    check("1b gemini-2.0-flash -> google", providers.provider_of("gemini-2.0-flash") == "google")
    check("1c opus -> anthropic", providers.provider_of("opus") == "anthropic")
    check("1d mistral-local -> local", providers.provider_of("mistral-local") == "local")
    for m in ["opus", "gpt-4o", "gemini-2.0-flash", "mistral-local"]:
        r = providers.generate(m, "hola resume esto")
        check(f"2 generate({m}) tokens>0 y texto", r["tokens"] > 0 and bool(r["text"]))


def e2e():
    port = free_port(); base = f"http://127.0.0.1:{port}"; tmp = tempfile.mkdtemp()
    env = dict(os.environ, AGENT_BOARD_PORT=str(port), AGENT_BOARD_OP_TOKEN="tk",
               AGENT_BOARD_STATE=os.path.join(tmp, "s.json"))
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "hooks", "broker.py")],
                            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try: get(base, "/api/state"); break
            except Exception: time.sleep(0.1)
        board = AgentBoard(broker=base)
        sid = board.start("Agente OpenAI", model="gpt-4o", kind="implementer")
        board.report_usage(sid, "gpt-4o", 1200, 800, "generó respuesta")   # 2000 tok
        time.sleep(0.2)
        card = next((a for a in get(base, "/api/state")["agents"] if a.get("sid") == sid), None)
        check("3a la tarjeta refleja 2000 tokens reales", bool(card) and card.get("tokens") == 2000)
        check("3b el modelo quedó fijado", bool(card) and card.get("model") == "gpt-4o")
        # segundo reporte acumula
        board.report_usage(sid, "gpt-4o", 0, 500, "más tokens")
        time.sleep(0.2)
        card = next((a for a in get(base, "/api/state")["agents"] if a.get("sid") == sid), None)
        check("3c los tokens se acumulan (2500)", bool(card) and card.get("tokens") == 2500)
    finally:
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()


def main():
    unit(); e2e()
    print()
    if failures:
        print(f"FALLARON {len(failures)}: {failures}"); sys.exit(1)
    print("TODAS LAS COMPROBACIONES PASARON")


if __name__ == "__main__":
    main()
