#!/usr/bin/env python3
"""
Ejemplo GENERICO: aplicar la puerta determinista a tools de tu servidor MCP.
Los nombres son neutrales; la decision la pone mcp/policy.json (no el modelo).
"""
from agentboard_gate import gated, GateDenied

@gated("get_item")           # 'get_*' -> allow (no pregunta)
def get_item(id: str):
    return {"id": id}

@gated("write_docs")         # documentacion -> allow
def write_docs(path: str, text: str):
    return {"written": path}

@gated("delete_item")        # sin regla especifica -> default 'ask' (tablero)
def delete_item(id: str, count: int = 1):
    return {"deleted": id}

@gated("purge_cache")        # 'purge_*' -> deny (nunca ejecuta)
def purge_cache():
    return {"purged": True}

# Resumen legible en la tarjeta del tablero (opcional)
@gated("deploy_release", summary=lambda kw: f"Desplegar {kw.get('version')}")
def deploy_release(version: str):
    return {"deployed": version}
