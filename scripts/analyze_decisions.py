#!/usr/bin/env python3
"""Analiza la cadena de auditoría de agent-board y agrega las DECISIONES HUMANAS por
unidad/departamento, despliegue (tenant), agente, modelo, tool y coste; exporta el
dataset {contexto, decisión_humana} en JSONL para evals / captura de conocimiento.

Federación → central: acepta UN log, VARIOS logs o una CARPETA de logs (un fichero por
unidad). Verifica la integridad de CADA cadena por separado (no se fusionan: cada unidad
conserva su prueba) y agrega el conjunto de forma central.

Uso:
  python3 scripts/analyze_decisions.py [log|carpeta ...] [--jsonl salida.jsonl] [--all]

  sin args        usa $AGENT_BOARD_AUDIT o mcp/gate-audit.log
  <carpeta>       agrega todos los *.log de la carpeta (modo central)
  <log> <log> …   agrega varios logs concretos
  --jsonl FILE    exporta el dataset {contexto, decisión} (una línea por decisión humana)
  --all           incluye también decisiones automáticas (policy/quota), no solo humanas
"""
import os
import sys
import json
import glob
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.environ.get("AGENT_BOARD_AUDIT",
                         os.path.join(HERE, "..", "mcp", "gate-audit.log"))
sys.path.insert(0, os.path.join(HERE, "..", "mcp"))
try:
    import audit as _audit
except Exception:
    _audit = None


def expand_logs(paths):
    """Convierte paths (ficheros, carpetas o globs) en una lista de ficheros de log."""
    out = []
    for p in paths:
        if os.path.isdir(p):
            out += sorted(glob.glob(os.path.join(p, "*.log")))
        elif any(ch in p for ch in "*?["):
            out += sorted(glob.glob(p))
        else:
            out.append(p)
    # dedup preservando orden
    seen = set()
    uniq = []
    for f in out:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    return uniq


def read_entries(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def load_all(logs):
    """Lee todos los logs. Verifica cada cadena por separado. Devuelve (entries, report).
    A cada entrada le asegura un 'deployment' (procedencia): el del propio registro o,
    en su defecto, el nombre del fichero (unidad)."""
    entries = []
    report = []
    for path in logs:
        if not os.path.exists(path):
            report.append((path, "no existe", 0))
            continue
        integ = "sin verificar"
        if _audit:
            ok, msg = _audit.verify(path)
            integ = "OK ✓" if ok else "ROTA ✗ (%s)" % msg
        prov = os.path.splitext(os.path.basename(path))[0]
        es = read_entries(path)
        for e in es:
            e.setdefault("deployment", prov)   # procedencia si no la trae
        entries += es
        report.append((path, integ, len(es)))
    return entries, report


def aggregate(human, key, label):
    by = collections.defaultdict(collections.Counter)
    cost = collections.defaultdict(float)
    for e in human:
        k = e.get(key) or "(sin " + key + ")"
        by[k][e.get("decision", "?")] += 1
        c = e.get("cost_eur")
        if isinstance(c, (int, float)):
            cost[k] += c
    if not by:
        return
    print("\n=== decisiones humanas por %s ===" % label)
    for k in sorted(by, key=lambda x: -sum(by[x].values())):
        c = by[k]
        tot = sum(c.values())
        allow = c.get("allow", 0)
        deny = c.get("deny", 0)
        rate = ("%d%% allow" % round(100 * allow / tot)) if tot else "-"
        eur = (" · €%.2f" % cost[k]) if cost[k] else ""
        print("  %-24s %4d  (allow %d / deny %d, %s)%s" % (k, tot, allow, deny, rate, eur))


def main():
    args = sys.argv[1:]
    jsonl = None
    only_human = True
    rest = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--jsonl" and i + 1 < len(args):
            jsonl = args[i + 1]
            i += 2
            continue
        if a == "--all":
            only_human = False
            i += 1
            continue
        rest.append(a)
        i += 1

    logs = expand_logs(rest) if rest else [DEFAULT]
    entries, report = load_all(logs)

    print("Logs (%d) — integridad por cadena:" % len(report))
    for path, integ, n in report:
        print("  %-40s %s  (%d entradas)" % (os.path.basename(path), integ, n))

    human = [e for e in entries if e.get("source") == "operator"]
    print("\nEntradas totales: %d  ·  decisiones humanas: %d" % (len(entries), len(human)))
    if not human:
        print("\nAún no hay decisiones humanas (source=operator) en los logs.")
        return

    # agregados: el corte por DESPLIEGUE (unidad federada) y por UNIDAD/departamento
    aggregate(human, "deployment", "DESPLIEGUE/TENANT")
    aggregate(human, "unit", "DEPARTAMENTO/UNIDAD")
    aggregate(human, "kind", "AGENTE")
    aggregate(human, "model", "MODELO")
    aggregate(human, "tool", "TOOL")

    if jsonl:
        with_payload = 0
        n = 0
        with open(jsonl, "w", encoding="utf-8") as out:
            for e in human:
                if e.get("payload") is not None:
                    with_payload += 1
                rec = {
                    "context": {
                        "tool": e.get("tool"),
                        "summary": e.get("summary"),
                        "payload": e.get("payload"),
                        "deployment": e.get("deployment"),
                        "unit": e.get("unit"),
                        "profile": e.get("profile"),
                        "agent": e.get("kind"),
                        "model": e.get("model"),
                        "cost_eur": e.get("cost_eur"),
                        "payload_hash": e.get("payload_hash"),
                    },
                    "human_decision": e.get("decision"),
                    "source": e.get("source"),
                    "req_id": e.get("req_id"),
                    "ts": e.get("ts"),
                }
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
        print("\n✓ Exportadas %d decisiones humanas a %s (%d con payload completo)."
              % (n, jsonl, with_payload))
        if with_payload == 0:
            print("  Nota: para el CONTEXTO íntegro, arranca los brokers con "
                  "AGENT_BOARD_AUDIT_FULL_PAYLOAD=1.")


if __name__ == "__main__":
    main()
