import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

from chunkers.excel import chunk_excel
from chunkers.docx import chunk_docx
from chunkers.pdf import chunk_pdf
from embedder import embed_batch, probe_embedding_dim
from uploader import upload_chunks

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
OPENROUTER_KEY = os.environ["OPENROUTER_API_KEY"]
EMBED_MODEL = os.environ["EMBED_MODEL"]

ROOT = Path(__file__).parent.parent
SOURCES = [
    (ROOT / "info.pdf",                "manual",    chunk_pdf),
    (ROOT / "set esercizi.xlsx",       "exercise",  chunk_excel),
    (ROOT / "indicazioni schede.docx", "guideline", chunk_docx),
]


def main() -> None:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("Rilevamento dimensione embedding...")
    dim = probe_embedding_dim(OPENROUTER_KEY, EMBED_MODEL)
    print(f"  Dimensione: {dim}")
    if dim != 2048:
        raise RuntimeError(
            f"Schema atteso halfvec(2048) ma il modello restituisce {dim} dimensioni. "
            f"Aggiorna schema.sql e ricrea la tabella."
        )

    for filepath, doc_type_label, chunker in SOURCES:
        if not filepath.exists():
            print(f"  SKIP (non trovato): {filepath.name}")
            continue

        print(f"\n-> {filepath.name}")
        chunks = chunker(str(filepath))
        print(f"  Chunk generati: {len(chunks)}")

        if not chunks:
            print("  Nessun chunk, skip.")
            continue

        texts = [c["content"] for c in chunks]
        print(f"  Embedding in corso ({len(texts)} testi, batch da 20)...")
        embeddings = embed_batch(OPENROUTER_KEY, EMBED_MODEL, texts)

        for chunk, emb in zip(chunks, embeddings):
            chunk["embedding"] = emb

        print(f"  Upload su Supabase...")
        upload_chunks(supabase_client, chunks)
        print(f"  Completato: {len(chunks)} chunk caricati")

    print("\nIngestion completata.")


if __name__ == "__main__":
    main()
