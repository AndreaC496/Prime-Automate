def upload_chunks(client, chunks: list[dict], batch_size: int = 20) -> None:
    if not chunks:
        return
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        client.table("document_chunks").upsert(batch).execute()
        print(f"  Caricati {min(i + batch_size, len(chunks))}/{len(chunks)} chunk")
