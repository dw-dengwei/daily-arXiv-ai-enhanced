let currentDate = '';
let availableDates = [];
let currentView = 'grid'; // 'grid' 或 'list'
let currentCategory = 'all';
let paperData = {};
let flatpickrInstance = null;
let isRangeMode = false;
let activeKeywords = []; // 存储激活的关键词
let userKeywords = []; // 存储用户的关键词
let activeAuthors = []; // 存储激活的作者
let userAuthors = []; // 存储用户的作者
let currentPaperIndex = 0; // 当前查看的论文索引
let currentFilteredPapers = []; // 当前过滤后的论文列表

// 加载用户的关键词设置
function loadUserKeywords() {
  const savedKeywords = localStorage.getItem('preferredKeywords');
  if (savedKeywords) {
    try {
      userKeywords = JSON.parse(savedKeywords);
      // 默认激活所有关键词
      activeKeywords = [...userKeywords];
    } catch (error) {
      console.error('解析关键词失败:', error);
      userKeywords = [];
      activeKeywords = [];
    }
  } else {
    userKeywords = [];
    activeKeywords = [];
  }
  
  renderKeywordTags();
}

// 加载用户的作者设置
function loadUserAuthors() {
  const savedAuthors = localStorage.getItem('preferredAuthors');
  if (savedAuthors) {
    try {
      userAuthors = JSON.parse(savedAuthors);
      // 默认激活所有作者
      activeAuthors = [...userAuthors];
    } catch (error) {
      console.error('解析作者失败:', error);
      userAuthors = [];
      activeAuthors = [];
    }
  } else {
    userAuthors = [];
    activeAuthors = [];
  }
  
  renderAuthorTags();
}

// 渲染关键词标签
function renderKeywordTags() {
  const keywordTagsElement = document.getElementById('keywordTags');
  const keywordContainer = document.querySelector('.keyword-label-container');
  
  if (!userKeywords || userKeywords.length === 0) {
    keywordContainer.style.display = 'none';
    return;
  }
  
  keywordContainer.style.display = 'flex';
  keywordTagsElement.innerHTML = '';
  
  // 添加关键词标签
  userKeywords.forEach(keyword => {
    const tagElement = document.createElement('span');
    tagElement.className = `category-button ${activeKeywords.includes(keyword) ? 'active' : ''}`;
    tagElement.dataset.keyword = keyword;
    tagElement.textContent = keyword;
    // 添加提示信息，解释关键词匹配的范围
    tagElement.title = "匹配标题和摘要中的关键词";
    
    tagElement.addEventListener('click', () => {
      toggleKeywordFilter(keyword);
    });
    
    keywordTagsElement.appendChild(tagElement);
    
    // 添加出现动画后移除动画类
    if (!activeKeywords.includes(keyword)) {
      tagElement.classList.add('tag-appear');
      setTimeout(() => {
        tagElement.classList.remove('tag-appear');
      }, 300);
    }
  });
  
  // 添加"清除全部"按钮和逻辑提示
  // if (activeKeywords.length > 0) {
  //   const logicIndicator = document.createElement('span');
  //   logicIndicator.className = 'logic-indicator';
  //   logicIndicator.textContent = 'SORT';
  //   // 添加提示信息，解释排序逻辑
  //   logicIndicator.title = "多个关键词使用'或'逻辑，匹配任一关键词的论文会被优先显示";
  //   keywordTagsElement.appendChild(logicIndicator);
    
  //   const clearButton = document.createElement('span');
  //   clearButton.className = 'category-button clear-button';
  //   clearButton.textContent = 'Clear';
  //   clearButton.addEventListener('click', clearAllKeywords);
  //   keywordTagsElement.appendChild(clearButton);
  // }
}

// 切换关键词过滤
function toggleKeywordFilter(keyword) {
  const index = activeKeywords.indexOf(keyword);
  
  if (index === -1) {
    // 激活该关键词
    activeKeywords.push(keyword);
  } else {
    // 取消激活该关键词
    activeKeywords.splice(index, 1);
  }
  
  // 更新关键词标签UI
  const keywordTags = document.querySelectorAll('[data-keyword]');
  keywordTags.forEach(tag => {
    if (tag.dataset.keyword === keyword) {
      // 先移除上一次可能的高亮动画
      tag.classList.remove('tag-highlight');
      
      // 添加/移除激活状态
      tag.classList.toggle('active', activeKeywords.includes(keyword));
      
      // 添加高亮动画
      setTimeout(() => {
        tag.classList.add('tag-highlight');
      }, 10);
      
      // 移除高亮动画
      setTimeout(() => {
        tag.classList.remove('tag-highlight');
      }, 1000);
    }
  });
  
  // 重新渲染论文列表
  renderPapers();
}

