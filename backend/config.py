"""
配置管理模块 - 管理 API Key、路径、模型配置等
"""
import os
import json
import sqlite3
from pathlib import Path
from threading import Lock

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
INDUSTRIES_DIR = DATA_DIR / "industries"
CONFIG_DB_PATH = DATA_DIR / "config.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
INDUSTRIES_DIR.mkdir(parents=True, exist_ok=True)

VALID_LLM_MODELS = {"qwen-turbo", "qwen-plus", "qwen-max", "qwen-long"}
VALID_EMBEDDING_MODELS = {"text-embedding-v1", "text-embedding-v2", "text-embedding-v3"}

EMBEDDING_DIMENSIONS = {
    "text-embedding-v1": 1536,
    "text-embedding-v2": 1536,
    "text-embedding-v3": 1024,
}

DEFAULT_LLM_MODEL = "qwen-plus"
DEFAULT_EMBEDDING_MODEL = "text-embedding-v2"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
FAISS_TOP_K = 10
BM25_TOP_K = 10
FUSION_TOP_K = 5
RRF_K = 60
MAX_FILE_SIZE_MB = 10
MAX_CHAT_HISTORY_ROUNDS = 5

_config_lock = Lock()


def _init_config_db():
    """初始化配置数据库"""
    CONFIG_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CONFIG_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.execute("""
        INSERT OR IGNORE INTO config (key, value) VALUES ('llm_model', ?)
    """, (DEFAULT_LLM_MODEL,))
    conn.execute("""
        INSERT OR IGNORE INTO config (key, value) VALUES ('embedding_model', ?)
    """, (DEFAULT_EMBEDDING_MODEL,))
    conn.execute("""
        INSERT OR IGNORE INTO config (key, value) VALUES ('api_key', '')
    """)
    conn.commit()
    conn.close()


def get_config(key: str) -> str | None:
    """获取配置值"""
    conn = sqlite3.connect(str(CONFIG_DB_PATH))
    row = conn.execute("SELECT value FROM config WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row[0] if row else None


def set_config(key: str, value: str):
    """设置配置值"""
    conn = sqlite3.connect(str(CONFIG_DB_PATH))
    conn.execute(
        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
        (key, value)
    )
    conn.commit()
    conn.close()


def get_llm_model() -> str:
    """获取当前 LLM 模型"""
    model = get_config("llm_model")
    return model if model else DEFAULT_LLM_MODEL


def get_embedding_model() -> str:
    """获取当前 Embedding 模型"""
    model = get_config("embedding_model")
    return model if model else DEFAULT_EMBEDDING_MODEL


def get_api_key() -> str:
    """获取 API Key"""
    key = get_config("api_key")
    if key:
        return key
    return os.getenv("DASHSCOPE_API_KEY", "")


def get_embedding_dimension() -> int:
    """获取当前 Embedding 模型的维度"""
    model = get_embedding_model()
    return EMBEDDING_DIMENSIONS.get(model, 1536)


_init_config_db()