# 🚀 daily-arXiv-ai-enhanced

> [!CAUTION]
> 若您所在法域对学术数据有审查要求，谨慎运行本代码；任何二次分发版本必须履行合规审查（包括但不限于原始论文合规性、AI合规性）义务，否则一切法律后果由下游自行承担。

> [!CAUTION]
> If your jurisdiction has censorship requirements for academic data, run this code with caution; any secondary distribution version must remove the entrance accessible to China and fulfill the content review obligations, otherwise all legal consequences will be borne by the downstream.


This innovative tool transforms how you stay updated with arXiv papers by combining automated crawling with AI-powered summarization.

## Daily Research Radar

This fork adds a personalised **Daily Research Radar** for biomedical and genetic epidemiology reading. It keeps the existing arXiv crawler and AI-enhanced JSONL workflow, then adds a second ranking/reporting pass that:

- monitors machine-learning, statistics, quantitative-biology, and retrieval categories: `cs.LG`, `stat.ML`, `cs.AI`, `cs.CL`, `cs.CV`, `q-bio.GN`, `q-bio.QM`, `stat.AP`, `stat.ME`, and `cs.IR`
- scores papers against `research_profile.yaml`
- rotates the main learning theme using `daily_topic_schedule.yaml`
- recommends only 2-3 key papers plus 5-10 secondary papers
- writes archival Markdown to `data/YYYY-MM-DD_research_radar.md`
- writes a standalone responsive HTML dashboard to `data/YYYY-MM-DD_research_radar.html`
- stores scored radar data in `data/YYYY-MM-DD_research_radar_enhanced.jsonl`
- records recent recommendations in `data/research_radar_history.json` to avoid repeated recommendations within 30 days
- exposes the latest HTML dashboard through `research-radar.html` on GitHub Pages, with Markdown fallback for older reports

### Research Radar setup

Required GitHub secrets:

- `OPENAI_API_KEY`: API key for the LLM provider
- `SMTP_USERNAME`: SMTP account username for email notification
- `SMTP_PASSWORD`: SMTP account password or app password for email notification

Required GitHub variables:

- `OPENAI_BASE_URL`: use `https://api.deepseek.com`
- `MODEL_NAME`: use `deepseek-chat`
- `SMTP_HOST`: SMTP server hostname
- `SMTP_PORT`: SMTP server port, for example `465` or `587`
- `EMAIL_FROM`: sender address used by the workflow
- `EMAIL_TO`: recipient address, for example `weijie.j.liu@gmail.com`

Recommended GitHub variables:

- `CATEGORIES`: comma-separated arXiv categories; leave unset to use `research_profile.yaml`
- `DAILY_TOPIC_MODE`: `rotate`, `fixed`, or `exploratory`
- `MAX_KEY_PAPERS_PER_DAY`: default `3`
- `MAX_OTHER_PAPERS_PER_DAY`: default `8`
- `SERENDIPITY_RATIO`: default `0.25`
- `RESEARCH_PROFILE_PATH`: default `research_profile.yaml`
- `RADAR_MAX_WORKERS`: default `4`
- `LLM_TIMEOUT_SECONDS`: default `60`
- `ENABLE_EMAIL`: set to `false` to disable email notifications while keeping daily report generation enabled

Daily automation is defined in `.github/workflows/run.yml`. GitHub cron is UTC, so the workflow uses 07:00 and 08:00 UTC schedules plus a Europe/London guard; only the run matching 08:00 UK time generates and emails the report. Manual runs are available from the GitHub Actions tab through **Run workflow**.

The workflow publishes daily report artifacts to the `data` branch, updates the main `research-radar.html` dashboard/index files when needed, then emails the daily report link and dashboard link. To test manually in GitHub, open **Actions -> Daily Research Radar -> Run workflow**. To disable email, set repository variable `ENABLE_EMAIL=false`; leave it unset or set it to any other value to send email.

Edit `research_profile.yaml` to change long-term interests, arXiv categories, topic keywords, and scoring keywords. Edit `daily_topic_schedule.yaml` to change the seven-day rotating topic cycle, the anchor date, learning points, or the reason each topic matters.

Run locally after installing dependencies:

```bash
uv sync
source .venv/bin/activate
python daily_research_radar.py --date today
python daily_research_radar.py --days-back 7
python daily_research_radar.py --start-date 2026-06-01 --end-date 2026-06-17
```