// 渲染作者标签
function renderAuthorTags() {
  const authorTagsElement = document.getElementById('authorTags');
  const authorContainer = document.querySelector('.author-label-container');
  
  if (!userAuthors || userAuthors.length === 0) {
    authorContainer.style.display = 'none';
    return;
  }
  
  authorContainer.style.display = 'flex';
  authorTagsElement.innerHTML = '';
  
  // 添加作者标签
  userAuthors.forEach(author => {
    const tagElement = document.createElement('span');
    tagElement.className = `category-button ${activeAuthors.includes(author) ? 'active' : ''}`;
    tagElement.dataset.author = author;
    tagElement.textContent = author;
    // 添加提示信息，解释作者匹配的范围
    tagElement.title = "匹配作者列表中的名字";
    
    tagElement.addEventListener('click', () => {
      toggleAuthorFilter(author);
    });
    
    authorTagsElement.appendChild(tagElement);
    
    // 添加出现动画后移除动画类
    if (!activeAuthors.includes(author)) {
      tagElement.classList.add('tag-appear');
      setTimeout(() => {
        tagElement.classList.remove('tag-appear');
      }, 300);
    }
  });
  
  // // 添加"清除全部"按钮和逻辑提示
  // if (activeAuthors.length > 0) {
  //   const logicIndicator = document.createElement('span');
  //   logicIndicator.className = 'logic-indicator';
  //   logicIndicator.textContent = 'SORT';
  //   // 添加提示信息，解释排序逻辑
  //   logicIndicator.title = "多个作者使用'或'逻辑，匹配任一作者的论文会被优先显示";
  //   authorTagsElement.appendChild(logicIndicator);
    
  //   const clearButton = document.createElement('span');
  //   clearButton.className = 'category-button clear-button';
  //   clearButton.textContent = 'Clear';
  //   clearButton.addEventListener('click', clearAllAuthors);
  //   authorTagsElement.appendChild(clearButton);
  // }
}

// 切换作者过滤
function toggleAuthorFilter(author) {
  const index = activeAuthors.indexOf(author);
  
  if (index === -1) {
    // 激活该作者
    activeAuthors.push(author);
  } else {
    // 取消激活该作者
    activeAuthors.splice(index, 1);
  }
  
  // 更新作者标签UI
  const authorTags = document.querySelectorAll('[data-author]');
  authorTags.forEach(tag => {
    if (tag.dataset.author === author) {
      // 先移除上一次可能的高亮动画
      tag.classList.remove('tag-highlight');
      
      // 添加/移除激活状态
      tag.classList.toggle('active', activeAuthors.includes(author));
      
      // 添加高亮动画
      setTimeout(() => {
        tag.classList.add('tag-highlight');
      }, 10);
      
      // 移除高亮动画
      setTimeout(() => {
        tag.classList.remove('tag-highlight');
      }, 1000);
    }
  });
  
  // 重新渲染论文列表
  renderPapers();
}

document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  
  fetchGitHubStats();
  
  // 加载用户关键词
  loadUserKeywords();
  
  // 加载用户作者
  loadUserAuthors();
  
  fetchAvailableDates().then(() => {
    if (availableDates.length > 0) {
      loadPapersByDate(availableDates[0]);
    }
  });
});

async function fetchGitHubStats() {
  try {
    const response = await fetch('https://api.github.com/repos/dw-dengwei/daily-arXiv-ai-enhanced');
    const data = await response.json();
    const starCount = data.stargazers_count;
    const forkCount = data.forks_count;
    
    document.getElementById('starCount').textContent = starCount;
    document.getElementById('forkCount').textContent = forkCount;
  } catch (error) {
    console.error('获取GitHub统计数据失败:', error);
    document.getElementById('starCount').textContent = '?';
    document.getElementById('forkCount').textContent = '?';
  }
}

