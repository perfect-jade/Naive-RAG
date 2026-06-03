# RAG 智能问答系统

基于 Retrieval-Augmented Generation (RAG) 技术的智能问答系统，支持行业级知识管理和智能对话功能。

## 项目结构

```
RAG/
├── backend/                    # 后端代码
│   ├── api/                   # REST API 接口
│   │   ├── industry.py        # 行业管理接口
│   │   ├── knowledge.py       # 知识管理接口
│   │   ├── chat.py            # 对话接口
│   │   └── settings.py        # 设置接口
│   ├── services/              # 业务逻辑层
│   │   ├── industry_service.py # 行业业务逻辑
│   │   ├── knowledge_service.py # 知识业务逻辑
│   │   ├── chat_service.py    # 对话业务逻辑
│   │   └── file_parser.py     # 文件解析服务
│   ├── core/                  # 核心引擎
│   │   ├── faiss_engine.py    # FAISS 向量检索引擎
│   │   ├── bm25_engine.py     # BM25 关键词检索引擎
│   │   ├── embedding.py       # Embedding 向量化服务
│   │   ├── retriever.py       # 检索器
│   │   └── llm_client.py      # LLM 客户端
│   ├── models/                # 数据模型
│   │   └── schemas.py         # API 数据结构定义
│   ├── config.py              # 配置管理
│   └── main.py                # 应用入口
├── frontend/                  # 前端代码
│   ├── src/
│   │   ├── views/             # 页面视图
│   │   │   ├── IndustryList.vue    # 行业管理页面
│   │   │   ├── KnowledgeManage.vue # 知识管理页面
│   │   │   ├── ChatView.vue        # 智能对话页面
│   │   │   └── SettingsView.vue    # 设置页面
│   │   ├── api/               # API 调用层
│   │   │   ├── industry.ts    # 行业 API
│   │   │   ├── knowledge.ts   # 知识 API
│   │   │   ├── chat.ts        # 对话 API
│   │   │   └── settings.ts    # 设置 API
│   │   ├── stores/            # 状态管理
│   │   ├── router/            # 路由配置
│   │   └── main.ts            # 应用入口
│   └── index.html
└── data/                      # 数据存储目录（自动生成）
    └── industries/            # 行业数据目录
```

## 后端功能说明

### 1. 配置管理 (`backend/config.py`)

| 函数/变量 | 功能说明 |
|----------|---------|
| `BASE_DIR` | 项目根目录路径 |
| `DATA_DIR` | 数据存储目录 |
| `INDUSTRIES_DIR` | 行业数据目录 |
| `CHUNK_SIZE` | 默认切片大小（500字符） |
| `CHUNK_OVERLAP` | 默认切片重叠大小（50字符） |
| `get_config(key)` | 获取配置值 |
| `set_config(key, value)` | 设置配置值 |
| `get_llm_model()` | 获取当前 LLM 模型 |
| `get_embedding_model()` | 获取当前 Embedding 模型 |
| `get_api_key()` | 获取 API Key |

### 2. 行业服务 (`backend/services/industry_service.py`)

| 函数 | 功能说明 |
|-----|---------|
| `create_industry(name, description)` | 创建新行业，初始化目录结构和数据库 |
| `list_industries()` | 获取所有行业列表 |
| `get_industry(slug)` | 获取指定行业详情 |
| `update_industry(slug, ...)` | 更新行业信息（支持分片配置） |
| `delete_industry(slug)` | 删除行业及所有相关数据 |
| `get_chunk_config(slug)` | 获取行业的分片配置 |
| `add_document(slug, doc_id, ...)` | 添加文档记录到数据库 |
| `list_documents(slug, page, page_size)` | 分页获取文档列表 |
| `get_document(slug, doc_id)` | 获取文档详情 |
| `get_document_chunks(slug, doc_id)` | 获取文档的所有切片 |
| `delete_document(slug, doc_id)` | 删除文档及其所有切片 |

### 3. 知识服务 (`backend/services/knowledge_service.py`)

| 函数 | 功能说明 |
|-----|---------|
| `split_text(text, chunk_size, chunk_overlap)` | 文本分块处理，支持多种分隔符 |
| `insert_text_knowledge(slug, content, ...)` | 录入文本知识，自动分块并入库 |
| `remove_knowledge(slug, doc_id)` | 删除知识文档及相关索引 |
| `remove_chunk(slug, doc_id, chunk_id)` | 删除单个切片 |

### 4. 行业 API (`backend/api/industry.py`)

