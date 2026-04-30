# daily-arXiv (Local Offline Edition)

本项目提供一个本地可运行的完整流水线：每日抓取 arXiv 最新论文 → 去重 → 使用本地 `llama-server`（llama.cpp）生成结构化摘要 → 生成本地数据索引 → 用纯静态网页本地浏览。

## 特性

- 本地全流程：crawl → dedup → AI enhance → index → serve
- AI 完全走本地 `llama-server` 的 OpenAI 兼容接口（`/v1/chat/completions`）
- 结构化输出：强制模型返回严格 JSON（tldr/motivation/method/result/conclusion）
- 前端只读本地文件：`assets/file-list.txt` + `data/*.jsonl`

## 目录结构（核心）

- 抓取/去重：[/daily_arxiv](file:///workspace/daily_arxiv)
- AI 增强：[/ai](file:///workspace/ai)
- 本地 CLI：[/local_arxiv](file:///workspace/local_arxiv)
- 静态站：[/index.html](file:///workspace/index.html) + [/js](file:///workspace/js)

## 前置条件

- Python 3.12+
- `uv`（推荐，用于安装依赖）
- 已启动的 `llama-server`（llama.cpp），且开启 OpenAI 兼容接口

## 快速开始

1) 安装依赖

```bash
uv sync
```

2) 启动 llama-server（示例，按你的 llama.cpp 安装方式调整）

确保你能访问：

- `GET http://127.0.0.1:8080/v1/models`
- `POST http://127.0.0.1:8080/v1/chat/completions`

3) 配置环境变量

```bash
export LLAMA_BASE_URL="http://127.0.0.1:8080/v1"
export LLAMA_MODEL="Qwen3.5-9B-Q4_K_M.gguf"
export LANGUAGE="Chinese"
export CATEGORIES="cs.CV,cs.CL"
export MAX_TOKENS="1000"
export TEMPERATURE="0.2"
```

4) 运行流水线（产出数据）

```bash
python -m local_arxiv run
```

运行完成后会生成：

- `data/YYYY-MM-DD.jsonl`
- `data/YYYY-MM-DD_AI_enhanced_<LANG>.jsonl`
- `assets/file-list.txt`

5) 启动本地静态站（浏览）

```bash
python -m local_arxiv serve
```

默认监听 `127.0.0.1:8000`，打开浏览器访问 `http://127.0.0.1:8000/`。

## 常用参数

```bash
python -m local_arxiv run --help
python -m local_arxiv serve --help
```

常见用法：

```bash
python -m local_arxiv run --date 2026-04-30
python -m local_arxiv run --max-workers 1 --convert-md
python -m local_arxiv serve --host 127.0.0.1 --port 8000
```

## 运行测试

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## 设计说明

- 设计文档：[2026-04-30-llama-server-local-qwen35-9b-design.md](file:///workspace/docs/superpowers/specs/2026-04-30-llama-server-local-qwen35-9b-design.md)
- 实施计划（as-built）：[2026-04-30-llama-server-local-qwen35-9b.md](file:///workspace/docs/superpowers/plans/2026-04-30-llama-server-local-qwen35-9b.md)

## License

Apache-2.0
