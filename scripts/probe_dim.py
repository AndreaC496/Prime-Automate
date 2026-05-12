import os
import httpx
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

api_key = os.environ["OPENROUTER_API_KEY"]
model = os.environ["EMBED_MODEL"]

response = httpx.post(
    "https://openrouter.ai/api/v1/embeddings",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json={"model": model, "input": ["test dimensione embedding"]},
    timeout=30,
)
response.raise_for_status()
data = response.json()
dim = len(data["data"][0]["embedding"])
print(f"Embedding dimension: {dim}")
print(f"Usa vector({dim}) nello schema SQL.")
