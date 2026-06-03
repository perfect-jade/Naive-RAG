# 测试计划文档

> **项目**: 多行业知识库 RAG 系统  
> **版本**: v1.0  
> **日期**: 2026-06-01  

---

## 一、测试范围总览

```
tests/
├── conftest.py                           # 全局 Fixtures（临时目录、Mock 数据等）
├── api/
│   └── conftest.py                       # API 层专有 Fixtures（TestClient、Mock DashScope）
├── test_industry_api.py                  # 行业管理 API 测试 (18 用例)
├── test_knowledge_api.py                 # 知识管理 API 测试 (19 用例)
├── test_chat_api.py                      # 智能对话 API 测试 (14 用例)
├── test_settings_api.py                  # 系统配置 API 测试 (19 用例)
├── test_core_engine.py                   # 核心引擎单元测试 (28 用例)
├── test_file_parser_and_embedding.py     # 文件解析 + Embedding 测试 (19 用例)
├── frontend/
│   └── chat.test.ts                      # 前端组件 + API 层测试 (22 用例)
└── test_data/                            # 测试用样本文件
    ├── sample.txt
    ├── sample.pdf
    └── sample.docx
```

---

## 二、测试用例矩阵

### 2.1 行业管理 API (`test_industry_api.py`)

| 编号 | 测试用例 | 类型 | 优先级 |
|------|----------|------|--------|
| TC-IND-001 | 正常创建行业，验证返回完整数据 | 功能 | P0 |
| TC-IND-002 | 创建行业时 description 为空 | 边界 | P1 |
| TC-IND-003 | 创建重名行业应返回 409 冲突 | 异常 | P0 |
| TC-IND-004 | 名称为空字符串应返回 422 校验错误 | 校验 | P1 |
| TC-IND-005 | 名称含特殊字符时 slug 应正确处理 | 边界 | P1 |
| TC-IND-006 | 超长名称应被校验或截断 | 边界 | P2 |
| TC-IND-007 | 创建行业后验证目录结构已初始化 | 集成 | P0 |
| TC-IND-008 | 无行业时返回空列表 | 功能 | P1 |
| TC-IND-009 | 创建两个行业后列表返回 2 条 | 功能 | P0 |
| TC-IND-010 | 列表中每项应含 name/slug/doc_count/created_at | 功能 | P1 |
| TC-IND-011 | 获取存在的行业详情 | 功能 | P0 |
| TC-IND-012 | 获取不存在的行业返回 404 | 异常 | P0 |
| TC-IND-013 | 更新行业描述 | 功能 | P1 |
| TC-IND-014 | 更新行业名称应同步更新 slug | 功能 | P0 |
| TC-IND-015 | 更新不存在的行业返回 404 | 异常 | P1 |
| TC-IND-016 | 正常删除行业 | 功能 | P0 |
| TC-IND-017 | 删除不存在的行业返回 404 | 异常 | P1 |
| TC-IND-018 | 删除后列表不再包含该行业 | 功能 | P0 |

### 2.2 知识管理 API (`test_knowledge_api.py`)

| 编号 | 测试用例 | 类型 | 优先级 |
|------|----------|------|--------|
| TC-KNW-001 | 正常录入文本知识，返回 chunk_count | 功能 | P0 |
| TC-KNW-002 | 无标题的文本录入 | 边界 | P1 |
| TC-KNW-003 | 空内容录入应返回 422 | 校验 | P0 |
| TC-KNW-004 | 向不存在的行业录入文本返回 404 | 异常 | P1 |
| TC-KNW-005 | 超长文本录入应正确分块 | 功能 | P0 |
| TC-KNW-006 | 带标签录入，标签应正确保存 | 功能 | P1 |
| TC-KNW-007 | 上传 TXT 文件成功 | 功能 | P0 |
| TC-KNW-008 | 批量上传多个文件 | 功能 | P1 |
| TC-KNW-009 | 上传不支持的文件类型应返回错误 | 安全 | P0 |
| TC-KNW-010 | 上传超大文件应被限制 | 安全 | P1 |
| TC-KNW-011 | 向不存在的行业上传文件返回 404 | 异常 | P1 |
| TC-KNW-012 | 不附带文件的上传请求返回 422 | 校验 | P2 |
| TC-KNW-013 | 新建行业的知识列表为空 | 功能 | P1 |
| TC-KNW-014 | 录入文本后列表包含该文档 | 功能 | P0 |
| TC-KNW-015 | 分页参数验证 | 功能 | P1 |
| TC-KNW-016 | 不存在的行业列表返回 404 | 异常 | P1 |
| TC-KNW-017 | 正常删除文档 | 功能 | P0 |
| TC-KNW-018 | 删除不存在的文档返回 404 | 异常 | P1 |
| TC-KNW-019 | 删除后列表不再包含该文档 | 功能 | P0 |