If `data/YYYY-MM-DD.jsonl` does not exist, the command fetches arXiv papers from the configured categories for that date and then generates the report. Use `--skip-existing` during backfills to avoid regenerating dates that already have enhanced JSONL, Markdown, and HTML outputs. To use a file already produced by the existing crawler or AI enhancer for a single date:

```bash
python daily_research_radar.py --date 2026-06-17 --data data/2026-06-17_AI_enhanced_English.jsonl
```

Example report structure:

```markdown
# Daily Research Radar - 2026-06-17

## Today's main topic
Clinical prediction, survival modelling, and risk-score evaluation

## Read these first
2-3 papers with summaries, relevance, research-use notes, scores, and reading-time labels.

## Other relevant papers
5-10 shorter recommendations.

## Idea generation
3 concrete project ideas with data sources, methods, publishability, and difficulty.
```


## ✨ Key Features

🎯 **Zero Infrastructure Required**
- Leverages GitHub Actions and Pages - no server needed
- Completely free to deploy and use

🤖 **Smart AI Summarization**
- Daily paper crawling with DeepSeek-powered summaries
- Cost-effective: Only ~0.2 CNY per day

💫 **Smart Reading Experience**
- Personalized paper highlighting based on your interests
- Cross-device compatibility (desktop & mobile)
- Local preference storage for privacy
- Flexible date range filtering

🧩 **SKILL System**
- Plug-and-play skill modules for customizing paper filtering

⚙️ **Easy Preference Export & Integration**
- One-click copy in Settings to export your keywords and authors configuration
- Seamlessly combine exported preferences with SKILL for reproducible and shareable setups

