"""
FastAPI 入口 - 多行业知识库 RAG 系统
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.industry import router as industry_router
from backend.api.knowledge import router as knowledge_router
from backend.api.chat import router as chat_router
from backend.api.settings import router as settings_router

app = FastAPI(
    title="多行业知识库 RAG 系统",
    description="基于 DashScope + FAISS + BM25 的多行业知识库检索增强生成系统",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(industry_router)
app.include_router(knowledge_router)
app.include_router(chat_router)
app.include_router(settings_router)


@app.get("/")
def root():
    return {"name": "多行业知识库 RAG 系统", "version": "1.0.0", "status": "running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)