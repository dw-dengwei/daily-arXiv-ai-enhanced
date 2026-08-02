"use strict";

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightTextHtml(text, terms, className = "highlight-match") {
  const safeText = escapeHtml(text);
  const normalizedTerms = (terms || [])
    .map(term => escapeHtml(term))
    .filter(Boolean)
    .sort((a, b) => b.length - a.length);
  if (!normalizedTerms.length || !safeText) {
    return safeText;
  }

  const regex = new RegExp(
    `(${normalizedTerms.map(escapeRegExp).join("|")})`,
    "gi"
  );
  return safeText.replace(
    regex,
    `<span class="${escapeHtml(className)}">$1</span>`
  );
}

function safeExternalUrl(value, allowedHosts) {
  try {
    const url = new URL(String(value));
    const hosts = allowedHosts || [];
    if (url.protocol !== "https:" || !hosts.includes(url.hostname)) {
      return "#";
    }
    return url.href;
  } catch (_error) {
    return "#";
  }
}

function arxivUrl(value, suffix) {
  const url = safeExternalUrl(value, ["arxiv.org", "export.arxiv.org"]);
  if (url === "#") {
    return "#";
  }
  return url.replace("/abs/", `/${suffix}/`);
}

if (typeof module !== "undefined") {
  module.exports = { escapeHtml, highlightTextHtml, safeExternalUrl, arxivUrl };
}
