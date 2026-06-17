let radarDates = [];
let radarFileMap = new Map();

document.addEventListener('DOMContentLoaded', async () => {
  const dateSelect = document.getElementById('radarDateSelect');
  const previousButton = document.getElementById('radarPreviousButton');
  const nextButton = document.getElementById('radarNextButton');
  const status = document.getElementById('radarStatus');
  const report = document.getElementById('radarReport');

  try {
    radarDates = await fetchRadarDates();
    if (!radarDates.length) {
      status.textContent = 'No Daily Research Radar reports are available yet.';
      report.innerHTML = '<div class="radar-empty">Run the daily workflow to generate the first radar report.</div>';
      return;
    }

    dateSelect.innerHTML = radarDates
      .map((date) => `<option value="${date}">${date}</option>`)
      .join('');
    dateSelect.disabled = false;
    dateSelect.addEventListener('change', () => loadRadarReport(dateSelect.value));
    previousButton.addEventListener('click', () => moveRadarDate(1));
    nextButton.addEventListener('click', () => moveRadarDate(-1));
    renderArchiveLinks();

    const requestedDate = new URLSearchParams(window.location.search).get('date');
    const initialDate = radarDates.includes(requestedDate) ? requestedDate : radarDates[0];
    await loadRadarReport(initialDate, false);
  } catch (error) {
    status.textContent = `Could not load radar reports: ${error.message}`;
  }
});

async function fetchRadarDates() {
  const fileListUrl = DATA_CONFIG.getDataUrl('assets/file-list.txt');
  const response = await fetch(fileListUrl);
  if (!response.ok) {
    throw new Error(`file list request failed with ${response.status}`);
  }
  const text = await response.text();
  const htmlRegex = /(\d{4}-\d{2}-\d{2})_research_radar\.html$/;
  const markdownRegex = /(\d{4}-\d{2}-\d{2})_research_radar\.md$/;
  radarFileMap = new Map();
  text
    .trim()
    .split('\n')
    .filter(Boolean)
    .forEach((file) => {
      const htmlMatch = file.match(htmlRegex);
      const markdownMatch = file.match(markdownRegex);
      if (htmlMatch) {
        const date = htmlMatch[1];
        radarFileMap.set(date, { ...(radarFileMap.get(date) || {}), html: file });
      }
      if (markdownMatch) {
        const date = markdownMatch[1];
        radarFileMap.set(date, { ...(radarFileMap.get(date) || {}), markdown: file });
      }
    });
  const dates = [...radarFileMap.keys()];
  return [...new Set(dates)].sort((a, b) => new Date(b) - new Date(a));
}

async function loadRadarReport(date, updateUrl = true) {
  const status = document.getElementById('radarStatus');
  const report = document.getElementById('radarReport');
  const dateSelect = document.getElementById('radarDateSelect');
  status.textContent = `Loading ${date}...`;
  report.innerHTML = '';
  dateSelect.value = date;
  updateNavigation(date);
  setActiveArchiveLink(date);
  if (updateUrl) {
    const url = new URL(window.location.href);
    url.searchParams.set('date', date);
    window.history.replaceState({}, '', url);
  }

  const files = radarFileMap.get(date) || {};
  const htmlFile = files.html || `${date}_research_radar.html`;
  const markdownFile = files.markdown || `${date}_research_radar.md`;
  const reportUrl = DATA_CONFIG.getDataUrl(`data/${htmlFile}`);
  const response = await fetch(reportUrl);
  if (response.ok) {
    const dashboardHtml = await response.text();
    renderEmbeddedDashboard(report, dashboardHtml);
    status.textContent = `Showing dashboard for ${date}`;
    return;
  }

  const fallbackUrl = DATA_CONFIG.getDataUrl(`data/${markdownFile}`);
  const fallbackResponse = await fetch(fallbackUrl);
  if (!fallbackResponse.ok) {
    status.textContent = `Could not load ${date}: ${fallbackResponse.status}`;
    report.innerHTML = '<div class="radar-empty">The selected radar report could not be loaded.</div>';
    return;
  }

  const markdown = await fallbackResponse.text();
  report.innerHTML = window.marked ? marked.parse(markdown) : `<pre>${escapeHtml(markdown)}</pre>`;
  status.textContent = `Showing Markdown archive for ${date}`;
}

function moveRadarDate(offset) {
  const dateSelect = document.getElementById('radarDateSelect');
  const currentIndex = radarDates.indexOf(dateSelect.value);
  const nextIndex = currentIndex + offset;
  if (nextIndex < 0 || nextIndex >= radarDates.length) {
    return;
  }
  loadRadarReport(radarDates[nextIndex]);
}

function updateNavigation(date) {
  const currentIndex = radarDates.indexOf(date);
  const previousButton = document.getElementById('radarPreviousButton');
  const nextButton = document.getElementById('radarNextButton');
  previousButton.disabled = currentIndex < 0 || currentIndex >= radarDates.length - 1;
  nextButton.disabled = currentIndex <= 0;
}

function renderArchiveLinks() {
  const archive = document.getElementById('radarArchiveLinks');
  archive.innerHTML = radarDates
    .map((date) => `<a href="?date=${encodeURIComponent(date)}" data-radar-date="${date}">${date}</a>`)
    .join('');
  archive.addEventListener('click', (event) => {
    const link = event.target.closest('a[data-radar-date]');
    if (!link) {
      return;
    }
    event.preventDefault();
    loadRadarReport(link.dataset.radarDate);
  });
}

function setActiveArchiveLink(date) {
  document.querySelectorAll('#radarArchiveLinks a').forEach((link) => {
    link.classList.toggle('active', link.dataset.radarDate === date);
  });
}

function renderEmbeddedDashboard(container, dashboardHtml) {
  const parsed = new DOMParser().parseFromString(dashboardHtml, 'text/html');
  parsed.querySelectorAll('script').forEach((script) => script.remove());
  const scopedCss = Array.from(parsed.querySelectorAll('style'))
    .map((style) => scopeDashboardCss(style.textContent || ''))
    .join('\n');
  container.innerHTML = `<div class="embedded-dashboard"><style>${scopedCss}</style><div class="dashboard-root">${parsed.body.innerHTML}</div></div>`;
  attachEmbeddedDarkMode(container.querySelector('.dashboard-root'));
}

function scopeDashboardCss(css) {
  return css
    .replaceAll(':root', '.dashboard-root')
    .replaceAll('body.dark', '.dashboard-root.dark')
    .replaceAll('body {', '.dashboard-root {');
}

function attachEmbeddedDarkMode(root) {
  if (!root) {
    return;
  }
  const toggle = root.querySelector('#darkModeToggle');
  if (!toggle) {
    return;
  }
  const storedTheme = localStorage.getItem('researchRadarTheme');
  if (storedTheme === 'dark') {
    root.classList.add('dark');
  }
  const syncToggleLabel = () => {
    toggle.textContent = root.classList.contains('dark') ? 'Light mode' : 'Dark mode';
  };
  toggle.addEventListener('click', () => {
    root.classList.toggle('dark');
    localStorage.setItem('researchRadarTheme', root.classList.contains('dark') ? 'dark' : 'light');
    syncToggleLabel();
  });
  syncToggleLabel();
}

function escapeHtml(value) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
