#!/usr/bin/env python3
"""
canonical.py — fuente UNICA del hash canonico de una operacion (tool + payload).

ADR-0007 (binding de aprobacion al payload). Una aprobacion vale para EXACTAMENTE
un contenido. Para eso todos los puntos del sistema (broker, hook, gate, cliente)
deben calcular el MISMO hash del mismo payload. Este modulo es esa unica fuente.

Sin dependencias: solo stdlib. Importable desde cualquier carpeta del repo.

    from canonical import op_hash
    h = op_hash("Write", {"path": "a.py", "content": "x"})   # sha256 hex, estable
"""
import json
import hashlib


def canonical_json(obj) -> str:
    """Serializacion estable: claves ordenadas, sin espacios, unicode preservado.
    Mismo objeto logico -> misma cadena -> mismo hash, en cualquier proceso."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def op_hash(tool, payload=None) -> str:
    """sha256 hex de {tool, payload} canonicalizado. Es el identificador de
    contenido al que se liga una aprobacion."""
    blob = canonical_json({"tool": tool or "", "payload": payload or {}})
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    # auto-comprobacion rapida: el orden de las claves no cambia el hash
    a = op_hash("Write", {"path": "a.py", "n": 1})
    b = op_hash("Write", {"n": 1, "path": "a.py"})
    assert a == b, "canonicalizacion inestable"
    assert op_hash("Write", {"path": "a.py"}) != op_hash("Edit", {"path": "a.py"})
    print("canonical OK", a[:16])
