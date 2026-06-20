CREATE TABLE addresses (
    address       TEXT PRIMARY KEY,
    is_contract   BOOLEAN NOT NULL DEFAULT FALSE,
    first_seen_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE contracts (
    address          TEXT PRIMARY KEY REFERENCES addresses(address),
    name             TEXT,
    deployer_address TEXT REFERENCES addresses(address),
    deployed_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE token_transfers (
    id               BIGSERIAL PRIMARY KEY,
    transaction_hash TEXT NOT NULL REFERENCES transactions(hash),
    from_address     TEXT NOT NULL REFERENCES addresses(address),
    to_address       TEXT NOT NULL REFERENCES addresses(address),
    token_address    TEXT NOT NULL REFERENCES addresses(address),
    value            NUMERIC,
    block_timestamp  TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_token_transfers_token ON token_transfers(token_address);
CREATE INDEX idx_token_transfers_tx ON token_transfers(transaction_hash);

ALTER TABLE transactions
    ADD CONSTRAINT transactions_from_address_fkey FOREIGN KEY (from_address) REFERENCES addresses(address),
    ADD CONSTRAINT transactions_to_address_fkey FOREIGN KEY (to_address) REFERENCES addresses(address);