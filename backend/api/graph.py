from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from database.neo4j_db import run_query

router = APIRouter(prefix="/graph", tags=["图数据"])


@router.get("/network")
def get_graph_network(
    node_types: Optional[List[str]] = Query(default=None),
    limit_per_type: int = 50,
    include_relations: bool = True
):
    nodes = []
    edges = []
    
    if node_types is None or "Herb" in node_types:
        herb_query = """
        MATCH (h:Herb)
        RETURN h
        LIMIT $limit
        """
        herbs = run_query(herb_query, {"limit": limit_per_type})
        for h in herbs:
            herb_data = h["h"]
            nodes.append({
                "id": f"herb_{herb_data['name']}",
                "label": herb_data["name"],
                "type": "herb",
                "properties": {
                    "nature": herb_data.get("nature", ""),
                    "flavor": herb_data.get("flavor", []),
                    "meridians": herb_data.get("meridians", []),
                    "category": herb_data.get("category", "")
                }
            })
    
    if node_types is None or "Formula" in node_types:
        formula_query = """
        MATCH (f:Formula)
        RETURN f
        ORDER BY f.frequency DESC
        LIMIT $limit
        """
        formulas = run_query(formula_query, {"limit": limit_per_type})
        for f in formulas:
            formula_data = f["f"]
            nodes.append({
                "id": f"formula_{formula_data['name']}",
                "label": formula_data["name"],
                "type": "formula",
                "size": formula_data.get("frequency", 1),
                "properties": {
                    "dynasty": formula_data.get("dynasty", ""),
                    "author": formula_data.get("author", ""),
                    "frequency": formula_data.get("frequency", 1),
                    "source": formula_data.get("source", "")
                }
            })
    
    if node_types is None or "Disease" in node_types:
        disease_query = """
        MATCH (d:Disease)
        RETURN d
        LIMIT $limit
        """
        diseases = run_query(disease_query, {"limit": limit_per_type})
        for d in diseases:
            disease_data = d["d"]
            nodes.append({
                "id": f"disease_{disease_data['name']}",
                "label": disease_data["name"],
                "type": "disease",
                "properties": {
                    "category": disease_data.get("category", ""),
                    "symptoms": disease_data.get("symptoms", [])
                }
            })
    
    if include_relations:
        node_ids = [n["id"] for n in nodes]
        
        contains_query = """
        MATCH (f:Formula)-[:CONTAINS]->(h:Herb)
        WHERE f.name IN $formula_names AND h.name IN $herb_names
        RETURN f.name AS source, h.name AS target, 'CONTAINS' AS type
        """
        
        formula_names = [n["label"] for n in nodes if n["type"] == "formula"]
        herb_names = [n["label"] for n in nodes if n["type"] == "herb"]
        
        if formula_names and herb_names:
            contains_rels = run_query(
                contains_query,
                {"formula_names": formula_names, "herb_names": herb_names}
            )
            for rel in contains_rels:
                edges.append({
                    "source": f"formula_{rel['source']}",
                    "target": f"herb_{rel['target']}",
                    "label": "contains",
                    "type": "contains"
                })
        
        treats_query = """
        MATCH (f:Formula)-[:TREATS]->(d:Disease)
        WHERE f.name IN $formula_names AND d.name IN $disease_names
        RETURN f.name AS source, d.name AS target, 'TREATS' AS type
        """
        
        disease_names = [n["label"] for n in nodes if n["type"] == "disease"]
        
        if formula_names and disease_names:
            treats_rels = run_query(
                treats_query,
                {"formula_names": formula_names, "disease_names": disease_names}
            )
            for rel in treats_rels:
                edges.append({
                    "source": f"formula_{rel['source']}",
                    "target": f"disease_{rel['target']}",
                    "label": "treats",
                    "type": "treats"
                })
        
        co_occurs_query = """
        MATCH (h1:Herb)-[r:CO_OCCURS]->(h2:Herb)
        WHERE h1.name IN $herb_names AND h2.name IN $herb_names
        RETURN h1.name AS source, h2.name AS target, r.count AS count, r.weight AS weight
        ORDER BY r.weight DESC
        LIMIT 100
        """
        
        if herb_names:
            co_occurs = run_query(
                co_occurs_query,
                {"herb_names": herb_names}
            )
            for rel in co_occurs:
                edges.append({
                    "source": f"herb_{rel['source']}",
                    "target": f"herb_{rel['target']}",
                    "label": "co-occurs",
                    "type": "co_occurs",
                    "weight": rel.get("weight", 0),
                    "count": rel.get("count", 0)
                })
    
    return {"nodes": nodes, "edges": edges, "total_nodes": len(nodes), "total_edges": len(edges)}


