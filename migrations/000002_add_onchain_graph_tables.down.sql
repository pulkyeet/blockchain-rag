ALTER TABLE transactions
    DROP CONSTRAINT IF EXISTS transactions_from_address_fkey,
    DROP CONSTRAINT IF EXISTS transactions_to_address_fkey;

DROP TABLE IF EXISTS token_transfers;
DROP TABLE IF EXISTS contracts;
DROP TABLE IF EXISTS addresses;