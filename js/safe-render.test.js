const test = require("node:test");
const assert = require("node:assert/strict");

const {
  escapeHtml,
  highlightTextHtml,
  safeExternalUrl,
  arxivUrl,
} = require("./safe-render.js");

test("escapes paper content before highlighting", () => {
  const rendered = highlightTextHtml('<img src=x onerror="bad">', ["img"]);

  assert.match(rendered, /&lt;<span class="highlight-match">img<\/span>/);
  assert.doesNotMatch(rendered, /<img|onerror="/);
  assert.equal(escapeHtml("A & B"), "A &amp; B");
});

test("only accepts HTTPS arXiv links", () => {
  assert.equal(
    arxivUrl("https://arxiv.org/abs/2607.12345", "pdf"),
    "https://arxiv.org/pdf/2607.12345"
  );
  assert.equal(safeExternalUrl("javascript:alert(1)", ["arxiv.org"]), "#");
});
