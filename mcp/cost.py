#!/usr/bin/env python3
"""
cost.py — coste en EUROS de los tokens, por modelo (control de coste).

No todos los tokens cuestan igual: un token de un modelo local (Mistral/Llama en tu
hardware) es ~gratis; uno de un modelo fundacional (Opus, GPT-4o) es caro. Medir el
WIP y las cuotas en "tokens a secas" mezcla ambos. Este módulo traduce
(modelo, tokens) -> € usando la tabla de precios `mcp/models.json`, y expone la CLASE
del modelo (local|foundational) para presupuestos separados por clase.

Lógica pura (stdlib). El tablero replica esta tabla inline; el broker la importa.

    from cost import load_prices, cost_eur, model_class
    P = load_prices()
    cost_eur("opus", 20000, P)      # -> 0.30  (20k tok * 15 €/Mtok)
    model_class("mistral-local", P) # -> "local"
"""
import os
import json

PRICES_PATH = os.environ.get("AGENT_BOARD_PRICES",
                             os.path.join(os.path.dirname(__file__), "models.json"))


def load_prices(path=None):
    """Lee models.json. Devuelve dict {default, models}. Tolerante a fallos."""
    try:
        with open(path or PRICES_PATH) as f:
            d = json.load(f)
        return {"default": d.get("default", {"price_eur_per_mtok": 5.0, "class": "foundational"}),
                "models": d.get("models", {})}
    except Exception:
        return {"default": {"price_eur_per_mtok": 5.0, "class": "foundational"}, "models": {}}


def _entry(model, prices):
    """Busca el modelo: match exacto, si no por subcadena (gpt-4o-mini -> gpt-4o), si no default."""
    models = prices.get("models", {})
    m = (model or "").strip().lower()
    if m in models:
        return models[m]
    # subcadena: alguna clave conocida contenida en el nombre del modelo
    for key, val in models.items():
        if key and key.lower() in m:
            return val
    return prices.get("default", {"price_eur_per_mtok": 5.0, "class": "foundational"})


def price_per_mtok(model, prices):
    return float(_entry(model, prices).get("price_eur_per_mtok", 5.0))


def model_class(model, prices):
    return _entry(model, prices).get("class", "foundational")


def cost_eur(model, tokens, prices):
    """Coste en € de `tokens` tokens del `model`. tokens en unidades (no millones)."""
    try:
        return (float(tokens) / 1_000_000.0) * price_per_mtok(model, prices)
    except (TypeError, ValueError):
        return 0.0


if __name__ == "__main__":
    P = load_prices()
    c = cost_eur("opus", 20000, P)
    assert abs(c - 0.30) < 1e-9, c
    assert model_class("mistral-local", P) == "local"
    assert cost_eur("local", 1_000_000, P) == 0.0          # local no consume presupuesto €
    assert model_class("gpt-4o-mini", P) == "foundational"  # match por subcadena
    assert cost_eur("desconocido", 1_000_000, P) == 5.0     # default
    print("cost OK · opus 20k =", round(c, 4), "€ · local 1M = 0 €")