function initEventListeners() {
  // 日期选择器相关的事件监听
  const calendarButton = document.getElementById('calendarButton');
  calendarButton.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleDatePicker();
  });
  
  const datePickerModal = document.querySelector('.date-picker-modal');
  datePickerModal.addEventListener('click', (event) => {
    if (event.target === datePickerModal) {
      toggleDatePicker();
    }
  });
  
  const datePickerContent = document.querySelector('.date-picker-content');
  datePickerContent.addEventListener('click', (e) => {
    e.stopPropagation();
  });

  document.getElementById('dateRangeMode').addEventListener('change', toggleRangeMode);
  
  // 其他原有的事件监听器
  document.getElementById('closeModal').addEventListener('click', closeModal);
  
  document.querySelector('.paper-modal').addEventListener('click', (event) => {
    const modal = document.querySelector('.paper-modal');
    const pdfContainer = modal.querySelector('.pdf-container');
    
    // 如果点击的是模态框背景
    if (event.target === modal) {
      // 检查PDF是否处于放大状态
      if (pdfContainer && pdfContainer.classList.contains('expanded')) {
        // 如果PDF是放大的，先将其恢复正常大小
        const expandButton = modal.querySelector('.pdf-expand-btn');
        if (expandButton) {
          togglePdfSize(expandButton);
        }
        // 阻止事件继续传播，防止关闭整个模态框
        event.stopPropagation();
      } else {
        // 如果PDF不是放大状态，则关闭整个模态框
        closeModal();
      }
    }
  });
  
  // 添加键盘事件监听 - Esc 键关闭模态框，左右箭头键切换论文，R 键显示随机论文
  document.addEventListener('keydown', (event) => {
    // 检查是否有输入框或文本区域处于焦点状态
    const activeElement = document.activeElement;
    const isInputFocused = activeElement && (
      activeElement.tagName === 'INPUT' || 
      activeElement.tagName === 'TEXTAREA' || 
      activeElement.isContentEditable
    );
    
    if (event.key === 'Escape') {
      const paperModal = document.getElementById('paperModal');
      const datePickerModal = document.getElementById('datePickerModal');
      
      // 关闭论文模态框
      if (paperModal.classList.contains('active')) {
        closeModal();
      }
      // 关闭日期选择器模态框
      else if (datePickerModal.classList.contains('active')) {
        toggleDatePicker();
      }
    }
    // 左右箭头键导航论文（仅在论文模态框打开时）
    else if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      const paperModal = document.getElementById('paperModal');
      if (paperModal.classList.contains('active')) {
        event.preventDefault(); // 防止页面滚动
        
        if (event.key === 'ArrowLeft') {
          navigateToPreviousPaper();
        } else if (event.key === 'ArrowRight') {
          navigateToNextPaper();
        }
      }
    }
    // space 键显示随机论文（在没有输入框焦点且日期选择器未打开时）
    else if (event.key === ' ' || event.key === 'Spacebar') {
      const paperModal = document.getElementById('paperModal');
      const datePickerModal = document.getElementById('datePickerModal');
      
      // 只有在没有输入框焦点且日期选择器没有打开时才触发
      // 现在允许在论文模态框打开时也能使用R键切换到随机论文
      if (!isInputFocused && !datePickerModal.classList.contains('active')) {
        event.preventDefault(); // 防止页面刷新
        event.stopPropagation(); // 阻止事件冒泡
        showRandomPaper();
      }
    }
  });
  
  // 添加鼠标滚轮横向滚动支持
  const categoryScroll = document.querySelector('.category-scroll');
  const keywordScroll = document.querySelector('.keyword-scroll');
  const authorScroll = document.querySelector('.author-scroll');
  
  // 为类别滚动添加鼠标滚轮事件
  if (categoryScroll) {
    categoryScroll.addEventListener('wheel', function(e) {
      if (e.deltaY !== 0) {
        e.preventDefault();
        this.scrollLeft += e.deltaY;
      }
    });
  }
  
  // 为关键词滚动添加鼠标滚轮事件
  if (keywordScroll) {
    keywordScroll.addEventListener('wheel', function(e) {
      if (e.deltaY !== 0) {
        e.preventDefault();
        this.scrollLeft += e.deltaY;
      }
    });
  }
  
  // 为作者滚动添加鼠标滚轮事件
  if (authorScroll) {
    authorScroll.addEventListener('wheel', function(e) {
      if (e.deltaY !== 0) {
        e.preventDefault();
        this.scrollLeft += e.deltaY;
      }
    });
  }

  // 其他事件监听器...
  const categoryButtons = document.querySelectorAll('.category-button');
  categoryButtons.forEach(button => {
    button.addEventListener('click', () => {
      const category = button.dataset.category;
      filterByCategory(category);
    });
  });
}

// Function to detect preferred language based on browser settings
function getPreferredLanguage() {
  const browserLang = navigator.language || navigator.userLanguage;
  // Check if browser is set to Chinese variants
  if (browserLang.startsWith('zh')) {
    return 'Chinese';
  }
  // Default to English for all other languages
  return 'English';
}

// Function to select the best available language for a date
function selectLanguageForDate(date, preferredLanguage = null) {
  const availableLanguages = window.dateLanguageMap?.get(date) || [];
  
  if (availableLanguages.length === 0) {
    return 'English'; // fallback
  }
  
  // Use provided preference or detect from browser
  const preferred = preferredLanguage || getPreferredLanguage();
  
  // If preferred language is available, use it
  if (availableLanguages.includes(preferred)) {
    return preferred;
  }
  
  // Fallback: prefer English if available, otherwise use the first available
  return availableLanguages.includes('English') ? 'English' : availableLanguages[0];
}

async function fetchAvailableDates() {
  try {
    const response = await fetch('assets/file-list.txt');
    if (!response.ok) {
      console.error('Error fetching file list:', response.status);
      return [];
    }
    const text = await response.text();
    const files = text.trim().split('\n');

    const dateRegex = /(\d{4}-\d{2}-\d{2})_AI_enhanced_(English|Chinese)\.jsonl/;
    const dateLanguageMap = new Map(); // Store date -> available languages
    const dates = [];
    
    files.forEach(file => {
      const match = file.match(dateRegex);
      if (match && match[1] && match[2]) {
        const date = match[1];
        const language = match[2];
        
        if (!dateLanguageMap.has(date)) {
          dateLanguageMap.set(date, []);
          dates.push(date);
        }
        dateLanguageMap.get(date).push(language);
      }
    });
    
    // Store the language mapping globally for later use
    window.dateLanguageMap = dateLanguageMap;
    availableDates = [...new Set(dates)];
    availableDates.sort((a, b) => new Date(b) - new Date(a));

    initDatePicker(); // Assuming this function uses availableDates

    return availableDates;
  } catch (error) {
    console.error('获取可用日期失败:', error);
  }
}

