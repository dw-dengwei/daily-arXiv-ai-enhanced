#!/bin/bash

# 本地测试脚本 / Local testing script
# 主要工作流已迁移到 GitHub Actions (.github/workflows/run.yml)
# Main workflow has been migrated to GitHub Actions (.github/workflows/run.yml)

# 环境变量检查和提示 / Environment variables check and prompt
echo "=== 本地调试环境检查 / Local Debug Environment Check ==="

# 检查必需的环境变量 / Check required environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  提示：未设置 OPENAI_API_KEY / Warning: OPENAI_API_KEY not set"
    echo "📝 要进行完整本地调试，请设置以下环境变量 / For complete local debugging, please set the following environment variables:"
    echo ""
    echo "🔑 必需变量 / Required variables:"
    echo "   export OPENAI_API_KEY=\"your-api-key-here\""
    echo ""
    echo "🔧 可选变量 / Optional variables:"
    echo "   export OPENAI_BASE_URL=\"https://api.openai.com/v1\"  # API基础URL / API base URL"
    echo "   export LANGUAGE=\"Chinese\"                           # 语言设置 / Language setting"
    echo "   export CATEGORIES=\"cs.CV, cs.CL\"                    # 关注分类 / Categories of interest"
    echo "   export MODEL_NAME=\"gpt-4o-mini\"                     # 模型名称 / Model name"
    echo ""
    echo "💡 设置后重新运行此脚本即可进行完整测试 / After setting, rerun this script for complete testing"
    echo "🚀 或者继续运行部分流程（爬取+去重检查）/ Or continue with partial workflow (crawl + dedup check)"
    echo ""
    read -p "继续部分流程？(y/N) / Continue with partial workflow? (y/N): " continue_partial
    if [[ ! $continue_partial =~ ^[Yy]$ ]]; then
        echo "退出脚本 / Exiting script"
        exit 0
    fi
    PARTIAL_MODE=true
else
    echo "✅ OPENAI_API_KEY 已设置 / OPENAI_API_KEY is set"
    PARTIAL_MODE=false
    
    # 设置默认值 / Set default values
    export LANGUAGE="${LANGUAGE:-Chinese}"
    export CATEGORIES="${CATEGORIES:-cs.CV, cs.CL}"
    export MODEL_NAME="${MODEL_NAME:-gpt-4o-mini}"
    export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"
    
    echo "🔧 当前配置 / Current configuration:"
    echo "   LANGUAGE: $LANGUAGE"
    echo "   CATEGORIES: $CATEGORIES"
    echo "   MODEL_NAME: $MODEL_NAME"
    echo "   OPENAI_BASE_URL: $OPENAI_BASE_URL"
fi

echo ""
echo "=== 开始本地调试流程 / Starting Local Debug Workflow ==="

# 获取当前日期 / Get current date
today=`date -u "+%Y-%m-%d"`

echo "本地测试：爬取 $today 的arXiv论文... / Local test: Crawling $today arXiv papers..."

# 第一步：爬取数据 / Step 1: Crawl data
echo "步骤1：开始爬取... / Step 1: Starting crawl..."

# 检查今日文件是否已存在，如存在则删除 / Check if today's file exists, delete if found
if [ -f "data/${today}.jsonl" ]; then
    echo "🗑️ 发现今日文件已存在，正在删除重新生成... / Found existing today's file, deleting for fresh start..."
    rm "data/${today}.jsonl"
    echo "✅ 已删除现有文件：data/${today}.jsonl / Deleted existing file: data/${today}.jsonl"
else
    echo "📝 今日文件不存在，准备新建... / Today's file doesn't exist, ready to create new one..."
fi

cd daily_arxiv
scrapy crawl arxiv -o ../data/${today}.jsonl

if [ ! -f "../data/${today}.jsonl" ]; then
    echo "爬取失败，未生成数据文件 / Crawling failed, no data file generated"
    exit 1
fi

