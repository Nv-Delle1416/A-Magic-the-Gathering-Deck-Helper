import ollama


async def generate_recommendations(prompt: str, model: str = "llama3") -> str:
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"]
