ONCHAIN_SCHEMA = """
TABLE addresses
  address       TEXT PRIMARY KEY     -- 0x-prefixed ethereum address
  is_contract   BOOLEAN              -- true if this address is a known contract
  first_seen_at TIMESTAMPTZ
  created_at    TIMESTAMPTZ

TABLE contracts
  address          TEXT PRIMARY KEY  -- FK to addresses.address
  name             TEXT              -- e.g. 'Uniswap V2 Router'
  deployer_address TEXT              -- FK to addresses.address
  deployed_at      TIMESTAMPTZ
  created_at       TIMESTAMPTZ

TABLE transactions
  hash            TEXT PRIMARY KEY
  block_number    BIGINT
  from_address    TEXT               -- FK to addresses.address
  to_address      TEXT               -- FK to addresses.address, the contract/router being called
  value_eth       NUMERIC(38,18)     -- ETH transferred in this tx
  gas_used        BIGINT
  block_timestamp TIMESTAMPTZ

TABLE token_transfers
  id               BIGSERIAL PRIMARY KEY
  transaction_hash TEXT              -- FK to transactions.hash
  from_address     TEXT              -- FK to addresses.address
  to_address       TEXT              -- FK to addresses.address
  token_address    TEXT              -- FK to addresses.address (which token, e.g. USDC)
  value             NUMERIC          -- raw token amount transferred (not decimal-adjusted)
  block_timestamp   TIMESTAMPTZ

NOTES:
- Data covers exactly 2024-01-01 to 2024-01-08, 4 routers (Uniswap V2/V3, SushiSwap, Balancer), 2 tokens (USDC, USDT).
- Join transactions.to_address = contracts.address to get a router's name.
- Join token_transfers.token_address = contracts.address to filter by token (USDC/USDT).
- contracts.name actual values: 'Uniswap V2 Router', 'Uniswap V3 SwapRouter', 'SushiSwap Router', 'Balancer Vault', 'USD Coin', 'Tether USD'.
- token_transfers.value is NOT decimal-adjusted (USDC/USDT have 6 decimals, divide by 1e6 for human-readable amounts).
"""
