# RAG 学习系统

一个**教学向、可本地运行、前后端齐全**的检索增强生成（RAG，Retrieval-Augmented Generation）完整示例。

你可以在浏览器里走完 RAG 的全部流程：**上传文档 → 切块 → 向量化 → 建索引 → 检索 → 增强提示词 → 生成答案**，每一步都能看到中间结果（切块内容、相似度分数、完整 Prompt、各步骤耗时、引用来源）。

**不需要任何 API Key 就能跑通全链路**：默认用本地 embedding 模型做检索，用“句子级抽取拼接”生成可解释的答案；配置了 OpenAI 兼容 API 后自动切换为真正的 LLM 生成。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.11+ / FastAPI / Uvicorn / Pydantic |
| 向量库 | ChromaDB（持久化到本地目录） |
| 向量化 | sentence-transformers（默认 `all-MiniLM-L6-v2`，CPU 可跑） |
| 文档解析 | txt / markdown / pdf（pypdf） |
| 可选 LLM | OpenAI 兼容接口（openai SDK，支持自定义 base_url） |
| 前端 | React 18 / TypeScript / Vite / Tailwind CSS |
| 测试 | pytest（切块边界、API 冒烟、检索命中） |

## 快速开始

### 方式一：本地运行（推荐用于学习）

**1. 启动后端**（首次运行会自动下载约 90MB 的 embedding 模型）：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 可选：先装 CPU 版 torch，体积更小、安装更快
pip install torch --index-url https://download.pytorch.org/whl/cpu

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

启动时知识库为空会**自动导入 `samples/` 下的 4 篇中文示例文档**，打开就能提问。

**2. 启动前端**（另开一个终端）：

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 <http://localhost:5173>，Vite 会把 `/api` 请求代理到后端 8000 端口。

### 方式二：Docker 一键启动

```bash
docker compose up --build
```

前端 <http://localhost:5173>，后端 API <http://localhost:8000/docs>（Swagger 文档）。

### 可选：接入真正的 LLM

复制 `backend/.env.example` 为 `backend/.env`，填入任意 OpenAI 兼容服务：

```bash
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.openai.com/v1   # 或其他兼容服务地址
OPENAI_MODEL=gpt-4o-mini
```

重启后端即可。不配置时系统自动降级为“检索片段拼接”回答，链路完全可用。

## RAG 七步详解 × 代码对照

这是本项目的学习主线。每一步都对应一个可以直接阅读的源码文件：

| 步骤 | 做什么 | 代码位置 |
| --- | --- | --- |
| **1. Ingest 文档入库** | 把 txt / markdown / pdf 解析成纯文本（UTF-8/GBK 自适应，pypdf 抽取 PDF 文本） | `backend/app/rag/loading.py` |
| **2. Chunk 切块** | 句子感知的滑动窗口切块：按标点拆句 → 贪心装箱到 `chunk_size` → 相邻块保留 `chunk_overlap` 字符重叠，防止关键句被拦腰截断 | `backend/app/rag/chunking.py` |
| **3. Embed 向量化** | 用 sentence-transformers 把每个块编码成 384 维归一化向量；语义相近的文本向量距离更近 | `backend/app/rag/embedding.py` |
| **4. Index 建索引** | 向量 + 原文 + 元数据（来源文件、块序号）写入 ChromaDB，持久化到 `backend/data/chroma/`，用 HNSW 图做近似最近邻 | `backend/app/rag/vectorstore.py` |
| **5. Retrieve 检索** | 问题用**同一个模型**向量化，按余弦相似度找出 top_k 个最相关块（分数 = 1 − 余弦距离） | `backend/app/rag/vectorstore.py` |
| **6. Augment 增强提示词** | 把检索到的块按编号拼进 Prompt 模板，要求模型“只根据资料回答、句末标注 [编号]”——这是 RAG 抑制幻觉的关键 | `backend/app/rag/generation.py` |
| **7. Generate 生成答案** | 有 API Key 时调用 LLM；否则把检索块再拆成句子、按与问题的相似度挑出最相关的几句拼接成答案（零幻觉、可解释的降级方案） | `backend/app/rag/generation.py` |