function initDatePicker() {
  const datepickerInput = document.getElementById('datepicker');
  
  if (flatpickrInstance) {
    flatpickrInstance.destroy();
  }
  
  // 创建可用日期的映射，用于禁用无效日期
  const enabledDatesMap = {};
  availableDates.forEach(date => {
    enabledDatesMap[date] = true;
  });
  
  // 配置 Flatpickr
  flatpickrInstance = flatpickr(datepickerInput, {
    inline: true,
    dateFormat: "Y-m-d",
    defaultDate: availableDates[0],
    enable: [
      function(date) {
        // 只启用有效日期
        const dateStr = date.getFullYear() + "-" + 
                        String(date.getMonth() + 1).padStart(2, '0') + "-" + 
                        String(date.getDate()).padStart(2, '0');
        return !!enabledDatesMap[dateStr];
      }
    ],
    onChange: function(selectedDates, dateStr) {
      if (isRangeMode && selectedDates.length === 2) {
        // 处理日期范围选择
        const startDate = formatDateForAPI(selectedDates[0]);
        const endDate = formatDateForAPI(selectedDates[1]);
        loadPapersByDateRange(startDate, endDate);
        toggleDatePicker();
      } else if (!isRangeMode && selectedDates.length === 1) {
        // 处理单个日期选择
        const selectedDate = formatDateForAPI(selectedDates[0]);
        if (availableDates.includes(selectedDate)) {
          loadPapersByDate(selectedDate);
          toggleDatePicker();
        }
      }
    }
  });
  
  // 隐藏日期输入框
  const inputElement = document.querySelector('.flatpickr-input');
  if (inputElement) {
    inputElement.style.display = 'none';
  }
}

function formatDateForAPI(date) {
  return date.getFullYear() + "-" + 
         String(date.getMonth() + 1).padStart(2, '0') + "-" + 
         String(date.getDate()).padStart(2, '0');
}

function toggleRangeMode() {
  isRangeMode = document.getElementById('dateRangeMode').checked;
  
  if (flatpickrInstance) {
    flatpickrInstance.set('mode', isRangeMode ? 'range' : 'single');
  }
}

async function loadPapersByDate(date) {
  currentDate = date;
  document.getElementById('currentDate').textContent = formatDate(date);
  
  // 更新日期选择器中的选中日期
  if (flatpickrInstance) {
    flatpickrInstance.setDate(date, false);
  }
  
  // 不再重置激活的关键词和作者
  // 而是保持当前选择状态
  
  const container = document.getElementById('paperContainer');
  container.innerHTML = `
    <div class="loading-container">
      <div class="loading-spinner"></div>
      <p>Loading paper...</p>
    </div>
  `;
  
  try {
    const selectedLanguage = selectLanguageForDate(date);
    const response = await fetch(`data/${date}_AI_enhanced_${selectedLanguage}.jsonl`);
    const text = await response.text();
    
    paperData = parseJsonlData(text, date);
    
    const categories = getAllCategories(paperData);
    
    renderCategoryFilter(categories);
    
    renderPapers();
  } catch (error) {
    console.error('加载论文数据失败:', error);
    container.innerHTML = `
      <div class="loading-container">
        <p>Loading data fails. Please retry.</p>
        <p>Error messages: ${error.message}</p>
      </div>
    `;
  }
}

function parseJsonlData(jsonlText, date) {
  const result = {};
  
  const lines = jsonlText.trim().split('\n');
  
  lines.forEach(line => {
    try {
      const paper = JSON.parse(line);
      
      if (!paper.categories) {
        return;
      }
      
      let allCategories = Array.isArray(paper.categories) ? paper.categories : [paper.categories];
      
      const primaryCategory = allCategories[0];
      
      if (!result[primaryCategory]) {
        result[primaryCategory] = [];
      }
      
      const summary = paper.AI && paper.AI.tldr ? paper.AI.tldr : paper.summary;
      
      result[primaryCategory].push({
        title: paper.title,
        url: paper.abs || paper.pdf || `https://arxiv.org/abs/${paper.id}`,
        authors: Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors,
        category: allCategories,
        summary: summary,
        details: paper.summary || '',
        date: date,
        id: paper.id,
        motivation: paper.AI && paper.AI.motivation ? paper.AI.motivation : '',
        method: paper.AI && paper.AI.method ? paper.AI.method : '',
        result: paper.AI && paper.AI.result ? paper.AI.result : '',
        conclusion: paper.AI && paper.AI.conclusion ? paper.AI.conclusion : ''
      });
    } catch (error) {
      console.error('解析JSON行失败:', error, line);
    }
  });
  
  return result;
}

// 获取所有类别并按偏好排序
function getAllCategories(data) {
  const categories = Object.keys(data);
  const catePaperCount = {};
  
  categories.forEach(category => {
    catePaperCount[category] = data[category] ? data[category].length : 0;
  });
  
  return {
    sortedCategories: categories.sort((a, b) => {
      return a.localeCompare(b);
    }),
    categoryCounts: catePaperCount
  };
}

