from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import networkx as nx

from database.mongodb import get_collection
from database.neo4j_db import run_query
from services.apriori_mining import Apriori
from services.louvain_community import LouvainCommunity

router = APIRouter(prefix="/mining", tags=["配伍规律挖掘"])


@router.get("/frequent-itemsets")
def frequent_itemsets(
    min_support: float = Query(default=0.05, ge=0.001, le=1.0),
    min_confidence: float = Query(default=0.3, ge=0.0, le=1.0),
    max_items: int = Query(default=5, ge=2, le=10),
    limit: int = Query(default=100, ge=1, le=1000)
):
    formulas_col = get_collection("formulas")
    
    transactions = []
    cursor = formulas_col.find({}, {"herbs.name": 1})
    for f in cursor:
        herb_names = [h["name"] for h in f["herbs"]]
        transactions.append(herb_names)
    
    apriori = Apriori(min_support=min_support, min_confidence=min_confidence)
    L, support_data = apriori.fit(transactions)
    
    itemsets_by_size = {}
    for k, itemsets in enumerate(L, 1):
        if k <= max_items:
            items = []
            for itemset, support in itemsets.items():
                items.append({
                    "items": sorted(list(itemset)),
                    "support": round(support, 4),
                    "count": int(support * len(transactions))
                })
            items.sort(key=lambda x: -x["support"])
            itemsets_by_size[f"{k}-item"] = items[:limit]
    
    return {
        "total_transactions": len(transactions),
        "min_support": min_support,
        "itemsets": itemsets_by_size
    }


@router.get("/association-rules")
def association_rules(
    min_support: float = Query(default=0.02, ge=0.001, le=1.0),
    min_confidence: float = Query(default=0.3, ge=0.0, le=1.0),
    min_lift: float = Query(default=1.0, ge=0.0),
    limit: int = Query(default=50, ge=1, le=500)
):
    formulas_col = get_collection("formulas")
    
    transactions = []
    cursor = formulas_col.find({}, {"herbs.name": 1})
    for f in cursor:
        herb_names = [h["name"] for h in f["herbs"]]
        transactions.append(herb_names)
    
    apriori = Apriori(min_support=min_support, min_confidence=min_confidence, min_lift=min_lift)
    apriori.fit(transactions)
    rules = apriori.generate_rules()
    
    return {
        "total_transactions": len(transactions),
        "min_support": min_support,
        "min_confidence": min_confidence,
        "min_lift": min_lift,
        "total_rules": len(rules),
        "rules": rules[:limit]
    }


@router.get("/top-herb-pairs")
def top_herb_pairs(
    n: int = Query(default=20, ge=1, le=200),
    min_support: float = Query(default=0.01, ge=0.001, le=1.0)
):
    formulas_col = get_collection("formulas")
    
    transactions = []
    cursor = formulas_col.find({}, {"herbs.name": 1})
    for f in cursor:
        herb_names = [h["name"] for h in f["herbs"]]
        transactions.append(herb_names)
    
    apriori = Apriori(min_support=min_support)
    apriori.fit(transactions)
    pairs = apriori.get_top_pairs(n)
    
    return {
        "total_transactions": len(transactions),
        "pairs": pairs
    }


@router.get("/top-herb-triplets")
def top_herb_triplets(
    n: int = Query(default=20, ge=1, le=100),
    min_support: float = Query(default=0.005, ge=0.001, le=1.0)
):
    formulas_col = get_collection("formulas")
    
    transactions = []
    cursor = formulas_col.find({}, {"herbs.name": 1})
    for f in cursor:
        herb_names = [h["name"] for h in f["herbs"]]
        transactions.append(herb_names)
    
    apriori = Apriori(min_support=min_support)
    apriori.fit(transactions)
    triplets = apriori.get_top_triplets(n)
    
    return {
        "total_transactions": len(transactions),
        "triplets": triplets
    }


