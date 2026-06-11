import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.neo4j_db import get_neo4j_driver, run_query
from database.mongodb import get_collection


def clear_neo4j():
    print("清空Neo4j数据库...")
    run_query("MATCH (n) DETACH DELETE n")
    print("已清空")


def create_constraints():
    print("创建索引和约束...")
    queries = [
        "CREATE CONSTRAINT herb_name IF NOT EXISTS FOR (h:Herb) REQUIRE h.name IS UNIQUE",
        "CREATE CONSTRAINT formula_name IF NOT EXISTS FOR (f:Formula) REQUIRE f.name IS UNIQUE",
        "CREATE CONSTRAINT disease_name IF NOT EXISTS FOR (d:Disease) REQUIRE d.name IS UNIQUE",
        "CREATE INDEX herb_category IF NOT EXISTS FOR (h:Herb) ON (h.category)",
        "CREATE INDEX formula_dynasty IF NOT EXISTS FOR (f:Formula) ON (f.dynasty)",
        "CREATE INDEX disease_category IF NOT EXISTS FOR (d:Disease) ON (d.category)",
    ]
    for q in queries:
        try:
            run_query(q)
        except Exception as e:
            print(f"  跳过: {e}")
    print("索引创建完成")


def import_herbs():
    print("导入中药节点...")
    herbs_col = get_collection("herbs")
    herbs = list(herbs_col.find())
    
    driver = get_neo4j_driver()
    with driver.session() as session:
        for herb in herbs:
            session.run(
                """
                CREATE (h:Herb {
                    name: $name,
                    nature: $nature,
                    flavor: $flavor,
                    meridians: $meridians,
                    category: $category
                })
                """,
                {
                    "name": herb["name"],
                    "nature": herb["nature"],
                    "flavor": herb["flavor"],
                    "meridians": herb["meridians"],
                    "category": herb["category"]
                }
            )
    print(f"已导入 {len(herbs)} 味中药")


def import_diseases():
    print("导入病症节点...")
    diseases_col = get_collection("diseases")
    diseases = list(diseases_col.find())
    
    driver = get_neo4j_driver()
    with driver.session() as session:
        for disease in diseases:
            session.run(
                """
                CREATE (d:Disease {
                    name: $name,
                    category: $category,
                    symptoms: $symptoms
                })
                """,
                {
                    "name": disease["name"],
                    "category": disease["category"],
                    "symptoms": disease["symptoms"]
                }
            )
    print(f"已导入 {len(diseases)} 种病症")


def import_formulas_and_relations(batch_size=100):
    print("导入方剂节点及关系...")
    formulas_col = get_collection("formulas")
    total = formulas_col.count_documents({})
    
    driver = get_neo4j_driver()
    processed = 0
    
    cursor = formulas_col.find(batch_size=batch_size)
    batch = []
    
    for formula in cursor:
        batch.append(formula)
        if len(batch) >= batch_size:
            with driver.session() as session:
                for f in batch:
                    herb_names = [h["name"] for h in f["herbs"]]
                    herb_dosages = [h["dosage"] for h in f["herbs"]]
                    
                    session.run(
                        """
                        CREATE (form:Formula {
                            name: $name,
                            dynasty: $dynasty,
                            author: $author,
                            frequency: $frequency,
                            source: $source,
                            form: $form
                        })
                        WITH form
                        UNWIND $herb_names AS herb_name
                        MATCH (h:Herb {name: herb_name})
                        CREATE (form)-[:CONTAINS {dosage: ''}]->(h)
                        WITH form
                        UNWIND $indications AS disease_name
                        MATCH (d:Disease {name: disease_name})
                        CREATE (form)-[:TREATS]->(d)
                        """,
                        {
                            "name": f["name"],
                            "dynasty": f["dynasty"],
                            "author": f["author"],
                            "frequency": f["frequency"],
                            "source": f.get("source", ""),
                            "form": f.get("form", ""),
                            "herb_names": herb_names,
                            "indications": f["indications"]
                        }
                    )
            processed += len(batch)
            print(f"  进度: {processed}/{total}")
            batch = []
    
    if batch:
        with driver.session() as session:
            for f in batch:
                herb_names = [h["name"] for h in f["herbs"]]
                session.run(
                    """
                    CREATE (form:Formula {
                        name: $name,
                        dynasty: $dynasty,
                        author: $author,
                        frequency: $frequency,
                        source: $source,
                        form: $form
                    })
                    WITH form
                    UNWIND $herb_names AS herb_name
                    MATCH (h:Herb {name: herb_name})
                    CREATE (form)-[:CONTAINS]->(h)
                    WITH form
                    UNWIND $indications AS disease_name
                    MATCH (d:Disease {name: disease_name})
                    CREATE (form)-[:TREATS]->(d)
                    """,
                    {
                        "name": f["name"],
                        "dynasty": f["dynasty"],
                        "author": f["author"],
                        "frequency": f["frequency"],
                        "source": f.get("source", ""),
                        "form": f.get("form", ""),
                        "herb_names": herb_names,
                        "indications": f["indications"]
                    }
                )
        processed += len(batch)
        print(f"  进度: {processed}/{total}")
    
    print(f"已导入 {total} 首方剂及关联关系")


def create_herb_cooccurrence():
    print("计算药物共现关系...")
    
    query = """
    MATCH (f:Formula)-[:CONTAINS]->(h1:Herb)
    MATCH (f:Formula)-[:CONTAINS]->(h2:Herb)
    WHERE h1.name < h2.name
    WITH h1, h2, COUNT(f) AS co_count, SUM(f.frequency) AS weight
    CREATE (h1)-[:CO_OCCURS {count: co_count, weight: weight}]->(h2)
    """
    
    run_query(query)
    print("药物共现关系创建完成")


def import_all():
    print("=" * 50)
    print("开始 Neo4j 图数据库数据导入")
    print("=" * 50)
    
    clear_neo4j()
    create_constraints()
    import_herbs()
    import_diseases()
    import_formulas_and_relations()
    create_herb_cooccurrence()
    
    print()
    print("=" * 50)
    print("Neo4j 数据导入完成！")
    print("=" * 50)
    
    stats = run_query("MATCH (n) RETURN labels(n)[0] as label, count(n) as count")
    print("\n节点统计:")
    for s in stats:
        print(f"  {s['label']}: {s['count']}")
    
    rel_stats = run_query("MATCH ()-[r]->() RETURN type(r) as rel, count(r) as count")
    print("\n关系统计:")
    for s in rel_stats:
        print(f"  {s['rel']}: {s['count']}")


if __name__ == "__main__":
    import_all()