function renderCategoryFilter(categories) {
  const container = document.querySelector('.category-scroll');
  const { sortedCategories, categoryCounts } = categories;
  
  let totalPapers = 0;
  Object.values(categoryCounts).forEach(count => {
    totalPapers += count;
  });
  
  container.innerHTML = `
    <button class="category-button ${currentCategory === 'all' ? 'active' : ''}" data-category="all">All<span class="category-count">${totalPapers}</span></button>
  `;
  
  sortedCategories.forEach(category => {
    const count = categoryCounts[category];
    const button = document.createElement('button');
    button.className = `category-button ${category === currentCategory ? 'active' : ''}`;
    button.innerHTML = `${category}<span class="category-count">${count}</span>`;
    button.dataset.category = category;
    button.addEventListener('click', () => {
      filterByCategory(category);
    });
    
    container.appendChild(button);
  });
  
  document.querySelector('.category-button[data-category="all"]').addEventListener('click', () => {
    filterByCategory('all');
  });
}

function filterByCategory(category) {
  currentCategory = category;
  
  document.querySelectorAll('.category-button').forEach(button => {
    button.classList.toggle('active', button.dataset.category === category);
  });
  
  // 保持当前激活的关键词
  renderKeywordTags();
  
  // 保持当前激活的作者
  renderAuthorTags();
  
  renderPapers();
}

// 帮助函数：高亮文本中的匹配内容
function highlightMatches(text, terms, className = 'highlight-match') {
  if (!terms || terms.length === 0 || !text) {
    return text;
  }
  
  let result = text;
  
  // 按照长度排序关键词，从长到短，避免短词先替换导致长词匹配失败
  const sortedTerms = [...terms].sort((a, b) => b.length - a.length);
  
  // 为每个词创建一个正则表达式，使用 'gi' 标志进行全局、不区分大小写的匹配
  sortedTerms.forEach(term => {
    const regex = new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    result = result.replace(regex, `<span class="${className}">$1</span>`);
  });
  
  return result;
}

function renderPapers() {
  const container = document.getElementById('paperContainer');
  container.innerHTML = '';
  container.className = `paper-container ${currentView === 'list' ? 'list-view' : ''}`;
  
  let papers = [];
  if (currentCategory === 'all') {
    const { sortedCategories } = getAllCategories(paperData);
    sortedCategories.forEach(category => {
      if (paperData[category]) {
        papers = papers.concat(paperData[category]);
      }
    });
  } else if (paperData[currentCategory]) {
    papers = paperData[currentCategory];
  }
  
  // 创建匹配论文的集合
  let filteredPapers = [...papers];
  
  // 关键词和作者匹配，但不过滤，只排序
  if (activeKeywords.length > 0 || activeAuthors.length > 0) {
    // 对论文进行排序，将匹配的论文放在前面
    filteredPapers.sort((a, b) => {
      const aMatchesKeyword = activeKeywords.length > 0 ? 
        activeKeywords.some(keyword => {
          // 仅在标题和摘要中搜索关键词
          const searchText = `${a.title} ${a.summary}`.toLowerCase();
          return searchText.includes(keyword.toLowerCase());
        }) : false;
        
      const aMatchesAuthor = activeAuthors.length > 0 ?
        activeAuthors.some(author => {
          // 仅在作者中搜索作者名
          return a.authors.toLowerCase().includes(author.toLowerCase());
        }) : false;
        
      const bMatchesKeyword = activeKeywords.length > 0 ?
        activeKeywords.some(keyword => {
          // 仅在标题和摘要中搜索关键词
          const searchText = `${b.title} ${b.summary}`.toLowerCase();
          return searchText.includes(keyword.toLowerCase());
        }) : false;
        
      const bMatchesAuthor = activeAuthors.length > 0 ?
        activeAuthors.some(author => {
          // 仅在作者中搜索作者名
          return b.authors.toLowerCase().includes(author.toLowerCase());
        }) : false;
      
      // a和b的匹配状态（关键词或作者匹配都算）
      const aMatches = aMatchesKeyword || aMatchesAuthor;
      const bMatches = bMatchesKeyword || bMatchesAuthor;
      
      if (aMatches && !bMatches) return -1;
      if (!aMatches && bMatches) return 1;
      return 0;
    });
    
    // 标记匹配的论文
    filteredPapers.forEach(paper => {
      const matchesKeyword = activeKeywords.length > 0 ?
        activeKeywords.some(keyword => {
          const searchText = `${paper.title} ${paper.summary}`.toLowerCase();
          return searchText.includes(keyword.toLowerCase());
        }) : false;
        
      const matchesAuthor = activeAuthors.length > 0 ?
        activeAuthors.some(author => {
          return paper.authors.toLowerCase().includes(author.toLowerCase());
        }) : false;
        
      // 添加匹配标记（用于后续高亮整个论文卡片）
      paper.isMatched = matchesKeyword || matchesAuthor;
      
      // 添加匹配原因（用于显示匹配提示）
      if (paper.isMatched) {
        paper.matchReason = [];
        if (matchesKeyword) {
          const matchedKeywords = activeKeywords.filter(keyword => 
            `${paper.title} ${paper.summary}`.toLowerCase().includes(keyword.toLowerCase())
          );
          if (matchedKeywords.length > 0) {
            paper.matchReason.push(`关键词: ${matchedKeywords.join(', ')}`);
          }
        }
        if (matchesAuthor) {
          const matchedAuthors = activeAuthors.filter(author => 
            paper.authors.toLowerCase().includes(author.toLowerCase())
          );
          if (matchedAuthors.length > 0) {
            paper.matchReason.push(`作者: ${matchedAuthors.join(', ')}`);
          }
        }
      }
    });
  }
  
  // 存储当前过滤后的论文列表，用于箭头键导航
  currentFilteredPapers = [...filteredPapers];
  
  if (filteredPapers.length === 0) {
    container.innerHTML = `
      <div class="loading-container">
        <p>No paper found.</p>
      </div>
    `;
    return;
  }
  
  filteredPapers.forEach((paper, index) => {
    const paperCard = document.createElement('div');
    // 添加匹配高亮类
    paperCard.className = `paper-card ${paper.isMatched ? 'matched-paper' : ''}`;
    paperCard.dataset.id = paper.id || paper.url;
    
    if (paper.isMatched) {
      // 添加匹配原因提示
      paperCard.title = `匹配: ${paper.matchReason.join(' | ')}`;
    }
    
    const categoryTags = paper.allCategories ? 
      paper.allCategories.map(cat => `<span class="category-tag">${cat}</span>`).join('') : 
      `<span class="category-tag">${paper.category}</span>`;
    
    // 高亮标题中的关键词
    const highlightedTitle = activeKeywords.length > 0 
      ? highlightMatches(paper.title, activeKeywords, 'keyword-highlight') 
      : paper.title;
    
    // 高亮摘要中的关键词
    const highlightedSummary = activeKeywords.length > 0 
      ? highlightMatches(paper.summary, activeKeywords, 'keyword-highlight') 
      : paper.summary;
    
    // 高亮作者中的匹配
    const highlightedAuthors = activeAuthors.length > 0 
      ? highlightMatches(paper.authors, activeAuthors, 'author-highlight') 
      : paper.authors;
    
    paperCard.innerHTML = `
      <div class="paper-card-index">${index + 1}</div>
      ${paper.isMatched ? '<div class="match-badge" title="匹配您的搜索条件"></div>' : ''}
      <div class="paper-card-header">
        <h3 class="paper-card-title">${highlightedTitle}</h3>
        <p class="paper-card-authors">${highlightedAuthors}</p>
        <div class="paper-card-categories">
          ${categoryTags}
        </div>
      </div>
      <div class="paper-card-body">
        <p class="paper-card-summary">${highlightedSummary}</p>
        <div class="paper-card-footer">
          <span class="paper-card-date">${formatDate(paper.date)}</span>
          <span class="paper-card-link">Details</span>
        </div>
      </div>
    `;
    
    paperCard.addEventListener('click', () => {
      currentPaperIndex = index; // 记录当前点击的论文索引
      showPaperDetails(paper, index + 1);
    });
    
    container.appendChild(paperCard);
  });
}

