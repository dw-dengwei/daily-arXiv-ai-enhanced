#!/bin/bash

# 本地测试脚本 / Local testing script
# 主要工作流已迁移到 GitHub Actions (.github/workflows/run.yml)
# Main workflow has been migrated to GitHub Actions (.github/workflows/run.yml)

# 获取当前日期 / Get current date
today=`date -u "+%Y-%m-%d"`

echo "本地测试：爬取 $today 的arXiv论文... / Local test: Crawling $today arXiv papers..."

# 第一步：爬取数据 / Step 1: Crawl data
echo "步骤1：开始爬取... / Step 1: Starting crawl..."
cd daily_arxiv
scrapy crawl arxiv -o ../data/${today}.jsonl

if [ ! -f "../data/${today}.jsonl" ]; then
    echo "爬取失败，未生成数据文件 / Crawling failed, no data file generated"
    exit 1
fi

# 第二步：检查去重 / Step 2: Check duplicates  
echo "步骤2：检查去重... / Step 2: Checking duplicates..."
python daily_arxiv/check_stats.py
dedup_exit_code=$?

case $dedup_exit_code in
    0)
        echo "发现新内容，继续处理... / New content found, continuing..."
        ;;
    1)
        echo "今日无新论文 / No new papers today"
        exit 1
        ;;
    2)
        echo "内容重复 / Content duplicated"
        exit 2
        ;;
    *)
        echo "去重检查状态未知，继续处理... / Unknown dedup status, continuing..."
        ;;
esac

cd ..

# 第三步：AI处理 / Step 3: AI processing
if [ -n "$OPENAI_API_KEY" ]; then
    echo "步骤3：AI增强处理... / Step 3: AI enhancement processing..."
    cd ai
    python enhance.py --data ../data/${today}.jsonl
    
    if [ $? -ne 0 ]; then
        echo "AI处理失败 / AI processing failed"
        exit 1
    fi
    cd ..
else
    echo "跳过AI处理（未设置OPENAI_API_KEY）/ Skipping AI processing (OPENAI_API_KEY not set)"
fi

# 第四步：转换为Markdown / Step 4: Convert to Markdown
echo "步骤4：转换为Markdown... / Step 4: Converting to Markdown..."
cd to_md
if [ -f "../data/${today}_AI_enhanced_${LANGUAGE:-Chinese}.jsonl" ]; then
    python convert.py --data ../data/${today}_AI_enhanced_${LANGUAGE:-Chinese}.jsonl
else
    python convert.py --data ../data/${today}.jsonl
fi

if [ $? -ne 0 ]; then
    echo "Markdown转换失败 / Markdown conversion failed"
    exit 1
fi

cd ..

# 第五步：更新文件列表 / Step 5: Update file list
echo "步骤5：更新文件列表... / Step 5: Updating file list..."
ls data/*.jsonl | sed 's|data/||' > assets/file-list.txt

echo "本地测试完成 / Local test completed"
