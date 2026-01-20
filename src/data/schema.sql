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
