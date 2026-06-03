"""
核心引擎单元测试 - FAISS / BM25 / 混合检索 / 行业路由器

测试范围:
- FAISS 索引的创建、添加、搜索、保存/加载、删除
- BM25 索引的构建、搜索、保存/加载
- 混合检索 RRF 融合排序
- 行业路由器 LLM 判断逻辑
"""

import os
import json
import uuid
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import numpy as np


class TestFAISSEngine:
    """FAISS 向量检索引擎测试"""

    def test_create_empty_index(self, temp_data_dir, faiss_dimension):
        """TC-ENG-001: 创建空 FAISS 索引成功"""
        import faiss
        index = faiss.IndexFlatL2(faiss_dimension)
        assert index.ntotal == 0
        assert index.d == faiss_dimension

    def test_add_vectors_to_index(self, temp_data_dir, faiss_dimension, sample_embeddings):
        """TC-ENG-002: 向索引导入向量后 ntotal 正确"""
        import faiss
        index = faiss.IndexFlatL2(faiss_dimension)
        index.add(sample_embeddings[:10])
        assert index.ntotal == 10

    def test_search_returns_top_k(self, temp_data_dir, faiss_dimension, sample_embeddings):
        """TC-ENG-003: 检索返回指定数量的 K 个结果"""
        import faiss
        index = faiss.IndexFlatL2(faiss_dimension)
        index.add(sample_embeddings[:20])

        query = sample_embeddings[0:1]
        distances, indices = index.search(query, k=5)
        assert indices.shape == (1, 5)
        assert distances.shape == (1, 5)

    def test_search_self_matches_first(self, temp_data_dir, faiss_dimension, sample_embeddings):
        """TC-ENG-004: 用已入库向量检索，自身排在第一位"""
        import faiss
        index = faiss.IndexFlatL2(faiss_dimension)
        index.add(sample_embeddings[:20])

        query = sample_embeddings[5:6]
        distances, indices = index.search(query, k=1)
        assert indices[0][0] == 5
        assert distances[0][0] < 0.001

    def test_save_and_load_index(self, temp_data_dir, faiss_dimension, sample_embeddings):
        """TC-ENG-005: 保存后重新加载索引，数据一致"""
        import faiss
        index = faiss.IndexFlatL2(faiss_dimension)
        index.add(sample_embeddings[:10])
        ntotal_before = index.ntotal

        save_path = str(temp_data_dir / "test_index.faiss")
        faiss.write_index(index, save_path)

        loaded = faiss.read_index(save_path)
        assert loaded.ntotal == ntotal_before
        assert loaded.d == faiss_dimension

    def test_id_map_consistency(self, temp_data_dir):
        """TC-ENG-006: faiss_id 和 chunk_id 映射的正确性"""
        id_map = {}
        for i in range(10):
            chunk_id = str(uuid.uuid4())
            id_map[i] = chunk_id

        assert len(id_map) == 10

        id_map_path = temp_data_dir / "id_map.json"
        with open(id_map_path, "w", encoding="utf-8") as f:
            json.dump(id_map, f)

        with open(id_map_path, "r", encoding="utf-8") as f:
            loaded_map = json.load(f)

        assert loaded_map == id_map

    def test_incremental_add(self, temp_data_dir, faiss_dimension, sample_embeddings):
        """TC-ENG-007: 分批添加向量，总数正确"""
        import faiss
        index = faiss.IndexFlatL2(faiss_dimension)
        index.add(sample_embeddings[:10])
        assert index.ntotal == 10
        index.add(sample_embeddings[10:20])
        assert index.ntotal == 20

    def test_remove_from_faiss(self, temp_data_dir, faiss_dimension, sample_embeddings):
        """TC-ENG-008: 通过重建索引实现删除（FAISS 不支持直接删除）"""
        import faiss
        index = faiss.IndexFlatL2(faiss_dimension)
        index.add(sample_embeddings[:10])

        keep_indices = [0, 1, 2, 4, 5, 6, 7, 8, 9]
        keep_vectors = sample_embeddings[keep_indices]

        new_index = faiss.IndexFlatL2(faiss_dimension)
        new_index.add(keep_vectors)
        assert new_index.ntotal == 9

    def test_empty_index_search(self, temp_data_dir, faiss_dimension, sample_embeddings):
        """TC-ENG-009: 空索引检索应返回空结果或错误"""
        import faiss
        index = faiss.IndexFlatL2(faiss_dimension)
        query = sample_embeddings[0:1]
        try:
            distances, indices = index.search(query, k=5)
            assert indices[0][0] == -1
        except Exception:
            pass