function showPaperDetails(paper, paperIndex) {
  const modal = document.getElementById('paperModal');
  const modalTitle = document.getElementById('modalTitle');
  const modalBody = document.getElementById('modalBody');
  const paperLink = document.getElementById('paperLink');
  const pdfLink = document.getElementById('pdfLink');
  const htmlLink = document.getElementById('htmlLink');
  
  // 重置模态框的滚动位置
  modalBody.scrollTop = 0;
  
  // 高亮标题中的关键词
  const highlightedTitle = activeKeywords.length > 0 
    ? highlightMatches(paper.title, activeKeywords, 'keyword-highlight') 
    : paper.title;
  
  // 在标题前添加索引号
  modalTitle.innerHTML = paperIndex ? `<span class="paper-index-badge">${paperIndex}</span> ${highlightedTitle}` : highlightedTitle;
  
  const abstractText = paper.details || '';
  
  const categoryDisplay = paper.allCategories ? 
    paper.allCategories.join(', ') : 
    paper.category;
  
  // 高亮作者中的匹配
  const highlightedAuthors = activeAuthors.length > 0 
    ? highlightMatches(paper.authors, activeAuthors, 'author-highlight') 
    : paper.authors;
  
  // 高亮摘要中的关键词
  const highlightedSummary = activeKeywords.length > 0 
    ? highlightMatches(paper.summary, activeKeywords, 'keyword-highlight') 
    : paper.summary;
  
  // 不再高亮详情中的关键词，只有在标题和摘要中高亮
  const highlightedAbstract = abstractText;
  
  // 高亮其他部分（如果存在且是摘要的一部分）
  const highlightedMotivation = paper.motivation && activeKeywords.length > 0 
    ? highlightMatches(paper.motivation, activeKeywords, 'keyword-highlight') 
    : paper.motivation;
  
  const highlightedMethod = paper.method && activeKeywords.length > 0 
    ? highlightMatches(paper.method, activeKeywords, 'keyword-highlight') 
    : paper.method;
  
  const highlightedResult = paper.result && activeKeywords.length > 0 
    ? highlightMatches(paper.result, activeKeywords, 'keyword-highlight') 
    : paper.result;
  
  const highlightedConclusion = paper.conclusion && activeKeywords.length > 0 
    ? highlightMatches(paper.conclusion, activeKeywords, 'keyword-highlight') 
    : paper.conclusion;
  
  // 判断是否需要显示高亮说明
  const showHighlightLegend = activeKeywords.length > 0 || activeAuthors.length > 0;
  
  // 添加匹配标记
  const matchedPaperClass = paper.isMatched ? 'matched-paper-details' : '';
  
  const modalContent = `
    <div class="paper-details ${matchedPaperClass}">
      <p><strong>Authors: </strong>${highlightedAuthors}</p>
      <p><strong>Categories: </strong>${categoryDisplay}</p>
      <p><strong>Date: </strong>${formatDate(paper.date)}</p>
      
      
      <h3>TL;DR</h3>
      <p>${highlightedSummary}</p>
      
      <div class="paper-sections">
        ${paper.motivation ? `<div class="paper-section"><h4>Motivation</h4><p>${highlightedMotivation}</p></div>` : ''}
        ${paper.method ? `<div class="paper-section"><h4>Method</h4><p>${highlightedMethod}</p></div>` : ''}
        ${paper.result ? `<div class="paper-section"><h4>Result</h4><p>${highlightedResult}</p></div>` : ''}
        ${paper.conclusion ? `<div class="paper-section"><h4>Conclusion</h4><p>${highlightedConclusion}</p></div>` : ''}
      </div>
      
      ${highlightedAbstract ? `<h3>Abstract</h3><p class="original-abstract">${highlightedAbstract}</p>` : ''}
      
      <div class="pdf-preview-section">
        <div class="pdf-header">
          <h3>PDF Preview</h3>
          <button class="pdf-expand-btn" onclick="togglePdfSize(this)">
            <svg class="expand-icon" viewBox="0 0 24 24" width="24" height="24">
              <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
            </svg>
            <svg class="collapse-icon" viewBox="0 0 24 24" width="24" height="24" style="display: none;">
              <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/>
            </svg>
          </button>
        </div>
        <div class="pdf-container">
          <iframe src="${paper.url.replace('abs', 'pdf')}" width="100%" height="800px" frameborder="0"></iframe>
        </div>
      </div>
    </div>
  `;
  
  // Update modal content
  document.getElementById('modalBody').innerHTML = modalContent;
  document.getElementById('paperLink').href = paper.url;
  document.getElementById('pdfLink').href = paper.url.replace('abs', 'pdf');
  document.getElementById('htmlLink').href = paper.url.replace('abs', 'html');
  // 提示词来自：https://papers.cool/
  prompt = `请你阅读这篇文章${paper.url.replace('abs', 'pdf')},总结一下这篇文章解决的问题、相关工作、研究方法、做了什么实验及其结果、结论，最后整体总结一下这篇文章的内容`
  document.getElementById('kimiChatLink').href = `https://www.kimi.com/_prefill_chat?prefill_prompt=${prompt}&system_prompt=你是一个学术助手，后面的对话将围绕着以下论文内容进行，已经通过链接给出了论文的PDF和论文已有的FAQ。用户将继续向你咨询论文的相关问题，请你作出专业的回答，不要出现第一人称，当涉及到分点回答时，鼓励你以markdown格式输出。&send_immediately=true&force_search=false`;
  
  // 更新论文位置信息
  const paperPosition = document.getElementById('paperPosition');
  if (paperPosition && currentFilteredPapers.length > 0) {
    paperPosition.textContent = `${currentPaperIndex + 1} / ${currentFilteredPapers.length}`;
  }
  
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  const modal = document.getElementById('paperModal');
  const modalBody = document.getElementById('modalBody');
  
  // 重置模态框的滚动位置
  modalBody.scrollTop = 0;
  
  modal.classList.remove('active');
  document.body.style.overflow = '';
}

