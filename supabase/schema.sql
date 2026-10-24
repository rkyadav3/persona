-- Run once: Supabase dashboard -> SQL Editor -> New query -> paste all -> Run.
create extension if not exists vector with schema extensions;

create table if not exists topics (
  id bigint generated always as identity primary key,
  name text not null, description text not null default '',
  created_at timestamptz not null default now()
);
create table if not exists folders (
  id bigint generated always as identity primary key,
  parent_id bigint references folders(id) on delete cascade,
  name text not null, created_at timestamptz not null default now()
);
create unique index if not exists folders_unique_name on folders (coalesce(parent_id, 0), name);
create table if not exists files (
  id bigint generated always as identity primary key,
  folder_id bigint references folders(id) on delete cascade,
  topic_id bigint references topics(id) on delete set null,
  name text not null, storage_path text not null, mime text, size bigint not null default 0,
  text_content text not null default '',
  status text not null default 'published' check (status in ('draft','published')),
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index if not exists files_folder_idx on files (folder_id);
create table if not exists templates (
  id bigint generated always as identity primary key,
  name text not null, html text not null default '', created_at timestamptz not null default now()
);
create table if not exists posts (
  id bigint generated always as identity primary key,
  title text not null default 'Untitled', html text not null default '',
  status text not null default 'draft' check (status in ('draft','published')),
  topic_id bigint references topics(id) on delete set null,
  template_id bigint references templates(id) on delete set null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);

-- The knowledge index: one row per chunk, with its meaning vector and a keyword index.
create table if not exists chunks (
  id bigint generated always as identity primary key,
  source_key text not null,            -- 'file:12' or 'post:3'
  source_type text, source_id bigint, source_name text, source_hash text,
  ord int, heading text not null default '', content text not null,
  embedding extensions.vector(768),
  fts tsvector generated always as (
    to_tsvector('english', coalesce(source_name,'') || ' ' || coalesce(heading,'') || ' ' || content)
  ) stored
);
create index if not exists chunks_source_idx on chunks (source_key);
create index if not exists chunks_fts_idx on chunks using gin (fts);
create index if not exists chunks_embedding_idx on chunks using hnsw (embedding extensions.vector_cosine_ops);

create table if not exists chat_log (
  id bigint generated always as identity primary key,
  question text not null, answered boolean not null default false,
  top_similarity real, created_at timestamptz not null default now()
);

-- Security: the website and the admin both use the server-side secret key, which bypasses RLS.
-- With RLS on and no policies, nobody using the public (publishable/anon) key can read or write anything.
alter table topics enable row level security;
alter table folders enable row level security;
alter table files enable row level security;
alter table templates enable row level security;
alter table posts enable row level security;
alter table chunks enable row level security;
alter table chat_log enable row level security;

-- Private bucket for the uploaded files themselves.
insert into storage.buckets (id, name, public) values ('files', 'files', false) on conflict (id) do nothing;

insert into templates (name, html)
select * from (values
  ('Blank', '<p></p>'),
  ('Research note', '<h1>Title</h1><h2>Question</h2><p></p><h2>Method</h2><p></p><h2>Findings</h2><p></p><h2>Open problems</h2><p></p>'),
  ('Blog post', '<h1>Headline</h1><p>Opening paragraph.</p><h2>Section</h2><p></p>')
) as t(name, html)
where not exists (select 1 from templates);

-- ---------- functions ----------
create or replace function chunk_sources()
returns table (source_key text, source_hash text)
language sql stable as $$ select source_key, min(source_hash) from chunks group by source_key $$;

create or replace function set_embeddings(items jsonb)
returns void language sql set search_path = public, extensions as $$
  update chunks c set embedding = (i->>'embedding')::extensions.vector(768)
  from jsonb_array_elements(items) i where c.id = (i->>'id')::bigint
$$;

-- Hybrid search: meaning (vector) + keywords, merged with reciprocal rank fusion.
-- A chunk passes the relevance gate if its similarity >= min_similarity, or it is a strong keyword hit.
create or replace function hybrid_search(
  query_embedding extensions.vector(768),
  keyword_query text default '',
  match_count int default 6,
  min_similarity float default 0.6,
  min_keyword_rank float default 0.2
)
returns table (id bigint, source_name text, heading text, content text, similarity float, keyword_rank float, score float)
language sql stable set search_path = public, extensions as $$
  with vec as (
    select c.id, 1 - (c.embedding <=> query_embedding) as sim,
           row_number() over (order by c.embedding <=> query_embedding) as rnk
    from chunks c where c.embedding is not null
    order by c.embedding <=> query_embedding limit 30
  ),
  q as (select case when coalesce(keyword_query,'') = '' then null else to_tsquery('english', keyword_query) end as tsq),
  kw as (
    select c.id, ts_rank_cd(c.fts, q.tsq) as r,
           row_number() over (order by ts_rank_cd(c.fts, q.tsq) desc) as rnk
    from chunks c, q where q.tsq is not null and c.fts @@ q.tsq
    order by r desc limit 30
  ),
  fused as (
    select coalesce(v.id, k.id) as id, v.sim, k.r,
           coalesce(1.0 / (60 + v.rnk), 0) + coalesce(1.0 / (60 + k.rnk), 0) as score
    from vec v full outer join kw k on k.id = v.id
  )
  select c.id, c.source_name, c.heading, c.content,
         coalesce(f.sim, 0)::float, coalesce(f.r, 0)::float, f.score::float
  from fused f join chunks c on c.id = f.id
  where coalesce(f.sim, 0) >= min_similarity or coalesce(f.r, 0) >= min_keyword_rank
  order by f.score desc limit match_count
$$;
