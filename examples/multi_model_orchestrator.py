#!/usr/bin/env python3
"""
multi_model_orchestrator.py — dynamic workflow MULTI-PROVEEDOR sobre el tablero.

Pilota el tablero con CUALQUIER LLM — Claude, Gemini, OpenAI y modelos locales —
sin Claude Code. El orquestador vive aquí (Python plano) y pinta cada agente en el
tablero vía el cliente genérico. Cada agente puede usar un proveedor DISTINTO.

Qué demuestra:
  - MULTI-PROVEEDOR: un rol → un proveedor (providers.py despacha por el nombre del
    modelo). Sin API keys funciona en modo SIMULADO; con keys, llama de verdad.
  - TOKENS REALES: report_usage() manda el uso de cada llamada al tablero → ves los
    tokens y el coste € por agente, por proveedor.
  - COSTE: account_llm() aplica el presupuesto (los locales ~gratis, los fundacionales
    pesan; si se agota, cae en "⚡ Sin presupuesto").
  - PUERTA: las escrituras esperan tu aprobación humana en el tablero.
  - VERIFICACIÓN CRUZADA: el verifier usa un proveedor distinto al implementer.

Antes:  python3 hooks/broker.py     (abre el tablero con el token que imprime)
Ejecuta: python3 examples/multi_model_orchestrator.py
Con proveedores reales, exporta las keys:  ANTHROPIC_API_KEY / OPENAI_API_KEY /
GOOGLE_API_KEY  y para locales AGENT_BOARD_LOCAL_URL (def http://localhost:11434).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "client"))
from agentboard_client import AgentBoard
from providers import generate, provider_of

# ---- ROL -> MODELO: cada tipo de agente usa un proveedor distinto ----
ROLE_MODELS = {
    "explorer":    "gemini-2.0-flash",  # Google · rápido/barato: mapear el terreno
    "auditor":     "mistral-local",     # LOCAL · ~gratis, solo lectura
    "implementer": "gpt-4o",            # OpenAI · potente: escribir el cambio
    "verifier":    "opus",              # Anthropic · juez de OTRA familia que el implementer
    "documenter":  "sonnet",            # Anthropic · buena prosa, escribe SOLO documentación
}
def model_for(role): return ROLE_MODELS.get(role, "opus")

board = AgentBoard()  # AGENT_BOARD_BROKER o :8787

def think(sid, model, prompt, action):
    """Una llamada LLM que se refleja en el tablero: paso + uso real de tokens + coste."""
    board.step(sid, action)
    r = generate(model, prompt)
    board.report_usage(sid, r["model"], r["tokens_in"], r["tokens_out"], action)
    tag = "real" if r["real"] else "sim"
    print(f"    · {provider_of(model):9} {model:16} {r['tokens']:>4} tok [{tag}]  {action}")
    return r

def run_unit(unit):
    impl = model_for("implementer")
    sid = board.start(f"Implementar: {unit}", model=impl, kind="implementer")
    work = think(sid, impl, f"Implementa el cambio para {unit}", "generando el cambio")

    # coste: ¿hay presupuesto para esta llamada del implementer (fundacional)?
    if not board.account_llm(impl, work["tokens"], sid, block_on_ask=False):
        board.step(sid, "sin presupuesto para el modelo fundacional"); board.stop(sid)
        print(f"  {unit}: FRENADO por presupuesto de coste"); return

    # PUERTA: la escritura espera aprobación humana en el tablero
    if board.gate(sid, "Write", {"unit": unit}):
        board.step(sid, "escrito; pasando a verificación")
        # verifier con proveedor DISTINTO (verificación cruzada)
        vmodel = model_for("verifier")
        vsid = board.start(f"Verificar: {unit}", model=vmodel, kind="verifier")
        think(vsid, vmodel, f"¿El trabajo sobre {unit} cumple criterios? Sé adversarial.\n{work['text']}",
              f"juez {provider_of(vmodel)} revisa a {provider_of(impl)}")
        board.stop(vsid); board.stop(sid)
        print(f"  {unit}: impl={impl} ({provider_of(impl)})  verifier={vmodel} ({provider_of(vmodel)}) -> OK")
    else:
        board.stop(sid)
        print(f"  {unit}: escritura DENEGADA en el tablero")

def main():
    # explorer (Google) mapea el terreno
    esid = board.start("Mapear arquitectura y unidades", model=model_for("explorer"), kind="explorer")
    think(esid, model_for("explorer"), "Mapea las unidades a migrar", "recorriendo el repo")
    board.stop(esid)
    # auditor (LOCAL, solo lectura) inventaria
    dsid = board.start("Inventariar unidades a migrar", model=model_for("auditor"), kind="auditor")
    think(dsid, model_for("auditor"), "Enumera los módulos", "enumerando módulos")
    board.stop(dsid)

    units = ["modulo_auth", "modulo_pagos", "modulo_reporting"]
    print("Workflow multi-proveedor (abre el tablero para aprobar las escrituras)...")
    for u in units:
        run_unit(u)

    # documenter (Anthropic): escribir docs es 'allow' por política -> no pasa por la puerta
    docsid = board.start("Documentar la migración", model=model_for("documenter"), kind="documenter")
    think(docsid, model_for("documenter"), "Documenta los módulos migrados: " + ", ".join(units),
          "redactando CHANGELOG y docs")
    board.stop(docsid)
    print("Workflow terminado. Revisa tokens y coste por proveedor en el tablero.")

if __name__ == "__main__":
    main()
