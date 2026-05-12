-- Abilita pgvector
create extension if not exists vector;

-- Tabella principale
create table if not exists document_chunks (
  id          uuid primary key default gen_random_uuid(),
  content     text not null,
  embedding   vector(2048),
  fts         tsvector generated always as
                (to_tsvector('italian', content)) stored,
  metadata    jsonb not null default '{}',
  source      text not null,
  doc_type    text not null check (doc_type in ('exercise', 'manual', 'guideline')),
  created_at  timestamptz default now()
);

-- Indice HNSW per ricerca vettoriale (approximate nearest neighbor)
create index if not exists document_chunks_embedding_idx
  on document_chunks using hnsw (embedding vector_cosine_ops)
  with (m = 32, ef_construction = 128);

-- Indice GIN per full-text search italiano
create index if not exists document_chunks_fts_idx
  on document_chunks using gin (fts);

-- Indice GIN per filtri metadata
create index if not exists document_chunks_metadata_idx
  on document_chunks using gin (metadata jsonb_path_ops);

-- Funzione di ricerca ibrida con Reciprocal Rank Fusion
create or replace function match_documents(
  query_embedding  vector(2048),
  query_text       text,
  filter_metadata  jsonb    default '{}',
  match_count      int      default 10,
  vector_weight    float    default 0.7,
  fts_weight       float    default 0.3
)
returns table (
  id         uuid,
  content    text,
  metadata   jsonb,
  doc_type   text,
  source     text,
  similarity float
)
language plpgsql as $$
begin
  return query
  with vector_results as (
    select dc.id,
           1 - (dc.embedding <=> query_embedding) as v_score,
           row_number() over (order by dc.embedding <=> query_embedding) as v_rank
    from document_chunks dc
    where (filter_metadata is null or filter_metadata = '{}' or dc.metadata @> filter_metadata)
    order by dc.embedding <=> query_embedding
    limit match_count * 3
  ),
  fts_results as (
    select dc.id,
           row_number() over (
             order by ts_rank(dc.fts, plainto_tsquery('italian', query_text)) desc
           ) as f_rank
    from document_chunks dc
    where (filter_metadata is null or filter_metadata = '{}' or dc.metadata @> filter_metadata)
      and dc.fts @@ plainto_tsquery('italian', query_text)
    order by ts_rank(dc.fts, plainto_tsquery('italian', query_text)) desc
    limit match_count * 3
  ),
  fused as (
    select coalesce(vr.id, fr.id) as id,
           coalesce(1.0 / (60 + vr.v_rank), 0) * vector_weight +
           coalesce(1.0 / (60 + fr.f_rank), 0) * fts_weight  as rrf_score
    from vector_results vr
    full outer join fts_results fr using (id)
  )
  select dc.id, dc.content, dc.metadata, dc.doc_type, dc.source,
         f.rrf_score as similarity
  from fused f
  join document_chunks dc on dc.id = f.id
  order by f.rrf_score desc
  limit match_count;
end; $$;
