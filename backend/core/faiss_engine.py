"""
FAISS 索引管理
"""
import json
import logging
import numpy as np
import faiss
from pathlib import Path
from typing import Optional

from backend.config import get_embedding_dimension

_log = logging.getLogger(__name__)


class FAISSEngine:
    """FAISS 向量检索引擎"""

    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.index_dir / "index.faiss"
        self.id_map_path = self.index_dir / "id_map.json"
        self.dimension = get_embedding_dimension()
        self._index: Optional[faiss.Index] = None
        self._id_map: dict[int, str] = {}
        self._next_id = 0
        self._load()

    def _load(self):
        """加载已有的索引"""
        if self.index_path.exists():
            try:
                self._index = faiss.read_index(str(self.index_path))
                self.dimension = self._index.d
                if self.id_map_path.exists():
                    with open(self.id_map_path, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                        self._id_map = {int(k): v for k, v in raw.items()}
                        if self._id_map:
                            self._next_id = max(self._id_map.keys()) + 1
            except Exception as e:
                _log.warning(f"加载 FAISS 索引失败: {e}，将创建新索引")
                self._create_new()
        else:
            self._create_new()

    def _create_new(self):
        """创建新的空索引"""
        self._index = faiss.IndexFlatIP(self.dimension)
        self._id_map = {}
        self._next_id = 0

    def _save(self):
        """保存索引和 ID 映射"""
        if self._index is not None:
            faiss.write_index(self._index, str(self.index_path))
            with open(self.id_map_path, "w", encoding="utf-8") as f:
                json.dump({str(k): v for k, v in self._id_map.items()}, f)

    def add(self, embeddings: list[list[float]], chunk_ids: list[str]) -> list[int]:
        """添加向量到索引"""
        if not embeddings:
            return []

        normalized = []
        for emb in embeddings:
            vec = np.array(emb, dtype=np.float32)
            norm = np.linalg.norm(vec)
            normalized.append(vec / norm if norm > 0 else vec)

        vectors = np.array(normalized, dtype=np.float32)
        faiss_ids = list(range(self._next_id, self._next_id + len(vectors)))
        self._next_id += len(vectors)

        self._index.add(vectors)
        for faiss_id, chunk_id in zip(faiss_ids, chunk_ids):
            self._id_map[faiss_id] = chunk_id
        self._save()
        return faiss_ids

    def search(self, query_embedding: list[float], k: int = 10) -> list[dict]:
        """检索最相似的 Top-K 结果"""
        if self._index.ntotal == 0:
            return []

        vec = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        k = min(k, self._index.ntotal)
        distances, indices = self._index.search(vec, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx in self._id_map:
                results.append({
                    "chunk_id": self._id_map[idx],
                    "score": float(dist),
                    "faiss_id": int(idx),
                })
        return results

    def remove_by_ids(self, chunk_ids: list[str]) -> int:
        """通过重建索引来删除指定 chunk（FAISS 不支持直接删除）"""
        ids_to_remove = set(chunk_ids)
        keep_indices = []
        keep_embeddings = []
        new_id_map = {}
        new_id = 0

        for faiss_id, chunk_id in self._id_map.items():
            if chunk_id not in ids_to_remove:
                vec = self._index.reconstruct(faiss_id)
                keep_embeddings.append(vec)
                keep_indices.append(faiss_id)
                new_id_map[new_id] = chunk_id
                new_id += 1

        removed = len(self._id_map) - len(new_id_map)
        self._create_new()
        if keep_embeddings:
            vectors = np.array(keep_embeddings, dtype=np.float32)
            self._index.add(vectors)
            self._id_map = new_id_map
            self._next_id = len(keep_embeddings)
        self._save()
        return removed

    @property
    def count(self) -> int:
        return self._index.ntotal if self._index else 0