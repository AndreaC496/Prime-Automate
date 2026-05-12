from embedder import _call_embeddings_api


def search(
    supabase_client,
    api_key: str,
    model: str,
    query: str,
    filters: dict = {},
    top_k: int = 10,
) -> list[dict]:
    """
    Search for documents using hybrid search via Supabase RPC.

    Args:
        supabase_client: Supabase client instance
        api_key: OpenRouter API key
        model: Embedding model name
        query: Search query text
        filters: Optional metadata filters (dict)
        top_k: Number of results to return (default: 10)

    Returns:
        List of matching documents with metadata and similarity scores
    """
    embeddings = _call_embeddings_api(api_key, model, [query])
    embedding = embeddings[0]
    result = supabase_client.rpc(
        "match_documents",
        {
            "query_embedding": embedding,
            "query_text": query,
            "filter_metadata": filters,
            "match_count": top_k,
        },
    ).execute()
    return result.data or []
