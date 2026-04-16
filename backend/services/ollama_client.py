import asyncio
import json
import re

import ollama


async def generate_recommendations(prompt: str, model: str = "llama3") -> str:
    try:
        response = await asyncio.to_thread(
            ollama.chat,
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.message.content
    except ollama.ResponseError as e:
        raise RuntimeError(f"Ollama model error ({model}): {e}") from e
    except Exception as e:
        raise RuntimeError(f"Ollama unavailable: {e}") from e


def extract_json_from_response(text: str) -> dict | None:
    """Extract and parse a JSON object from LLM output.

    Handles plain JSON, JSON wrapped in markdown code blocks,
    and JSON embedded in surrounding prose.
    """
    # Strip markdown code block if present
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block:
        text = code_block.group(1)

    # Find the first {...} block in the text
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if not json_match:
        return None

    try:
        return json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return None
