#!/usr/bin/env python3
"""
quota.py — contabilidad agregada en ventana deslizante (ADR-0008).

Cierra la amenaza #11 del threat model: trocear una operacion (60 borrados de 1 en 1)
para esquivar un umbral por-llamada (`deny_if count>50`). El umbral real es el
ACUMULADO por (agente | workflow | tool | recurso) dentro de una ventana de tiempo.

Logica PURA, sin I/O ni red: el broker la usa bajo su lock y persiste el estado.

Config de una quota (vive en policy.json, clave "quotas"):
    {
      "name": "borrados-por-hora",
      "tool": "*delete*",          # glob sobre el nombre de la tool
      "key": ["agent", "tool"],     # dimensiones que definen el cubo
      "window": 3600,                # segundos
      "limit": 100,                  # maximo acumulado en la ventana
      "amount_field": "count",      # campo del payload con la cantidad (def 1)
      "on_exceed": "deny"           # "deny" | "ask"
    }

Dimensiones soportadas en "key": agent, workflow, tool.
Precedencia cuando varias quotas casan: deny > ask > allow.
"""
import json
import fnmatch

_PRECEDENCE = {"allow": 0, "ask": 1, "deny": 2}
_DIMS = ("agent", "workflow", "tool")


def _amount(payload, quota, ctx=None):
    """Cantidad que suma esta operacion: amount_field leido en payload (y si no, en ctx),
    o 1. Permite cuotas en EUROS: amount_field='cost_eur', que el broker calcula y pone
    en ctx a partir de (modelo, tokens)."""
    field = quota.get("amount_field")
    if not field:
        return 1
    payload = payload or {}
    ctx = ctx or {}
    v = payload[field] if field in payload else ctx.get(field, 1)
    try:
        n = float(v)
        return n if n >= 0 else 0.0
    except (TypeError, ValueError):
        return 1


def bucket_key(quota, tool, ctx):
    """Clave canonica del cubo: nombre de la quota + valores de sus dimensiones.
    Namespeada por quota para que dos quotas no compartan contador por error."""
    dims = {"agent": (ctx or {}).get("agent", ""),
            "workflow": (ctx or {}).get("workflow", ""),
            "tool": tool or ""}
    selected = {d: dims.get(d, "") for d in quota.get("key", []) if d in _DIMS}
    return json.dumps({"q": quota.get("name", ""), "k": selected},
                      sort_keys=True, separators=(",", ":"))


def match_quotas(quotas, tool):
    """Quotas cuyo glob de tool casa con `tool`."""
    out = []
    for q in quotas or []:
        if fnmatch.fnmatch(tool or "", q.get("tool", "")):
            out.append(q)
    return out


class QuotaLedger:
    """Contadores por cubo: clave -> lista de [ts, amount]. Poda por la ventana mayor."""

    def __init__(self, events=None):
        # events: { key(str): [[ts(float), amount(float)], ...] }
        self.events = {k: [list(e) for e in v] for k, v in (events or {}).items()}

    # --- consulta / mutacion ---
    def windowed_sum(self, key, window, now):
        cutoff = now - window
        return sum(a for ts, a in self.events.get(key, []) if ts >= cutoff)

    def record(self, key, amount, now):
        self.events.setdefault(key, []).append([now, amount])

    def prune(self, max_window, now):
        cutoff = now - max_window
        for k in list(self.events.keys()):
            kept = [e for e in self.events[k] if e[0] >= cutoff]
            if kept:
                self.events[k] = kept
            else:
                del self.events[k]

    # --- persistencia ---
    def to_dict(self):
        return self.events

    @classmethod
    def from_dict(cls, d):
        return cls(d)


def evaluate(quotas, tool, payload, ctx, ledger, now, mode="commit"):
    """Evalua TODAS las quotas que casan con la tool y devuelve la decision agregada.

    mode:
      "check"  -> solo evalua, no registra.
      "commit" -> evalua y registra SOLO si la decision final es 'allow'.
      "force"  -> registra siempre (tras aprobacion humana de un 'ask').

    Devuelve dict: {decision, hits:[{name,limit,current,amount,decision}], recorded:bool}
    Precedencia: deny > ask > allow.
    """
    hits = []
    worst = "allow"
    cls = (ctx or {}).get("model_class")
    applicable = match_quotas(quotas, tool)
    for q in applicable:
        # filtro por clase de modelo: una cuota con match_class solo cuenta operaciones
        # de esa clase (p. ej. solo 'foundational' para un techo de coste de API).
        mc = q.get("match_class")
        if mc and cls != mc:
            continue
        amt = _amount(payload, q, ctx)
        key = bucket_key(q, tool, ctx)
        cur = ledger.windowed_sum(key, q.get("window", 3600), now)
        if cur + amt > q.get("limit", float("inf")):
            dec = q.get("on_exceed", "deny")
            if dec not in ("deny", "ask"):
                dec = "deny"
        else:
            dec = "allow"
        hits.append({"name": q.get("name", ""), "limit": q.get("limit"),
                     "current": cur, "amount": amt, "decision": dec, "key": key})
        if _PRECEDENCE[dec] > _PRECEDENCE[worst]:
            worst = dec

    recorded = False
    do_record = (mode == "force") or (mode == "commit" and worst == "allow")
    if do_record:
        for h in hits:
            ledger.record(h["key"], h["amount"], now)
        recorded = True

    return {"decision": worst, "hits": hits, "recorded": recorded}


if __name__ == "__main__":
    # auto-comprobacion: el troceo se caza igual que el bloque grande
    quotas = [{"name": "del", "tool": "*delete*", "key": ["agent"], "window": 3600,
               "limit": 50, "amount_field": "count", "on_exceed": "deny"}]
    ctx = {"agent": "a1"}
    # un bloque de 60 -> excede
    L = QuotaLedger()
    r = evaluate(quotas, "delete_rows", {"count": 60}, ctx, L, now=0.0, mode="commit")
    assert r["decision"] == "deny" and not r["recorded"], r
    # 60 de 1 en 1 -> al superar 50 acumulado, deny
    L = QuotaLedger()
    denies = 0
    for i in range(60):
        r = evaluate(quotas, "delete_rows", {"count": 1}, ctx, L, now=float(i), mode="commit")
        if r["decision"] == "deny":
            denies += 1
    assert denies > 0, "el troceo deberia acabar denegado"
    # otra agente distinta no comparte cubo
    r = evaluate(quotas, "delete_rows", {"count": 10}, {"agent": "a2"}, L, now=100.0, mode="commit")
    assert r["decision"] == "allow", r
    print("quota OK (troceo cazado, cubos por agente)")
