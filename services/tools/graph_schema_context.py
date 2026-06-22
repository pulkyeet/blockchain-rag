"""
Hardcoded Neo4j graph schema context, same rationale as services/tools/schema_context.py:
schema is migration/loader-controlled, not introspected live.

CRITICAL: token/value notation must match Postgres source exactly, same lesson as
schema_context.py's USDC/USDT 6-decimal note -- value on TRANSFERRED is the raw
on-chain integer (6 decimals for USDC/USDT), value_eth on TX is already human-readable ETH.
"""

GRAPH_SCHEMA_CONTEXT = """
Graph schema:

Node: (:Address {address: string, is_contract: bool, name: string|null})
  - name is non-null only for known contracts (e.g. "Uniswap V2 Router", "USDC").
  - Wallets (is_contract=false) have name = null.

Edge: (:Address)-[:TX {hash, value_eth, gas_used, block_timestamp}]->(:Address)
  - Represents a raw ETH transaction. value_eth is already in ETH (not wei).
  - Direction: (from)-[:TX]->(to), i.e. (caller)-[:TX]->(called_contract_or_recipient).
  - IMPORTANT: known router/contract addresses in this dataset are almost always the
    TARGET of calls, not the initiator. "What contracts/wallets interacted with router X"
    means "who called X", which is the INCOMING direction: (caller)-[:TX]->(router).
    Use MATCH (other:Address)-[:TX]->(router:Address {address: "0x..."}) for this,
    NOT (router)-[:TX]->(other). Only use the outgoing direction if the question is
    explicitly about what the router/contract itself sent to others.

Edge: (:Address)-[:TRANSFERRED {tx_hash, token_address, token_symbol, value, block_timestamp}]->(:Address)
  - Represents an ERC-20 token transfer. value is the RAW on-chain integer
    (USDC/USDT both use 6 decimals -- divide by 1e6 to get human-readable amount).
  - token_symbol is the human name (e.g. "USDC") resolved from the contracts table, may be null.
  - Direction: (from)-[:TRANSFERRED]->(to).
  - A single transaction (tx_hash) can have multiple TRANSFERRED edges (multi-hop swaps).

Known contract addresses in this dataset (one-week window, 2024-01-01 to 2024-01-08):
  - Uniswap V2 Router: 0x7a250d5630b4cf539739df2c5dacb4c659f2488d
  - Uniswap V3 SwapRouter: 0xe592427a0aece92de3edee1f18e0157c05861564
  - SushiSwap Router: 0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f
  - Balancer Vault: 0xba12222222228d8ba445958a75a0704d566bf2c8
  - USDC token: 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48
  - USDT token: 0xdac17f958d2ee523a2206206994597c13d831ec7

Do not assume any other address/name exists. If the question names a wallet/contract not
in this list and not given explicitly as a 0x address, you cannot resolve it.

Example queries:

"What contracts/wallets did the Uniswap V2 Router interact with?"
"What contracts did the Uniswap V2 Router interact with?"
"Who interacted with the Uniswap V2 Router?"
-> All of these ask who CALLED the router (router is the TARGET, not the initiator):
MATCH (caller:Address)-[:TX]->(router:Address {address: "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"})
RETURN DISTINCT caller.address, caller.is_contract, caller.name
LIMIT 50

"What contracts/addresses did wallet 0xABC (a non-router, ordinary wallet) send transactions to?"
-> This asks what the wallet INITIATED (wallet is the source):
MATCH (w:Address {address: "0xABC"})-[:TX]->(c:Address {is_contract: true})
RETURN DISTINCT c.address, c.name
LIMIT 50

RULE OF THUMB: for any question of the form "what did X interact with", if X is one of
the known router/contract addresses listed above, X is virtually always the TARGET of the
interaction (people call into it), so the correct pattern is
(other:Address)-[:TX]->(X:Address {address: "0x..."}) with X on the right side of the arrow.
Only put a known router/contract on the LEFT side of -[:TX]-> if the question explicitly
asks what that contract itself sent out.

"Show me a wallet's transfer path within 2 hops of the Uniswap V2 Router"
MATCH (router:Address {address: "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"})
MATCH path = (router)-[:TRANSFERRED*1..2]->(end:Address)
RETURN path
LIMIT 50

"Did wallet 0xABC ever send tokens to wallet 0xDEF?"
MATCH (a:Address {address: "0xABC"})-[t:TRANSFERRED]->(b:Address {address: "0xDEF"})
RETURN t.token_symbol, t.value, t.block_timestamp
LIMIT 50
"""
