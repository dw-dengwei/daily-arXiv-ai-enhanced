#!/bin/bash

# 获取当前日期 / Get current date
today=`date -u "+%Y-%m-%d"`

echo "开始爬取 $today 的arXiv论文（集成去重检查）... / Starting to crawl $today arXiv papers (with integrated dedup check)..."
cd daily_arxiv

# 使用Scrapy爬取，内置去重检查管道会自动执行
# Use Scrapy to crawl, built-in dedup check pipeline will execute automatically
scrapy crawl arxiv -o ../data/${today}.jsonl

# 检查爬取是否成功 / Check if crawling was successful
if [ ! -f "../data/${today}.jsonl" ]; then
    echo "爬取失败，未生成数据文件 / Crawling failed, no data file generated"
    exit 1
fi

echo "检查Scrapy内置去重结果... / Checking Scrapy built-in dedup results..."
# 执行去重状态检查脚本 / Execute dedup status check script
python daily_arxiv/check_stats.py

# 检查去重结果的退出码 / Check exit code of dedup results
dedup_exit_code=$?
case $dedup_exit_code in
    0)
        echo "发现新内容，继续处理... / New content found, continuing processing..."
        ;;
    2)
        echo "今日无新论文，工作流结束 / No new papers today, workflow ends"
        exit 2  # 返回非0退出码，告知GitHub Actions跳过提交 / Return non-zero exit code to tell GitHub Actions to skip commit
        ;;
    3)
        echo "内容重复，工作流提前结束 / Content duplicated, workflow ends early"
        # 重复文件已在check_stats.py中删除 / Duplicate file already deleted in check_stats.py
        exit 3  # 返回非0退出码，告知GitHub Actions跳过提交 / Return non-zero exit code to tell GitHub Actions to skip commit
        ;;
    *)
        echo "去重检查状态未知，继续处理... / Dedup check status unknown, continuing processing..."
        ;;
esac

cd ..

echo "开始AI增强处理... / Starting AI enhancement processing..."
cd ai
python enhance.py --data ../data/${today}.jsonl

# 检查AI处理是否成功 / Check if AI processing was successful
if [ $? -ne 0 ]; then
    echo "AI处理失败 / AI processing failed"
    exit 1
fi

echo "转换为Markdown格式... / Converting to Markdown format..."
cd ../to_md
python convert.py --data ../data/${today}_AI_enhanced_${LANGUAGE}.jsonl

# 检查转换是否成功 / Check if conversion was successful
if [ $? -ne 0 ]; then
    echo "Markdown转换失败 / Markdown conversion failed"
    exit 1
fi

cd ..
echo "更新文件列表... / Updating file list..."
ls data/*.jsonl | sed 's|data/||' > assets/file-list.txt

echo "工作流完成，发现新内容并成功处理 / Workflow completed, new content found and processed successfully"
exit 0  # 明确返回0，表示有新内容且处理成功 / Explicitly return 0 to indicate new content found and processed successfully
