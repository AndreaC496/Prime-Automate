from unittest.mock import MagicMock, patch
import pytest
from retriever import search


def _mock_supabase(results: list[dict]):
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = results
    return client


def test_search_returns_results():
    sb = _mock_supabase([{"id": "1", "content": "Panca piana", "similarity": 0.9}])
    with patch("retriever._call_embeddings_api") as mock_embed:
        mock_embed.return_value = [[0.1] * 2048]
        results = search(sb, "test-key", "test-model", "esercizi petto")
    assert len(results) == 1
    assert results[0]["content"] == "Panca piana"


def test_search_calls_rpc_with_correct_params():
    sb = _mock_supabase([])
    with patch("retriever._call_embeddings_api") as mock_embed:
        mock_embed.return_value = [[0.1] * 2048]
        search(sb, "test-key", "test-model", "dorsali",
               filters={"doc_type": "exercise"}, top_k=5)
    sb.rpc.assert_called_once_with(
        "match_documents",
        {
            "query_embedding": [0.1] * 2048,
            "query_text": "dorsali",
            "filter_metadata": {"doc_type": "exercise"},
            "match_count": 5,
        },
    )


def test_search_empty_results():
    sb = _mock_supabase([])
    with patch("retriever._call_embeddings_api") as mock_embed:
        mock_embed.return_value = [[0.1] * 2048]
        results = search(sb, "test-key", "test-model", "query senza risultati")
    assert results == []