// 导航到上一篇论文
function navigateToPreviousPaper() {
  if (currentFilteredPapers.length === 0) return;
  
  currentPaperIndex = currentPaperIndex > 0 ? currentPaperIndex - 1 : currentFilteredPapers.length - 1;
  const paper = currentFilteredPapers[currentPaperIndex];
  showPaperDetails(paper, currentPaperIndex + 1);
}

// 导航到下一篇论文
function navigateToNextPaper() {
  if (currentFilteredPapers.length === 0) return;
  
  currentPaperIndex = currentPaperIndex < currentFilteredPapers.length - 1 ? currentPaperIndex + 1 : 0;
  const paper = currentFilteredPapers[currentPaperIndex];
  showPaperDetails(paper, currentPaperIndex + 1);
}

// 显示随机论文
function showRandomPaper() {
  // 检查是否有可用的论文
  if (currentFilteredPapers.length === 0) {
    console.log('No papers available to show random paper');
    return;
  }
  
  // 生成随机索引
  const randomIndex = Math.floor(Math.random() * currentFilteredPapers.length);
  const randomPaper = currentFilteredPapers[randomIndex];
  
  // 更新当前论文索引
  currentPaperIndex = randomIndex;
  
  // 显示随机论文
  showPaperDetails(randomPaper, currentPaperIndex + 1);
  
  // 显示随机论文指示器
  showRandomPaperIndicator();
  
  console.log(`Showing random paper: ${randomIndex + 1}/${currentFilteredPapers.length}`);
}

