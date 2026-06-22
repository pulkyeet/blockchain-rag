from neo4j import GraphDatabase
from config import settings

driver = GraphDatabase.driver(
    settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
)

with driver.session() as session:
    result = session.run("""
        MATCH (caller:Address)-[:TX]->(router:Address {address: "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"})
        RETURN count(caller) AS total_callers
    """)
    print(result.single())

    result = session.run("""
        MATCH (caller:Address)-[:TX]->(router:Address {address: "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"})
        WHERE caller.is_contract = true
        RETURN count(caller) AS contract_callers
    """)
    print(result.single())