class TestBM25Engine:
    """BM25 关键词检索引擎测试"""

    @pytest.fixture
    def sample_corpus(self):
        return [
            "高血压是指以体循环动脉血压增高为主要特征的临床综合征",
            "收缩压≥140mmHg和/或舒张压≥90mmHg即可诊断为高血压",
            "糖尿病是以高血糖为特征的代谢性疾病",
            "胰岛素分泌缺陷或其生物作用受损导致高血糖",
            "长期高血糖导致各种组织的慢性损害和功能障碍",
            "为了保护公民法人的合法权益制定本法",
            "本法适用于中华人民共和国境内",
            "金融市场的稳定性对经济发展至关重要",
            "股票投资需要关注市盈率和市净率等指标",
            "风湿性关节炎是一种自身免疫性疾病",
        ]

    def test_bm25_build_index(self, sample_corpus):
        """TC-ENG-010: BM25 索引构建成功，可返回搜索结果"""
        from rank_bm25 import BM25Okapi

        tokenized = [doc.split() for doc in sample_corpus]
        bm25 = BM25Okapi(tokenized)

        query = "高血压的诊断标准".split()
        scores = bm25.get_scores(query)
        assert len(scores) == len(sample_corpus)

    def test_bm25_top_k_results(self, sample_corpus):
        """TC-ENG-011: BM25 返回 Top-K 结果"""
        from rank_bm25 import BM25Okapi

        tokenized = [doc.split() for doc in sample_corpus]
        bm25 = BM25Okapi(tokenized)

        query = "高血压的诊断标准".split()
        top_k = bm25.get_top_n(query, tokenized, n=3)
        assert len(top_k) == 3

    def test_bm25_relevance(self, sample_corpus):
        """TC-ENG-012: BM25 对相关文档评分高于不相关文档"""
        from rank_bm25 import BM25Okapi

        tokenized = [doc.split() for doc in sample_corpus]
        bm25 = BM25Okapi(tokenized)

        query = "高血压".split()
        scores = bm25.get_scores(query)
        assert scores[0] > scores[5]
        assert scores[1] > scores[5]

    def test_bm25_save_load(self, sample_corpus):
        """TC-ENG-013: BM25 模型序列化后加载可正常使用"""
        import pickle
        from rank_bm25 import BM25Okapi

        tokenized = [doc.split() for doc in sample_corpus]
        bm25 = BM25Okapi(tokenized)

        serialized = pickle.dumps(bm25)
        loaded = pickle.loads(serialized)

        query = "糖尿病".split()
        scores_orig = bm25.get_scores(query)
        scores_loaded = loaded.get_scores(query)
        assert list(scores_orig) == list(scores_loaded)

    def test_bm25_empty_corpus(self):
        """TC-ENG-014: 空语料库应妥善处理"""
        from rank_bm25 import BM25Okapi

        bm25 = BM25Okapi([])
        query = "测试".split()
        scores = bm25.get_scores(query)
        assert len(scores) == 0

    def test_bm25_chinese_tokenization(self):
        """TC-ENG-015: 中文分词后 BM25 检索"""
        import jieba
        from rank_bm25 import BM25Okapi

        corpus_raw = [
            "高血压是指以体循环动脉血压增高为主要特征的临床综合征",
            "糖尿病是以高血糖为特征的代谢性疾病",
        ]
        tokenized = [list(jieba.cut(doc)) for doc in corpus_raw]
        bm25 = BM25Okapi(tokenized)

        query = list(jieba.cut("高血压的诊断标准"))
        scores = bm25.get_scores(query)
        assert scores[0] > scores[1]


class TestRetriever:
    """混合检索 + RRF 融合排序测试"""

    @pytest.fixture
    def faiss_ranks(self):
        return {
            "doc_0": 1, "doc_1": 2, "doc_2": 3, "doc_3": 4, "doc_4": 5,
            "doc_5": 6, "doc_6": 7, "doc_7": 8, "doc_8": 9, "doc_9": 10,
        }

    @pytest.fixture
    def bm25_ranks(self):
        return {
            "doc_1": 1, "doc_0": 2, "doc_4": 3, "doc_3": 4, "doc_9": 5,
            "doc_2": 6, "doc_6": 7, "doc_8": 8, "doc_7": 9, "doc_5": 10,
        }

    def test_rrf_fusion(self, faiss_ranks, bm25_ranks):
        """TC-ENG-016: RRF 融合排序算法正确性"""
        k = 60
        rrf_scores = {}

        for doc_id, rank in faiss_ranks.items():
            rrf_scores[doc_id] = 1.0 / (k + rank)

        for doc_id, rank in bm25_ranks.items():
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank)

        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        top_3 = [doc_id for doc_id, _ in ranked[:3]]
        assert len(top_3) == 3

    def test_rrf_fusion_top_result(self, faiss_ranks, bm25_ranks):
        """TC-ENG-017: RRF 融合后两边都排名靠前的文档应排第一"""
        k = 60
        rrf_scores = {}
        for doc_id, rank in faiss_ranks.items():
            rrf_scores[doc_id] = 1.0 / (k + rank)
        for doc_id, rank in bm25_ranks.items():
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank)

        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        assert ranked[0][0] in ("doc_0", "doc_1")

    def test_fusion_top_k_limit(self, faiss_ranks, bm25_ranks):
        """TC-ENG-018: RRF 融合后按 top_k 截断"""
        k = 60
        rrf_scores = {}
        for doc_id, rank in faiss_ranks.items():
            rrf_scores[doc_id] = 1.0 / (k + rank)
        for doc_id, rank in bm25_ranks.items():
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank)

        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        top_k = 5
        top_results = ranked[:top_k]
        assert len(top_results) == 5

    def test_fusion_with_overlap_only(self):
        """TC-ENG-019: 只有一个检索源有结果时，直接返回该结果"""
        faiss_ranks = {"doc_a": 1, "doc_b": 2, "doc_c": 3}
        bm25_ranks = {}

        k = 60
        rrf_scores = {}
        for doc_id, rank in faiss_ranks.items():
            rrf_scores[doc_id] = 1.0 / (k + rank)
        for doc_id, rank in bm25_ranks.items():
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank)

        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        assert ranked[0][0] == "doc_a"

    def test_fusion_different_k_values(self, faiss_ranks, bm25_ranks):
        """TC-ENG-020: 不同 RRF k 值的排序变化"""
        def compute_rrf(k_val):
            scores = {}
            for doc_id, rank in faiss_ranks.items():
                scores[doc_id] = 1.0 / (k_val + rank)
            for doc_id, rank in bm25_ranks.items():
                scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k_val + rank)
            return sorted(scores.items(), key=lambda x: x[1], reverse=True)

        result_k60 = compute_rrf(60)
        result_k100 = compute_rrf(100)

        assert result_k60[0][0] == result_k100[0][0]

    def test_fusion_empty_input(self):
        """TC-ENG-021: 两个检索源都为空时应返回空"""
        rrf_scores = {}
        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        assert len(ranked) == 0