@router.get("/communities")
def detect_communities(
    min_co_occurrence: int = Query(default=5, ge=1),
    resolution: float = Query(default=1.0, ge=0.1, le=5.0)
):
    query = """
    MATCH (h1:Herb)-[r:CO_OCCURS]->(h2:Herb)
    WHERE r.count >= $min_count
    RETURN h1.name AS herb_a, h2.name AS herb_b, r.count AS count, r.weight AS weight
    """
    
    results = run_query(query, {"min_count": min_co_occurrence})
    
    G = nx.Graph()
    for r in results:
        G.add_edge(r["herb_a"], r["herb_b"], weight=r["weight"], count=r["count"])
    
    if G.number_of_nodes() == 0:
        return {"communities": [], "modularity": 0, "total_nodes": 0}
    
    louvain = LouvainCommunity(resolution=resolution)
    louvain.fit(G)
    
    communities = louvain.get_communities()
    sizes = louvain.get_community_sizes()
    
    community_list = []
    for comm_id, herbs in communities.items():
        herb_info = []
        for herb in herbs:
            degree = G.degree(herb)
            herb_info.append({
                "name": herb,
                "degree": degree
            })
        herb_info.sort(key=lambda x: -x["degree"])
        
        community_list.append({
            "community_id": comm_id,
            "size": sizes[comm_id],
            "herbs": herb_info
        })
    
    community_list.sort(key=lambda x: -x["size"])
    
    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "modularity": round(louvain.modularity, 6),
        "num_communities": len(communities),
        "communities": community_list
    }


@router.get("/community/{community_id}")
def get_community_detail(
    community_id: int,
    min_co_occurrence: int = Query(default=5, ge=1),
    resolution: float = Query(default=1.0, ge=0.1, le=5.0)
):
    query = """
    MATCH (h1:Herb)-[r:CO_OCCURS]->(h2:Herb)
    WHERE r.count >= $min_count
    RETURN h1.name AS herb_a, h2.name AS herb_b, r.count AS count, r.weight AS weight
    """
    
    results = run_query(query, {"min_count": min_co_occurrence})
    
    G = nx.Graph()
    for r in results:
        G.add_edge(r["herb_a"], r["herb_b"], weight=r["weight"], count=r["count"])
    
    louvain = LouvainCommunity(resolution=resolution)
    louvain.fit(G)
    
    communities = louvain.get_communities()
    
    if community_id not in communities:
        raise HTTPException(status_code=404, detail="社区不存在")
    
    community_herbs = communities[community_id]
    subgraph = G.subgraph(community_herbs)
    
    nodes = []
    for herb in community_herbs:
        degree = subgraph.degree(herb)
        nodes.append({
            "id": f"herb_{herb}",
            "label": herb,
            "type": "herb",
            "degree": degree
        })
    
    edges = []
    for u, v, data in subgraph.edges(data=True):
        edges.append({
            "source": f"herb_{u}",
            "target": f"herb_{v}",
            "weight": data.get("weight", 1),
            "count": data.get("count", 1)
        })
    
    herb_query = """
    MATCH (h:Herb)
    WHERE h.name IN $names
    RETURN h.name AS name, h.nature AS nature, h.category AS category, 
           h.flavor AS flavor, h.meridians AS meridians
    """
    
    herb_details = run_query(herb_query, {"names": community_herbs})
    herb_info_map = {h["name"]: h for h in herb_details}
    
    for node in nodes:
        info = herb_info_map.get(node["label"], {})
        node["properties"] = {
            "nature": info.get("nature", ""),
            "category": info.get("category", ""),
            "flavor": info.get("flavor", []),
            "meridians": info.get("meridians", [])
        }
    
    return {
        "community_id": community_id,
        "size": len(community_herbs),
        "nodes": nodes,
        "edges": edges
    }


@router.get("/by-disease/{disease_name}")
def mining_by_disease(
    disease_name: str,
    min_support: float = Query(default=0.05, ge=0.001, le=1.0),
    min_confidence: float = Query(default=0.3, ge=0.0, le=1.0)
):
    formulas_col = get_collection("formulas")
    
    cursor = formulas_col.find({"indications": {"$in": [disease_name]}}, {"herbs.name": 1})
    
    transactions = []
    for f in cursor:
        herb_names = [h["name"] for h in f["herbs"]]
        transactions.append(herb_names)
    
    if not transactions:
        raise HTTPException(status_code=404, detail=f"未找到治疗{disease_name}的方剂")
    
    apriori = Apriori(min_support=min_support, min_confidence=min_confidence)
    apriori.fit(transactions)
    rules = apriori.generate_rules()
    pairs = apriori.get_top_pairs(20)
    triplets = apriori.get_top_triplets(10)
    
    return {
        "disease": disease_name,
        "total_formulas": len(transactions),
        "top_pairs": pairs,
        "top_triplets": triplets,
        "rules": rules[:30]
    }