把七步串起来的编排层在 `backend/app/rag/pipeline.py`（`RAGService`），REST 接口在 `backend/app/api/routes.py`。

**在界面上观察这些步骤**：

- 「知识库」页：上传文档后显示 Ingest→Chunk→Embed→Index 各步耗时；「查看切块」能看到每个块的内容和重叠效果；
- 「问答」页：提问后显示 Embed→Retrieve→Augment→Generate 耗时、答案生成方式（LLM / 抽取拼接）、引用来源及相似度分数，还能展开查看**增强后的完整 Prompt**；
- 「设置与原理」页：当前运行配置（chunk 参数、top_k、模型、LLM 状态）+ 七步代码对照表。

## API 一览

启动后端后可在 <http://localhost:8000/docs> 交互式调试。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/documents` | 上传文档（multipart，字段名 `file`），完成入库四步 |
| GET | `/api/documents` | 文档列表 |
| DELETE | `/api/documents/{id}` | 删除文档及其向量块 |
| GET | `/api/documents/{id}/chunks` | 查看切块结果 |
| POST | `/api/query` | 问答：`{"question": "...", "top_k": 4}`，返回答案、引用、分数、生成方式、Prompt、耗时 |
| GET | `/api/health` | 健康检查（文档数 / 块数 / 模型状态） |
| GET | `/api/settings` | 当前运行配置（不返回密钥） |

curl 示例：

```bash
# 提问
curl -s -X POST http://localhost:8000/api/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "什么是 RAG？"}' | python3 -m json.tool

# 上传文档
curl -s -X POST http://localhost:8000/api/documents -F 'file=@samples/01-什么是RAG.md'
```

## 项目结构

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口（CORS、启动时自动 seed、托管前端构建产物）
│   │   ├── config.py            # 运行配置（环境变量 / .env）
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── api/routes.py        # REST 接口
│   │   └── rag/                 # RAG 核心（按七步拆分，见上表）
│   ├── scripts/seed.py          # 手动导入示例文档（--force 强制重导）
│   ├── tests/                   # pytest：切块边界 / API 冒烟 / 检索命中
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── pages/               # 问答 / 知识库 / 设置与原理
│       ├── components/          # 流水线可视化、相似度分数条
│       └── api.ts               # 类型化 API 客户端
├── samples/                     # 4 篇中文教学文档（RAG/向量检索/切块/提示词）
├── docker-compose.yml
└── README.md
```

## 运行测试

```bash
cd backend
source .venv/bin/activate
pytest            # 切块边界、API 冒烟、检索命中（首次会加载 embedding 模型）

cd ../frontend
npm run build     # TypeScript 类型检查 + 生产构建
```

## 常见问题

**首次启动很慢？** 第一次运行会从 HuggingFace 下载 embedding 模型（约 90MB）并缓存到 `~/.cache`，之后启动只需数秒。

**回答看起来是“要点罗列”而不是流畅的话？** 说明当前没有配置 LLM，系统在用抽取式回答（这本身就是教学点：RAG 的前六步完全不依赖 LLM）。配置 `OPENAI_API_KEY` 后即为流畅的 LLM 生成。

**想换 embedding 模型？** 在 `backend/.env` 里设置 `EMBEDDING_MODEL`（如 `BAAI/bge-small-zh-v1.5` 对中文效果更好）。换模型后建议删除 `backend/data/` 重建索引——**问题与文档必须用同一个模型向量化**。

**数据存在哪里？** 向量库在 `backend/data/chroma/`，文档元信息在 `backend/data/documents.json`，均已被 `.gitignore` 忽略。删除 `backend/data/` 即可重置知识库。

## 已知限制（有意为之的教学取舍）

- 无 LLM Key 时的抽取式回答只做句子级重排拼接，不做改写归纳；
- 检索为纯向量检索，未实现关键词混合检索（BM25）与重排序（rerank）；
- chunk 参数改动只对**新上传**的文档生效，旧文档需删除后重新上传；
- 文档注册表用 JSON 文件存储，适合单机教学场景，不适合并发生产环境。

这些都是很好的练习方向：试着自己实现混合检索或接入 rerank 模型吧。
