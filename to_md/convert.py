import json
import argparse
import os
from itertools import count
from pathlib import Path


def main_category(item):
    """Return the category that produced the record, including cross-lists."""

    matched = item.get("matched_categories") or item.get("matched_category")
    if isinstance(matched, str):
        matched = [matched]
    if matched:
        return matched[0]

    categories = item.get("categories") or []
    if isinstance(categories, str):
        return categories
    return categories[0] if categories else None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="Path to the jsonline file")
    args = parser.parse_args()
    data = []
    preference = os.environ.get('CATEGORIES', 'cs.CV, cs.CL').split(',')
    preference = list(map(lambda x: x.strip(), preference))
    def rank(cate):
        if cate in preference:
            return preference.index(cate)
        else:
            return len(preference)

    with open(args.data, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))

    categories = {category for item in data if (category := main_category(item))}
    template_path = Path(__file__).resolve().parent / "paper_template.md"
    template = template_path.read_text(encoding="utf-8")
    categories = sorted(categories, key=rank)
    cnt = {cate: 0 for cate in categories}
    for item in data:
        category = main_category(item)
        if category not in cnt.keys():
            continue
        cnt[category] += 1

    markdown = f"<div id=toc></div>\n\n# Table of Contents\n\n"
    for idx, cate in enumerate(categories):
        markdown += f"- [{cate}](#{cate}) [Total: {cnt[cate]}]\n"

    idx = count(1)
    for cate in categories:
        markdown += f"\n\n<div id='{cate}'></div>\n\n"
        markdown += f"# {cate} [[Back]](#toc)\n\n"
        papers = []
        for item in data:
            if main_category(item) == cate:
                # Safely access AI fields with default values
                ai_data = item.get('AI', {})
                if not ai_data or not isinstance(ai_data, dict):
                    print(f"Skipping item '{item.get('title', 'Unknown')}' due to missing or invalid AI data")
                    continue
                
                # Check if all required AI fields are present
                required_fields = ['tldr', 'motivation', 'method', 'result', 'conclusion']
                if not all(field in ai_data for field in required_fields):
                    print(f"Skipping item '{item.get('title', 'Unknown')}' due to incomplete AI fields")
                    continue
                
                authors = item.get("authors", [])
                if isinstance(authors, (list, tuple)):
                    authors = ",".join(str(author) for author in authors)
                else:
                    authors = str(authors)

                papers.append(
                    template.format(
                        title=item.get("title", "Untitled"),
                        authors=authors,
                        summary=item.get("summary", ""),
                        url=item.get("abs", item.get("pdf", "")),
                        tldr=ai_data.get('tldr', ''),
                        motivation=ai_data.get('motivation', ''),
                        method=ai_data.get('method', ''),
                        result=ai_data.get('result', ''),
                        conclusion=ai_data.get('conclusion', ''),
                        cate=main_category(item),
                        idx=next(idx)
                    )
                )
        markdown += "\n\n".join(papers)
    data_path = Path(args.data)
    date_stem = data_path.name.split("_AI_enhanced_", 1)[0]
    output_path = data_path.with_name(f"{date_stem}.md")
    with output_path.open("w", encoding="utf-8") as f:
        f.write(markdown)
