from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from api.formulas import router as formulas_router
from api.herbs import router as herbs_router
from api.diseases import router as diseases_router
from api.graph import router as graph_router
from api.mining import router as mining_router
from api.discovery import router as discovery_router

app = FastAPI(
    title="古代中医药方剂配伍规律挖掘与现代新药发现辅助系统",
    description="基于MongoDB、Neo4j、Apriori、Louvain和链路预测的中医药知识图谱系统",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(formulas_router)
app.include_router(herbs_router)
app.include_router(diseases_router)
app.include_router(graph_router)
app.include_router(mining_router)
app.include_router(discovery_router)

frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
def root():
    return {
        "name": "中医药方剂配伍规律挖掘系统",
        "version": "1.0.0",
        "endpoints": {
            "formulas": "/formulas/",
            "herbs": "/herbs/",
            "diseases": "/diseases/",
            "graph": "/graph/",
            "mining": "/mining/",
            "discovery": "/discovery/"
        },
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/api/stats")
def get_stats():
    from database.mongodb import get_collection
    
    formulas_col = get_collection("formulas")
    herbs_col = get_collection("herbs")
    diseases_col = get_collection("diseases")
    
    return {
        "formulas_count": formulas_col.count_documents({}),
        "herbs_count": herbs_col.count_documents({}),
        "diseases_count": diseases_col.count_documents({})
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    from config import get_settings
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
