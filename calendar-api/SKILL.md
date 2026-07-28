---
name: calendar-api
description: >-
  Chinese calendar query tool — retrieves comprehensive traditional calendar
  information for any date, including lunar calendar, Heavenly Stems and Earthly
  Branches (干支), solar terms (节气), festivals, auspicious/inauspicious
  activities (宜忌), zodiac (生肖), constellation (星座), fetal god (胎神),
  Peng Zu's hundred taboos (彭祖百忌), 28 mansions (星宿), Buddhist/Taoist
  calendar, and more. Triggered whenever the user asks about the Chinese
  calendar: "what's the lunar date today", "today's 宜忌", "what solar term
  is it", "is today auspicious", "Chinese zodiac for this year",
  "constellation", "今天农历几号", "今天宜做什么", "黄历", "万年历",
  "今天什么节气". Trigger even for casual one-line questions.
---

# Chinese Calendar Query

Queries the [接口盒子 API](https://apihz.cn) (API ID: 278) to retrieve comprehensive traditional Chinese calendar (黄历) information for any date.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `JKHZ_ID` | 接口盒子 (apihz.cn) user ID |
| `JKHZ_KEY` | 接口盒子 API key |

The script loads these from `scripts/.env` automatically. See `scripts/.env.example` for the template.

## Requirements

```bash
pip install python-dotenv
```

## Usage

Script: `scripts/getzdday.py`

### Query today
```bash
python scripts/getzdday.py
```

### Query a specific date
```bash
python scripts/getzdday.py 2025-06-05
```

### Output raw JSON (debugging)
```bash
python scripts/getzdday.py 2025-06-05 --json
```

## Output Categories

The script organizes returned data into these categories:

| Category | Fields |
|----------|--------|
| 📆 Gregorian Calendar (公历) | Year, month, day, weekday, leap year |
| 🌙 Lunar Calendar (农历) | Lunar year, month, day |
| 🎊 Festivals (节日) | Solar festivals, lunar festivals |
| ⭐ Constellation & Zodiac (星座与生肖) | Constellation, Chinese zodiac, daily zodiac |
| 📜 Stems & Branches (干支) | Year/month/day Ganzhi, day Nayin |
| 🌿 Solar Terms & Phenology (节气与物候) | Solar term, description, Wuhou, Shujiu, Sanfu |
| ☯ Auspicious/Inauspicious (宜忌) | Yi (宜), Ji (忌), auspicious/inauspicious gods |
| 🧭 Directions (方位) | Xi (喜), Cai (财), Fu (福), Gui (贵) spirit directions |
| ⚠️ Clash & Sha (冲煞) | Xiangchong, Richtungschong, Tian Shen, Huang/Hei Dao |
| 🔢 Star & Spirit (值星与神煞) | Zhi Xing (12 value stars), 12 spirits, Liuyao, moon phase |
| 🌟 Mansions (星宿) | 28 mansions, animal, luck, 7 luminaries, 4 palaces, 4 symbols |
| 📖 Peng Zu & Fetal God (彭祖与胎神) | Peng Zu's hundred taboos, fetal god direction, Taisui |
| 📅 Buddhist/Taoist Calendar (佛道历) | Buddhist calendar, Taoist calendar, Islamic calendar |
| 📊 Other (其他) | Wuxing (5 elements), Julian day, 9 stars, season |

## Notes

- Defaults to today's date (Asia/Shanghai timezone)
- API year range: 1800 to next year
- Formatted output is suitable for direct display; `--json` for debugging
- The API may return different fields per date; the script dynamically displays all non-empty fields
- **Match the user's language.** The output language MUST match the language of the user's question. If the user asks in Chinese, output all category labels and descriptions in Chinese; if in English, output in English.
