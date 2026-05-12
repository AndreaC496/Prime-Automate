from __future__ import annotations
import math
import random

from models import UserPreferences


def softmax_sample(
    items: list[tuple[dict, float]],
    temperature: float,
    n: int,
) -> list[dict]:
    """Probabilistic sampling from scored items. Higher score = higher probability.
    Low temperature → near-deterministic (best items always win).
    High temperature → uniform distribution (any item can be picked)."""
    if not items:
        return []

    scores = [score for _, score in items]
    max_score = max(scores)
    exp_scores = [math.exp((s - max_score) / temperature) for s in scores]
    total = sum(exp_scores)
    probs = [e / total for e in exp_scores]

    pool = list(range(len(items)))
    pool_probs = probs[:]
    selected: list[dict] = []

    for _ in range(min(n, len(items))):
        total_p = sum(pool_probs)
        if total_p <= 0:
            break
        norm = [p / total_p for p in pool_probs]
        idx = random.choices(pool, weights=norm, k=1)[0]
        pos = pool.index(idx)
        selected.append(items[idx][0])
        pool.pop(pos)
        pool_probs.pop(pos)

    return selected


# ── Compound detection ────────────────────────────────────────────────────────

_COMPOUND_KEYWORDS = {
    "squat", "deadlift", "stacco", "panca", "rematore", "press",
    "pull-up", "chin-up", "dip", "hip thrust", "affondi", "bulgarian",
    "lat machine", "t-bar", "hyperextension", "good morning",
}


def _is_compound(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in _COMPOUND_KEYWORDS)


# ── RAGRetriever ──────────────────────────────────────────────────────────────

class RAGRetriever:
    def __init__(self, chroma_path: str = "db"):
        import chromadb
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self._client = chromadb.PersistentClient(path=chroma_path)
        self.exercises = self._client.get_collection("exercises")
        self.knowledge = self._client.get_collection("knowledge")

    def _build_query(self, prefs: UserPreferences) -> str:
        return (
            f"{prefs.level} {prefs.gender} "
            f"{' '.join(prefs.targetMuscles)} {prefs.equipment} "
            "scheda allenamento ipertrofia evidence-based"
        )

    def get_knowledge_chunks(self, prefs: UserPreferences, n: int = 5) -> list[str]:
        query = self._build_query(prefs)
        embedding = self._model.encode(query).tolist()
        n_results = min(n, self.knowledge.count())
        if n_results == 0:
            return []
        results = self.knowledge.query(
            query_embeddings=[embedding],
            n_results=n_results,
        )
        return results["documents"][0] if results["documents"] else []

    def get_exercises(self, prefs: UserPreferences) -> list[dict]:
        query = self._build_query(prefs)
        embedding = self._model.encode(query).tolist()

        all_count = self.exercises.count()
        if all_count == 0:
            return []

        results = self.exercises.query(
            query_embeddings=[embedding],
            n_results=all_count,
            include=["documents", "metadatas", "distances"],
        )

        compounds: list[tuple[dict, float]] = []
        isolations: list[tuple[dict, float]] = []

        for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
            home_gym = str(meta.get("homeGym", "no")).lower()

            # Equipment filter
            if prefs.equipment == "home" and home_gym not in ("si", "si*"):
                continue
            if prefs.equipment == "corpo-libero" and home_gym != "si":
                continue

            # Cosine similarity from L2 distance
            semantic_score = max(0.0, 1.0 - dist / 2.0)

            # Priority bonus for muscles the user is targeting
            primary_lower = str(meta.get("primaryMuscle", "")).lower()
            priority_bonus = 0.15 if any(m in primary_lower for m in prefs.targetMuscles) else 0.0

            sfr = float(meta.get("sfr_score", 0.6))
            rom = float(meta.get("rom_score", 0.6))

            composite = sfr * 0.30 + rom * 0.30 + semantic_score * 0.25 + priority_bonus

            entry = (meta, composite)
            if _is_compound(str(meta.get("name", ""))):
                compounds.append(entry)
            else:
                isolations.append(entry)

        # Low temperature for compounds (always want the best), high for isolations (variety)
        selected_compounds = softmax_sample(compounds, temperature=0.35, n=10)
        selected_isolations = softmax_sample(isolations, temperature=0.90, n=10)

        return selected_compounds + selected_isolations
