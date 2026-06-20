from google.cloud import bigquery

client = bigquery.Client(project="blockchain-rag")

routers = {
    "uniswap_v2": "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
    "uniswap_v3": "0xe592427a0aece92de3edee1f18e0157c05861564",
    "sushiswap": "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f",
    "balancer": "0xba12222222228d8ba445958a75a0704d566bf2c8",
}

for name, addr in routers.items():
    q = f"""
    SELECT COUNT(*) as cnt
    FROM `bigquery-public-data.crypto_ethereum.transactions`
    WHERE DATE(block_timestamp) >= '2024-01-01' AND DATE(block_timestamp) < '2024-01-08'
      AND to_address = '{addr}'
    """
    result = list(client.query(q).result())[0]["cnt"]
    print(f"{name}: {result}")