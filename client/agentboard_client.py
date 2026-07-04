#!/usr/bin/env python3
"""
agentboard_client.py — cliente genérico del tablero, INDEPENDIENTE del LLM.

El tablero/broker hablan por HTTP, así que cualquier runtime de agentes (OpenAI
Agents SDK, LangGraph, CrewAI, AutoGen, tu propio bucle...) puede pilotarlo con
esta clase. Solo dos cosas que mapear desde tu framework:

  1. ciclo de vida  -> start() / step() / stop()   (observabilidad)
  2. operación con efectos -> gate()  (puerta de aprobación humana, BLOQUEANTE)
  3. control de coste -> account_llm(model, tokens)  (presupuesto en €, por clase)

Ejemplo mínimo (cualquier LLM):

    from agentboard_client import AgentBoard
    board = AgentBoard()                       # broker en :8787 por defecto
    sid = board.start("Refactor del cliente HTTP", model="gpt-4o", kind="implementer")
    board.step(sid, "leyendo ficheros")
    ...
    if board.gate(sid, "Write", {"path": "client.py"}):   # bloquea hasta Aprobar/Denegar
        do_the_write()
    else:
        skip()
    # antes de una llamada LLM cara, comprueba presupuesto de coste (una línea):
    if not board.account_llm("opus", 18000, sid):         # False -> presupuesto agotado
        return
    board.stop(sid)
"""
import os, time, json, uuid, hashlib, urllib.request


def _op_hash(tool, payload=None):
    """Hash canonico de la operacion (ADR-0007). Igual que mcp/canonical.op_hash."""
    blob = json.dumps({"tool": tool or "", "payload": payload or {}},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class AgentBoard:
    def __init__(self, broker=None, gate_timeout=300):
        self.broker = (broker or os.environ.get("AGENT_BOARD_BROKER", "http://127.0.0.1:8787")).rstrip("/")
        self.gate_timeout = gate_timeout

    def _post(self, path, payload, t=4):
        req = urllib.request.Request(self.broker + path, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=t) as r:
            return json.loads(r.read() or b"{}")

    def _get(self, path, t=4):
        with urllib.request.urlopen(self.broker + path, timeout=t) as r:
            return json.loads(r.read() or b"{}")

    # ---- ciclo de vida (observabilidad) ----
    def start(self, job, model="opus", kind="implementer", parent_id=None, session_id=None):
        sid = session_id or uuid.uuid4().hex[:8]
        self._post("/api/event", {"event": "SessionStart", "session_id": sid,
                                  "prompt": job, "model": model, "kind": kind, "parent_id": parent_id})
        return sid

    def step(self, session_id, action):
        try: self._post("/api/event", {"event": "PreToolUse", "session_id": session_id, "tool_name": action})
        except Exception: pass

    def report_usage(self, session_id, model, tokens_in=0, tokens_out=0, action=None):
        """Reporta el uso REAL de tokens de una llamada LLM (cualquier proveedor) a la
        tarjeta del tablero. El tablero muestra tokens y calcula el coste € por modelo.
        Combínalo con account_llm() si además quieres el enforcement de presupuesto."""
        try:
            self._post("/api/event", {"event": "Usage", "session_id": session_id,
                                      "tokens": int(tokens_in) + int(tokens_out),
                                      "model": model, "action": action})
        except Exception:
            pass

    def stop(self, session_id):
        try: self._post("/api/event", {"event": "Stop", "session_id": session_id})
        except Exception: pass

    # ---- puerta de aprobación (bloqueante) ----
    def gate(self, session_id, tool, tool_input=None) -> bool:
        """Registra una petición y BLOQUEA hasta que el tablero decida.
        Devuelve True (allow) o False (deny / timeout). Sin broker -> False (conservador)."""
        try:
            resp = self._post("/api/request", {"session_id": session_id, "tool_name": tool,
                                               "tool_input": tool_input or {}})
            rid = resp["req_id"]
            expected_hash = resp.get("payload_hash")
        except Exception:
            return False
        deadline = time.time() + self.gate_timeout
        while time.time() < deadline:
            time.sleep(1.5)
            try:
                st = self._get(f"/api/decision?req_id={rid}").get("status", "pending")
            except Exception:
                continue
            if st == "allow":
                # binding (ADR-0007): el contenido debe ser el aprobado, si no -> deny
                if expected_hash and _op_hash(tool, tool_input or {}) != expected_hash:
                    return False
                return True
            if st in ("deny", "expired", "unknown"):
                return False
        return False

    # ---- control de coste (presupuesto en €, por modelo/clase) ----
    def account_llm(self, model, tokens, session_id=None, workflow=None,
                    tool="llm_call", block_on_ask=True) -> bool:
        """Contabiliza el coste de una llamada LLM y dice si puedes proceder.
        El broker traduce (modelo, tokens) -> € con mcp/models.json y aplica las cuotas
        de coste (p. ej. techo de €/hora en modelos fundacionales). Devuelve:
          True  -> dentro de presupuesto (queda contabilizado).
          False -> denegado / sin broker / no aprobado.
        Si la cuota es 'ask' y block_on_ask, abre tarjeta en el tablero y espera tu
        aprobación; si la apruebas, contabiliza el gasto y devuelve True.

        Uso (una línea antes de gastar):
            if not board.account_llm("opus", 18000, sid): return  # presupuesto agotado
        """
        ctx = {"agent": session_id or "", "workflow": workflow or os.environ.get("AGENT_BOARD_WORKFLOW", ""),
               "model": model, "tokens": tokens}
        try:
            r = self._post("/api/account", {"tool": tool, "payload": {}, "ctx": ctx, "mode": "commit"})
        except Exception:
            return False  # sin broker -> conservador: no gastar
        dec = r.get("decision", "allow")
        if dec == "allow":
            return True            # dentro de presupuesto, ya contabilizado
        if dec == "deny":
            return False
        # dec == 'ask': presupuesto excedido -> aprobación humana
        if not block_on_ask:
            return False
        if self.gate(session_id or "llm", tool, {"model": model, "tokens": tokens,
                                                  "reason": "presupuesto de coste excedido"}):
            try: self._post("/api/account", {"tool": tool, "payload": {}, "ctx": ctx, "mode": "force"})
            except Exception: pass
            return True
        return False
