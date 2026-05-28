# 🎓 成都理工大学校园信息助手

自动监控教务系统（走我平台 SimpleCDUT），推送到个人微信。

## 功能

- 📝 **考试安排监控** — 新考试出现时推送
- 📊 **成绩发布监控** — 有新成绩时立即推送
- 📅 **课表变动监控** — 课表变化时推送
- 📱 **微信推送** — 通过 PushPlus 推送到个人微信

## 架构

基于 Playwright 浏览器自动化，通过走我平台（cdutdev.zouwo.tech）抓取数据：
1. 设置 OpenId cookie 模拟微信小程序认证
2. Playwright 渲染 Blazor Server 页面
3. 从渲染后的 DOM 提取文本数据
4. 检测新增/变动，通过 PushPlus 推送

## 快速开始

### 1. 获取 OpenId

你的 OpenId 可以从微信小程序 Simple成理 中获取（通常在抓包工具中可以看到）。

### 2. 获取 PushPlus Token

1. 访问 [PushPlus](https://www.pushplus.plus/)
2. 微信扫码关注公众号
3. 进入「个人中心」→「开发设置」→ 复制 Token

### 3. 配置环境变量

**GitHub Actions（推荐）：**

| Secret 名称 | 说明 | 示例 |
|-------------|------|------|
| `OPEN_ID` | 走我平台 OpenId | `oS2DU4ti-mNtXGGoyNqwD6I70xF0` |
| `PUSHPLUS_TOKEN` | PushPlus Token | `abc123...` |

**本地测试：**

```bash
pip install -r requirements.txt
playwright install chromium

$env:OPEN_ID="你的OpenId"
$env:PUSHPLUS_TOKEN="你的token"

python main.py
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `main.py` | 主程序入口 |
| `auth.py` | 认证模块（OpenId / CAS） |
| `scraper.py` | Playwright 页面抓取模块 |
| `notifier.py` | PushPlus 推送 |
| `requirements.txt` | Python 依赖 |

## 免责声明

本项目仅供学习交流使用，请勿用于非法用途。使用本项目造成的一切后果由用户自行承担。
