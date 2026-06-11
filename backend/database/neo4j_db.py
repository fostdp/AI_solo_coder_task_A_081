from neo4j import GraphDatabase
from config import get_settings

settings = get_settings()

_driver = None


def get_neo4j_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
    return _driver


def close_neo4j():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def run_query(query, parameters=None):
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run(query, parameters or {})
        return [record.data() for record in result]
