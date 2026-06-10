-- documents: tracks ingested source files
CREATE TABLE documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source      TEXT NOT NULL,
    doc_type    TEXT NOT NULL,
    checksum    TEXT NOT NULL UNIQUE,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- chunks: individual text chunks from documents
CREATE TABLE chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    text        TEXT NOT NULL,
    chunk_index INT NOT NULL,
    token_count INT NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}'
);

-- transactions: on-chain data (Text-to-SQL target)
CREATE TABLE transactions (
    hash            TEXT PRIMARY KEY,
    block_number    BIGINT NOT NULL,
    from_address    TEXT NOT NULL,
    to_address      TEXT,
    value_eth       NUMERIC(38, 18) NOT NULL DEFAULT 0,
    gas_used        BIGINT,
    block_timestamp TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_transactions_from ON transactions(from_address);
CREATE INDEX idx_transactions_to ON transactions(to_address);
CREATE INDEX idx_transactions_block ON transactions(block_number);

-- read-only role for Text-to-SQL tool (SQL safety)
CREATE ROLE rag_readonly;
GRANT CONNECT ON DATABASE bc_rag TO rag_readonly;
GRANT USAGE ON SCHEMA public TO rag_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO rag_readonly;