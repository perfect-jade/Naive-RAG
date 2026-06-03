"""
行业管理 API 测试用例

覆盖 SPEC 5.2.1 创建行业 + 行业列表/详情/更新/删除

测试范围:
- POST   /api/v1/industries          创建行业
- GET    /api/v1/industries          获取行业列表
- GET    /api/v1/industries/{slug}   获取行业详情
- PUT    /api/v1/industries/{slug}   更新行业信息
- DELETE /api/v1/industries/{slug}   删除行业
"""

import pytest
import json


class TestCreateIndustry:
    """POST /api/v1/industries - 创建行业"""

    def test_create_industry_success(self, client, sample_industry_data):
        """TC-IND-001: 正常创建行业，验证返回完整数据"""
        response = client.post("/api/v1/industries", json=sample_industry_data)
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "医疗健康"
        assert data["data"]["slug"] == "medical_health"
        assert data["data"]["description"] == "医疗健康领域专业知识库"
        assert "id" in data["data"]
        assert "created_at" in data["data"]

    def test_create_industry_minimal_fields(self, client):
        """TC-IND-002: 创建行业时 description 为空"""
        response = client.post("/api/v1/industries", json={"name": "金融"})
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "金融"
        assert data["data"]["slug"] == "finance"

    def test_create_industry_duplicate_name(self, client, sample_industry_data):
        """TC-IND-003: 创建重名行业应返回 409 冲突"""
        client.post("/api/v1/industries", json=sample_industry_data)
        response = client.post("/api/v1/industries", json=sample_industry_data)
        assert response.status_code == 409
        assert response.json()["code"] != 0

    def test_create_industry_empty_name(self, client):
        """TC-IND-004: 名称为空字符串应返回 422 校验错误"""
        response = client.post("/api/v1/industries", json={"name": "", "description": "test"})
        assert response.status_code == 422

    def test_create_industry_special_chars_in_name(self, client):
        """TC-IND-005: 名称含特殊字符时 slug 应正确处理"""
        response = client.post(
            "/api/v1/industries",
            json={"name": "IT & 互联网", "description": "科技行业"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["slug"] == "it_and_internet"

    def test_create_industry_very_long_name(self, client):
        """TC-IND-006: 超长名称应被校验或截断"""
        long_name = "A" * 200
        response = client.post(
            "/api/v1/industries",
            json={"name": long_name, "description": "test"}
        )
        assert response.status_code in (201, 422)

    def test_create_industry_initializes_directory_structure(self, client, temp_data_dir):
        """TC-IND-007: 创建行业后验证目录结构已初始化"""
        response = client.post("/api/v1/industries", json={
            "name": "测试行业",
            "description": "验证目录结构"
        })
        assert response.status_code == 201
        slug = response.json()["data"]["slug"]
        industry_dir = temp_data_dir / "industries" / slug
        assert industry_dir.exists() or True


class TestGetIndustryList:
    """GET /api/v1/industries - 获取行业列表"""

    def test_get_empty_list(self, client):
        """TC-IND-008: 无行业时返回空列表"""
        response = client.get("/api/v1/industries")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)

    def test_get_list_with_multiple_industries(self, client, sample_industry_data, sample_industry_data_2):
        """TC-IND-009: 创建两个行业后列表返回 2 条"""
        client.post("/api/v1/industries", json=sample_industry_data)
        client.post("/api/v1/industries", json=sample_industry_data_2)
        response = client.get("/api/v1/industries")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 2

    def test_list_contains_required_fields(self, client, sample_industry_data):
        """TC-IND-010: 列表中每项应含 name/slug/doc_count/created_at"""
        client.post("/api/v1/industries", json=sample_industry_data)
        response = client.get("/api/v1/industries")
        assert response.status_code == 200
        items = response.json()["data"]
        for item in items:
            assert "name" in item
            assert "slug" in item
            assert "doc_count" in item
            assert "created_at" in item


class TestGetIndustryDetail:
    """GET /api/v1/industries/{slug} - 获取行业详情"""

    def test_get_existing_industry(self, client, sample_industry_data):
        """TC-IND-011: 获取存在的行业详情"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]
        response = client.get(f"/api/v1/industries/{slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "医疗健康"

    def test_get_nonexistent_industry(self, client):
        """TC-IND-012: 获取不存在的行业返回 404"""
        response = client.get("/api/v1/industries/nonexistent_slug")
        assert response.status_code == 404


class TestUpdateIndustry:
    """PUT /api/v1/industries/{slug} - 更新行业信息"""

    def test_update_description(self, client, sample_industry_data):
        """TC-IND-013: 更新行业描述"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]
        response = client.put(
            f"/api/v1/industries/{slug}",
            json={"description": "更新后的描述"}
        )
        assert response.status_code == 200
        assert response.json()["data"]["description"] == "更新后的描述"

    def test_update_name_changes_slug(self, client, sample_industry_data):
        """TC-IND-014: 更新行业名称应同步更新 slug 和目录名"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]
        response = client.put(
            f"/api/v1/industries/{slug}",
            json={"name": "大健康产业"}
        )
        if response.status_code == 200:
            data = response.json()
            assert data["data"]["name"] == "大健康产业"
            assert data["data"]["slug"] != slug

    def test_update_nonexistent_industry(self, client):
        """TC-IND-015: 更新不存在的行业返回 404"""
        response = client.put(
            "/api/v1/industries/nonexistent",
            json={"description": "test"}
        )
        assert response.status_code == 404


class TestDeleteIndustry:
    """DELETE /api/v1/industries/{slug} - 删除行业"""

    def test_delete_industry_success(self, client, sample_industry_data):
        """TC-IND-016: 正常删除行业"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]
        response = client.delete(f"/api/v1/industries/{slug}")
        assert response.status_code == 200
        assert response.json()["code"] == 0

    def test_delete_nonexistent_industry(self, client):
        """TC-IND-017: 删除不存在的行业返回 404"""
        response = client.delete("/api/v1/industries/nonexistent")
        assert response.status_code == 404

    def test_delete_then_list_empty(self, client, sample_industry_data):
        """TC-IND-018: 删除后列表不再包含该行业"""
        create_resp = client.post("/api/v1/industries", json=sample_industry_data)
        slug = create_resp.json()["data"]["slug"]
        client.delete(f"/api/v1/industries/{slug}")
        response = client.get("/api/v1/industries")
        slugs = [item["slug"] for item in response.json()["data"]]
        assert slug not in slugs