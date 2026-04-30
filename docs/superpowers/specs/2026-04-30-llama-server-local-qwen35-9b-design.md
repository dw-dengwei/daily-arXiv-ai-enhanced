# 本地 llama-server（Qwen3.5-9B GGUF）离线增强与本地静态站设计

日期：2026-04-30  
范围：将 `daily-arXiv-ai-enhanced` 改造成“全流程本地运行 + 本地静态页面”，使用本地 `llama-server`（llama.cpp）提供 OpenAI 兼容接口完成 AI 摘要增强，前端不再拉取 `raw.githubusercontent.com` 数据源。

## 1. 目标与非目标

### 目标

- 全流程本地运行：抓取 → 去重 → AI 增强 → 生成文件列表 → 本地静态页面浏览。
- AI 增强使用本地 `llama-server`：通过 `/v1/chat/completions` 调用，模型为 `Qwen3.5-9B-Q4_K_M.gguf`（可配置）。
- 完全离线：移除外部敏感词检测网络请求与过滤逻辑。
- 前端本地化：前端在 `localhost/127.0.0.1` 下仅从本地相对路径加载 `assets/file-list.txt` 与 `data/*.jsonl`。
- 兼容性：保留原有远端数据分支模式的兼容能力（在非本地 host 时仍可走现有 GitHub raw 模式）。

### 非目标

- 不追求严格复刻 OpenAI function/tool calling 结构化输出；改用“强制 JSON 输出 + 本地解析容错”。
- 不在本次改造中实现并发推理优化（默认串行处理，保证稳定性）。
- 不改变前端 UI/交互，仅调整数据源定位逻辑。

## 2. 当前系统简述（基线）

- 抓取：Scrapy 爬取 `arxiv.org/list/<cat>/new` 得到 id，再用 `arxiv` SDK 补全论文元数据。
- 去重：与历史多日 jsonl 比对，删除重复条目；无新内容则终止。
- AI 增强：当前使用 LangChain + OpenAI compatible API，并依赖 function calling 结构化输出。
- 前端：静态页面通过 `DATA_CONFIG.getDataUrl(...)` 拉取 `assets/file-list.txt` 与 `data/*.jsonl`。

## 3. 目标架构（本地）

### 3.1 数据流

1. `scrapy crawl arxiv -o data/YYYY-MM-DD.jsonl`
2. `python daily_arxiv/check_stats.py`（对比过去 7 天，删除重复）
3. `python ai/enhance.py --data data/YYYY-MM-DD.jsonl`
4. `python to_md/convert.py --data data/YYYY-MM-DD_AI_enhanced_<LANG>.jsonl`
5. 生成 `assets/file-list.txt`（列出 `data/*.jsonl`）
6. 静态服务器启动后浏览：`index.html` / `statistic.html`

### 3.2 AI 调用方式（llama-server）

- 服务地址：`LLAMA_BASE_URL`，默认 `http://127.0.0.1:8080/v1`
- 可用模型：从 `GET /v1/models` 获取（用户已确认可用，model id 为 `Qwen3.5-9B-Q4_K_M.gguf`）
- 推理接口：`POST /v1/chat/completions`
- 结构化输出策略：提示词强制模型输出严格 JSON（仅一个对象，必须包含 5 个字段）

## 4. AI 增强实现细节

### 4.1 配置项（环境变量）

- `LLM_BACKEND`：固定使用 `llama_server`
- `LLAMA_BASE_URL`：如 `http://127.0.0.1:8080/v1`
- `LLAMA_MODEL`：如 `Qwen3.5-9B-Q4_K_M.gguf`
- `LANGUAGE`：`Chinese` 或 `English`
- `MAX_TOKENS`：客户端 max_tokens（建议默认 800~1200）
- `TEMPERATURE`：默认 0.2

### 4.2 Prompt 约束（关键）

输入：论文 `summary`（abstract）。  
输出：严格 JSON：

```json
{
  "tldr": "...",
  "motivation": "...",
  "method": "...",
  "result": "...",
  "conclusion": "..."
}
```

约束：

- 只允许输出一个 JSON 对象，不允许任何额外文本、Markdown、代码块标记。
- 五个字段必须全部出现，字段值为字符串。
- 仅基于提供的 abstract，不引入不存在的信息。
- 可限制每个字段长度（例如 2~5 句）。

### 4.3 解析与容错

解析优先级：

1. 直接 `json.loads(response_text)`
2. 若失败：截取第一个 `{` 到最后一个 `}` 的子串再解析
3. 若仍失败：进行轻量修复（去除尾随逗号、替换不合法控制字符）
4. 若仍失败：写入默认占位值（保证前端渲染不崩）

缺字段处理：

- 任何缺失字段使用默认占位补齐，确保 `AI` 字段总是包含五个 key。

### 4.4 敏感词检测移除

- 删除外部网络检测逻辑（`https://spam.dw-dengwei.workers.dev`）。
- 不再因敏感检测而过滤论文条目，保证纯离线。

## 5. 前端本地化实现细节

### 5.1 设计目标

- 本地访问 `http://127.0.0.1:<port>/` 时，数据源定位为本地：
  - `assets/file-list.txt`
  - `data/*.jsonl`

### 5.2 实现方案

修改 `js/data-config.js`：

- 自动识别本地 host：
  - `localhost`
  - `127.0.0.1`
- 本地模式：
  - `getDataBaseUrl()` 返回 `window.location.origin`
  - `getDataUrl(filePath)` 返回 `${origin}/${filePath}`
- 非本地模式：保持现有 GitHub raw 逻辑，继续支持 data 分支远端拉取。

## 6. 本地一键流水线

新增脚本 `scripts/local_pipeline.py`（无交互）：

- 输入：可选日期（默认 UTC 当天），分类、语言等从环境变量读取
- 顺序执行：抓取、去重、AI 增强、转 md、生成 file-list
- 失败策略：任何一步失败立即退出，并打印可定位的错误信息

本地服务启动方式：

- 推荐：`python -m http.server 8000`
- 然后访问：`http://127.0.0.1:8000/`

## 7. 验收标准

- 在本地启动 `llama-server` 后，执行本地流水线能生成：
  - `data/YYYY-MM-DD.jsonl`
  - `data/YYYY-MM-DD_AI_enhanced_Chinese.jsonl`（或 English）
  - `assets/file-list.txt`
- 本地起静态服务器后：
  - 首页可加载日期列表并渲染论文
  - 论文详情可展示 5 段 AI 字段
- 运行过程中无任何外部网络依赖（除 arXiv 抓取与 llama-server 本地请求外）。