@router.get("/herb-cooccurrence")
def get_herb_cooccurrence(
    min_count: int = 10,
    limit: int = 100
):
    query = """
    MATCH (h1:Herb)-[r:CO_OCCURS]->(h2:Herb)
    WHERE r.count >= $min_count
    RETURN h1.name AS herb_a, h2.name AS herb_b, r.count AS count, r.weight AS weight
    ORDER BY r.weight DESC
    LIMIT $limit
    """
    
    results = run_query(query, {"min_count": min_count, "limit": limit})
    return {"pairs": results, "total": len(results)}


@router.get("/disease-formulas/{disease_name}")
def get_disease_formula_graph(disease_name: str):
    query = """
    MATCH (d:Disease {name: $disease_name})
    OPTIONAL MATCH (f:Formula)-[:TREATS]->(d)
    OPTIONAL MATCH (f)-[:CONTAINS]->(h:Herb)
    WITH d, COLLECT(DISTINCT f) AS formulas, COLLECT(DISTINCT h) AS herbs
    RETURN d, formulas, herbs
    """
    
    results = run_query(query, {"disease_name": disease_name})
    
    if not results:
        raise HTTPException(status_code=404, detail="病症不存在")
    
    result = results[0]
    nodes = []
    edges = []
    
    disease_data = result["d"]
    nodes.append({
        "id": f"disease_{disease_data['name']}",
        "label": disease_data["name"],
        "type": "disease",
        "properties": {
            "category": disease_data.get("category", ""),
            "symptoms": disease_data.get("symptoms", [])
        }
    })
    
    formula_set = set()
    herb_set = set()
    
    for f in result["formulas"]:
        fid = f"formula_{f['name']}"
        if fid not in formula_set:
            formula_set.add(fid)
            nodes.append({
                "id": fid,
                "label": f["name"],
                "type": "formula",
                "size": f.get("frequency", 1),
                "properties": {
                    "dynasty": f.get("dynasty", ""),
                    "author": f.get("author", ""),
                    "frequency": f.get("frequency", 1)
                }
            })
            edges.append({
                "source": fid,
                "target": f"disease_{disease_name}",
                "label": "treats",
                "type": "treats"
            })
    
    for h in result["herbs"]:
        hid = f"herb_{h['name']}"
        if hid not in herb_set:
            herb_set.add(hid)
            nodes.append({
                "id": hid,
                "label": h["name"],
                "type": "herb",
                "properties": {
                    "nature": h.get("nature", ""),
                    "category": h.get("category", "")
                }
            })
    
    return {"nodes": nodes, "edges": edges, "total_nodes": len(nodes), "total_edges": len(edges)}