### 2.3 智能对话 API (`test_chat_api.py`)

| 编号 | 测试用例 | 类型 | 优先级 |
|------|----------|------|--------|
| TC-CHT-001 | 医疗问题路由到医疗健康行业 | 功能 | P0 |
| TC-CHT-002 | 无行业时路由返回 general | 边界 | P0 |
| TC-CHT-003 | 路由结果应包含置信度 | 功能 | P1 |
| TC-CHT-004 | 空问题路由返回 422 | 校验 | P0 |
| TC-CHT-005 | 模糊问题应返回 confidence=low | 边界 | P1 |
| TC-CHT-006 | 超长问题路由请求不崩溃 | 边界 | P2 |
| TC-CHT-007 | 自动判断行业 + 流式对话完整流程 | 功能 | P0 |
| TC-CHT-008 | 手动指定行业，跳过路由步骤 | 功能 | P0 |
| TC-CHT-009 | 带历史记录的流式对话 | 功能 | P1 |
| TC-CHT-010 | 空问题流式对话返回 422 | 校验 | P0 |
| TC-CHT-011 | SSE 响应格式校验（content-type） | 集成 | P0 |
| TC-CHT-012 | 知识库无相关内容时告知无法回答 | 功能 | P0 |
| TC-CHT-013 | 无对话时返回空历史列表 | 功能 | P1 |
| TC-CHT-014 | 对话后历史记录应包含该对话 | 功能 | P1 |

### 2.4 系统配置 API (`test_settings_api.py`)

| 编号 | 测试用例 | 类型 | 优先级 |
|------|----------|------|--------|
| TC-CFG-001 | 健康检查返回 200 | 冒烟 | P0 |
| TC-CFG-002 | 健康检查响应格式 | 冒烟 | P1 |
| TC-CFG-003 | 获取默认系统配置 | 功能 | P0 |
| TC-CFG-004 | 默认 LLM 模型为 qwen-plus | 功能 | P0 |
| TC-CFG-005 | 默认 Embedding 模型为 text-embedding-v2 | 功能 | P0 |
| TC-CFG-006 | 未配置 API Key 时 api_key_configured 为 false | 功能 | P1 |
| TC-CFG-007 | 更新 LLM 模型 | 功能 | P0 |
| TC-CFG-008 | 更新 Embedding 模型 | 功能 | P0 |
| TC-CFG-009 | 切换 Embedding 模型时返回警告 | 功能 | P0 |
| TC-CFG-010 | 更新 API Key | 功能 | P1 |
| TC-CFG-011 | 同时更新所有配置 | 功能 | P1 |
| TC-CFG-012 | 更新为无效的 LLM 模型应返回错误 | 校验 | P0 |
| TC-CFG-013 | 更新为无效的 Embedding 模型应返回错误 | 校验 | P0 |
| TC-CFG-014 | 空请求体更新应返回错误 | 校验 | P1 |
| TC-CFG-015 | 更新为相同 Embedding 模型时 embedding_changed 为 false | 边界 | P1 |
| TC-CFG-016 | 获取可用模型列表 | 功能 | P0 |
| TC-CFG-017 | LLM 模型列表含 qwen-turbo/plus/max/long | 功能 | P0 |
| TC-CFG-018 | Embedding 模型列表含 v1/v2/v3 及维度 | 功能 | P0 |
| TC-CFG-019 | 模型列表每项含 name 和 description | 功能 | P1 |

### 2.5 核心引擎 (`test_core_engine.py`)

