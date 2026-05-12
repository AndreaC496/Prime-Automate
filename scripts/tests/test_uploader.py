from unittest.mock import MagicMock, call
import pytest
from uploader import upload_chunks


def _make_chunk(i: int) -> dict:
    return {
        "content": f"contenuto {i}",
        "embedding": [0.1] * 2048,
        "metadata": {"doc_type": "exercise"},
        "source": "test.xlsx",
        "doc_type": "exercise",
    }


def test_upload_chunks_calls_upsert():
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    chunks = [_make_chunk(i) for i in range(3)]
    upload_chunks(mock_client, chunks)
    mock_client.table.assert_called_with("document_chunks")
    mock_client.table.return_value.upsert.assert_called_once()


def test_upload_chunks_batch_size():
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    chunks = [_make_chunk(i) for i in range(55)]
    upload_chunks(mock_client, chunks, batch_size=20)
    # 55 chunks in batches of 20: [0:20], [20:40], [40:55] = 3 calls
    assert mock_client.table.return_value.upsert.call_count == 3


def test_upload_chunks_empty():
    mock_client = MagicMock()
    upload_chunks(mock_client, [])
    mock_client.table.assert_not_called()
