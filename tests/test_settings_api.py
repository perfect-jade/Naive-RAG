"""
系统配置 API 测试用例

覆盖 SPEC 5.2.6 ~ 5.2.8

测试范围:
- GET    /api/v1/settings             获取当前模型配置
- PUT    /api/v1/settings             更新模型配置
- GET    /api/v1/settings/models      获取可用模型列表
- GET    /api/v1/health               健康检查
"""

import pytest
import json


class TestHealthCheck:
    """GET /api/v1/health - 健康检查"""

    def test_health_check_ok(self, client):
        """TC-CFG-001: 健康检查返回 200"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_check_response_format(self, client):
        """TC-CFG-002: 健康检查响应格式"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "code" in data


class TestGetSettings:
    """GET /api/v1/settings - 获取系统配置"""

    def test_get_default_settings(self, client):
        """TC-CFG-003: 获取默认系统配置"""
        response = client.get("/api/v1/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "llm_model" in data["data"]
        assert "embedding_model" in data["data"]
        assert "api_key_configured" in data["data"]

    def test_get_settings_has_default_llm_model(self, client):
        """TC-CFG-004: 默认 LLM 模型为 qwen-plus"""
        response = client.get("/api/v1/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["llm_model"] == "qwen-plus"

    def test_get_settings_has_default_embedding_model(self, client):
        """TC-CFG-005: 默认 Embedding 模型为 text-embedding-v2"""
        response = client.get("/api/v1/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["embedding_model"] == "text-embedding-v2"

    def test_get_settings_api_key_not_configured(self, client):
        """TC-CFG-006: 未配置 API Key 时 api_key_configured 为 false"""
        response = client.get("/api/v1/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["api_key_configured"] == False


class TestUpdateSettings:
    """PUT /api/v1/settings - 更新系统配置"""

    def test_update_llm_model(self, client):
        """TC-CFG-007: 更新 LLM 模型"""
        response = client.put(
            "/api/v1/settings",
            json={"llm_model": "qwen-max"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["message"] == "配置已更新"

        get_resp = client.get("/api/v1/settings")
        assert get_resp.json()["data"]["llm_model"] == "qwen-max"

    def test_update_embedding_model(self, client):
        """TC-CFG-008: 更新 Embedding 模型"""
        response = client.put(
            "/api/v1/settings",
            json={"embedding_model": "text-embedding-v3"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        get_resp = client.get("/api/v1/settings")
        assert get_resp.json()["data"]["embedding_model"] == "text-embedding-v3"

    def test_update_embedding_model_warning(self, client):
        """TC-CFG-009: 切换 Embedding 模型时返回警告"""
        response = client.put(
            "/api/v1/settings",
            json={"embedding_model": "text-embedding-v3"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["embedding_changed"] == True
        assert "warning" in data["data"]
        assert "Embedding" in data["data"]["warning"]

    def test_update_api_key(self, client, sample_settings_update):
        """TC-CFG-010: 更新 API Key"""
        response = client.put(
            "/api/v1/settings",
            json={"api_key": "sk-test-key-updated"}
        )
        assert response.status_code == 200
        assert response.json()["code"] == 0

        get_resp = client.get("/api/v1/settings")
        assert get_resp.json()["data"]["api_key_configured"] == True

    def test_update_all_settings(self, client, sample_settings_update):
        """TC-CFG-011: 同时更新所有配置"""
        response = client.put("/api/v1/settings", json=sample_settings_update)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        get_resp = client.get("/api/v1/settings")
        settings = get_resp.json()["data"]
        assert settings["llm_model"] == "qwen-max"
        assert settings["embedding_model"] == "text-embedding-v3"
        assert settings["api_key_configured"] == True

    def test_update_invalid_llm_model(self, client):
        """TC-CFG-012: 更新为无效的 LLM 模型应返回错误"""
        response = client.put(
            "/api/v1/settings",
            json={"llm_model": "invalid-model-name"}
        )
        assert response.status_code in (400, 422)

    def test_update_invalid_embedding_model(self, client):
        """TC-CFG-013: 更新为无效的 Embedding 模型应返回错误"""
        response = client.put(
            "/api/v1/settings",
            json={"embedding_model": "invalid-embedding-model"}
        )
        assert response.status_code in (400, 422)

    def test_update_empty_body(self, client):
        """TC-CFG-014: 空请求体更新应返回错误"""
        response = client.put("/api/v1/settings", json={})
        assert response.status_code in (400, 422)

    def test_update_no_change_embedding(self, client):
        """TC-CFG-015: 更新为相同 Embedding 模型时 embedding_changed 为 false"""
        client.put("/api/v1/settings", json={"embedding_model": "text-embedding-v2"})
        response = client.put(
            "/api/v1/settings",
            json={"embedding_model": "text-embedding-v2"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["embedding_changed"] == False


class TestGetModels:
    """GET /api/v1/settings/models - 获取可用模型列表"""

    def test_get_available_models(self, client):
        """TC-CFG-016: 获取可用的 LLM 和 Embedding 模型列表"""
        response = client.get("/api/v1/settings/models")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "llm_models" in data["data"]
        assert "embedding_models" in data["data"]

    def test_llm_models_list(self, client):
        """TC-CFG-017: LLM 模型列表包含 qwen-turbo/plus/max/long"""
        response = client.get("/api/v1/settings/models")
        assert response.status_code == 200
        models = response.json()["data"]["llm_models"]
        model_ids = {m["id"] for m in models}
        expected = {"qwen-turbo", "qwen-plus", "qwen-max", "qwen-long"}
        assert expected.issubset(model_ids)

    def test_embedding_models_list(self, client):
        """TC-CFG-018: Embedding 模型列表包含 v1/v2/v3 及维度信息"""
        response = client.get("/api/v1/settings/models")
        assert response.status_code == 200
        models = response.json()["data"]["embedding_models"]
        model_ids = {m["id"] for m in models}
        expected = {"text-embedding-v1", "text-embedding-v2", "text-embedding-v3"}
        assert expected.issubset(model_ids)
        for m in models:
            assert "dimension" in m
            assert isinstance(m["dimension"], int)

    def test_models_list_has_descriptions(self, client):
        """TC-CFG-019: 模型列表每项含 name 和 description"""
        response = client.get("/api/v1/settings/models")
        assert response.status_code == 200
        data = response.json()["data"]
        for m in data["llm_models"]:
            assert "name" in m
            assert "description" in m