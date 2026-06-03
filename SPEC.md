# 多行业知识库 RAG 系统 - 需求规格说明书 (SPEC)

> **版本**: v0.2  
> **日期**: 2026-06-01  
> **状态**: 已确认核心方案，待确认部分细节

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术架构](#2-技术架构)
3. [功能需求](#3-功能需求)
4. [数据模型](#4-数据模型)
5. [API 接口设计](#5-api-接口设计)
6. [前端设计](#6-前端设计)
7. [非功能需求](#7-非功能需求)
8. [待确认事项](#8-待确认事项)

---

## 1. 项目概述

### 1.1 项目背景

构建一个支持**多行业数据隔离**的 RAG（检索增强生成）知识库系统。系统以 DashScope 作为大模型（LLM + Embedding）服务商，本地使用 FAISS + BM25 实现混合检索，前端提供完整的行业管理、知识录入、智能对话功能。

### 1.2 项目目标

| 目标 | 描述 |
|------|------|
| 多行业隔离 | 每个行业拥有独立的向量库和 BM25 索引，数据物理隔离 |
| 智能路由 | LLM 自动判断用户问题所属行业，路由到对应知识库检索 |
| 混合检索 | FAISS（语义检索）+ BM25（关键词检索）+ 结果融合排序 |
| 便捷管理 | 前端可视化完成行业创建、知识录入、文件上传、对话交互 |

### 1.3 核心流程

```
用户输入问题
    │
    ▼
┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐
│  行业识别     │───▶│  对应行业知识库   │───▶│  FAISS + BM25    │
│  (LLM判断)   │    │  路由 & 检索     │    │  混合检索        │
└──────────────┘    └─────────────────┘    └──────────────────┘
                                                 │
                                                 ▼
                    ┌─────────────────┐    ┌──────────────────┐
                    │  前端展示回答    │◀───│  LLM 生成回答    │
                    │  + 引用来源     │    │  (DashScope)     │
                    └─────────────────┘    └──────────────────┘
```

---

## 2. 技术架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层                               │
│  行业管理 │ 知识录入 │ 文件上传 │ 智能对话                    │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP / WebSocket / SSE
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      后端 API 层 (Python)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ 行业管理  │ │ 知识管理  │ │ 对话管理  │ │ 文件处理      │  │
│  │ Module   │ │ Module   │ │ Module   │ │ Module        │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│  FAISS 引擎  │ │  BM25 引擎   │ │  DashScope API   │
│  (向量检索)  │ │  (关键词检索) │ │  (LLM+Embedding) │
└──────────────┘ └──────────────┘ └──────────────────┘
          │              │
          ▼              ▼
┌─────────────────────────────────────────────┐
│              本地文件存储                     │
│  data/industries/{industry_name}/           │
│    ├── faiss_index/      # FAISS 向量索引   │
│    ├── bm25_index/       # BM25 索引        │
│    ├── metadata.db       # 文档元数据        │
│    └── raw_docs/         # 原始上传文件      │
└─────────────────────────────────────────────┘
```

### 2.2 技术选型

| 层次 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Python + FastAPI | 异步支持好，适合 LLM 流式输出 |
| LLM 服务 | DashScope (阿里百炼) | 使用 Qwen 系列模型；**用户可在前端配置切换** |
| Embedding | DashScope text-embedding | 文本向量化；**用户可在前端配置切换版本** |
| 向量存储 | FAISS (CPU) | 本地轻量级向量检索 |
| 关键词检索 | rank-bm25 | BM25 算法 Python 实现 |
| 前端 | **Vue 3 + Vite** | 前后端分离架构，TypeScript + Element Plus |
| 文档解析 | python-docx, PyPDF2, markdown | 支持多格式文件上传解析 |
| 元数据存储 | SQLite | 存储文档片段、行业等元信息 |
| 系统配置存储 | SQLite / JSON | 存储用户模型选择等配置 |
| 文本分块 | LangChain TextSplitter 或自实现 | RecursiveCharacterTextSplitter |

### 2.3 目录结构设计

```
RAG/
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置管理（API Key、路径、模型配置等）
│   ├── api/
│   │   ├── __init__.py
│   │   ├── industry.py         # 行业管理接口
│   │   ├── knowledge.py        # 知识管理接口
│   │   ├── chat.py             # 对话接口（SSE 流式）
│   │   └── settings.py         # 系统配置接口（模型切换等）
│   ├── core/
│   │   ├── __init__.py
│   │   ├── llm_client.py       # DashScope LLM 调用封装
│   │   ├── embedding.py        # DashScope Embedding 封装
│   │   ├── faiss_engine.py     # FAISS 索引管理
│   │   ├── bm25_engine.py      # BM25 索引管理
│   │   ├── retriever.py        # 混合检索 + 融合排序
│   │   └── router.py           # 行业路由器（LLM判断行业）
│   ├── services/
│   │   ├── __init__.py
│   │   ├── industry_service.py # 行业业务逻辑
│   │   ├── knowledge_service.py# 知识业务逻辑（分块、入库）
│   │   ├── chat_service.py     # 对话业务逻辑
│   │   └── file_parser.py      # 文件解析（PDF/Word/TXT）
│   └── models/
│       ├── __init__.py
│       └── schemas.py          # Pydantic 数据模型
├── frontend/                    # Vue 3 前端项目
│   ├── src/
│   │   ├── views/              # 页面组件
│   │   ├── components/         # 通用组件
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── api/                # API 请求封装
│   │   └── router/             # Vue Router 路由
│   ├── package.json
│   └── vite.config.ts
├── data/
│   ├── config.db               # 全局系统配置（模型选择等）
│   └── industries/             # 按行业隔离的数据目录
│       └── {industry_name}/
│           ├── faiss_index/
│           ├── bm25_index/
│           ├── metadata.db
│           └── raw_docs/
├── requirements.txt
└── SPEC.md
```

---

## 3. 功能需求

### 3.1 功能模块总览

```
┌─────────────────────────────────────────────────────────┐
│                    功能模块                              │
├───────────────┬───────────────┬───────────┬─────────────┤
│  行业管理      │  知识管理      │  智能对话  │  系统配置   │
├───────────────┼───────────────┼───────────┼─────────────┤
│ • 创建行业    │ • 文本录入    │ • 对话界面 │ • API Key   │
│ • 行业列表    │ • 文件上传    │ • 行业识别 │   配置      │
│ • 编辑行业    │ • 批量导入    │ • 知识检索 │ • LLM 模型  │
│ • 删除行业    │ • 知识检索    │ • 引用展示 │   选择切换  │
│               │ • 知识删除    │ • 流式输出 │ • Embedding │
│               │ • 知识列表    │ • 对话历史 │   模型切换  │
└───────────────┴───────────────┴───────────┴─────────────┘
```

### 3.2 行业管理模块

#### 3.2.1 创建行业

| 项目 | 描述 |
|------|------|
| 触发 | 用户在前端点击「创建行业」 |
| 输入 | 行业名称（如"医疗健康"）、行业描述（如"医疗领域的专业知识库"） |
| 处理 | 1. 校验行业名称唯一性<br>2. 创建 `data/industries/{name}/` 目录结构<br>3. 初始化空 FAISS 索引<br>4. 初始化空 BM25 索引<br>5. 初始化 SQLite 元数据库 |
| 输出 | 创建成功 / 名称已存在提示 |
| 异常 | 目录创建失败 → 回滚并报错 |

#### 3.2.2 行业列表

| 项目 | 描述 |
|------|------|
| 触发 | 进入首页 / 手动刷新 |
| 展示 | 行业卡片列表，含名称、描述、文档数量、创建时间 |
| 排序 | 按创建时间倒序 |

#### 3.2.3 编辑/删除行业

| 操作 | 描述 |
|------|------|
| 编辑 | 修改行业名称或描述（名称变更需重命名目录及所有索引文件） |
| 删除 | 删除整个行业目录（含全部索引和文档），需二次确认 |

### 3.3 知识管理模块

#### 3.3.1 文本录入

| 项目 | 描述 |
|------|------|
| 入口 | 选择目标行业 → 进入知识管理 → 文本录入 |
| 输入 | 文本内容 + 可选标题 + 可选标签 |
| 处理流程 | 1. 文本分块（chunk_size=500, overlap=50）<br>2. 每块生成 Embedding（DashScope）<br>3. 写入 FAISS 索引<br>4. 构建 BM25 索引<br>5. 写入 SQLite 元数据 |
| 分块策略 | RecursiveCharacterTextSplitter，按段落/句子边界切分 |

**文本分块参数（可配置）：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| chunk_size | 500 | 每个 chunk 的最大字符数 |
| chunk_overlap | 50 | 相邻 chunk 的重叠字符数 |

#### 3.3.2 文件上传

| 项目 | 描述 |
|------|------|
| 支持格式 | PDF (.pdf), Word (.docx), 纯文本 (.txt), Markdown (.md) |
| 大小限制 | 单文件 ≤ 10MB（可配置） |
| 批量上传 | 支持一次上传多个文件 |
| 处理流程 | 1. 上传文件保存至 `raw_docs/`<br>2. 根据文件类型解析文本<br>3. 执行文本分块<br>4. 生成 Embedding 并入库<br>5. 更新 BM25 索引 |
| 进度反馈 | 返回处理进度（已处理 N/M 个文件） |

#### 3.3.3 知识列表/删除

| 功能 | 描述 |
|------|------|
| 列表 | 分页展示某行业下的所有文档，含标题、来源、分块数、录入时间 |
| 删除 | 支持删除单个文档（从其所有 chunk 的 FAISS/BM25/元数据中移除） |

### 3.4 智能对话模块

#### 3.4.1 行业自动识别（路由判断）

这是系统的核心逻辑，流程如下：

```
用户输入问题
    │
    ▼
┌─────────────────────────────────────────────┐
│ Step 1: 收集所有行业名称及描述列表            │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│ Step 2: 调用 DashScope LLM                  │
│ Prompt: "根据以下行业列表，判断用户问题属于   │
│ 哪个行业。行业列表：[...]。用户问题：{query}" │
│ 要求返回 JSON: {"industry": "行业名"}        │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│ Step 3: 路由到对应行业的检索器进行混合检索    │
└─────────────────────┬───────────────────────┘
                      ▼
┌─────────────────────────────────────────────┐
│ Step 4: 检索结果 + 用户问题 → LLM 生成回答   │
└─────────────────────────────────────────────┘
```

**路由判断 Prompt 模板：**

```
你是一个行业分类助手。当前知识库包含以下行业：
{industry_list}

请判断以下用户问题属于哪个行业，只返回 JSON 格式，不要包含其他内容：
{"industry": "行业名称", "confidence": "high/medium/low"}

如果问题不属于任何行业，返回：
{"industry": "general", "confidence": "low"}

用户问题：{user_query}
```

#### 3.4.2 混合检索策略

```
用户问题
    │
    ├──────────────┬──────────────┐
    ▼              ▼              │
┌────────┐   ┌─────────┐         │
│Embedding│   │  BM25   │         │
│语义检索 │   │关键词检索│         │
└────┬───┘   └────┬────┘         │
     │            │              │
     ▼            ▼              │
┌─────────────────────────┐      │
│ 结果融合 (RRF 算法)      │      │
│ score = 1/(k+rank_faiss) │      │
│       + 1/(k+rank_bm25)  │      │
└────────────┬────────────┘      │
             ▼                   │
┌─────────────────────────┐      │
│ Top-K 结果 (默认 K=5)    │      │
└─────────────────────────┘      │
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| faiss_top_k | 10 | FAISS 召回数量 |
| bm25_top_k | 10 | BM25 召回数量 |
| fusion_top_k | 5 | 融合后最终返回数量 |
| rrf_k | 60 | RRF 融合算法常数参数 |

#### 3.4.3 对话生成

| 项目 | 描述 |
|------|------|
| 模型 | DashScope Qwen 系列（**用户可在系统配置中选择**，默认 qwen-plus） |
| 输出方式 | SSE 流式输出，逐 token 返回前端 |
| System Prompt | "你是一个专业的行业知识助手，请根据提供的参考资料回答用户问题。如果参考资料不足以回答问题，请如实告知用户无法回答，不要编造信息。" |
| 上下文组装 | 检索到的 chunks 拼接为上下文，注入 Prompt |
| 引用展示 | 回答末尾标注使用了哪些来源文档 |
| 检索为空策略 | **直接告知用户"当前知识库中未找到相关内容，无法回答此问题"**，不进行 LLM 自由发挥 |
| 行业锁定 | 一次对话会话锁定一个行业，会话期间不切换行业 |

**对话 Prompt 模板：**

```
## 参考资料
{retrieved_chunks}

## 对话历史
{chat_history}

## 用户问题
{user_query}

请基于以上参考资料回答问题。如果资料不足以回答，请明确说明。回答时请注明引用的资料编号。
```

#### 3.4.4 对话历史与会话管理

| 功能 | 描述 |
|------|------|
| 存储 | 对话历史保存在后端 SQLite，关联会话 ID；前端可同步展示 |
| 会话 | 每次新建对话创建新会话 ID，会话绑定行业（首轮判断后锁定） |
| 管理 | 支持查看历史对话、新建对话、删除对话、切换对话 |
| 上下文 | 最近 N 轮对话（默认 5 轮）作为上下文传入 LLM |
| 行业切换 | 用户需手动开始新对话才能切换到其他行业 |

### 3.5 系统配置模块

#### 3.5.1 模型配置

用户可在前端设置页面切换 DashScope 的 LLM 模型和 Embedding 模型，配置持久化保存。

| 配置项 | 可选值 | 默认值 | 说明 |
|--------|--------|--------|------|
| LLM 模型 | `qwen-turbo` / `qwen-plus` / `qwen-max` / `qwen-long` | `qwen-plus` | 用于对话生成和行业判断 |
| Embedding 模型 | `text-embedding-v1` / `text-embedding-v2` / `text-embedding-v3` | `text-embedding-v2` | 用于文本向量化 |
| API Key | 用户输入的 DashScope API Key | 空 | 前端输入，后端加密存储 |

#### 3.5.2 配置存储

```
data/config.db  (SQLite)

CREATE TABLE config (
    key    TEXT PRIMARY KEY,   -- 配置项名称
    value  TEXT                -- 配置项值
);

示例数据:
  key="llm_model",       value="qwen-plus"
  key="embedding_model", value="text-embedding-v2"
  key="api_key",         value="sk-xxxxx"
```

#### 3.5.3 配置生效机制

```
用户在前端修改模型配置
    │
    ▼
调用 PUT /api/v1/settings
    │
    ▼
后端更新 config.db
    │
    ▼
后续对话/行业判断/Embedding 调用
均读取最新配置中的模型名称
    │
    ▼
⚠️ Embedding 模型切换后，
  已入库的向量维度可能不同，
  需要告警提示用户"切换 Embedding 模型后需重新录入知识"
```

#### 3.5.4 模型切换的影响与处理

| 切换场景 | 影响 | 处理方式 |
|----------|------|----------|
| 切换 LLM 模型 | 对话生成质量变化 | 即时生效，无需额外操作 |
| 切换 Embedding 模型 | 新旧向量维度不一致，FAISS 索引不兼容 | 前端弹出警告："切换 Embedding 模型后，已有的知识库向量将无法使用，建议重新录入知识或备份后清空重来" |

---

## 4. 数据模型

### 4.1 行业元数据

存储在 `data/industries/meta.json`（全局索引）或各行业目录内：

```json
{
  "id": "uuid",
  "name": "医疗健康",
  "slug": "medical_health",
  "description": "医疗健康领域专业知识库",
  "doc_count": 42,
  "chunk_count": 520,
  "created_at": "2026-06-01T10:00:00",
  "updated_at": "2026-06-01T12:00:00"
}
```

### 4.2 文档元数据 (SQLite)

每个行业目录下的 `metadata.db` 中 `documents` 表：

```sql
CREATE TABLE documents (
    id          TEXT PRIMARY KEY,       -- UUID
    title       TEXT,                   -- 文档标题
    source_type TEXT,                   -- 'text' | 'file'
    source_name TEXT,                   -- 上传文件名（file类型时）
    file_path   TEXT,                   -- 原始文件路径
    chunk_count INTEGER DEFAULT 0,
    tags        TEXT,                   -- JSON 数组
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.3 文本块元数据 (SQLite)

```sql
CREATE TABLE chunks (
    id          TEXT PRIMARY KEY,       -- UUID
    doc_id      TEXT NOT NULL,          -- 关联 documents.id
    chunk_index INTEGER,               -- 块序号
    content     TEXT,                   -- 块文本内容
    token_count INTEGER,               -- Token 数量
    faiss_id    INTEGER,               -- FAISS 索引中的 ID
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id)
);
```

### 4.4 FAISS 索引结构

每个行业一个 FAISS 索引文件：

```
data/industries/{slug}/faiss_index/
├── index.faiss       # FAISS 二进制索引文件
└── id_map.json       # faiss_id → chunk_id 映射
```

### 4.5 BM25 索引结构

每个行业一个 BM25 索引：

```
data/industries/{slug}/bm25_index/
├── corpus.json       # 分词后的语料库
├── index.pkl         # BM25 模型序列化文件
└── id_map.json       # bm25_id → chunk_id 映射
```

---

## 5. API 接口设计

### 5.1 接口总览

```
Base URL: http://localhost:8000/api/v1

行业管理:
  POST   /industries              创建行业
  GET    /industries              获取行业列表
  GET    /industries/{slug}       获取行业详情
  PUT    /industries/{slug}       更新行业信息
  DELETE /industries/{slug}       删除行业

知识管理:
  POST   /industries/{slug}/knowledge/text     文本录入
  POST   /industries/{slug}/knowledge/upload   文件上传
  GET    /industries/{slug}/knowledge          知识列表（分页）
  DELETE /industries/{slug}/knowledge/{doc_id} 删除文档

对话:
  POST   /chat/route              行业路由判断（仅判断行业）
  POST   /chat/stream             流式对话（SSE，含检索+生成）
  GET    /chat/history            获取对话历史（可选）

系统:
  GET    /health                  健康检查
  GET    /settings                获取当前模型配置
  PUT    /settings                更新模型配置
  GET    /settings/models         获取可用模型列表（从 DashScope 查询或本地预设）
```

### 5.2 核心接口详情

#### 5.2.1 创建行业

```
POST /api/v1/industries
Content-Type: application/json

Request:
{
  "name": "医疗健康",
  "description": "医疗健康领域专业知识库"
}

Response 201:
{
  "code": 0,
  "data": {
    "id": "uuid",
    "name": "医疗健康",
    "slug": "medical_health",
    "description": "医疗健康领域专业知识库",
    "created_at": "2026-06-01T10:00:00"
  }
}
```

#### 5.2.2 文本录入

```
POST /api/v1/industries/{slug}/knowledge/text
Content-Type: application/json

Request:
{
  "title": "高血压诊疗指南",
  "content": "高血压是指...（长文本）",
  "tags": ["心血管", "慢性病"]
}

Response 200:
{
  "code": 0,
  "data": {
    "doc_id": "uuid",
    "chunk_count": 15,
    "message": "知识录入成功"
  }
}
```

#### 5.2.3 文件上传

```
POST /api/v1/industries/{slug}/knowledge/upload
Content-Type: multipart/form-data

Form Fields:
  files: [file1.pdf, file2.docx]   // 多文件

Response 200:
{
  "code": 0,
  "data": {
    "results": [
      {"filename": "file1.pdf", "doc_id": "uuid1", "chunk_count": 20, "status": "success"},
      {"filename": "file2.docx", "doc_id": "uuid2", "chunk_count": 12, "status": "success"}
    ],
    "total_chunks": 32
  }
}
```

#### 5.2.4 流式对话（核心接口）

```
POST /api/v1/chat/stream
Content-Type: application/json

Request:
{
  "query": "高血压的诊断标准是什么？",
  "history": [                           // 可选，对话历史
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "industry": null                       // null 表示自动判断；可手动指定行业 slug
}

Response: SSE Stream
event: route
data: {"industry": "医疗健康", "slug": "medical_health", "confidence": "high"}

event: retrieval
data: {"count": 5, "sources": [{"title": "xxx", "chunk_index": 3}, ...]}

event: token
data: {"token": "根据"}

event: token
data: {"token": "资料"}

event: token
data: {"token": "显示"}

...

event: done
data: {"total_tokens": 350}
```

#### 5.2.5 行业路由判断（独立接口）

```
POST /api/v1/chat/route
Content-Type: application/json

Request:
{
  "query": "高血压的诊断标准是什么？"
}

Response 200:
{
  "code": 0,
  "data": {
    "industry": "医疗健康",
    "slug": "medical_health",
    "confidence": "high"
  }
}
```

#### 5.2.6 获取系统配置

```
GET /api/v1/settings

Response 200:
{
  "code": 0,
  "data": {
    "llm_model": "qwen-plus",
    "embedding_model": "text-embedding-v2",
    "api_key_configured": true
  }
}
```

#### 5.2.7 更新系统配置

```
PUT /api/v1/settings
Content-Type: application/json

Request:
{
  "llm_model": "qwen-max",
  "embedding_model": "text-embedding-v3",
  "api_key": "sk-xxxxx"
}

Response 200:
{
  "code": 0,
  "data": {
    "message": "配置已更新",
    "embedding_changed": true,
    "warning": "Embedding 模型已变更，已入库的向量索引可能不再兼容，建议重新录入知识"
  }
}
```

#### 5.2.8 获取可用模型列表

```
GET /api/v1/settings/models

Response 200:
{
  "code": 0,
  "data": {
    "llm_models": [
      {"id": "qwen-turbo", "name": "Qwen Turbo", "description": "快速、经济"},
      {"id": "qwen-plus", "name": "Qwen Plus", "description": "效果与速度平衡"},
      {"id": "qwen-max", "name": "Qwen Max", "description": "最强效果"},
      {"id": "qwen-long", "name": "Qwen Long", "description": "长文本处理"}
    ],
    "embedding_models": [
      {"id": "text-embedding-v1", "name": "Embedding V1", "dimension": 1536},
      {"id": "text-embedding-v2", "name": "Embedding V2", "dimension": 1536},
      {"id": "text-embedding-v3", "name": "Embedding V3", "dimension": 1024}
    ]
  }
}
```

---

## 6. 前端设计

### 6.1 页面结构

```
┌─────────────────────────────────────────────┐
│  Header / 导航栏                             │
│  [Logo]  多行业知识库 RAG 系统                 │
├──────────┬──────────────────────────────────┤
│          │                                  │
│  侧边栏  │         主内容区                  │
│          │                                  │
│ • 首页   │  根据左侧导航切换：               │
│ • 行业   │  - 行业卡片列表                  │
│   管理   │  - 知识录入/列表                 │
│ • 对话   │  - 对话面板                      │
│ • 系统   │  - 模型配置                      │
│   设置   │  - API Key 配置                  │
│          │                                  │
├──────────┴──────────────────────────────────┤
│  Footer                                     │
└─────────────────────────────────────────────┘
```

### 6.2 页面详情

#### 6.2.1 首页 / 行业选择页

```
┌─────────────────────────────────────────────┐
│  🏠 首页                                     │
│                                              │
│  [＋ 创建新行业]                              │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 🏥       │  │ ⚖️       │  │ 🏦       │   │
│  │ 医疗健康  │  │ 法律法规  │  │ 金融财经  │   │
│  │ 42 篇文档 │  │ 28 篇文档 │  │ 15 篇文档 │   │
│  │ [进入]   │  │ [进入]   │  │ [进入]   │   │
│  └──────────┘  └──────────┘  └──────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ 💬 快捷对话                           │    │
│  │ 输入问题，自动判断行业 → 检索 → 回答   │    │
│  │ [______________________________] [发送]│    │
│  └──────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

#### 6.2.2 行业详情 / 知识管理页

```
┌─────────────────────────────────────────────┐
│  📁 医疗健康 / 知识管理                       │
│                                              │
│  [文本录入]  [上传文件]  [批量导入]            │
│                                              │
│  ┌─ 搜索 ──────────────────────────────┐     │
│  │ [___________] 🔍                    │     │
│  └─────────────────────────────────────┘     │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ 📄 高血压诊疗指南              [删除] │    │
│  │    📅 2026-06-01   📊 15 chunks      │    │
│  │    🏷️ 心血管 慢性病                  │    │
│  ├──────────────────────────────────────┤    │
│  │ 📄 糖尿病防治手册              [删除] │    │
│  │    📅 2026-05-28   📊 23 chunks      │    │
│  │    🏷️ 内分泌                         │    │
│  ├──────────────────────────────────────┤    │
│  │ ...                                  │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  [← 上一页]  第 1/3 页  [下一页 →]           │
└─────────────────────────────────────────────┘
```

#### 6.2.3 对话页

```
┌─────────────────────────────────────────────┐
│  💬 智能对话                                 │
│                                              │
│  📍 当前行业：[自动判断 ▼]  或手动选择       │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ 对话区域                              │    │
│  │                                      │    │
│  │ 🤖 您好！我是行业知识助手，请提问。    │    │
│  │                                      │    │
│  │ 👤 高血压的诊断标准是什么？           │    │
│  │                                      │    │
│  │ 🔄 正在识别行业... → 医疗健康(high)   │    │
│  │ 🔍 正在检索知识库... → 找到5条相关    │    │
│  │                                      │    │
│  │ 🤖 根据资料显示，高血压的诊断标准为： │    │
│  │    1. 在未使用降压药物的情况下...     │    │
│  │    （流式逐字输出）                   │    │
│  │                                      │    │
│  │    📚 参考来源：                      │    │
│  │    • 高血压诊疗指南 (第3段)           │    │
│  │    • 心血管疾病手册 (第1段)           │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ [输入问题...___________________] [发送]│    │
│  └──────────────────────────────────────┘    │
│                                              │
│  📋 历史对话：[对话1] [对话2] ...  [+新对话]  │
└─────────────────────────────────────────────┘
```

### 6.3 文本录入弹窗

```
┌───────────────────────────────────┐
│  ✏️ 文本录入                       │
│                                   │
│  标题：[高血压诊疗指南 2024版___]   │
│                                   │
│  内容：                           │
│  ┌─────────────────────────────┐  │
│  │ 高血压是指以体循环动脉血压  │  │
│  │ （收缩压和/或舒张压）增高为  │  │
│  │ 主要特征...                  │  │
│  │                              │  │
│  └─────────────────────────────┘  │
│                                   │
│  标签：[心血管] [慢性病] [+添加]   │
│                                   │
│  [取消]              [确认录入]   │
└───────────────────────────────────┘
```

### 6.4 交互流程 - 完整对话流程

```
用户打开对话页
    │
    ├── 方式1: 自动判断行业
    │     ├── 用户输入问题
    │     ├── 前端显示"正在识别行业..."
    │     ├── 后端调用 /chat/stream
    │     ├── 收到 route 事件 → 展示识别结果
    │     ├── 收到 retrieval 事件 → 展示检索信息
    │     ├── 收到 token 事件 → 流式展示回答
    │     └── 收到 done 事件 → 对话结束
    │
    └── 方式2: 手动选择行业
          ├── 用户选择行业下拉框
          ├── 用户输入问题
          └── 后续流程同上（跳过 route 步骤）
```

### 6.5 系统设置页

```
┌─────────────────────────────────────────────────┐
│  ⚙️ 系统设置                                     │
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │ 🔑 API Key 配置                          │    │
│  │                                          │    │
│  │ DashScope API Key                        │    │
│  │ [sk-xxxxxxxxxxxxxxxxxxxxxxxx______] [🔒] │    │
│  │                                          │    │
│  │ ℹ️ 密钥将加密存储在本地服务器，不会外泄    │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │ 🤖 LLM 模型选择                          │    │
│  │                                          │    │
│  │ ○ Qwen Turbo    快速、经济，适合简单任务  │    │
│  │ ● Qwen Plus     效果与速度平衡（推荐）    │    │
│  │ ○ Qwen Max      最强效果，适合复杂推理    │    │
│  │ ○ Qwen Long     长文本处理，适合长文档    │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  ┌─────────────────────────────────────────┐    │
│  │ 📊 Embedding 模型选择                    │    │
│  │                                          │    │
│  │ ○ Embedding V1     维度 1536            │    │
│  │ ● Embedding V2     维度 1536（推荐）     │    │
│  │ ○ Embedding V3     维度 1024            │    │
│  │                                          │    │
│  │ ⚠️ 切换 Embedding 模型后，需要重新录入    │    │
│  │    知识库中的文档才能正常检索              │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  [保存配置]                                      │
│  ✅ 配置已保存                                   │
└─────────────────────────────────────────────────┘
```

---

## 7. 非功能需求

### 7.1 性能指标

| 指标 | 目标值 | 备注 |
|------|--------|------|
| 行业判断延迟 | < 2s | LLM 分类单次调用 |
| 检索延迟 | < 500ms | FAISS + BM25 检索 |
| 首 Token 延迟 | < 3s | 从请求到第一个 token 输出 |
| 文档录入速度 | > 100 chunks/min | 含 Embedding 生成 |
| 并发对话 | ≥ 5 用户 | 本地单机部署 |

### 7.2 安全性

| 项目 | 措施 |
|------|------|
| API Key | DashScope API Key 通过环境变量或配置文件管理，不暴露给前端 |
| 文件上传 | 校验文件类型和大小，防止恶意文件上传 |
| 路径遍历 | 行业 slug 需校验，防止路径遍历攻击 |

### 7.3 可扩展性

| 项目 | 设计 |
|------|------|
| 新增行业 | 无需修改代码，前端创建即可 |
| Embedding 模型切换 | 封装在 embedding.py 中，统一接口 |
| LLM 模型切换 | 封装在 llm_client.py 中，统一接口 |
| 检索策略扩展 | retriever.py 可增加其他检索器 |

---

## 8. 待确认事项

以下事项需要协商确认后才能进入开发阶段：

### 🔴 高优先级（影响整体架构）

| # | 事项 | 状态 | 决策 |
|---|------|------|------|
| 1 | **前端技术选型** | ✅ 已确认 | **Vue 3 + Vite + Element Plus**，前后端分离 |
| 2 | **DashScope 模型选择** | ✅ 已确认 | **用户可在前端配置中切换**，默认 qwen-plus |
| 3 | **Embedding 模型选择** | ✅ 已确认 | **用户可在前端配置中切换**，默认 text-embedding-v2 |

### 🟡 中优先级（影响功能细节）

| # | 事项 | 状态 | 决策 |
|---|------|------|------|
| 4 | **行业是否预设默认值** | 🔲 待确认 | A. 预设模板 + 可自定义 / B. 完全自定义 |
| 5 | **对话历史存储方式** | ✅ 已确认 | 后端 SQLite 存储，关联会话 ID |
| 6 | **文件上传支持的格式范围** | 🔲 待确认 | PDF + DOCX + TXT + MD？是否加更多？ |
| 7 | **多轮对话中行业切换** | ✅ 已确认 | **锁定行业**，一次对话一个行业，切换需新建对话 |
| 8 | **检索结果为空时策略** | ✅ 已确认 | **直接告知无法回答**，不进行 LLM 自由发挥 |

### 🟢 低优先级（体验优化层面）

| # | 事项 | 状态 | 决策 |
|---|------|------|------|
| 9 | **是否支持引用高亮** | 🔲 待确认 | 点击引用 → 展开原文片段 |
| 10 | **是否支持重新生成** | 🔲 待确认 | 对话中提供"重新生成"按钮 |
| 11 | **是否支持导出对话** | 🔲 待确认 | 导出为 PDF / Markdown |
| 12 | **部署方式** | 🔲 待确认 | 本地启动 vs Docker 化 |

---

## 附录 A：DashScope API 参考

### Embedding 调用示例

```python
from dashscope import TextEmbedding

def get_embedding(text: str) -> list[float]:
    resp = TextEmbedding.call(
        model="text-embedding-v2",
        input=text
    )
    return resp.output["embeddings"][0]["embedding"]
```

### LLM 调用示例（流式）

```python
from dashscope import Generation
from http import HTTPStatus

def stream_chat(messages: list[dict]):
    resp = Generation.call(
        model="qwen-plus",
        messages=messages,
        result_format="message",
        stream=True,
        incremental_output=True
    )
    for chunk in resp:
        if chunk.status_code == HTTPStatus.OK:
            yield chunk.output.choices[0].message.content
```

---

> **下一步**: 请逐项确认第 8 节中的待确认事项，确认完毕后进入开发阶段。