| 编号 | 测试用例 | 类型 | 优先级 |
|------|----------|------|--------|
| TC-ENG-001 | 创建空 FAISS 索引成功 | 单元 | P0 |
| TC-ENG-002 | 向索引导入向量后 ntotal 正确 | 单元 | P0 |
| TC-ENG-003 | 检索返回指定数量的 K 个结果 | 单元 | P0 |
| TC-ENG-004 | 用已入库向量检索自身排第一位 | 单元 | P0 |
| TC-ENG-005 | 保存后重新加载索引数据一致 | 单元 | P0 |
| TC-ENG-006 | faiss_id 和 chunk_id 映射正确性 | 单元 | P1 |
| TC-ENG-007 | 分批添加向量总数正确 | 单元 | P1 |
| TC-ENG-008 | 通过重建索引实现删除 | 单元 | P1 |
| TC-ENG-009 | 空索引检索应返回空结果或错误 | 边界 | P1 |
| TC-ENG-010 | BM25 索引构建成功 | 单元 | P0 |
| TC-ENG-011 | BM25 返回 Top-K 结果 | 单元 | P0 |
| TC-ENG-012 | BM25 对相关文档评分高于不相关 | 单元 | P0 |
| TC-ENG-013 | BM25 序列化后加载可正常使用 | 单元 | P1 |
| TC-ENG-014 | 空语料库妥善处理 | 边界 | P1 |
| TC-ENG-015 | 中文分词后 BM25 检索 | 单元 | P0 |
| TC-ENG-016 | RRF 融合排序算法正确性 | 单元 | P0 |
| TC-ENG-017 | RRF 融合后两边都排名靠前的文档排第一 | 单元 | P0 |
| TC-ENG-018 | RRF 融合后按 top_k 截断 | 单元 | P1 |
| TC-ENG-019 | 只有一个检索源有结果时直接返回 | 边界 | P1 |
| TC-ENG-020 | 不同 RRF k 值的排序变化 | 边界 | P2 |
| TC-ENG-021 | 两个检索源都为空时返回空 | 边界 | P1 |
| TC-ENG-022 | 解析合法路由响应 JSON | 单元 | P0 |
| TC-ENG-023 | 解析 general 类型路由响应 | 单元 | P0 |
| TC-ENG-024 | 路由 Prompt 模板包含行业列表和用户问题 | 单元 | P1 |
| TC-ENG-025 | LLM 返回非法 JSON 时容错处理 | 异常 | P0 |
| TC-ENG-026 | LLM 返回不在列表中的行业名时 fallback | 异常 | P1 |
| TC-ENG-027 | 行业名 -> slug 映射关系 | 单元 | P1 |
| TC-ENG-028 | 多个行业时选最匹配的 | 逻辑 | P0 |

### 2.6 文件解析 & Embedding (`test_file_parser_and_embedding.py`)

| 编号 | 测试用例 | 类型 | 优先级 |
|------|----------|------|--------|
| TC-FPR-001 | 解析 TXT 文件 | 单元 | P0 |
| TC-FPR-002 | 解析 Markdown 文件 | 单元 | P0 |
| TC-FPR-003 | 解析 DOCX 文件 | 单元 | P0 |
| TC-FPR-004 | 解析 PDF 文件 | 单元 | P0 |
| TC-FPR-005 | 不支持的文件类型返回错误 | 校验 | P1 |
| TC-FPR-006 | 解析空文件返回空字符串 | 边界 | P1 |
| TC-FPR-007 | 解析大文件不崩溃 | 边界 | P1 |
| TC-FPR-008 | UTF-8 编码中文文件正确解析 | 功能 | P0 |
| TC-SPL-001 | 按 chunk_size 分块 | 单元 | P0 |
| TC-SPL-002 | 短文本分块不超过 1 个 | 边界 | P1 |
| TC-SPL-003 | 分块重叠验证 | 单元 | P1 |
| TC-SPL-004 | 空文本分块返回空列表 | 边界 | P1 |
| TC-SPL-005 | 中文文本按句号分块 | 功能 | P1 |
| TC-EMB-001 | Embedding 返回正确维度 | 单元 | P0 |
| TC-EMB-002 | Embedding 值均为浮点数 | 单元 | P1 |
| TC-EMB-003 | 批量生成 Embedding | 单元 | P1 |
| TC-EMB-004 | 切换 Embedding 模型后维度变化 | 功能 | P0 |
| TC-EMB-005 | Embedding 归一化后 L2 范数为 1 | 单元 | P1 |
| TC-EMB-006 | 相似文本 Embedding 相似度更高 | 单元 | P0 |

