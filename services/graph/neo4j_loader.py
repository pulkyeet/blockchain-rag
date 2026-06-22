import psycopg
from neo4j import GraphDatabase

from config import settings

BATCH_SIZE = 5_000

def get_pg_conn():
    return psycopg.connect(settings.postgres_url)

def load_addresses(pg_conn, neo4j_driver):
    # Pass 1: addresses -> Address nodes (LEFT JOIN contracts for name)
    with pg_conn.cursor() as cur:
        cur.execute("""
                    SELECT a.address, a.is_contract, c.name FROM addresses a LEFT JOIN contracts c ON c.address = a.address""")
        rows = cur.fetchall()
        print(f"[addresses] {len(rows)} rows to load")

        with neo4j_driver.session() as session:
            for i in range(0, len(rows), BATCH_SIZE):
                batch = rows[i:i+BATCH_SIZE]
                params = [{
                    "address": addr, "is_contract": is_contract, "name": name
                } for addr, is_contract, name in batch]
                session.run(
                    """
                    UNWIND $rows AS row
                    MERGE (a:Address {address: row.address})
                    SET a.is_contract = row.is_contract,
                        a.name = row.name""",
                    rows=params
                )
                print(f"[addresses] loaded {min(i + BATCH_SIZE, len(rows))}/{len(rows)}")

def load_transactions(pg_conn, neo4j_driver):
    # Pass 2: txns -> tnx edges (if contract, to_address would be NULL; we can skip them)
    with pg_conn.cursor() as cur:
        cur.execute("""
SELECT hash, from_address, to_address, value_eth, gas_used, block_timestamp
                    FROM transactions
                    WHERE to_address IS NOT NULL""")
        rows = cur.fetchall()
        print(f"[transactions] {len(rows)} rows to load")

        with neo4j_driver.session() as session:
            for i in range(0, len(rows), BATCH_SIZE):
                batch = rows[i:i+BATCH_SIZE]
                params = [{
                    "hash": h,
                    "from_address": frm,
                    "to_address": to,
                    "value_eth": float(value_eth),
                    "gas_used": gas_used,
                    "block_timestamp": ts.isoformat(),
                } for h, frm, to, value_eth, gas_used, ts in batch]

                session.run("""UNWIND $rows AS row
                MATCH (from:Address {address: row.from_address})
                MATCH (to:Address {address: row.to_address})
                MERGE (from)-[t:TX {hash: row.hash}]->(to)
                SET t.value_eth = row.value_eth,
                    t.gas_used = row.gas_used,
                    t.block_timestamp = row.block_timestamp""", rows=params)
                print(f"[transactions] loaded {min(i+BATCH_SIZE, len(rows))}/{len(rows)}")

def load_token_transfers(pg_conn, neo4j_driver):
    """Pass 3: token_transfers -> TRANSFERRED edges. token_symbol resolved from contracts.name."""
    with pg_conn.cursor() as cur:
        cur.execute("""
            SELECT tt.transaction_hash, tt.from_address, tt.to_address,
                   tt.token_address, c.name AS token_symbol, tt.value, tt.block_timestamp
            FROM token_transfers tt
            LEFT JOIN contracts c ON c.address = tt.token_address
        """)
        rows = cur.fetchall()
 
    print(f"[token_transfers] {len(rows)} rows to load")
 
    with neo4j_driver.session() as session:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            params = [
                {
                    "tx_hash": tx_hash,
                    "from_address": frm,
                    "to_address": to,
                    "token_address": token_addr,
                    "token_symbol": symbol,
                    "value": float(value) if value is not None else None,
                    "block_timestamp": ts.isoformat(),
                }
                for tx_hash, frm, to, token_addr, symbol, value, ts in batch
            ]
            session.run(
                """
                UNWIND $rows AS row
                MATCH (from:Address {address: row.from_address})
                MATCH (to:Address {address: row.to_address})
                MERGE (from)-[xfer:TRANSFERRED {
                    tx_hash: row.tx_hash,
                    token_address: row.token_address,
                    from_address: row.from_address,
                    to_address: row.to_address
                }]->(to)
                SET xfer.token_symbol = row.token_symbol,
                    xfer.value = row.value,
                    xfer.block_timestamp = row.block_timestamp
                """,
                rows=params,
            )
            print(f"[token_transfers] loaded {min(i + BATCH_SIZE, len(rows))}/{len(rows)}")

def create_constraints(neo4j_driver):
    """Unique constraint on Address.address - required for MERGE to be idempotent and fast"""
    with neo4j_driver.session() as session:
        session.run(
            "CREATE CONSTRAINT address_unique IF NOT EXISTS "
            "FOR (a:Address) REQUIRE a.address IS UNIQUE"
        )

def main():
    pg_conn = get_pg_conn()
    neo4j_driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

    try:
        create_constraints(neo4j_driver)
        load_addresses(pg_conn, neo4j_driver)
        load_transactions(pg_conn, neo4j_driver)
        load_token_transfers(pg_conn, neo4j_driver)
    finally:
        pg_conn.close()
        neo4j_driver.close()
    
    print("Loading of Addresses, transactions and Token Transfers is complete.")

if __name__=="__main__":
    main()