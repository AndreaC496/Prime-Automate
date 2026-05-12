from unittest.mock import patch
import pytest
from embedder import embed_batch, probe_embedding_dim


def test_probe_embedding_dim():
    with patch("embedder._call_embeddings_api") as mock_api:
        mock_api.return_value = [[0.1] * 4096]
        dim = probe_embedding_dim("test-key", "test-model")
    assert dim == 4096
    mock_api.assert_called_once_with("test-key", "test-model", ["probe"])


def test_embed_batch_returns_embeddings():
    with patch("embedder._call_embeddings_api") as mock_api:
        mock_api.return_value = [[0.1] * 2048] * 3
        result = embed_batch("test-key", "test-model", ["a", "b", "c"])
    assert len(result) == 3
    assert len(result[0]) == 2048


def test_embed_batch_splits_into_batches_of_20():
    with patch("embedder._call_embeddings_api") as mock_api:
        mock_api.side_effect = [
            [[0.1] * 2048] * 20,
            [[0.1] * 2048] * 5,
        ]
        texts = ["t"] * 25
        result = embed_batch("test-key", "test-model", texts, batch_size=20)
    assert mock_api.call_count == 2
    assert len(result) == 25


def test_embed_batch_empty_input():
    with patch("embedder._call_embeddings_api") as mock_api:
        result = embed_batch("test-key", "test-model", [])
    assert result == []
    mock_api.assert_not_called()
