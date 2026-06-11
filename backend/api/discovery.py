from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import networkx as nx

from database.mongodb import get_collection
from database.neo4j_db import run_query
from services.link_prediction import LinkPredictor

router = APIRouter(prefix="/discovery", tags=["新药发现辅助"])


@router.get("/link-prediction")
def link_prediction(
    method: str = Query(default="adamic_adar", 
                       description="预测方法: common_neighbors, jaccard, adamic_adar, resource_allocation, preferential_attachment"),
    top_n: int = Query(default=50, ge=1, le=200),
    min_co_occurrence: int = Query(default=3, ge=1)
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
    
    if G.number_of_nodes() < 2:
        return {"predictions": [], "total_nodes": 0, "method": method}
    
    predictor = LinkPredictor(G)
    predictions = predictor.predict_links(method=method, top_n=top_n)
    
    return {
        "method": method,
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "predictions": predictions
    }


@router.get("/new-pairs")
def discover_new_pairs(
    top_n: int = Query(default=50, ge=1, le=200),
    min_co_occurrence: int = Query(default=3, ge=1)
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
    
    if G.number_of_nodes() < 2:
        return {"predictions": [], "total_nodes": 0}
    
    targets_col = get_collection("herb_targets")
    target_docs = list(targets_col.find({}))
    
    herb_targets = {}
    for doc in target_docs:
        targets = [t["target"] for t in doc.get("targets", [])]
        herb_targets[doc["herb_name"]] = targets
    
    predictor = LinkPredictor(G)
    predictions = predictor.predict_with_targets(herb_targets, top_n=top_n)
    
    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "total_predictions": len(predictions),
        "predictions": predictions
    }


@router.get("/pair-detail")
def pair_detail(
    herb_a: str,
    herb_b: str
):
    formulas_col = get_collection("formulas")
    herbs_col = get_collection("herbs")
    
    herb_a_doc = herbs_col.find_one({"name": herb_a})
    herb_b_doc = herbs_col.find_one({"name": herb_b})
    
    if not herb_a_doc or not herb_b_doc:
        raise HTTPException(status_code=404, detail="药物不存在")
    
    transactions = []
    cursor = formulas_col.find({}, {"herbs.name": 1})
    for f in cursor:
        herb_names = [h["name"] for h in f["herbs"]]
        transactions.append(herb_names)
    
    co_query = """
    MATCH (h1:Herb {name: $herb_a})-[r:CO_OCCURS]-(h2:Herb {name: $herb_b})
    RETURN r.count AS count, r.weight AS weight
    """
    
    co_results = run_query(co_query, {"herb_a": herb_a, "herb_b": herb_b})
    co_exists = len(co_results) > 0
    
    count_a = sum(1 for t in transactions if herb_a in t)
    count_b = sum(1 for t in transactions if herb_b in t)
    count_ab = sum(1 for t in transactions if herb_a in t and herb_b in t)
    
    total = len(transactions)
    support = count_ab / total if total > 0 else 0
    confidence_ab = count_ab / count_a if count_a > 0 else 0
    confidence_ba = count_ab / count_b if count_b > 0 else 0
    
    expected_support = (count_a / total) * (count_b / total) if total > 0 else 0
    lift = support / expected_support if expected_support > 0 else 0
    
    target_query = """
    MATCH (h1:Herb {name: $herb_a})
    MATCH (h2:Herb {name: $herb_b})
    RETURN h1, h2
    """
    
    results = run_query(target_query, {"herb_a": herb_a, "herb_b": herb_b})
    
    targets_col = get_collection("herb_targets")
    target_a_doc = targets_col.find_one({"herb_name": herb_a})
    target_b_doc = targets_col.find_one({"herb_name": herb_b})
    
    targets_a = [t["target"] for t in (target_a_doc.get("targets", []) if target_a_doc else [])]
    targets_b = [t["target"] for t in (target_b_doc.get("targets", []) if target_b_doc else [])]
    
    common_targets = list(set(targets_a) & set(targets_b))
    all_targets = list(set(targets_a) | set(targets_b))
    
    formulas_with_both = []
    cursor = formulas_col.find(
        {"$and": [{"herbs.name": herb_a}, {"herbs.name": herb_b}]}
    ).sort("frequency", -1).limit(10)
    
    for f in cursor:
        formulas_with_both.append({
            "name": f["name"],
            "frequency": f["frequency"],
            "dynasty": f["dynasty"]
        })
    
    formulas_with_either = []
    cursor = formulas_col.find(
        {"herbs.name": {"$in": [herb_a, herb_b]}}
    ).sort("frequency", -1).limit(10)
    
    for f in cursor:
        formulas_with_either.append({
            "name": f["name"],
            "frequency": f["frequency"],
            "dynasty": f["dynasty"]
        })
    
    prediction_score = 0
    if not co_exists:
        query = """
        MATCH (h1:Herb)-[r:CO_OCCURS]->(h2:Herb)
        WHERE r.count >= 3
        RETURN h1.name AS herb_a, h2.name AS herb_b, r.weight AS weight
        """
        results_g = run_query(query)
        G = nx.Graph()
        for r in results_g:
            G.add_edge(r["herb_a"], r["herb_b"], weight=r["weight"])
        
        if herb_a in G and herb_b in G:
            predictor = LinkPredictor(G)
            pred_results = predictor.predict_links(method="adamic_adar", top_n=1000)
            for pred in pred_results:
                if (pred["herb_a"] == herb_a and pred["herb_b"] == herb_b) or \
                   (pred["herb_a"] == herb_b and pred["herb_b"] == herb_a):
                    prediction_score = pred["score"]
                    break
    
    return {
        "herb_a": {
            "name": herb_a,
            "nature": herb_a_doc.get("nature", ""),
            "flavor": herb_a_doc.get("flavor", []),
            "meridians": herb_a_doc.get("meridians", []),
            "category": herb_a_doc.get("category", ""),
            "formula_count": count_a,
            "targets": targets_a
        },
        "herb_b": {
            "name": herb_b,
            "nature": herb_b_doc.get("nature", ""),
            "flavor": herb_b_doc.get("flavor", []),
            "meridians": herb_b_doc.get("meridians", []),
            "category": herb_b_doc.get("category", ""),
            "formula_count": count_b,
            "targets": targets_b
        },
        "pair_analysis": {
            "is_known_pair": co_exists,
            "co_occurrence_count": count_ab,
            "support": round(support, 4),
            "confidence_a_to_b": round(confidence_ab, 4),
            "confidence_b_to_a": round(confidence_ba, 4),
            "lift": round(lift, 4),
            "prediction_score": round(prediction_score, 6),
            "common_targets": common_targets,
            "common_target_count": len(common_targets),
            "target_similarity": round(len(common_targets) / len(all_targets), 4) if all_targets else 0
        },
        "formulas_with_both": formulas_with_both,
        "formulas_with_either": formulas_with_either
    }


@router.get("/target-based")
def target_based_discovery(
    target: str,
    top_n: int = Query(default=20, ge=1, le=100)
):
    targets_col = get_collection("herb_targets")
    herbs_col = get_collection("herbs")
    
    pipeline = [
        {"$unwind": "$targets"},
        {"$match": {"targets.target": target}},
        {"$sort": {"targets.affinity": -1}},
        {"$limit": top_n}
    ]
    
    results = list(targets_col.aggregate(pipeline))
    
    herbs = []
    for r in results:
        herb_name = r["herb_name"]
        target_info = r["targets"]
        
        herb_doc = herbs_col.find_one({"name": herb_name})
        herbs.append({
            "herb_name": herb_name,
            "category": herb_doc.get("category", "") if herb_doc else "",
            "nature": herb_doc.get("nature", "") if herb_doc else "",
            "target": target_info["target"],
            "affinity": target_info["affinity"],
            "effect_type": target_info["effect_type"]
        })
    
    return {
        "target": target,
        "total_herbs": len(herbs),
        "herbs": herbs
    }


@router.get("/recommend-for-disease")
def recommend_formula_for_disease(
    disease: str,
    top_n: int = Query(default=10, ge=1, le=50)
):
    formulas_col = get_collection("formulas")
    mining_results = []
    
    cursor = formulas_col.find({"indications": {"$in": [disease]}})
    
    herb_freq = {}
    herb_pair_freq = {}
    
    for f in cursor:
        herbs = [h["name"] for h in f["herbs"]]
        for herb in herbs:
            herb_freq[herb] = herb_freq.get(herb, 0) + 1
        
        for i in range(len(herbs)):
            for j in range(i + 1, len(herbs)):
                pair = tuple(sorted([herbs[i], herbs[j]]))
                herb_pair_freq[pair] = herb_pair_freq.get(pair, 0) + 1
    
    sorted_herbs = sorted(herb_freq.items(), key=lambda x: -x[1])[:20]
    sorted_pairs = sorted(herb_pair_freq.items(), key=lambda x: -x[1])[:20]
    
    core_herbs = [h[0] for h in sorted_herbs[:5]]
    
    recommendations = []
    for pair in sorted_pairs[:10]:
        pair_herbs = list(pair[0])
        pair_freq = pair[1]
        
        pair_support = pair_freq / max(herb_freq[pair_herbs[0]], 1)
        
        common_diseases = set()
        cursor2 = formulas_col.find(
            {"$and": [
                {"herbs.name": pair_herbs[0]},
                {"herbs.name": pair_herbs[1]}
            ]}
        ).limit(5)
        
        for f in cursor2:
            for ind in f["indications"]:
                common_diseases.add(ind)
        
        recommendations.append({
            "herbs": pair_herbs,
            "frequency": pair_freq,
            "confidence": round(pair_support, 4),
            "related_diseases": list(common_diseases)[:5]
        })
    
    return {
        "disease": disease,
        "total_formulas": sum(1 for _ in formulas_col.find({"indications": {"$in": [disease]}})),
        "core_herbs": [{"name": h[0], "frequency": h[1]} for h in sorted_herbs[:10]],
        "recommended_pairs": recommendations
    }


@router.get("/all-targets")
def get_all_targets():
    targets_col = get_collection("herb_targets")
    
    pipeline = [
        {"$unwind": "$targets"},
        {"$group": {"_id": "$targets.target", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    results = list(targets_col.aggregate(pipeline))
    
    return {
        "targets": [{"target": r["_id"], "herb_count": r["count"]} for r in results]
    }
