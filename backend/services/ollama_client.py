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
    and JSON embedded in surrounding prose. Uses bracket counting
    to correctly handle nested objects.
    """
    # Strip markdown code fence if present (```json ... ``` or ``` ... ```)
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if code_block:
        text = code_block.group(1)

    # Find the first '{' and extract the full balanced JSON object
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None

    return None
