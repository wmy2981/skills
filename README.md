# wmy-skills

Agent 技能集合

## 技能列表

| 技能 | 说明 |
|------|------|
| `calendar-api/` | 万年历查询（农历、干支、节气、宜忌等） |
| `deepseek_balance/` | DeepSeek 开放平台余额查询 |
| `domain-query/` | 域名 ICP 备案 + WHOIS + 微信防红查询 |
| `enterprise-info/` | 企业工商信息查询 |
| `freshrss/` | FreshRSS RSS 阅读器管理 |
| `gaokao-english-answer-parser/` | 高考结构英语试卷答案提取 |
| `gotify/` | Gotify 推送通知管理 |
| `linkgo/` | LinkGo v3 导航页管理 |
| `mimo-tts/` | MiMo-V2.5-TTS 语音合成 |
| `s3/` | S3 兼容对象存储操作 |
| `speech-recognition/` | 阿里云百炼 Fun-ASR 语音识别 |
| `wake-on-lan/` | 远程唤醒局域网计算机 |
| `zurl/` | Zurl 短链接服务管理 |

## 使用方式

每个技能是一个独立的 `SKILL.md` + 可选 `scripts/` 目录：

```
skill-name/
├── SKILL.md       # 技能说明与 Agent 使用指南
├── scripts/       # 工具脚本（可选）
│   ├── .env       # 环境变量模板
│   └── *.py
└── references/    # 参考文档（可选）
```

### 环境变量

带 `scripts/` 的 skill 在 `scripts/.env` 中提供了环境变量模板。脚本会在启动时自动通过 `python-dotenv` 加载该文件。复制模板并填入实际值即可：
