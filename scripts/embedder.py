import httpx

_OPENROUTER_EMBED_URL = "https://openrouter.ai/api/v1/embeddings"


def _call_embeddings_api(api_key: str, model: str, texts: list[str]) -> list[list[float]]:
    response = httpx.post(
        _OPENROUTER_EMBED_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "input": texts},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    try:
        return [item["embedding"] for item in data["data"]]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected embedding response shape: {e}\nFull response: {data}") from e


def probe_embedding_dim(api_key: str, model: str) -> int:
    embeddings = _call_embeddings_api(api_key, model, ["probe"])
    if not embeddings:
        raise RuntimeError("probe_embedding_dim: API returned empty embeddings list")
    return len(embeddings[0])


def embed_batch(
    api_key: str,
    model: str,
    texts: list[str],
    batch_size: int = 20,
) -> list[list[float]]:
    if not texts:
        return []
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings.extend(_call_embeddings_api(api_key, model, batch))
    return embeddings
