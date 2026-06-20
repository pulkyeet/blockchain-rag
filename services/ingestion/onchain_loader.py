from datetime import date
from decimal import Decimal

import psycopg
from google.cloud import bigquery

ROUTERS = {
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2 Router",
    "0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap V3 SwapRouter",
    "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f": "SushiSwap Router",
    "0xba12222222228d8ba445958a75a0704d566bf2c8": "Balancer Vault",
}
TOKENS = {
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USD Coin",
    "0xdac17f958d2ee523a2206206994597c13d831ec7": "Tether USD",
}
KNOWN_CONTRACTS = {**ROUTERS, **TOKENS}

START_DATE = date(2024, 1, 1)
END_DATE = date(2024, 1, 8) 


class OnchainLoader:
    def __init__(self, pg_url: str, bq_project: str):
        self.pg_url = pg_url
        self.bq_client = bigquery.Client(project=bq_project)

    def fetch_router_transactions(self) -> list[dict]:
        query = """
        SELECT `hash`, from_address, to_address, value, gas, block_number, block_timestamp
        FROM `bigquery-public-data.crypto_ethereum.transactions`
        WHERE DATE(block_timestamp) >= @start_date
          AND DATE(block_timestamp) < @end_date
          AND to_address IN UNNEST(@routers)
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "DATE", START_DATE),
                bigquery.ScalarQueryParameter("end_date", "DATE", END_DATE),
                bigquery.ArrayQueryParameter("routers", "STRING", list(ROUTERS.keys())),
            ]
        )
        return [dict(row) for row in self.bq_client.query(query, job_config=job_config).result()]

    def fetch_transfers_for_transactions(self, tx_hashes: list[str]) -> list[dict]:
        """Token transfers inside the given transactions. Bounded by tx_hashes,
        so FK to transactions is satisfied by construction."""
        if not tx_hashes:
            return []
        query = """
        SELECT transaction_hash, from_address, to_address, token_address, value, block_timestamp
        FROM `bigquery-public-data.crypto_ethereum.token_transfers`
        WHERE DATE(block_timestamp) >= @start_date
          AND DATE(block_timestamp) < @end_date
          AND transaction_hash IN UNNEST(@hashes)
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("start_date", "DATE", START_DATE),
                bigquery.ScalarQueryParameter("end_date", "DATE", END_DATE),
                bigquery.ArrayQueryParameter("hashes", "STRING", tx_hashes),
            ]
        )
        return [dict(row) for row in self.bq_client.query(query, job_config=job_config).result()]

    def load(self):
        txs = self.fetch_router_transactions()
        print(f"fetched {len(txs)} router transactions (4 routers combined)")

        tx_hashes = [tx["hash"] for tx in txs]
        transfers = self.fetch_transfers_for_transactions(tx_hashes)
        print(f"fetched {len(transfers)} token transfers (bounded by router tx hashes)")

        addresses: set[str] = set()
        for tx in txs:
            addresses.add(tx["from_address"])
            if tx["to_address"]:
                addresses.add(tx["to_address"])
        for tr in transfers:
            addresses.add(tr["from_address"])
            addresses.add(tr["to_address"])
            addresses.add(tr["token_address"])
        addresses.update(KNOWN_CONTRACTS.keys())

        with psycopg.connect(self.pg_url) as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """INSERT INTO addresses (address, is_contract)
                       VALUES (%s, %s)
                       ON CONFLICT (address) DO NOTHING""",
                    [(addr, addr in KNOWN_CONTRACTS) for addr in addresses],
                )

                cur.executemany(
                    """INSERT INTO contracts (address, name)
                       VALUES (%s, %s)
                       ON CONFLICT (address) DO NOTHING""",
                    [(addr, name) for addr, name in KNOWN_CONTRACTS.items()],
                )

                cur.executemany(
                    """INSERT INTO transactions
                       (hash, block_number, from_address, to_address, value_eth, gas_used, block_timestamp)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (hash) DO NOTHING""",
                    [
                        (
                            tx["hash"],
                            tx["block_number"],
                            tx["from_address"],
                            tx["to_address"],
                            Decimal(tx["value"]) / Decimal(10**18),
                            tx["gas"],
                            tx["block_timestamp"],
                        )
                        for tx in txs
                    ],
                )

                cur.executemany(
                    """INSERT INTO token_transfers
                       (transaction_hash, from_address, to_address, token_address, value, block_timestamp)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT DO NOTHING""",
                    [
                        (
                            tr["transaction_hash"],
                            tr["from_address"],
                            tr["to_address"],
                            tr["token_address"],
                            Decimal(tr["value"]),
                            tr["block_timestamp"],
                        )
                        for tr in transfers
                    ],
                )

            conn.commit()

        print(
            f"loaded {len(addresses)} addresses, {len(KNOWN_CONTRACTS)} contracts, "
            f"{len(txs)} transactions, {len(transfers)} token_transfers"
        )


if __name__ == "__main__":
    from config import settings

    loader = OnchainLoader(pg_url=settings.postgres_url, bq_project="blockchain-rag")
    loader.load()