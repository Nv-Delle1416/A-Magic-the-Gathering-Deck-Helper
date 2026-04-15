import asyncio
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
