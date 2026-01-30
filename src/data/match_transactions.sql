
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
