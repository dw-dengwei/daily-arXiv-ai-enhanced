import json
import argparse
import os
import sys
from itertools import count

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, help="Path to the jsonline file")
    args = parser.parse_args()
    
    # 检查文件是否存在 / Check if file exists
    if not os.path.exists(args.data):
        print(f"错误：数据文件不存在 / Error: Data file does not exist: {args.data}", file=sys.stderr)
        print("这可能是因为去重检查检测到重复内容，或AI处理失败 / This might be because dedup check detected duplicate content, or AI processing failed", file=sys.stderr)
        sys.exit(1)
    
    data = []
    preference = os.environ.get('CATEGORIES', 'cs.CV, cs.CL').split(',')
    preference = list(map(lambda x: x.strip(), preference))
    def rank(cate):
        if cate in preference:
            return preference.index(cate)
        else:
            return len(preference)

    # 尝试读取文件，添加异常处理 / Try to read file with exception handling
    try:
        with open(args.data, "r") as f:
            for line in f:
                if line.strip():  # 跳过空行 / Skip empty lines
                    data.append(json.loads(line))
    except json.JSONDecodeError as e:
        print(f"错误：JSON解析失败 / Error: JSON parsing failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误：读取文件失败 / Error: Failed to read file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 检查是否有数据 / Check if there is data
    if not data:
        print("警告：文件中没有有效数据 / Warning: No valid data in file", file=sys.stderr)
        sys.exit(1)

    # 检查数据是否包含AI增强字段 / Check if data contains AI enhancement fields
    has_ai_fields = len(data) > 0 and 'AI' in data[0]
    
    categories = set([item["categories"][0] for item in data])
    
    # 根据是否有AI字段选择模板 / Choose template based on whether AI fields exist
    if has_ai_fields:
        template = open("paper_template.md", "r").read()
        print("使用AI增强模板 / Using AI enhanced template", file=sys.stderr)
    else:
        # 检查是否存在简化模板，如果不存在则创建 / Check if simplified template exists, create if not
        simple_template_path = "paper_template_simple.md"
        if not os.path.exists(simple_template_path):
            # 创建简化模板 / Create simplified template
            simple_template_content = """## {idx}. {title}

**Authors**: {authors}

**Categories**: {cate}

**Summary**: {summary}

**Link**: [{url}]({url})

---
"""
            with open(simple_template_path, "w", encoding="utf-8") as f:
                f.write(simple_template_content)
            print("创建了简化模板文件 / Created simplified template file", file=sys.stderr)
        
        template = open(simple_template_path, "r").read()
        print("使用简化模板（无AI字段）/ Using simplified template (no AI fields)", file=sys.stderr)
    
    categories = sorted(categories, key=rank)
    cnt = {cate: 0 for cate in categories}
    for item in data:
        if item["categories"][0] not in cnt.keys():
            continue
        cnt[item["categories"][0]] += 1

    markdown = f"<div id=toc></div>\n\n# Table of Contents\n\n"
    for idx, cate in enumerate(categories):
        markdown += f"- [{cate}](#{cate}) [Total: {cnt[cate]}]\n"

    idx = count(1)
    for cate in categories:
        markdown += f"\n\n<div id='{cate}'></div>\n\n"
        markdown += f"# {cate} [[Back]](#toc)\n\n"
        
        # 获取当前分类的数据 / Get data for current category
        cate_items = [item for item in data if item["categories"][0] == cate]
        
        # 根据是否有AI字段生成不同的内容 / Generate different content based on whether AI fields exist
        if has_ai_fields:
            formatted_items = [
                template.format(
                    title=item["title"],
                    authors=",".join(item["authors"]),
                    summary=item["summary"],
                    url=item['abs'],
                    tldr=item['AI']['tldr'],
                    motivation=item['AI']['motivation'],
                    method=item['AI']['method'],
                    result=item['AI']['result'],
                    conclusion=item['AI']['conclusion'],
                    cate=item['categories'][0],
                    idx=next(idx)
                )
                for item in cate_items
            ]
        else:
            formatted_items = [
                template.format(
                    title=item["title"],
                    authors=",".join(item["authors"]),
                    summary=item["summary"],
                    url=item['abs'],
                    cate=item['categories'][0],
                    idx=next(idx)
                )
                for item in cate_items
            ]
        
        markdown += "\n\n".join(formatted_items)
    with open(args.data.split('_')[0] + '.md', "w") as f:
        f.write(markdown)
