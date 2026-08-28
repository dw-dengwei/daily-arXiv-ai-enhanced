#!/bin/bash

# 参数1: URL，参数2: 超时时间（毫秒），默认60000（1分钟）
url=${1:-"https://dw-dengwei.github.io/daily-arXiv-ai-enhanced/?category=cs.CV"}
timeout=${2:-60000}

# 检测 node 是否安装
if ! command -v node &> /dev/null; then
    echo "错误: Node.js 未安装"
    echo "请先安装 Node.js: https://nodejs.org/"
    exit 1
fi

# 检测 puppeteer 是否安装（更稳一点的写法）
if ! node -e "require('puppeteer')" &> /dev/null; then
    echo "警告: puppeteer 未安装"
    echo "正在安装 puppeteer..."
    npm install puppeteer
    if [ $? -ne 0 ]; then
        echo "错误: puppeteer 安装失败"
        exit 1
    fi
    echo "puppeteer 安装成功"
fi

# 执行抓取
node -e "
const puppeteer = require('puppeteer');

(async () => {
  try {
    const browser = await puppeteer.launch({
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu'
      ]
    });

    const page = await browser.newPage();

    await page.goto('$url', {
      waitUntil: 'networkidle0',
      timeout: $timeout
    });

    const content = await page.evaluate(() => document.body.innerText);

    console.log(content);

    await browser.close();
  } catch (err) {
    console.error('❌ Puppeteer 执行失败:');
    console.error(err);
    process.exit(1);
  }
})();
"