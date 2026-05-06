"""Cliente para el proveedor de IA (Lovable AI Gateway u OpenAI compatible)."""
from __future__ import annotations

import json
import os
from typing import Any

import requests

DEFAULT_BASE_URL = os.environ.get(
    "LEXAGENT_BASE_URL", "https://ai.gateway.lovable.dev/v1"
)
DEFAULT_MODEL = os.environ.get("LEXAGENT_MODEL", "google/gemini-2.5-flash")


def _api_key() -> str:
    key = os.environ.get("LOVABLE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "No se ha definido LOVABLE_API_KEY ni OPENAI_API_KEY en el entorno."
        )
    return key


def run_agent(
    *,
    system_prompt: str,
    knowledge_base: str,
    form_data: dict[str, Any],
    agent_name: str,
    doc_type: str,
    model: str | None = None,
    base_url: str | None = None,
) -> dict[str, str]:
    """Ejecuta el agente y devuelve {'report': str, 'document': str} en markdown."""
    model = model or DEFAULT_MODEL
    base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")

    system = (
        system_prompt
        + (
            "\n\n=== BASE DE CONOCIMIENTO (consultar para fundamentar tus respuestas) ===\n"
            + knowledge_base
            + "\n=== FIN DE LA BASE DE CONOCIMIENTO ==="
            if knowledge_base
            else ""
        )
        + f"\n\nEres \"{agent_name}\". Devuelves SIEMPRE el resultado llamando a la "
          "función `emit_result`. NO escribas texto fuera de la función."
    )

    user = (
        f"Tipo de documento: {doc_type}\n"
        "Datos del caso (formulario):\n"
        "```json\n" + json.dumps(form_data, ensure_ascii=False, indent=2) + "\n```\n\n"
        "Genera:\n"
        "1. Un INFORME de validación detallado en markdown, fundamentado en la base de "
        "conocimiento, indicando: tipo de operación detectada, reservas aplicables, "
        "recomendaciones, advertencias y nivel de riesgo.\n"
        "2. Un DOCUMENTO jurídico (borrador del aval / contragarantía / carta / "
        "informe según corresponda) listo para usar, con los datos del formulario "
        "incorporados, en markdown."
    )

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "emit_result",
                    "description": "Emite el informe de validación y el documento jurídico generado.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "report": {
                                "type": "string",
                                "description": "Informe de validación en markdown.",
                            },
                            "document": {
                                "type": "string",
                                "description": "Documento jurídico borrador en markdown.",
                            },
                        },
                        "required": ["report", "document"],
                        "additionalProperties": False,
                    },
                },
            }
        ],
        "tool_choice": {"type": "function", "function": {"name": "emit_result"}},
    }

    r = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=180,
    )
    if r.status_code == 429:
        raise RuntimeError("Límite de peticiones alcanzado. Espera y reintenta.")
    if r.status_code == 402:
        raise RuntimeError("Sin créditos disponibles en el proveedor de IA.")
    if not r.ok:
        raise RuntimeError(f"Error del modelo IA ({r.status_code}): {r.text[:400]}")

    data = r.json()
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    tool_calls = msg.get("tool_calls") or []
    if tool_calls:
        args = tool_calls[0].get("function", {}).get("arguments")
        if isinstance(args, str):
            args = json.loads(args)
        if args and "report" in args and "document" in args:
            return {"report": args["report"], "document": args["document"]}

    # Fallback: el modelo devolvió texto plano
    content = msg.get("content") or ""
    return {"report": content, "document": ""}
