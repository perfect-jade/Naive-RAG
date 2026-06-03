"""
DashScope Embedding 封装
"""
import logging
import dashscope
import numpy as np
from dashscope import TextEmbedding

from backend.config import get_api_key, get_embedding_model, get_embedding_dimension

_log = logging.getLogger(__name__)


def _ensure_api_key():
    key = get_api_key()
    if key:
        dashscope.api_key = key
    return key


def get_embeddings(texts: list[str], model: str | None = None) -> list[list[float]]:
    """批量获取文本的 Embedding"""
    _ensure_api_key()
    model = model or get_embedding_model()

    if not texts:
        return []

    if isinstance(texts, str):
        texts = [texts]

    texts = [t[:2048] for t in texts if t and t.strip()]

    if not texts:
        return []

    embeddings = []
    batch_size = 25

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = TextEmbedding.call(model=model, input=batch)

        if 'output' in resp and 'embeddings' in resp['output']:
            for emb in resp['output']['embeddings']:
                if emb.get('embedding') and len(emb['embedding']) > 0:
                    embeddings.append(emb['embedding'])
        elif 'output' in resp and 'embedding' in resp['output']:
            if resp['output']['embedding'] and len(resp['output']['embedding']) > 0:
                embeddings.append(resp['output']['embedding'])

    return embeddings


def get_single_embedding(text: str, model: str | None = None) -> list[float]:
    """获取单个文本的 Embedding"""
    result = get_embeddings([text], model)
    if result:
        return result[0]
    raise RuntimeError("Embedding 生成失败")


def normalize_embedding(embedding: list[float]) -> np.ndarray:
    """归一化 embedding"""
    vec = np.array(embedding, dtype=np.float32)
    norm = np.linalg.norm(vec)
    if norm > 0:
        return vec / norm
    return vec