### 2.7 前端 (`tests/frontend/chat.test.ts`)

| 编号 | 测试用例 | 类型 | 优先级 |
|------|----------|------|--------|
| TC-FE-001 | 行业列表为空时显示空状态提示 | UI | P1 |
| TC-FE-002 | 行业列表渲染多个行业卡片 | UI | P0 |
| TC-FE-003 | 点击创建行业按钮打开创建弹窗 | 交互 | P0 |
| TC-FE-004 | 行业名称输入校验 - 空名称不允许提交 | 校验 | P0 |
| TC-FE-005 | 知识列表分页展示 | UI | P1 |
| TC-FE-006 | 删除文档前弹出确认框 | 交互 | P1 |
| TC-FE-007 | 文件上传组件接受正确格式 | UI | P1 |
| TC-FE-008 | 发送消息后显示在对话列表中 | 交互 | P0 |
| TC-FE-009 | 行业选择器自动判断 vs 手动选择 | UI | P0 |
| TC-FE-010 | 流式输出 token 逐字追加 | 功能 | P0 |
| TC-FE-011 | 检索为空时显示提示信息 | UI | P0 |
| TC-FE-012 | 对话历史列表展示 | UI | P1 |
| TC-FE-013 | API Key 输入框为密码类型 | 安全 | P0 |
| TC-FE-014 | LLM 模型切换单选按钮组 | UI | P0 |
| TC-FE-015 | 切换 Embedding 模型时弹出警告 | 交互 | P0 |
| TC-FE-016 | 保存配置后显示成功提示 | UI | P1 |
| TC-FE-017 | 行业 API 请求封装 - 创建行业 | 集成 | P0 |
| TC-FE-018 | 知识 API 请求封装 - 文本录入 | 集成 | P0 |
| TC-FE-019 | SSE 流式对话事件解析 | 集成 | P0 |
| TC-FE-020 | 设置 API 请求封装 - 获取模型列表 | 集成 | P1 |
| TC-FE-021 | API 请求失败时显示错误提示 | 异常 | P1 |
| TC-FE-022 | 长文本在对话中正确截断显示 | 边界 | P2 |

---

## 三、统计汇总

| 分类 | 用例数 | P0 | P1 | P2 |
|------|--------|----|----|-----|
| 行业管理 API | 18 | 8 | 8 | 2 |
| 知识管理 API | 19 | 8 | 9 | 2 |
| 智能对话 API | 14 | 9 | 4 | 1 |
| 系统配置 API | 19 | 11 | 8 | 0 |
| 核心引擎 | 28 | 15 | 11 | 2 |
| 文件解析 & Embedding | 19 | 10 | 9 | 0 |
| 前端 | 22 | 12 | 8 | 2 |
| **总计** | **139** | **73** | **57** | **9** |

---

## 四、运行方式

### 后端测试（Python）

```bash
cd RAG

# 安装测试依赖
pip install pytest pytest-asyncio pytest-cov httpx

# 运行全部测试
pytest tests/ -v

# 运行特定模块
pytest tests/test_industry_api.py -v
pytest tests/test_knowledge_api.py -v
pytest tests/test_chat_api.py -v
pytest tests/test_settings_api.py -v
pytest tests/test_core_engine.py -v
pytest tests/test_file_parser_and_embedding.py -v

# 带覆盖率报告
pytest tests/ --cov=backend --cov-report=html
```

### 前端测试（TypeScript）

```bash
cd RAG

# 安装测试依赖
npm install -D vitest @vue/test-utils jsdom

# 运行前端测试
npx vitest run

# 带覆盖率
npx vitest run --coverage
```

---

## 五、Mock 策略说明

| 依赖 | Mock 方式 | 原因 |
|------|-----------|------|
| DashScope Embedding API | `unittest.mock.patch` | 不产生 API 调用费用 |
| DashScope Generation API | `unittest.mock.patch` | 不可控延迟和费用 |
| FAISS 索引 | 真实 FAISS 库 | 本地操作，无外部依赖 |
| BM25 (rank-bm25) | 真实库 | 纯计算，无外部依赖 |
| 文件解析 | 真实文件 I/O | 使用临时文件测试 |
| 前端 API (fetch) | `vi.fn().mockResolvedValue` | 隔离后端依赖 |