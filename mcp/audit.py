#!/usr/bin/env python3
"""
audit.py — auditoria append-only con hash-chain (ADR-0006).

Cada entrada encadena con la anterior: entry_hash = sha256(prev_hash || entrada).
Alterar o borrar cualquier linea rompe la cadena a partir de ahi -> la auditoria es
*tamper-evident*: se puede demostrar integridad y detectar manipulacion.

Sin dependencias (stdlib). El append es seguro entre procesos via flock (POSIX): el
gate (dentro del server MCP) y el broker pueden escribir en la MISMA cadena sin
corromper el encadenado, porque cada append re-lee el ultimo hash bajo el lock.

CLI:
    python3 mcp/audit.py verify [ruta]      # verifica la cadena
    python3 mcp/audit.py tail   [ruta] [n]  # ultimas n entradas legibles
"""
import os
import sys
import json
import time
import hashlib

try:
    from canonical import canonical_json
except Exception:
    def canonical_json(obj):
        return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, default=str)

try:
    import fcntl  # POSIX: lock entre procesos
except Exception:
    fcntl = None

GENESIS = "GENESIS"
DEFAULT_PATH = os.environ.get("AGENT_BOARD_AUDIT",
                              os.path.join(os.path.dirname(__file__), "gate-audit.log"))


def _entry_hash(prev_hash, entry_wo_hash):
    return hashlib.sha256((prev_hash + canonical_json(entry_wo_hash)).encode("utf-8")).hexdigest()


def _last_hash(path):
    """Lee el entry_hash de la ultima linea no vacia. GENESIS si el fichero esta vacio."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            if end == 0:
                return GENESIS
            buf = b""
            pos = end
            # retrocede en bloques hasta encontrar un salto de linea
            while pos > 0:
                step = min(1024, pos)
                pos -= step
                f.seek(pos)
                buf = f.read(step) + buf
                lines = buf.split(b"\n")
                nonempty = [ln for ln in lines if ln.strip()]
                if len(nonempty) >= 1 and (pos == 0 or len(lines) > 1):
                    last = nonempty[-1]
                    try:
                        return json.loads(last).get("hash", GENESIS)
                    except Exception:
                        return GENESIS
            return GENESIS
    except FileNotFoundError:
        return GENESIS


def append(entry, path=None):
    """Añade una entrada a la cadena. Devuelve el entry_hash. Serializado por flock."""
    path = path or DEFAULT_PATH
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a+") as f:
            if fcntl:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                prev = _last_hash(path)
                rec = dict(entry)
                rec.setdefault("ts", int(time.time()))
                rec["prev"] = prev
                rec.pop("hash", None)
                h = _entry_hash(prev, rec)
                rec["hash"] = h
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
                return h
            finally:
                if fcntl:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception:
        return None  # la auditoria nunca debe tumbar la operacion


def verify(path=None):
    """Recorre la cadena. Devuelve (ok: bool, problema: dict|None).
    problema = {line, reason} en el primer punto de ruptura."""
    path = path or DEFAULT_PATH
    prev = GENESIS
    n = 0
    try:
        with open(path) as f:
            for i, line in enumerate(f, 1):
                if not line.strip():
                    continue
                n += 1
                try:
                    rec = json.loads(line)
                except Exception:
                    return False, {"line": i, "reason": "JSON ilegible"}
                if rec.get("prev") != prev:
                    return False, {"line": i, "reason": "prev_hash no encadena"}
                stored = rec.get("hash")
                wo = {k: v for k, v in rec.items() if k != "hash"}
                if _entry_hash(prev, wo) != stored:
                    return False, {"line": i, "reason": "entry_hash no coincide (entrada alterada)"}
                prev = stored
    except FileNotFoundError:
        return True, None  # cadena vacia = integra
    return True, None


def _cli(argv):
    cmd = argv[1] if len(argv) > 1 else "verify"
    path = argv[2] if len(argv) > 2 else DEFAULT_PATH
    if cmd == "verify":
        ok, prob = verify(path)
        if ok:
            print(f"cadena INTEGRA: {path}")
            return 0
        print(f"cadena ROTA en linea {prob['line']}: {prob['reason']}")
        return 1
    if cmd == "tail":
        n = int(argv[3]) if len(argv) > 3 else 10
        try:
            lines = [l for l in open(path) if l.strip()][-n:]
        except FileNotFoundError:
            lines = []
        for l in lines:
            r = json.loads(l)
            print(f"{r.get('ts')}  {r.get('decision','?'):5}  {r.get('source','?'):12}  "
                  f"{r.get('tool','?')}  {r.get('hash','')[:12]}")
        return 0
    print("uso: audit.py [verify|tail] [ruta] [n]")
    return 2


if __name__ == "__main__":
    # auto-comprobacion ademas de servir de CLI
    if len(sys.argv) == 1:
        import tempfile
        p = os.path.join(tempfile.mkdtemp(), "chain.log")
        append({"tool": "Write", "decision": "allow", "source": "policy"}, p)
        append({"tool": "deploy", "decision": "deny", "source": "quota"}, p)
        ok, prob = verify(p)
        assert ok, prob
        # manipular una linea rompe la cadena
        lines = open(p).read().splitlines()
        rec = json.loads(lines[0]); rec["decision"] = "deny"
        lines[0] = json.dumps(rec)
        open(p, "w").write("\n".join(lines) + "\n")
        ok2, prob2 = verify(p)
        assert not ok2 and prob2["line"] == 1, prob2
        print("audit OK (cadena integra y manipulacion detectada)")
    else:
        sys.exit(_cli(sys.argv))