// 显示随机论文指示器
function showRandomPaperIndicator() {
  // 移除已存在的指示器
  const existingIndicator = document.querySelector('.random-paper-indicator');
  if (existingIndicator) {
    existingIndicator.remove();
  }
  
  // 创建新的指示器
  const indicator = document.createElement('div');
  indicator.className = 'random-paper-indicator';
  indicator.textContent = 'Random Paper';
  
  // 添加到页面
  document.body.appendChild(indicator);
  
  // 3秒后自动移除
  setTimeout(() => {
    if (indicator && indicator.parentNode) {
      indicator.remove();
    }
  }, 3000);
}

function toggleDatePicker() {
  const datePicker = document.getElementById('datePickerModal');
  datePicker.classList.toggle('active');
  
  if (datePicker.classList.contains('active')) {
    document.body.style.overflow = 'hidden';
    
    // 重新初始化日期选择器以确保它反映最新的可用日期
    if (flatpickrInstance) {
      flatpickrInstance.setDate(currentDate, false);
    }
  } else {
    document.body.style.overflow = '';
  }
}

function toggleView() {
  currentView = currentView === 'grid' ? 'list' : 'grid';
  document.getElementById('paperContainer').classList.toggle('list-view', currentView === 'list');
}

function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric'
  });
}

async function loadPapersByDateRange(startDate, endDate) {
  // 获取日期范围内的所有有效日期
  const validDatesInRange = availableDates.filter(date => {
    return date >= startDate && date <= endDate;
  });
  
  if (validDatesInRange.length === 0) {
    alert('No available papers in the selected date range.');
    return;
  }
  
  currentDate = `${startDate} to ${endDate}`;
  document.getElementById('currentDate').textContent = `${formatDate(startDate)} - ${formatDate(endDate)}`;
  
  // 不再重置激活的关键词和作者
  // 而是保持当前选择状态
  
  const container = document.getElementById('paperContainer');
  container.innerHTML = `
    <div class="loading-container">
      <div class="loading-spinner"></div>
      <p>Loading papers from ${formatDate(startDate)} to ${formatDate(endDate)}...</p>
    </div>
  `;
  
  try {
    // 加载所有日期的论文数据
    const allPaperData = {};
    
    for (const date of validDatesInRange) {
      const selectedLanguage = selectLanguageForDate(date);
      const response = await fetch(`data/${date}_AI_enhanced_${selectedLanguage}.jsonl`);
      const text = await response.text();
      const dataPapers = parseJsonlData(text, date);
      
      // 合并数据
      Object.keys(dataPapers).forEach(category => {
        if (!allPaperData[category]) {
          allPaperData[category] = [];
        }
        allPaperData[category] = allPaperData[category].concat(dataPapers[category]);
      });
    }
    
    paperData = allPaperData;
    
    const categories = getAllCategories(paperData);
    
    renderCategoryFilter(categories);
    
    renderPapers();
  } catch (error) {
    console.error('加载论文数据失败:', error);
    container.innerHTML = `
      <div class="loading-container">
        <p>Loading data fails. Please retry.</p>
        <p>Error messages: ${error.message}</p>
      </div>
    `;
  }
}

// 清除所有激活的关键词
function clearAllKeywords() {
  activeKeywords = [];
  renderKeywordTags();
  // 重新渲染论文列表，移除关键词匹配的高亮和优先排序
  renderPapers();
}

// 清除所有作者过滤
function clearAllAuthors() {
  activeAuthors = [];
  renderAuthorTags();
  // 重新渲染论文列表，移除作者匹配的高亮和优先排序
  renderPapers();
}

// 切换PDF预览器大小
function togglePdfSize(button) {
  const pdfContainer = button.closest('.pdf-preview-section').querySelector('.pdf-container');
  const iframe = pdfContainer.querySelector('iframe');
  const expandIcon = button.querySelector('.expand-icon');
  const collapseIcon = button.querySelector('.collapse-icon');
  
  if (pdfContainer.classList.contains('expanded')) {
    // 恢复正常大小
    pdfContainer.classList.remove('expanded');
    iframe.style.height = '800px';
    expandIcon.style.display = 'block';
    collapseIcon.style.display = 'none';
    
    // 移除遮罩层
    const overlay = document.querySelector('.pdf-overlay');
    if (overlay) {
      overlay.remove();
    }
  } else {
    // 放大显示
    pdfContainer.classList.add('expanded');
    iframe.style.height = '90vh';
    expandIcon.style.display = 'none';
    collapseIcon.style.display = 'block';
    
    // 添加遮罩层
    const overlay = document.createElement('div');
    overlay.className = 'pdf-overlay';
    document.body.appendChild(overlay);
    
    // 点击遮罩层时收起PDF
    overlay.addEventListener('click', () => {
      togglePdfSize(button);
    });
  }
}