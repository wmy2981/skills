# wmy-skills

Agent Skills Collection

### Npx Skills

[![Install with npx skills](https://img.shields.io/badge/Install%20with-npx%20skills-5B8DEF?logo=anthropic)](https://skills.sh/wmy2981/skills)

```bash
npx skills add wmy2981/skills --all
npx skills add wmy2981/skills -s <name> 
```

### Claude Code Plugin

This repo is also a Claude Code plugin marketplace — each skill installs as its own plugin:

```bash
# register the marketplace once
claude plugin marketplace add https://github.com/wmy2981/skills

# install a single skill plugin (repeatable)
claude plugin install skill-name@wmy-skills
```

## 技能列表 | Skills

| skill | Description | 说明 |
|------|-------------|------|
| `calendar-api/` | Chinese calendar query | 万年历查询 |
| `chinese-poetry-api/` | Chinese classical poetry REST API (Tang/Song/Yuan poems, search, authors) | 中国古诗词 REST API 查询（唐诗宋词、搜索、作者） |
| `deepseek-balance/` | DeepSeek Open Platform balance query | DeepSeek 开放平台余额查询 |
| `doubao-video/` | AI video generation on Doubao web via Chrome automation | 豆包网页版 AI 视频生成（Chrome 自动化） |
| `domain-query/` | Domain ICP filing, WHOIS & WeChat block check | 域名 ICP 备案 + WHOIS + 微信防红查询 |
| `enterprise-info/` | Chinese enterprise registration info lookup | 企业工商信息查询 |
| `epub-book-pipeline/` | EPUB book processing pipeline | EPUB 整本书处理流水线 |
| `freshrss/` | FreshRSS API | FreshRSS API |
| `fun-asr/` | Alibaba Cloud Fun-ASR speech recognition | 阿里云百炼 Fun-ASR 语音识别 |
| `gaozhong-english-answer-parser/` | Gaozhong English exam answer extraction | 高中英语试卷答案提取 |
| `gotify/` | Gotify push notification and management API | Gotify 推送通知和管理API |
| `img-recog/` | Image recognition via vision models | 图片识别（视觉模型） |
| `linkgo/` | LinkGo v3 navigation page management | LinkGo v3 导航页管理 |
| `mimo-tts/` | MiMo-V2.5-TTS speech synthesis | MiMo-V2.5-TTS 语音合成 |
| `personal-siyuan-standards/` | Personal SiYuan note standards — placement routing & tagging conventions | 个人思源笔记规范（位置映射与标签约定） |
| `scanned-pdf-to-epub/` | Scanned PDF to readable EPUB conversion (OCR by Claude vision) | 扫描版 PDF 转可读 EPUB（Claude 视觉识别） |
| `send-email/` | SMTP email sending | SMTP 邮件发送 |
| `wake-on-lan/` | Wake-on-LAN remote wake-up | 远程唤醒局域网计算机 |
| `zurl/` | Zurl short link service management | Zurl 短链接服务管理 |
