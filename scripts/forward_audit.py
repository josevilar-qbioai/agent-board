#!/usr/bin/env python3
"""Reenvía la cadena de auditoría de una UNIDAD hacia un log CENTRAL (federación).

Las cadenas NO se fusionan: cada unidad conserva su propia cadena hash-chain intacta y
verificable. El "central" es simplemente una carpeta con un fichero por unidad (o un
colector HTTP). Luego `analyze_decisions.py <carpeta>` agrega el conjunto.

Dos modos:

  --to-dir DIR   Copia el log local a DIR/<unidad>.log (cadena intacta, re-verificable).
                 Idempotente: vuelve a ejecutarlo (o por cron) y refleja el estado actual.

  --to-url URL   POST incremental de las líneas NUEVAS (ndjson) a un colector HTTP.
                 Guarda el offset en <log>.fwd-offset para no reenviar lo ya enviado.

El nombre de la unidad = --name, o $AGENT_BOARD_DEPLOYMENT, o el hostname.

Uso:
  python3 scripts/forward_audit.py --to-dir /central/logs [log]
  python3 scripts/forward_audit.py --to-url https://host/ingest [log]
  python3 scripts/forward_audit.py --to-dir /central/logs --name genomica-lab
"""
import os
import sys
import socket
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.environ.get("AGENT_BOARD_AUDIT",
                         os.path.join(HERE, "..", "mcp", "gate-audit.log"))
sys.path.insert(0, os.path.join(HERE, "..", "mcp"))
try:
    import audit as _audit
except Exception:
    _audit = None


def unit_name(explicit=None):
    name = explicit or os.environ.get("AGENT_BOARD_DEPLOYMENT") or socket.gethostname()
    # nombre de fichero seguro
    return "".join(c if (c.isalnum() or c in "-_.") else "-" for c in name).strip("-") or "unit"


def to_dir(log, dest_dir, name):
    if _audit:
        ok, msg = _audit.verify(log)
        print("Integridad de la cadena local:", "OK ✓" if ok else "ROTA ✗ (%s)" % msg)
        if not ok:
            print("Aviso: la cadena local no verifica; se copia igualmente para inspección.")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, name + ".log")
    shutil.copy2(log, dest)
    n = sum(1 for _ in open(dest, encoding="utf-8"))
    print("✓ %s  →  %s  (%d entradas)" % (os.path.basename(log), dest, n))


def to_url(log, url):
    import urllib.request
    off_path = log + ".fwd-offset"
    start = 0
    try:
        start = int(open(off_path).read().strip() or "0")
    except Exception:
        start = 0
    size = os.path.getsize(log)
    if start > size:                       # el log rotó/encogió: reenvía desde el principio
        start = 0
    with open(log, "rb") as f:
        f.seek(start)
        chunk = f.read()
        new_off = f.tell()
    lines = [l for l in chunk.splitlines() if l.strip()]
    if not lines:
        print("Nada nuevo que reenviar (offset %d/%d)." % (start, size))
        return
    body = b"\n".join(lines) + b"\n"
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/x-ndjson"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.getcode()
    except Exception as e:
        print("Error al enviar a %s: %s (offset NO avanzado, se reintenta luego)" % (url, e))
        sys.exit(1)
    with open(off_path, "w") as f:
        f.write(str(new_off))
    print("✓ Enviadas %d líneas nuevas a %s (HTTP %s). Offset %d→%d."
          % (len(lines), url, code, start, new_off))


def main():
    args = sys.argv[1:]
    dest_dir = url = name = None
    rest = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--to-dir" and i + 1 < len(args):
            dest_dir = args[i + 1]; i += 2; continue
        if a == "--to-url" and i + 1 < len(args):
            url = args[i + 1]; i += 2; continue
        if a == "--name" and i + 1 < len(args):
            name = args[i + 1]; i += 2; continue
        rest.append(a); i += 1

    log = rest[0] if rest else DEFAULT
    if not os.path.exists(log):
        print("No existe el log local:", log)
        sys.exit(1)
    if not dest_dir and not url:
        print("Indica un destino: --to-dir DIR  o  --to-url URL")
        sys.exit(2)

    who = unit_name(name)
    if dest_dir:
        to_dir(log, dest_dir, who)
    if url:
        to_url(log, url)


if __name__ == "__main__":
    main()
