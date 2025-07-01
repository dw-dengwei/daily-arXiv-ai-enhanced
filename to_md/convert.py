import json
import argparse
import os
from itertools import count

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, help="Path to the jsonline file")
    args = parser.parse_args()
    data = []
    preference = os.environ.get('CATEGORIES', 'cs.CV, cs.CL').split(',')
    preference = list(map(lambda x: x.strip(), preference))
    def rank(cate):
        if cate in preference:
            return preference.index(cate)
        else:
            return len(preference)

    with open(args.data, "r") as f:
        for line in f:
            data.append(json.loads(line))

    categories = set([item["categories"][0] for item in data])
    template = open("paper_template.md", "r").read()
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
        markdown += "\n\n".join(
            [
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
                for item in data if item["categories"][0] == cate
            ]
        )
    with open(args.data.split('_')[0] + '.md', "w") as f:
        f.write(markdown)