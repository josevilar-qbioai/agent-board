#!/usr/bin/env python3
"""
validate_config.py — valida la configuración del proyecto con mensajes claros.

Comprueba config.json, mcp/policy.json y mcp/models.json: estructura correcta,
perfiles y especialistas bien formados, unidades coherentes, roles válidos, y que
los modelos referenciados tienen precio. Pensado para que otra empresa detecte un
error de configuración en segundos (y para el CI).

Ejecuta:  python3 scripts/validate_config.py
Sale con 0 si todo OK; 1 si hay ERRORES (los WARN no fallan).
"""
import os, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLES = {"read", "effect", "verify", "write"}
errors, warns = [], []
def err(m): errors.append(m)
def warn(m): warns.append(m)


def load(path):
    try:
        with open(path) as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, "no existe"
    except json.JSONDecodeError as e:
        return None, f"JSON inválido: línea {e.lineno}, columna {e.colno} — {e.msg}"


def check_models(models):
    price_keys = set()
    if not isinstance(models, dict):
        err("models.json: se esperaba un objeto"); return price_keys
    ms = models.get("models", {})
    dflt = models.get("default")
    if not dflt or "price_eur_per_mtok" not in dflt:
        warn("models.json: falta 'default.price_eur_per_mtok' (se usará 5.0)")
    for name, m in ms.items():
        price_keys.add(name)
        if "price_eur_per_mtok" not in m:
            err(f"models.json: el modelo '{name}' no tiene 'price_eur_per_mtok'")
        if m.get("class") not in ("local", "foundational"):
            err(f"models.json: el modelo '{name}' tiene class='{m.get('class')}' (debe ser 'local' o 'foundational')")
    return price_keys


def model_known(model, price_keys):
    if not model:
        return True
    m = str(model).lower()
    if m in price_keys:
        return True
    return any(k.lower() in m for k in price_keys)  # match por subcadena (como cost.py)


def check_wip(w):
    if isinstance(w, (int, float)):
        return
    if isinstance(w, dict):
        for k in ("agents",):
            if k not in w:
                warn(f"wip_limit: falta '{k}'")
        return
    err("wip_limit: debe ser un número o un objeto { agents, cost_eur, foundational_cost_eur }")


def check_profiles(profiles, price_keys):
    if not isinstance(profiles, dict) or not profiles:
        warn("config.json: no hay 'profiles' (el tablero usará los embebidos)"); return
    for pk, p in profiles.items():
        if not p.get("label"):
            warn(f"perfil '{pk}': sin 'label'")
        units = p.get("units", [])
        specs = p.get("specialists")
        if not isinstance(specs, list) or not specs:
            err(f"perfil '{pk}': 'specialists' vacío o ausente"); continue
        ids = set(); has_effect = has_verify = False
        for i, s in enumerate(specs):
            sid = s.get("id")
            where = f"perfil '{pk}', especialista {sid or '#'+str(i)}"
            if not sid: err(f"{where}: falta 'id'")
            elif sid in ids: err(f"{where}: 'id' duplicado")
            else: ids.add(sid)
            if not s.get("label"): warn(f"{where}: sin 'label'")
            role = s.get("role")
            if role not in ROLES:
                err(f"{where}: role='{role}' inválido (usa uno de {sorted(ROLES)})")
            if role == "effect": has_effect = True
            if role == "verify": has_verify = True
            if not s.get("color"): warn(f"{where}: sin 'color'")
            u = s.get("unit")
            if u and units and u not in units:
                err(f"{where}: unit='{u}' no está en units {units}")
            if not model_known(s.get("model"), price_keys):
                warn(f"{where}: model='{s.get('model')}' no está en models.json (se usará el precio por defecto)")
        if has_effect and not has_verify:
            warn(f"perfil '{pk}': hay especialistas 'effect' pero ningún 'verify' (no habrá verificación cruzada)")


def check_policy(policy):
    if not isinstance(policy, dict):
        err("policy.json: se esperaba un objeto"); return
    for i, r in enumerate(policy.get("rules", [])):
        if "tool" not in r: err(f"policy.json regla #{i}: falta 'tool'")
        if r.get("decision") not in ("allow", "ask", "deny", None):
            err(f"policy.json regla #{i}: decision='{r.get('decision')}' inválida")
    for i, q in enumerate(policy.get("quotas", [])):
        for k in ("name", "tool", "window", "limit"):
            if k not in q: err(f"policy.json quota #{i}: falta '{k}'")
        if q.get("on_exceed") not in ("deny", "ask", None):
            err(f"policy.json quota #{i}: on_exceed='{q.get('on_exceed')}' inválido")


def main():
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "config.json")
    print(f"Validando configuración de agent-board ({os.path.basename(cfg_path)})…\n")
    cfg, e = load(cfg_path)
    if e: err(f"config.json: {e}")
    models, e = load(os.path.join(ROOT, "mcp", "models.json"))
    if e: err(f"mcp/models.json: {e}")
    policy, e = load(os.path.join(ROOT, "mcp", "policy.json"))
    if e: err(f"mcp/policy.json: {e}")

    price_keys = check_models(models) if models else set()
    if cfg:
        check_wip(cfg.get("wip_limit"))
        check_profiles(cfg.get("profiles", {}), price_keys)
        ap = cfg.get("active_profile")
        if ap and ap not in (cfg.get("profiles") or {}):
            err(f"active_profile='{ap}' no existe en profiles")
    if policy:
        check_policy(policy)

    for w in warns: print("  WARN  " + w)
    for e in errors: print("  ERROR " + e)
    print()
    if errors:
        print(f"❌ {len(errors)} error(es), {len(warns)} aviso(s). Corrígelos y reintenta.")
        sys.exit(1)
    print(f"✅ Configuración válida" + (f" ({len(warns)} aviso(s))" if warns else "") + ".")


if __name__ == "__main__":
    main()
