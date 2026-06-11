from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from bson import ObjectId
from bson.errors import InvalidId

from database.mongodb import get_collection

router = APIRouter(prefix="/diseases", tags=["病症管理"])


def disease_to_response(disease_doc):
    if not disease_doc:
        return None
    disease_doc["_id"] = str(disease_doc["_id"])
    return disease_doc


@router.get("/")
def list_diseases(
    skip: int = 0,
    limit: int = 50,
    keyword: Optional[str] = None,
    category: Optional[str] = None
):
    diseases_col = get_collection("diseases")
    
    query = {}
    if keyword:
        query["name"] = {"$regex": keyword, "$options": "i"}
    if category:
        query["category"] = category
    
    cursor = diseases_col.find(query).skip(skip).limit(limit)
    result = [disease_to_response(d) for d in cursor]
    return result


@router.get("/count")
def count_diseases(category: Optional[str] = None):
    diseases_col = get_collection("diseases")
    
    query = {}
    if category:
        query["category"] = category
    
    count = diseases_col.count_documents(query)
    return {"count": count}


@router.get("/{disease_id}")
def get_disease(disease_id: str):
    try:
        oid = ObjectId(disease_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="无效的ID格式")
    
    diseases_col = get_collection("diseases")
    disease = diseases_col.find_one({"_id": oid})
    
    if not disease:
        raise HTTPException(status_code=404, detail="病症不存在")
    
    return disease_to_response(disease)


@router.get("/by-name/{name}")
def get_disease_by_name(name: str):
    diseases_col = get_collection("diseases")
    disease = diseases_col.find_one({"name": name})
    
    if not disease:
        raise HTTPException(status_code=404, detail="病症不存在")
    
    return disease_to_response(disease)


@router.get("/{disease_id}/formulas")
def get_disease_formulas(
    disease_id: str,
    skip: int = 0,
    limit: int = 20
):
    try:
        oid = ObjectId(disease_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="无效的ID格式")
    
    diseases_col = get_collection("diseases")
    disease = diseases_col.find_one({"_id": oid})
    
    if not disease:
        raise HTTPException(status_code=404, detail="病症不存在")
    
    formulas_col = get_collection("formulas")
    cursor = formulas_col.find(
        {"indications": {"$in": [disease["name"]]}}
    ).sort("frequency", -1).skip(skip).limit(limit)
    
    formulas = []
    for f in cursor:
        f["_id"] = str(f["_id"])
        formulas.append(f)
    
    total = formulas_col.count_documents({"indications": {"$in": [disease["name"]]}})
    
    return {"disease": disease["name"], "formulas": formulas, "total": total}


@router.get("/stats/categories")
def get_disease_categories():
    diseases_col = get_collection("diseases")
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    result = list(diseases_col.aggregate(pipeline))
    return [{"category": r["_id"], "count": r["count"]} for r in result]


@router.get("/search/formulas")
def search_formulas_for_disease(
    disease_name: str,
    skip: int = 0,
    limit: int = 20
):
    formulas_col = get_collection("formulas")
    
    cursor = formulas_col.find(
        {"indications": {"$in": [disease_name]}}
    ).sort("frequency", -1).skip(skip).limit(limit)
    
    formulas = []
    for f in cursor:
        f["_id"] = str(f["_id"])
        formulas.append(f)
    
    total = formulas_col.count_documents({"indications": {"$in": [disease_name]}})
    
    return {
        "disease": disease_name,
        "formulas": formulas,
        "total": total,
        "message": f"共找到 {total} 首治疗 {disease_name} 的方剂"
    }
