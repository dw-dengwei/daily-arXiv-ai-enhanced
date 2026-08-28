---
name: daily-arxiv-ai-enhanced
version: 0.1
description: 通过URL请求，从daily-arxiv-ai-enhanced项目中获取论文json数据
---

# arXiv论文数据API

## 触发条件
用户想要获取daily-arXiv-ai-enhanced项目中的数据

## 功能说明
通过URL参数获取JSON格式的arXiv论文数据

## 基础仓库 URL
https://dw-dengwei.github.io/daily-arXiv-ai-enhanced/

## URL参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `category` | arXiv类别 | `cs.CV`, `cs.AI`, etc. |
| `author` | 作者姓名 | `Smith` |
| `keywords` | 关键词，逗号分隔 | `vision,learning` |

## 样例
```
bash scripts/fetch.sh "https://dw-dengwei.github.io/daily-arXiv-ai-enhanced/?category=cs.CV&author=Smith&keywords=deep"
```
这里使用到了`fetch.sh`脚本来发送请求并处理响应数据，该脚本基于NodeJS和puppeteer环境，如果没有安装则会自动安装。你不能直接wget或curl这个url，因为它需要执行JavaScript来生成最终的JSON响应。

## 筛选逻辑

```
category AND (keywords OR author)
```

- category: 硬筛选，只返回指定类别
- keywords: 在标题和摘要中搜索
- author: 在作者字段中搜索
- keywords与author是"或"关系

## JSON响应结构

```json
{
  "category": "cs.CV",
  "author": "Smith",
  "keywords": ["deep"],
  "count": 10,
  "papers": [
    {
      "id": "2401.00001",
      "title": "标题",
      "authors": "作者1, 作者2",
      "categories": ["cs.CV"],
      "summary": "tldr",
      "date": "2024-01-01",
      "url": "https://arxiv.org/abs/2401.00001"
    }
  ]
}
```