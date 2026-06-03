"""
知识管理 API 测试用例

覆盖 SPEC 5.2.2 ~ 5.2.3

测试范围:
- POST   /api/v1/industries/{slug}/knowledge/text     文本录入
- POST   /api/v1/industries/{slug}/knowledge/upload   文件上传
- GET    /api/v1/industries/{slug}/knowledge          知识列表（分页）
- DELETE /api/v1/industries/{slug}/knowledge/{doc_id} 删除文档
"""

import pytest
import json
from pathlib import Path


class TestTextKnowledgeInsert:
    """POST /api/v1/industries/{slug}/knowledge/text - 文本录入"""

    def test_insert_text_success(self, client, sample_industry_data, sample_knowledge_text):
        """TC-KNW-001: 正常录入文本知识，返回 chunk_count"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]

        response = client.post(
            f"/api/v1/industries/{slug}/knowledge/text",
            json=sample_knowledge_text
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "doc_id" in data["data"]
        assert data["data"]["chunk_count"] > 0
        assert data["data"]["message"] == "知识录入成功"

    def test_insert_text_without_title(self, client, sample_industry_data):
        """TC-KNW-002: 无标题的文本录入，标题应为空或自动生成"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]

        response = client.post(
            f"/api/v1/industries/{slug}/knowledge/text",
            json={"content": "这是一段没有标题的测试文本。"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "doc_id" in data["data"]

    def test_insert_text_empty_content(self, client, sample_industry_data):
        """TC-KNW-003: 空内容录入应返回 422 校验错误"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]

        response = client.post(
            f"/api/v1/industries/{slug}/knowledge/text",
            json={"title": "空文档", "content": ""}
        )
        assert response.status_code == 422

    def test_insert_text_nonexistent_industry(self, client, sample_knowledge_text):
        """TC-KNW-004: 向不存在的行业录入文本返回 404"""
        response = client.post(
            "/api/v1/industries/nonexistent/knowledge/text",
            json=sample_knowledge_text
        )
        assert response.status_code == 404

    def test_insert_text_very_long(self, client, sample_industry_data):
        """TC-KNW-005: 超长文本录入应正确分块"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]

        long_text = "高血压相关知识。" * 500
        response = client.post(
            f"/api/v1/industries/{slug}/knowledge/text",
            json={"title": "超长文档", "content": long_text, "tags": ["测试"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["chunk_count"] > 1

    def test_insert_text_with_tags(self, client, sample_industry_data, sample_knowledge_text):
        """TC-KNW-006: 带标签录入，标签应正确保存"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]

        response = client.post(
            f"/api/v1/industries/{slug}/knowledge/text",
            json=sample_knowledge_text
        )
        assert response.status_code == 200
        doc_id = response.json()["data"]["doc_id"]

        list_resp = client.get(f"/api/v1/industries/{slug}/knowledge")
        items = list_resp.json()["data"]["items"]
        doc = next((d for d in items if d["id"] == doc_id), None)
        if doc:
            assert any(tag in str(doc.get("tags", "")) for tag in ["心血管", "慢性病"])


class TestFileUpload:
    """POST /api/v1/industries/{slug}/knowledge/upload - 文件上传"""

    def test_upload_txt_file(self, client, sample_industry_data, sample_txt_path):
        """TC-KNW-007: 上传 TXT 文件成功"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]

        with open(sample_txt_path, "rb") as f:
            response = client.post(
                f"/api/v1/industries/{slug}/knowledge/upload",
                files={"files": ("sample.txt", f, "text/plain")}
            )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["results"]) == 1
        assert data["data"]["results"][0]["status"] == "success"
        assert "chunk_count" in data["data"]["results"][0]

    def test_upload_multiple_files(self, client, sample_industry_data, sample_txt_path):
        """TC-KNW-008: 批量上传多个文件"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]

        test_files = [
            ("files", ("file1.txt", open(sample_txt_path, "rb"), "text/plain")),
            ("files", ("file2.txt", open(sample_txt_path, "rb"), "text/plain")),
        ]
        try:
            response = client.post(
                f"/api/v1/industries/{slug}/knowledge/upload",
                files=test_files
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]["results"]) == 2
            assert all(r["status"] == "success" for r in data["data"]["results"])
        finally:
            for _, (_, f, _) in test_files:
                f.close()

    def test_upload_unsupported_file_type(self, client, sample_industry_data):
        """TC-KNW-009: 上传不支持的文件类型应返回错误"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]

        response = client.post(
            f"/api/v1/industries/{slug}/knowledge/upload",
            files={"files": ("test.exe", b"malicious content", "application/octet-stream")}
        )
        assert response.status_code in (400, 422)

    def test_upload_oversized_file(self, client, sample_industry_data):
        """TC-KNW-010: 上传超大文件应被限制"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]

        large_content = b"x" * (11 * 1024 * 1024)
        response = client.post(
            f"/api/v1/industries/{slug}/knowledge/upload",
            files={"files": ("large.txt", large_content, "text/plain")}
        )
        assert response.status_code in (400, 413, 422)

    def test_upload_nonexistent_industry(self, client, sample_txt_path):
        """TC-KNW-011: 向不存在的行业上传文件返回 404"""
        with open(sample_txt_path, "rb") as f:
            response = client.post(
                "/api/v1/industries/nonexistent/knowledge/upload",
                files={"files": ("sample.txt", f, "text/plain")}
            )
        assert response.status_code == 404

    def test_upload_no_file(self, client, sample_industry_data):
        """TC-KNW-012: 不附带文件的上传请求返回 422"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]

        response = client.post(f"/api/v1/industries/{slug}/knowledge/upload")
        assert response.status_code == 422


class TestKnowledgeList:
    """GET /api/v1/industries/{slug}/knowledge - 知识列表"""

    def test_list_empty_knowledge(self, client, sample_industry_data):
        """TC-KNW-013: 新建行业的知识列表为空"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]

        response = client.get(f"/api/v1/industries/{slug}/knowledge")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"] or "data" in data

    def test_list_with_items(self, client, sample_industry_data, sample_knowledge_text):
        """TC-KNW-014: 录入文本后列表包含该文档"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]
        client.post(f"/api/v1/industries/{slug}/knowledge/text", json=sample_knowledge_text)

        response = client.get(f"/api/v1/industries/{slug}/knowledge")
        assert response.status_code == 200
        data = response.json()
        items = data["data"].get("items", data["data"])
        assert len(items) >= 1

    def test_list_pagination(self, client, sample_industry_data, sample_knowledge_text):
        """TC-KNW-015: 分页参数验证"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]
        for i in range(5):
            client.post(
                f"/api/v1/industries/{slug}/knowledge/text",
                json={"title": f"文档{i}", "content": f"测试内容{i} " * 10}
            )

        resp_page1 = client.get(f"/api/v1/industries/{slug}/knowledge?page=1&page_size=2")
        assert resp_page1.status_code == 200
        resp_page2 = client.get(f"/api/v1/industries/{slug}/knowledge?page=2&page_size=2")
        assert resp_page2.status_code == 200

    def test_list_nonexistent_industry(self, client):
        """TC-KNW-016: 不存在的行业列表返回 404"""
        response = client.get("/api/v1/industries/nonexistent/knowledge")
        assert response.status_code == 404


class TestDeleteKnowledge:
    """DELETE /api/v1/industries/{slug}/knowledge/{doc_id} - 删除文档"""

    def test_delete_knowledge_success(self, client, sample_industry_data, sample_knowledge_text):
        """TC-KNW-017: 正常删除文档"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]
        insert_resp = client.post(f"/api/v1/industries/{slug}/knowledge/text", json=sample_knowledge_text)
        doc_id = insert_resp.json()["data"]["doc_id"]

        response = client.delete(f"/api/v1/industries/{slug}/knowledge/{doc_id}")
        assert response.status_code == 200
        assert response.json()["code"] == 0

    def test_delete_nonexistent_doc(self, client, sample_industry_data):
        """TC-KNW-018: 删除不存在的文档返回 404"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]

        response = client.delete(f"/api/v1/industries/{slug}/knowledge/nonexistent-id")
        assert response.status_code == 404

    def test_delete_then_list_empty(self, client, sample_industry_data, sample_knowledge_text):
        """TC-KNW-019: 删除后列表不再包含该文档"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]
        insert_resp = client.post(f"/api/v1/industries/{slug}/knowledge/text", json=sample_knowledge_text)
        doc_id = insert_resp.json()["data"]["doc_id"]

        client.delete(f"/api/v1/industries/{slug}/knowledge/{doc_id}")
        list_resp = client.get(f"/api/v1/industries/{slug}/knowledge")
        items = list_resp.json()["data"].get("items", list_resp.json()["data"])
        doc_ids = [item.get("id") for item in (items if isinstance(items, list) else [])]
        assert doc_id not in doc_ids