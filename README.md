# About
This tool will daily crawl https://arxiv.org and use LLMs to summary them.

# How to use
This repo will daily crawl arXiv papers about **cs.CV and cs.CL**, and use **DeepSeek** to summarize the papers in **Chinese**.
If you wish to crawl other arXiv categories, use other LLMs or other language, please follow the bellow instructions.
Otherwise, you can directly use this repo. Please star it if you like :)

**Instructions:**
1. Fork this repo to your own account
2. Go to: your-own-repo -> Settings -> Secrets and variables -> Actions
3. Go to Secrets. Secrets are encrypted and are used for sensitive data
4. Create two repository secrets named `OPENAI_API_KEY` and `OPENAI_BASE_URL`, and input corresponding values.
5. Go to Variables. Variables are shown as plain text and are used for non-sensitive data
6. Create the following repository variables:
   1. `CATEGORIES`: separate the categories with ",", such as "cs.CL, cs.CV"
   2. `LANGUAGE`: such as "Chinese" or "English"
   3. `MODEL_NAME`: such as "deepseek-chat"
   4. `EMAIL`: your email for push to github
   5. `NAME`: your name for push to github
7. Go to your-own-repo -> Actions -> arXiv-daily-ai-enhanced
8. You can manually click **Run workflow** to test if it works well (it may takes about one hour). 
By default, this action will automatically run every day
You can modify it in `.github/workflows/run.yml`

# Content
[2025-04-04](data/2025-04-04.md)

[2025-04-03](data/2025-04-03.md)

[2025-04-02](data/2025-04-02.md)

[2025-04-01](data/2025-04-01.md)

[2025-03-31](data/2025-03-31.md)

[2025-03-30](data/2025-03-30.md)

[2025-03-29](data/2025-03-29.md)

[2025-03-28](data/2025-03-28.md)

[2025-03-27](data/2025-03-27.md)

[2025-03-26](data/2025-03-26.md)

[2025-03-25](data/2025-03-25.md)

[2025-03-24](data/2025-03-24.md)

[2025-03-23](data/2025-03-23.md)

[2025-03-22](data/2025-03-22.md)

[2025-03-21](data/2025-03-21.md)

[2025-03-20](data/2025-03-20.md)

[2025-03-19](data/2025-03-19.md)

[2025-03-18](data/2025-03-18.md)

# Related tools
- ICML, ICLR, NeurIPS list: https://dw-dengwei.github.io/OpenReview-paper-list/index.html
