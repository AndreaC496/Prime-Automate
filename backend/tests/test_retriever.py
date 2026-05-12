import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag.retriever import softmax_sample


def test_softmax_sample_returns_correct_count():
    items = [({"name": f"ex{i}"}, float(i)) for i in range(10)]
    result = softmax_sample(items, temperature=0.5, n=5)
    assert len(result) == 5


def test_softmax_sample_no_duplicates():
    items = [({"name": f"ex{i}"}, float(i)) for i in range(10)]
    result = softmax_sample(items, temperature=0.5, n=10)
    names = [r["name"] for r in result]
    assert len(names) == len(set(names))


def test_softmax_sample_low_temp_favors_high_score():
    items = [({"name": "low"}, 0.1), ({"name": "high"}, 10.0)]
    counts = {"low": 0, "high": 0}
    for _ in range(200):
        result = softmax_sample(items, temperature=0.1, n=1)
        counts[result[0]["name"]] += 1
    assert counts["high"] > 180, f"Expected high score to win >180/200 times, got {counts['high']}"


def test_softmax_sample_high_temp_allows_low_score():
    items = [({"name": "low"}, 0.1), ({"name": "high"}, 10.0)]
    counts = {"low": 0, "high": 0}
    for _ in range(200):
        result = softmax_sample(items, temperature=5.0, n=1)
        counts[result[0]["name"]] += 1
    assert counts["low"] > 0, "High temperature should allow low-score items occasionally"


def test_softmax_sample_empty_returns_empty():
    result = softmax_sample([], temperature=0.5, n=5)
    assert result == []


def test_softmax_sample_n_larger_than_pool():
    items = [({"name": f"ex{i}"}, 1.0) for i in range(3)]
    result = softmax_sample(items, temperature=0.5, n=10)
    assert len(result) == 3