| 接口 | 方法 | 功能说明 |
|-----|-----|---------|
| `/api/v1/industries` | POST | 创建行业 |
| `/api/v1/industries` | GET | 获取行业列表 |
| `/api/v1/industries/{slug}` | GET | 获取行业详情 |
| `/api/v1/industries/{slug}` | PUT | 更新行业信息 |
| `/api/v1/industries/{slug}/chunk-config` | GET | 获取分片配置 |
| `/api/v1/industries/{slug}` | DELETE | 删除行业 |

### 5. 知识 API (`backend/api/knowledge.py`)

| 接口 | 方法 | 功能说明 |
|-----|-----|---------|
| `/api/v1/industries/{slug}/knowledge/text` | POST | 文本录入 |
| `/api/v1/industries/{slug}/knowledge/upload` | POST | 上传文件 |
| `/api/v1/industries/{slug}/knowledge` | GET | 获取知识列表 |
| `/api/v1/industries/{slug}/knowledge/{doc_id}` | DELETE | 删除知识文档 |
| `/api/v1/industries/{slug}/knowledge/{doc_id}/chunks` | GET | 获取文档切片 |
| `/api/v1/industries/{slug}/knowledge/{doc_id}/chunks/{chunk_id}` | DELETE | 删除单个切片 |

## 前端功能说明

### 1. 行业管理页面 (`frontend/src/views/IndustryList.vue`)

| 功能 | 说明 |
|-----|-----|
| 行业列表展示 | 展示所有行业，包含文档数、切片数和分片配置 |
| 创建行业 | 创建新行业，设置名称和描述 |
| 编辑行业 | 修改行业信息和分片配置（切片大小、重叠大小） |
| 删除行业 | 删除整个行业及所有数据 |
| 进入知识管理 | 点击行业卡片进入知识管理页面 |

### 2. 知识管理页面 (`frontend/src/views/KnowledgeManage.vue`)

| 功能 | 说明 |
|-----|-----|
| 文档列表 | 展示当前行业的所有文档 |
| 上传文件 | 支持上传 PDF、TXT 等文件，显示上传进度 |
| 文本录入 | 直接录入文本知识 |
| 查看切片 | 查看文档的所有切片内容 |
| 切片详情 | 查看单个切片的完整内容 |
| 删除切片 | 删除单个切片 |
| 删除文档 | 删除整个文档 |

### 3. 智能对话页面 (`frontend/src/views/ChatView.vue`)

| 功能 | 说明 |
|-----|-----|
| 对话列表 | 展示历史对话记录 |
| 新建对话 | 创建新的对话会话 |
| 删除对话 | 删除指定对话会话 |
| 智能问答 | 基于行业知识进行问答 |
| 上下文保持 | 支持多轮对话上下文 |

### 4. API 调用层

#### 行业 API (`frontend/src/api/industry.ts`)

| 方法 | 功能说明 |
|-----|---------|
| `list()` | 获取行业列表 |
| `detail(slug)` | 获取行业详情 |
| `create(data)` | 创建行业 |
| `update(slug, data)` | 更新行业信息 |
| `delete(slug)` | 删除行业 |
| `getChunkConfig(slug)` | 获取分片配置 |

#### 知识 API (`frontend/src/api/knowledge.ts`)

| 方法 | 功能说明 |
|-----|---------|
| `list(slug, page, pageSize)` | 获取文档列表 |
| `insertText(slug, data)` | 录入文本知识 |
| `uploadFiles(slug, files)` | 上传文件 |
| `delete(slug, docId)` | 删除文档 |
| `getDocumentChunks(slug, docId)` | 获取文档切片 |
| `deleteChunk(slug, docId, chunkId)` | 删除切片 |

## 核心技术栈

### 后端
- **框架**: FastAPI
- **向量检索**: FAISS
- **关键词检索**: BM25
- **文本分块**: LangChain TextSplitter
- **数据库**: SQLite
- **LLM 服务**: 阿里云 DashScope

### 前端
- **框架**: Vue 3 + TypeScript
- **UI 组件**: Element Plus
- **构建工具**: Vite
- **状态管理**: Pinia
- **路由**: Vue Router

## 运行方式

### 后端启动
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端启动
```bash
cd frontend
npm install
npm run dev
```

## 配置说明

### 环境变量
- `DASHSCOPE_API_KEY`: 阿里云 DashScope API Key

### 分片配置
每个行业可独立配置：
- **chunk_size**: 切片大小（50-2000字符），默认 500
- **chunk_overlap**: 切片重叠大小（0-500字符），默认 50

## 数据目录结构

```
data/
└── industries/
    └── {industry_slug}/
        ├── meta.json          # 行业元数据
        ├── metadata.db        # 文档和切片数据库
        ├── faiss_index/       # FAISS 向量索引
        ├── bm25_index/        # BM25 索引
        └── raw_docs/          # 原始文档存储
```