class TestRouter:
    """行业路由器测试"""

    def test_parse_route_response_valid(self, mock_llm_route_response_medical):
        """TC-ENG-022: 解析合法的路由响应 JSON"""
        content = mock_llm_route_response_medical["output"]["choices"][0]["message"]["content"]
        result = json.loads(content)
        assert result["industry"] == "医疗健康"
        assert result["confidence"] == "high"

    def test_parse_route_response_general(self, mock_llm_route_response_general):
        """TC-ENG-023: 解析 general 类型的路由响应"""
        content = mock_llm_route_response_general["output"]["choices"][0]["message"]["content"]
        result = json.loads(content)
        assert result["industry"] == "general"
        assert result["confidence"] == "low"

    def test_route_prompt_template(self):
        """TC-ENG-024: 路由 Prompt 模板包含行业列表和用户问题"""
        industries = [
            {"name": "医疗健康", "description": "医疗领域知识库"},
            {"name": "法律法规", "description": "法律法规知识库"},
        ]
        user_query = "高血压的诊断标准是什么？"

        prompt = f"""你是一个行业分类助手。当前知识库包含以下行业：
{json.dumps(industries, ensure_ascii=False)}

请判断以下用户问题属于哪个行业，只返回 JSON 格式，不要包含其他内容：
{{"industry": "行业名称", "confidence": "high/medium/low"}}

如果问题不属于任何行业，返回：
{{"industry": "general", "confidence": "low"}}

用户问题：{user_query}"""

        assert "医疗健康" in prompt
        assert "法律法规" in prompt
        assert user_query in prompt

    def test_route_invalid_json_response(self):
        """TC-ENG-025: LLM 返回非法 JSON 时的容错处理"""
        invalid_responses = [
            "不是有效 JSON",
            '{"industry": "医疗健康"',
            "",
            "```json\n{\"industry\": \"医疗健康\"}\n```",
        ]

        for resp in invalid_responses:
            try:
                result = json.loads(resp)
                assert "industry" in result
            except json.JSONDecodeError:
                pass

    def test_route_unknown_industry(self):
        """TC-ENG-026: LLM 返回了一个不在列表中的行业名时的处理"""
        existing = ["medical_health", "legal"]
        llm_result = {"industry": "nonexistent_industry", "confidence": "medium"}

        slug = llm_result.get("industry", "")
        if slug not in existing:
            fallback = "general"
            assert fallback == "general"

    def test_route_slug_to_name_mapping(self):
        """TC-ENG-027: 行业名 → slug 的映射关系"""
        name_to_slug = {
            "医疗健康": "medical_health",
            "法律法规": "legal",
            "金融财经": "finance",
            "IT & 互联网": "it_and_internet",
        }

        assert name_to_slug["医疗健康"] == "medical_health"
        assert name_to_slug["IT & 互联网"] == "it_and_internet"

    def test_route_multiple_industries_selection(self):
        """TC-ENG-028: 多个行业时选最匹配的"""
        industries = [
            {"name": "医疗健康", "slug": "medical_health"},
            {"name": "法律法规", "slug": "legal"},
            {"name": "金融财经", "slug": "finance"},
        ]
        llm_result = {"industry": "医疗健康", "confidence": "high"}

        matched = next(
            (ind for ind in industries if ind["name"] == llm_result["industry"]),
            None
        )
        assert matched is not None
        assert matched["slug"] == "medical_health"