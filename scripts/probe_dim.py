import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

response = client.embeddings.create(
    model=os.getenv("EMBED_MODEL"),
    input=["test dimensione embedding"],
)
dim = len(response.data[0].embedding)
print(f"Embedding dimension: {dim}")
print(f"Usa vector({dim}) nello schema SQL.")
