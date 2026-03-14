#!/usr/bin/env python3
"""Send daily report and author-focused source summaries via SMTP email."""

import argparse
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send daily markdown reports by email")
    parser.add_argument("--date", type=str, required=True, help="Report date (YYYY-MM-DD)")
    parser.add_argument("--report-file", type=str, required=True, help="Path to daily report markdown")
    parser.add_argument("--source-file", type=str, required=True, help="Path to author source guide markdown")
    parser.add_argument(
        "--default-to",
        type=str,
        default="",
        help="Default recipient when REPORT_EMAIL_TO is not set",
    )
    return parser.parse_args()


def get_env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is None:
        return default.strip()
    value = value.strip()
    return value if value else default.strip()


def read_text_if_exists(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def truncate_text(text: str, max_chars: int = 12000) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20] + "\n\n...[truncated]..."


def parse_recipients(value: str) -> List[str]:
    raw = value.replace(";", ",")
    recipients = [x.strip() for x in raw.split(",") if x.strip()]
    return recipients


def build_body(date_str: str, report_text: str, source_text: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        f"daily-arXiv 自动日报（{date_str}）",
        f"生成时间：{now}",
        "",
        "以下为正文预览（完整内容见附件）：",
        "",
        "==== 报告 report/YYYY-MM-DD.md ====",
        truncate_text(report_text) if report_text else "未找到日报文件。",
        "",
        "==== 关注作者来源总结 author_source_guides/YYYY-MM-DD.md ====",
        truncate_text(source_text) if source_text else "未找到关注作者来源总结文件。",
        "",
    ]
    return "\n".join(lines)


def resolve_smtp_mode(smtp_port: int) -> str:
    """
    Resolve SMTP mode from env, with safe defaults:
    - port 465 -> ssl
    - other ports -> starttls
    """
    raw = get_env("SMTP_USE_SSL", "")
    if raw:
        val = raw.lower()
        if val in {"1", "true", "yes", "y", "on"}:
            return "ssl"
        if val in {"0", "false", "no", "n", "off"}:
            return "starttls"
    return "ssl" if smtp_port == 465 else "starttls"


def send_via_ssl(msg: EmailMessage, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str) -> None:
    with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
        server.login(smtp_user, smtp_password)
        server.send_message(msg)


def send_via_starttls(msg: EmailMessage, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str) -> None:
    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)


def main() -> None:
    args = parse_args()

    smtp_host = get_env("SMTP_HOST")
    smtp_port = int(get_env("SMTP_PORT", "465") or "465")
    smtp_user = get_env("SMTP_USER")
    smtp_password = get_env("SMTP_PASSWORD")
    smtp_from = get_env("SMTP_FROM", smtp_user)
    smtp_mode = resolve_smtp_mode(smtp_port)

    to_value = get_env("REPORT_EMAIL_TO", args.default_to)
    recipients = parse_recipients(to_value)

    if not smtp_host or not smtp_user or not smtp_password:
        raise RuntimeError("SMTP config missing: SMTP_HOST/SMTP_USER/SMTP_PASSWORD are required")
    if not recipients:
        raise RuntimeError("No recipient set. Configure REPORT_EMAIL_TO or pass --default-to")

    report_text = read_text_if_exists(args.report_file)
    source_text = read_text_if_exists(args.source_file)

    msg = EmailMessage()
    msg["Subject"] = f"[daily-arXiv] {args.date} 日报与关注作者来源总结"
    msg["From"] = smtp_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(build_body(args.date, report_text, source_text))

    if report_text:
        msg.add_attachment(
            report_text.encode("utf-8"),
            maintype="text",
            subtype="markdown",
            filename=os.path.basename(args.report_file),
        )
    if source_text:
        msg.add_attachment(
            source_text.encode("utf-8"),
            maintype="text",
            subtype="markdown",
            filename=os.path.basename(args.source_file),
        )

    if smtp_mode == "ssl":
        try:
            send_via_ssl(msg, smtp_host, smtp_port, smtp_user, smtp_password)
        except ssl.SSLError as exc:
            # Common case: wrong SSL mode/port combination (e.g. SSL on 25/587).
            print(f"SSL failed ({exc}), retrying with STARTTLS...", flush=True)
            send_via_starttls(msg, smtp_host, smtp_port, smtp_user, smtp_password)
    else:
        send_via_starttls(msg, smtp_host, smtp_port, smtp_user, smtp_password)

    print(f"Email sent to: {', '.join(recipients)}")


if __name__ == "__main__":
    main()
