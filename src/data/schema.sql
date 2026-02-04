-- Enable pgvector extension for embeddings
create extension if not exists vector;

-- Transactions Table
create table if not exists transactions (
    id uuid default gen_random_uuid() primary key,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    user_id uuid not null, -- Assumes Supabase Auth
    date date not null,
    amount decimal(10, 2) not null,
    merchant text not null,
    category text,
    notes text,
    currency text default 'SGD',
    receipt_url text,
    embedding vector(768) -- Dimension depends on the Ollama model (e.g. nomic-embed-text is 768)
);

-- Friends Table (for bill splitting)
create table if not exists friends (
    id uuid default gen_random_uuid() primary key,
    user_id uuid not null,
    name text not null,
    phone text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Debts Table
create table if not exists debts (
    id uuid default gen_random_uuid() primary key,
    user_id uuid not null,
    friend_id uuid references friends(id),
    amount decimal(10, 2) not null,
    description text,
    is_paid boolean default false,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- RLS Policies (Basic examples - user can see their own data)
alter table transactions enable row level security;
create policy "Users can select their own transactions"
on transactions for select
using (auth.uid() = user_id);

create policy "Users can insert their own transactions"
on transactions for insert
with check (auth.uid() = user_id);

alter table friends enable row level security;
create policy "Users can manage their own friends"
on friends for all
using (auth.uid() = user_id);

alter table debts enable row level security;
create policy "Users can manage their own debts"
on debts for all
using (auth.uid() = user_id);

-- Function to search for similar transactions
create or replace function match_transactions (
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  p_user_id uuid
)
returns table (
  id uuid,
  date date,
  amount decimal(10, 2),
  merchant text,
  category text,
  notes text,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    transactions.id,
    transactions.date,
    transactions.amount,
    transactions.merchant,
    transactions.category,
    transactions.notes,
    1 - (transactions.embedding <=> query_embedding) as similarity
  from transactions
  where 1 - (transactions.embedding <=> query_embedding) > match_threshold
  and transactions.user_id = p_user_id
  order by transactions.embedding <=> query_embedding
  limit match_count;
end;
$$;