# 第二步：检查去重 / Step 2: Check duplicates  
echo "步骤2：执行去重检查... / Step 2: Performing intelligent deduplication check..."
python daily_arxiv/check_stats.py
dedup_exit_code=$?

case $dedup_exit_code in
    0)
        # check_stats.py已输出成功信息，继续处理 / check_stats.py already output success info, continue processing
        ;;
    1)
        # check_stats.py已输出无新内容信息，停止处理 / check_stats.py already output no new content info, stop processing
        exit 1
        ;;
    2)
        # check_stats.py已输出错误信息，停止处理 / check_stats.py already output error info, stop processing
        exit 2
        ;;
    *)
        echo "❌ 未知退出码，停止处理... / Unknown exit code, stopping..."
        exit 1
        ;;
esac

cd ..

# 第三步：AI处理 / Step 3: AI processing
if [ "$PARTIAL_MODE" = "false" ]; then
    echo "步骤3：AI增强处理... / Step 3: AI enhancement processing..."
    cd ai
    python enhance.py --data ../data/${today}.jsonl
    
    if [ $? -ne 0 ]; then
        echo "❌ AI处理失败 / AI processing failed"
        exit 1
    fi
    echo "✅ AI增强处理完成 / AI enhancement processing completed"
    cd ..
else
    echo "⏭️  跳过AI处理（部分模式）/ Skipping AI processing (partial mode)"
fi

# 第四步：转换为Markdown / Step 4: Convert to Markdown
echo "步骤4：转换为Markdown... / Step 4: Converting to Markdown..."
cd to_md

if [ "$PARTIAL_MODE" = "false" ] && [ -f "../data/${today}_AI_enhanced_${LANGUAGE}.jsonl" ]; then
    echo "📄 使用AI增强后的数据进行转换... / Using AI enhanced data for conversion..."
    python convert.py --data ../data/${today}_AI_enhanced_${LANGUAGE}.jsonl
    
    if [ $? -ne 0 ]; then
        echo "❌ Markdown转换失败 / Markdown conversion failed"
        exit 1
    fi
    echo "✅ AI增强版Markdown转换完成 / AI enhanced Markdown conversion completed"
    
else
    if [ "$PARTIAL_MODE" = "true" ]; then
        echo "⏭️  跳过Markdown转换（部分模式，需要AI增强数据）/ Skipping Markdown conversion (partial mode, requires AI enhanced data)"
    else
        echo "❌ 错误：未找到AI增强文件 / Error: AI enhanced file not found"
        echo "AI文件: ../data/${today}_AI_enhanced_${LANGUAGE}.jsonl"
        exit 1
    fi
fi

cd ..

# 第五步：更新文件列表 / Step 5: Update file list
echo "步骤5：更新文件列表... / Step 5: Updating file list..."
ls data/*.jsonl | sed 's|data/||' > assets/file-list.txt
echo "✅ 文件列表更新完成 / File list updated"

# 完成总结 / Completion summary
echo ""
echo "=== 本地调试完成 / Local Debug Completed ==="
if [ "$PARTIAL_MODE" = "false" ]; then
    echo "🎉 完整流程已完成 / Complete workflow finished:"
    echo "   ✅ 数据爬取 / Data crawling"
    echo "   ✅ 去重检查 / Smart duplicate check"
    echo "   ✅ AI增强处理 / AI enhancement"
    echo "   ✅ Markdown转换 / Markdown conversion"
    echo "   ✅ 文件列表更新 / File list update"
else
    echo "🔄 部分流程已完成 / Partial workflow finished:"
    echo "   ✅ 数据爬取 / Data crawling"
    echo "   ✅ 去重检查 / Smart duplicate check"
    echo "   ⏭️  跳过AI增强和Markdown转换 / Skipped AI enhancement and Markdown conversion"
    echo "   ✅ 文件列表更新 / File list update"
    echo ""
    echo "💡 提示：设置OPENAI_API_KEY可启用完整功能 / Tip: Set OPENAI_API_KEY to enable full functionality"
fi
