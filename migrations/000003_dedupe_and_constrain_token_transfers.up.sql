-- remove duplicate rows, keep the lowest id per natural key
DELETE FROM token_transfers a
USING token_transfers b
WHERE a.id > b.id
  AND a.transaction_hash = b.transaction_hash
  AND a.from_address = b.from_address
  AND a.to_address = b.to_address
  AND a.token_address = b.token_address
  AND a.value = b.value
  AND a.block_timestamp = b.block_timestamp;

ALTER TABLE token_transfers
    ADD CONSTRAINT token_transfers_natural_key
    UNIQUE (transaction_hash, from_address, to_address, token_address, value, block_timestamp);