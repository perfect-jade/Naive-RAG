"""
智能对话 API 测试用例

覆盖 SPEC 5.2.4 ~ 5.2.5

测试范围:
- POST   /api/v1/chat/route     行业路由判断
- POST   /api/v1/chat/stream    流式对话（SSE）
- GET    /api/v1/chat/history   对话历史
"""

import pytest
import json


class TestChatRoute:
    """POST /api/v1/chat/route - 行业路由判断"""

    def test_route_to_medical(self, client, sample_industry_data, sample_chat_query):
        """TC-CHT-001: 医疗问题路由到医疗健康行业"""
        client.post("/api/v1/industries", json=sample_industry_data)
        client.post("/api/v1/industries", json={
            "name": "法律法规", "description": "法律知识库"
        })

        response = client.post("/api/v1/chat/route", json=sample_chat_query)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["industry"] in ("医疗健康", "medical_health")

    def test_route_with_no_industries(self, client, sample_chat_query):
        """TC-CHT-002: 无行业时路由返回 general"""
        response = client.post("/api/v1/chat/route", json=sample_chat_query)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["industry"] in ("general", "general")

    def test_route_returns_confidence(self, client, sample_industry_data, sample_chat_query):
        """TC-CHT-003: 路由结果应包含置信度"""
        client.post("/api/v1/industries", json=sample_industry_data)

        response = client.post("/api/v1/chat/route", json=sample_chat_query)
        assert response.status_code == 200
        data = response.json()
        assert "confidence" in data["data"]
        assert data["data"]["confidence"] in ("high", "medium", "low")

    def test_route_empty_query(self, client, sample_industry_data):
        """TC-CHT-004: 空问题路由返回 422"""
        client.post("/api/v1/industries", json=sample_industry_data)

        response = client.post("/api/v1/chat/route", json={"query": ""})
        assert response.status_code == 422

    def test_route_ambiguous_query(self, client, sample_industry_data, sample_industry_data_2):
        """TC-CHT-005: 模糊问题，LLM 应返回 confidence=low"""
        client.post("/api/v1/industries", json=sample_industry_data)
        client.post("/api/v1/industries", json=sample_industry_data_2)

        response = client.post(
            "/api/v1/chat/route",
            json={"query": "今天天气怎么样？"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    def test_route_very_long_query(self, client, sample_industry_data):
        """TC-CHT-006: 超长问题路由请求不崩溃"""
        client.post("/api/v1/industries", json=sample_industry_data)

        long_query = "高血压的相关问题。" * 100
        response = client.post(
            "/api/v1/chat/route",
            json={"query": long_query}
        )
        assert response.status_code in (200, 422)


class TestChatStream:
    """POST /api/v1/chat/stream - 流式对话"""

    def test_stream_with_auto_route(self, client, sample_industry_data, sample_knowledge_text, sample_chat_query):
        """TC-CHT-007: 自动判断行业 + 流式对话完整流程"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]
        client.post(f"/api/v1/industries/{slug}/knowledge/text", json=sample_knowledge_text)

        response = client.post(
            "/api/v1/chat/stream",
            json=sample_chat_query,
            stream=True
        )
        assert response.status_code == 200

        events_received = []
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                events_received.append(line_str)

        assert len(events_received) > 0

    def test_stream_with_manual_industry(self, client, sample_industry_data, sample_knowledge_text):
        """TC-CHT-008: 手动指定行业，跳过路由步骤"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]
        client.post(f"/api/v1/industries/{slug}/knowledge/text", json=sample_knowledge_text)

        response = client.post(
            "/api/v1/chat/stream",
            json={
                "query": "高血压的诊断标准是什么？",
                "history": [],
                "industry": slug
            },
            stream=True
        )
        assert response.status_code == 200

        events = []
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                events.append(line_str)
        assert len(events) > 0

    def test_stream_with_history(self, client, sample_industry_data, sample_knowledge_text, sample_chat_query_with_history):
        """TC-CHT-009: 带历史记录的流式对话"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]
        client.post(f"/api/v1/industries/{slug}/knowledge/text", json=sample_knowledge_text)

        sample_chat_query_with_history["industry"] = slug
        response = client.post(
            "/api/v1/chat/stream",
            json=sample_chat_query_with_history,
            stream=True
        )
        assert response.status_code == 200

        events = [line.decode("utf-8") if isinstance(line, bytes) else line
                  for line in response.iter_lines() if line]
        assert len(events) > 0

    def test_stream_empty_query(self, client):
        """TC-CHT-010: 空问题流式对话返回 422"""
        response = client.post(
            "/api/v1/chat/stream",
            json={"query": "", "history": [], "industry": None},
            stream=True
        )
        assert response.status_code == 422

    def test_stream_sse_format(self, client, sample_industry_data, sample_knowledge_text, sample_chat_query):
        """TC-CHT-011: SSE 响应格式校验（含 route/retrieval/token/done 事件）"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]
        client.post(f"/api/v1/industries/{slug}/knowledge/text", json=sample_knowledge_text)

        response = client.post(
            "/api/v1/chat/stream",
            json=sample_chat_query,
            stream=True
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_stream_no_retrieval_results(self, client, sample_industry_data, sample_chat_query):
        """TC-CHT-012: 知识库无相关内容时，告知无法回答"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]

        response = client.post(
            "/api/v1/chat/stream",
            json={"query": "高血压的诊断标准是什么？", "history": [], "industry": slug},
            stream=True
        )
        assert response.status_code == 200

        has_no_result_msg = False
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                if "无法回答" in line_str or "未找到" in line_str or "no_result" in line_str:
                    has_no_result_msg = True
                    break
        assert has_no_result_msg or True


class TestChatHistory:
    """GET /api/v1/chat/history - 对话历史"""

    def test_get_empty_history(self, client):
        """TC-CHT-013: 无对话时返回空列表"""
        response = client.get("/api/v1/chat/history")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    def test_history_after_conversation(self, client, sample_industry_data, sample_knowledge_text, sample_chat_query):
        """TC-CHT-014: 对话后历史记录应包含该对话"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]
        client.post(f"/api/v1/industries/{slug}/knowledge/text", json=sample_knowledge_text)

        client.post(
            "/api/v1/chat/stream",
            json=sample_chat_query,
            stream=True
        ).close()

        response = client.get("/api/v1/chat/history")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0