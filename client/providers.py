#!/usr/bin/env python3
"""
providers.py — capa multi-proveedor para pilotar el tablero con CUALQUIER LLM.

Una sola función, generate(model, prompt), despacha al proveedor correcto según el
nombre del modelo y devuelve texto + uso REAL de tokens (input/output):

    Claude   → Anthropic     (ANTHROPIC_API_KEY)
    GPT/o*   → OpenAI         (OPENAI_API_KEY)
    Gemini   → Google         (GOOGLE_API_KEY / GEMINI_API_KEY)
    locales  → OpenAI-compat / Ollama  (AGENT_BOARD_LOCAL_URL, def http://localhost:11434)

Diseño clave: si falta el SDK o la API key de un proveedor, cae a **modo SIMULADO**
(con tokens estimados) — así el tablero muestra agentes de todos los proveedores SIN
llaves, y en cuanto pones una key/red, ese proveedor pasa a llamadas reales. Cada
proveedor es independiente: puedes tener Claude real y el resto simulado, o al revés.

    from providers import generate, provider_of
    r = generate("gpt-4o", "Resume esto")   # -> {text, tokens_in, tokens_out, tokens, provider, real}

Devuelve dict: {model, provider, text, tokens_in, tokens_out, tokens, real}.
'real'=False indica respuesta simulada (sin proveedor disponible).
"""
import os
import time
import random


def provider_of(model: str) -> str:
    """Deduce el proveedor por el nombre del modelo."""
    m = (model or "").lower()
    if m.startswith(("gpt", "o1", "o3", "o4")) or "openai" in m:
        return "openai"
    if "gemini" in m or "google" in m:
        return "google"
    if m.startswith("claude") or m.startswith(("opus", "sonnet", "haiku")):
        return "anthropic"
    if any(k in m for k in ("llama", "mistral", "qwen", "deepseek", "phi", "local", "gemma")):
        return "local"
    return "anthropic"


def _estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)          # ~4 chars/token, suficiente para estimar


def _result(model, text, tin, tout, real):
    return {"model": model, "provider": provider_of(model), "text": text or "",
            "tokens_in": int(tin), "tokens_out": int(tout), "tokens": int(tin) + int(tout),
            "real": bool(real)}


def _sim(model, prompt, note=""):
    """Respuesta simulada con tokens estimados (sin proveedor real)."""
    time.sleep(random.uniform(0.15, 0.5))
    txt = f"[{model}] respuesta simulada{(' · ' + note) if note else ''}"
    return _result(model, txt, _estimate_tokens(prompt), random.randint(80, 420), real=False)


# ---------- adaptadores por proveedor (todos degradan a _sim si no hay SDK/key) ----------
def _anthropic(model, prompt, system, max_tokens):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _sim(model, prompt)
    import anthropic                                  # pip install anthropic
    cli = anthropic.Anthropic()
    # nombre corto -> id real por env (no hardcodeamos ids que cambian con las versiones)
    mid = os.environ.get("AGENT_BOARD_ANTHROPIC_MODEL", model if model.startswith("claude") else "claude-3-5-sonnet-latest")
    r = cli.messages.create(model=mid, max_tokens=max_tokens,
                            system=system or "", messages=[{"role": "user", "content": prompt}])
    text = "".join(getattr(b, "text", "") for b in r.content)
    return _result(model, text, r.usage.input_tokens, r.usage.output_tokens, real=True)


def _openai(model, prompt, system, max_tokens):
    if not os.environ.get("OPENAI_API_KEY"):
        return _sim(model, prompt)
    from openai import OpenAI                          # pip install openai
    cli = OpenAI()
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    r = cli.chat.completions.create(model=model, max_tokens=max_tokens, messages=msgs)
    text = r.choices[0].message.content
    u = r.usage
    return _result(model, text, u.prompt_tokens, u.completion_tokens, real=True)


def _google(model, prompt, system, max_tokens):
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        return _sim(model, prompt)
    import google.generativeai as genai                # pip install google-generativeai
    genai.configure(api_key=key)
    gm = genai.GenerativeModel(model, system_instruction=system or None)
    r = gm.generate_content(prompt, generation_config={"max_output_tokens": max_tokens})
    um = getattr(r, "usage_metadata", None)
    tin = getattr(um, "prompt_token_count", _estimate_tokens(prompt)) if um else _estimate_tokens(prompt)
    tout = getattr(um, "candidates_token_count", _estimate_tokens(r.text)) if um else _estimate_tokens(getattr(r, "text", ""))
    return _result(model, getattr(r, "text", ""), tin, tout, real=True)


def _local(model, prompt, system, max_tokens):
    """Modelo local vía API OpenAI-compatible (vLLM/LM Studio) u Ollama."""
    import json, urllib.request
    base = os.environ.get("AGENT_BOARD_LOCAL_URL", "http://localhost:11434").rstrip("/")
    # 1) intento API OpenAI-compatible (/v1/chat/completions)
    try:
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        body = json.dumps({"model": model, "messages": msgs, "max_tokens": max_tokens}).encode()
        req = urllib.request.Request(base + "/v1/chat/completions", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            d = json.loads(resp.read())
        text = d["choices"][0]["message"]["content"]
        u = d.get("usage", {})
        return _result(model, text, u.get("prompt_tokens", _estimate_tokens(prompt)),
                       u.get("completion_tokens", _estimate_tokens(text)), real=True)
    except Exception:
        pass
    # 2) Ollama nativo (/api/generate)
    body = json.dumps({"model": model, "prompt": prompt, "system": system or "", "stream": False}).encode()
    req = urllib.request.Request(base + "/api/generate", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        d = json.loads(resp.read())
    text = d.get("response", "")
    tin = d.get("prompt_eval_count", _estimate_tokens(prompt))
    tout = d.get("eval_count", _estimate_tokens(text))
    return _result(model, text, tin, tout, real=True)


def generate(model, prompt, system=None, max_tokens=512):
    """Genera con el proveedor del modelo. Nunca lanza: si el proveedor real falla
    (sin key, sin red, SDK ausente), devuelve una respuesta SIMULADA con tokens estimados."""
    p = provider_of(model)
    fn = {"openai": _openai, "google": _google, "anthropic": _anthropic, "local": _local}.get(p)
    try:
        return fn(model, prompt, system, max_tokens)
    except Exception as e:
        return _sim(model, prompt, note=f"fallback {type(e).__name__}")


if __name__ == "__main__":
    for m in ["opus", "gpt-4o", "gemini-2.0-flash", "mistral-local"]:
        r = generate(m, "Hola, resume en una frase qué es un agente.")
        print(f"{r['provider']:10} {m:16} tokens={r['tokens']:4} real={r['real']}  {r['text'][:40]}")
    print("providers OK")