👉 **[Try it now!](https://dw-dengwei.github.io/daily-arXiv-ai-enhanced/)** - No installation required



https://github.com/user-attachments/assets/b25712a4-fb8d-484f-863d-e8da6922f9d7




# How to use
This repo will daily crawl arXiv papers about **cs.CV, cs.GR, cs.CL and cs.AI**, and use **DeepSeek** to summarize the papers in **Chinese**.
If you wish to crawl other arXiv categories, use other LLMs, or other languages, please follow the instructions.
Otherwise, you can watch the video above first and directly use this repo in https://dw-dengwei.github.io/daily-arXiv-ai-enhanced/. Please star it if you like :)

<details>
   <summary> If you want to customize categories, LLMs, or languages, click here.  </summary>

## Instructions
1. Fork this repo to your own account and delete my own information in [buy-me-a-coffee](./buy-me-a-coffee/README.md).
2. Go to: your-own-repo -> Settings -> Secrets and variables -> Actions
3. Go to Secrets. Secrets are encrypted and used for sensitive data
4. Create the repository secret `OPENAI_API_KEY`. For email notifications, also create `SMTP_USERNAME` and `SMTP_PASSWORD`.
5. [Optional] Set a password in `secrets.ACCESS_PASSWORD` if you do not wish others to access your page. (see https://github.com/dw-dengwei/daily-arXiv-ai-enhanced/pull/64)
6. Go to Variables. Variables are shown as plain text and are used for non-sensitive data
7. Create the following repository variables:
   1. `CATEGORIES`: separate the categories with ",", such as "cs.CL, cs.CV"
   2. `OPENAI_BASE_URL`: such as "https://api.deepseek.com"
   3. `MODEL_NAME`: such as "deepseek-chat"
   4. `SMTP_HOST`: SMTP server hostname
   5. `SMTP_PORT`: SMTP server port
   6. `EMAIL_FROM`: sender address for notification email and workflow commits
   7. `EMAIL_TO`: recipient address for notification email
   8. `ENABLE_EMAIL`: optional; set to `false` to disable email notification
8. Go to your-own-repo -> Actions -> Daily Research Radar
9. You can manually click **Run workflow** to test if it works well. By default, this action will automatically run every day at 08:00 UK time. You can modify it in `.github/workflows/run.yml`
10. Set up GitHub pages: Go to your own repo -> Settings -> Pages. In `Build and deployment`, set `Source="Deploy from a branch"`, `Branch="main", "/(root)"`. Wait for a few minutes, go to https://\<username\>.github.io/daily-arXiv-ai-enhanced/. Please see this [issue](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced/issues/14) for more precise instructions.
</details>

# Contributors
Thanks to the following special contributors for contributing code, discovering bugs, and sharing useful ideas for this project!!!
<table>
  <tbody>
    <tr>
      <td align="center" valign="top">
        <a href="https://github.com/JianGuanTHU"><img src="https://avatars.githubusercontent.com/u/44895708?v=4" width="100px;" alt="JianGuanTHU"/><br /><sub><b>JianGuanTHU</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://github.com/Chi-hong22"><img src="https://avatars.githubusercontent.com/u/75403952?v=4" width="100px;" alt="Chi-hong22"/><br /><sub><b>Chi-hong22</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://github.com/chaozg"><img src="https://avatars.githubusercontent.com/u/69794131?v=4" width="100px;" alt="chaozg"/><br /><sub><b>chaozg</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://github.com/quantum-ctrl"><img src="https://avatars.githubusercontent.com/u/16505311?v=4" width="100px;" alt="quantum-ctrl"/><br /><sub><b>quantum-ctrl</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://github.com/Zhao2z"><img src="https://avatars.githubusercontent.com/u/141019403?v=4" width="100px;" alt="Zhao2z"/><br /><sub><b>Zhao2z</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://github.com/eclipse0922"><img src="https://avatars.githubusercontent.com/u/6214316?v=4" width="100px;" alt="eclipse0922"/><br /><sub><b>eclipse0922</b></sub></a><br />
      </td>
    </tr>


  </tbody>
  <tbody>
   <tr>
      <td align="center" valign="top">
        <a href="https://github.com/xuemian168"><img src="https://avatars.githubusercontent.com/u/38741078?v=4" width="100px;" alt="xuemian168"/><br /><sub><b>xuemian168</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://github.com/Lrrrr549"><img src="https://avatars.githubusercontent.com/u/71866027?v=4" width="100px;" alt="Lrrrr549"/><br /><sub><b>Lrrrr549</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://github.com/AinzRimuru"><img src="https://avatars.githubusercontent.com/u/59441476?v=4" width="100px;" alt="AinzRimuru"/><br /><sub><b>AinzRimuru</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://github.com/fengxueguiren"><img src="https://avatars.githubusercontent.com/u/153522370?v=4" width="100px;" alt="fengxueguiren"/><br /><sub><b>fengxueguiren</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://github.com/zerocpp"><img src="https://avatars.githubusercontent.com/u/2630297?v=4" width="100px;" alt="fengxueguiren"/><br /><sub><b>zerocpp</b></sub></a><br />
      </td>
   </tr>
  </tbody>
</table>

# Acknowledgement
We sincerely thank the following individuals and organizations for their promotion and support!!!
<table>
  <tbody>
    <tr>
      <td align="center" valign="top">
        <a href="https://x.com/GitHub_Daily/status/1930610556731318781"><img src="https://pbs.twimg.com/profile_images/1660876795347111937/EIo6fIr4_400x400.jpg" width="100px;" alt="Github_Daily"/><br /><sub><b>Github_Daily</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://x.com/aigclink/status/1930897858963853746"><img src="https://pbs.twimg.com/profile_images/1729450995850027008/gllXr6bh_400x400.jpg" width="100px;" alt="AIGCLINK"/><br /><sub><b>AIGCLINK</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://www.ruanyifeng.com/blog/2025/06/weekly-issue-353.html"><img src="https://avatars.githubusercontent.com/u/905434" width="100px;" alt="阮一峰的网络日志"/><br /><sub><b>阮一峰的网络日志 <br> 科技爱好者周刊 <br> （第 353 期）</b></sub></a><br />
      </td>
      <td align="center" valign="top">
        <a href="https://hellogithub.com/periodical/volume/111"><img src="https://github.com/user-attachments/assets/eff6b6dd-0323-40c4-9db6-444a51bbc80a" width="100px;" alt="《HelloGitHub》第 111 期"/><br /><sub><b>《HelloGitHub》<br> 月刊第 111 期</b></sub></a><br />
      </td>
    </tr>
  </tbody>
</table>


# Star history

[![Stargazers over time](https://starchart.cc/dw-dengwei/daily-arXiv-ai-enhanced.svg?variant=adaptive)](https://starchart.cc/dw-dengwei/daily-arXiv-ai-enhanced)

# Buy me a coffee
[here](./buy-me-a-coffee/README.md)