@router.get("/herb-formulas/{herb_name}")
def get_herb_formula_graph(herb_name: str, depth: int = 1):
    query = """
    MATCH (h:Herb {name: $herb_name})
    OPTIONAL MATCH (f:Formula)-[:CONTAINS]->(h)
    OPTIONAL MATCH (f)-[:TREATS]->(d:Disease)
    WITH h, COLLECT(DISTINCT f) AS formulas, COLLECT(DISTINCT d) AS diseases
    RETURN h, formulas, diseases
    """
    
    results = run_query(query, {"herb_name": herb_name})
    
    if not results:
        raise HTTPException(status_code=404, detail="药物不存在")
    
    result = results[0]
    nodes = []
    edges = []
    
    herb_data = result["h"]
    nodes.append({
        "id": f"herb_{herb_data['name']}",
        "label": herb_data["name"],
        "type": "herb",
        "properties": {
            "nature": herb_data.get("nature", ""),
            "flavor": herb_data.get("flavor", []),
            "meridians": herb_data.get("meridians", []),
            "category": herb_data.get("category", "")
        }
    })
    
    formula_set = set()
    disease_set = set()
    
    for f in result["formulas"]:
        fid = f"formula_{f['name']}"
        if fid not in formula_set:
            formula_set.add(fid)
            nodes.append({
                "id": fid,
                "label": f["name"],
                "type": "formula",
                "size": f.get("frequency", 1),
                "properties": {
                    "dynasty": f.get("dynasty", ""),
                    "author": f.get("author", ""),
                    "frequency": f.get("frequency", 1)
                }
            })
            edges.append({
                "source": fid,
                "target": f"herb_{herb_name}",
                "label": "contains",
                "type": "contains"
            })
    
    for d in result["diseases"]:
        did = f"disease_{d['name']}"
        if did not in disease_set:
            disease_set.add(did)
            nodes.append({
                "id": did,
                "label": d["name"],
                "type": "disease",
                "properties": {
                    "category": d.get("category", "")
                }
            })
    
    return {"nodes": nodes, "edges": edges, "total_nodes": len(nodes), "total_edges": len(edges)}


@router.get("/formula-detail/{formula_name}")
def get_formula_detail_graph(formula_name: str):
    query = """
    MATCH (f:Formula {name: $formula_name})
    OPTIONAL MATCH (f)-[:CONTAINS]->(h:Herb)
    OPTIONAL MATCH (f)-[:TREATS]->(d:Disease)
    WITH f, COLLECT(DISTINCT h) AS herbs, COLLECT(DISTINCT d) AS diseases
    RETURN f, herbs, diseases
    """
    
    results = run_query(query, {"formula_name": formula_name})
    
    if not results:
        raise HTTPException(status_code=404, detail="方剂不存在")
    
    result = results[0]
    nodes = []
    edges = []
    
    formula_data = result["f"]
    nodes.append({
        "id": f"formula_{formula_data['name']}",
        "label": formula_data["name"],
        "type": "formula",
        "size": formula_data.get("frequency", 1),
        "properties": {
            "dynasty": formula_data.get("dynasty", ""),
            "author": formula_data.get("author", ""),
            "frequency": formula_data.get("frequency", 1),
            "source": formula_data.get("source", ""),
            "form": formula_data.get("form", "")
        }
    })
    
    for h in result["herbs"]:
        hid = f"herb_{h['name']}"
        nodes.append({
            "id": hid,
            "label": h["name"],
            "type": "herb",
            "properties": {
                "nature": h.get("nature", ""),
                "category": h.get("category", ""),
                "meridians": h.get("meridians", [])
            }
        })
        edges.append({
            "source": f"formula_{formula_name}",
            "target": hid,
            "label": "contains",
            "type": "contains"
        })
    
    for d in result["diseases"]:
        did = f"disease_{d['name']}"
        nodes.append({
            "id": did,
            "label": d["name"],
            "type": "disease",
            "properties": {
                "category": d.get("category", ""),
                "symptoms": d.get("symptoms", [])
            }
        })
        edges.append({
            "source": f"formula_{formula_name}",
            "target": did,
            "label": "treats",
            "type": "treats"
        })
    
    return {"nodes": nodes, "edges": edges, "total_nodes": len(nodes), "total_edges": len(edges)}
