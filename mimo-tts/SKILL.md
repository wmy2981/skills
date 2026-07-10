---
name: mimo-tts
description: 使用 MiMo-V2.5-TTS 系列模型进行语音合成，支持预置音色合成、文本设计音色、音色复刻、自然语言风格控制、流式输出。需要 MIMO_APIKEY 环境变量。
---

# MiMo-V2.5-TTS 语音合成

通过 OpenAI-compatible API (`/v1/chat/completions`) 调用语音合成模型。

## 前提

- 环境变量 `MIMO_APIKEY` 已设置
- 流式输出需要：`pip install numpy soundfile`

## API 基础

- **Base URL**: `https://api.xiaomimimo.com/v1`
- **认证**: HTTP Header `api-key`
- **接口**: `/v1/chat/completions` (OpenAI 兼容)
- **模型与功能对应关系**：

| 模型 | 功能 | 支持唱歌 | 支持音色设计 | 支持音色复刻 |
|------|------|:--------:|:----------:|:----------:|
| `mimo-v2.5-tts` | 预置音色合成 | ✅ | ❌ | ❌ |
| `mimo-v2.5-tts-voicedesign` | 文本设计音色 | ❌ | ✅ | ❌ |
| `mimo-v2.5-tts-voiceclone` | 音色复刻 | ❌ | ❌ | ✅ |

## ⚠️ 提示词传参规范（硬性规则）

**所有提示词（文本内容、音色描述、风格指令等）必须先写入 txt 文件，再用 `$(cat)` 传参。**

```bash
write_file("tts_text.txt", "要合成的文本")
python3 scripts/tts.py synthesize "$(cat tts_text.txt)" --voice 冰糖
```

---

# 风格控制指南

MiMo-V2.5-TTS 提供两种风格控制方式，可叠加使用。

## 一、自然语言控制（推荐）

放在 `user message` 中。一句话描述想要的风格。

### 简单指令示例

```
用轻快上扬的语调向领导报喜，语速稍快，带着查到成绩后压抑不住的激动与骄傲，声音明亮有活力。
```

```
用明亮活泼的青少年嗓音，带着恶作剧得逞后的得意与戏谑，语速偏快且咬字轻巧。
```

### 导演模式（高级）

像给演员写剧本，从**角色、场景、指导**三个维度刻画。

```
【角色】百年门阀岑家的现任大当家。常年深居简出，对人有着极强的阶级疏离感。
【场景】在祠堂的阴影里，看着那个不顾一切冲破保安防线来找她的男人。
【指导】冰冷、慵懒却极具威压的低音御姐。语速极慢，每个字都像是在舌尖滚过才吐出来。句与句之间留下极长的空白。实音重且硬，在某些尾音处加入轻微的气音收束。
```

### 使用方法

```bash
# 自然语言风格指令 → --user-prompt 参数
python3 scripts/tts.py synthesize "$(cat text.txt)" --voice 冰糖 --user-prompt "$(cat style.txt)"
```

## 二、音频标签控制（精细控制）

放在 `assistant content` 中，与合成文本在一起。

### 风格标签（文本开头）

在文本开头添加 `(风格)` 标签指定整体风格。

**格式**：`(风格1 风格2)待合成内容`

**风格标签列表：**

| 类型 | 可选值 |
|------|--------|
| 基础情绪 | 开心/悲伤/愤怒/恐惧/惊讶/兴奋/委屈/平静/冷漠 |
| 复合情绪 | 怅然/欣慰/无奈/愧疚/释然/嫉妒/厌倦/忐忑/动情 |
| 整体语调 | 温柔/高冷/活泼/严肃/慵懒/俏皮/深沉/干练/凌厉 |
| 音色定位 | 磁性/醇厚/清亮/空灵/稚嫩/苍老/甜美/沙哑/醇雅 |
| 人设腔调 | 夹子音/御姐音/正太音/大叔音/台湾腔 |
| 方言 | 东北话/四川话/河南话/粤语 |
| 角色扮演 | 孙悟空/林黛玉 |
| 唱歌 | 唱歌/sing/singing（必须在文本最开头） |

**示例：**
```
(怅然)这么多年过去了，再走过那条街，心里一下子空了一块。
(慵懒)再让我睡五分钟……就五分钟，真的。
(磁性)夜已经深了，我是今晚陪你的人，欢迎收听《午夜电台》。
(东北话)哎呀妈呀，这天儿也忒冷了吧！
(粤语)呢个真係好正啊！食过一次就唔会忘记！
(唱歌)原谅我这一生不羁放纵爱自由
```

### 音频标签（文本中任意位置插入）

在文本中插入 `[标签]` 进行细粒度控制。

**音频标签列表：**

| 类型 | 可选值 |
|------|--------|
| 语速与节奏 | 吸气/深呼吸/叹气/长叹一口气/喘息/屏息 |
| 情绪状态 | 紧张/害怕/激动/疲惫/委屈/撒娇/心虚/震惊/不耐烦 |
| 语音特征 | 颤抖/声音颤抖/变调/破音/鼻音/气声/沙哑 |
| 哭笑表达 | 笑/轻笑/大笑/冷笑/抽泣/呜咽/哽咽/嚎啕大哭 |

**示例：**
```
（紧张，深呼吸）呼……冷静，冷静。不就是一个面试吗……（语速加快）自我介绍已经背了五十遍了。
（极其疲惫，有气无力）师傅……到地方了叫我一声……（长叹一口气）我先眯一会儿。
（提高音量喊话）大姐！这鱼新鲜着呢！早上刚捞上来的！
```

---

# 文本设计音色指南

## 如何写好音色描述

使用 `mimo-v2.5-tts-voicedesign` 模型时，`user message` 中的文本就是音色设计描述。描述越具体越生动，效果越好。

### 关键维度

| 维度 | 示例 |
|------|------|
| 性别与年龄 | "young woman in her mid-20s"、"五十多岁的中年男性" |
| 音色/质感 | "deep and gravelly"、"丝滑醇厚、带着磁性" |
| 情绪/语气 | "warm and confident"、"温柔但带着一丝疲惫" |
| 语速/节奏 | "slow and deliberate"、"语速极快，像连珠炮" |

### 可增加丰富度的维度

- **角色/人设**：narrator, podcast host, 评书先生, 深夜电台DJ
- **说话风格**：casual and colloquial, 一本正经, 压低嗓音像在密谋
- **场景描写**：narrating a nature documentary, 在给投资人路演
- **年代参照**：1940s film noir, 八十年代译制片配音

### 写法风格

**简洁描述型：**
```
Heavy Russian accent, gruff middle-aged male, blunt and matter-of-fact.
```

**专业描述型：**
```
一位年迈的老先生，说带北方口音的普通话，语速缓慢而沉稳，嗓音略带沙哑和沧桑感，仿佛一位饱经风霜的老爷爷在讲故事，充满岁月的智慧。
```

### 注意事项

1. **长度**：1-4 句即可，核心特征比堆砌维度更重要
2. **避免冲突**：不要同时要求矛盾的特征（如"稚嫩的童声 + CEO气场"）
3. **避免音质效果词**：不要写混响、回声、EQ、压缩等后期处理描述
4. **避免模糊词**：不要用"普通的""正常的"等缺乏具体指向的描述
5. **中英文均可**：选择最能精确表达的语言
6. **合成文本要贴合音色**：`assistant` 消息中的合成文本应与音色描述相匹配

---

# 功能与用法

## 1. 预置音色合成 (synthesize)

```bash
python3 scripts/tts.py synthesize "$(cat text.txt)" --voice <音色ID> [--output <path>]
```

带自然语言风格控制：
```bash
python3 scripts/tts.py synthesize "$(cat text.txt)" --voice 茉莉 --user-prompt "$(cat style.txt)"
```

带音频标签控制（风格标签直接写在 text.txt 中）：
```bash
# text.txt 内容：(温柔)夜已经深了，欢迎收听我的节目。
python3 scripts/tts.py synthesize "$(cat text.txt)" --voice 冰糖
```

唱歌模式（需用 mimo-v2.5-tts 模型）：
```bash
# text.txt 内容：(唱歌)原谅我这一生不羁放纵爱自由
python3 scripts/tts.py synthesize "$(cat text.txt)" --voice 冰糖
```

## 2. 文本设计音色 (design)

```bash
python3 scripts/tts.py design "$(cat voice_desc.txt)" --text "$(cat speech.txt)"
```

不传 `--text` 时自动润色生成匹配文本：
```bash
python3 scripts/tts.py design "$(cat voice_desc.txt)"
```

## 3. 音色复刻 (clone)

```bash
python3 scripts/tts.py clone <样本音频.wav> "$(cat text.txt)"
```

带风格控制：
```bash
python3 scripts/tts.py clone <样本音频.wav> "$(cat text.txt)" --user-prompt "$(cat style.txt)"
```

## 4. 流式输出

所有合成命令加 `--stream` 参数（格式需指定为 `pcm16`）。

## 5. 查询音色

```bash
python3 scripts/tts.py voices
```

## 预置音色列表

| Voice ID | 名称 | 语言 | 性别 |
|----------|------|------|------|
| `mimo_default` | MiMo-默认 | 中国集群=冰糖，其他=Mia | — |
| `冰糖` | 冰糖 | 中文 | 女 |
| `茉莉` | 茉莉 | 中文 | 女 |
| `苏打` | 苏打 | 中文 | 男 |
| `白桦` | 白桦 | 中文 | 男 |
| `Mia` | Mia | 英文 | 女 |
| `Chloe` | Chloe | 英文 | 女 |
| `Milo` | Milo | 英文 | 男 |
| `Dean` | Dean | 英文 | 男 |

## 输出

- 音频默认输出到当前工作目录（可用 `--output` 或 `-o` 指定路径）
- 命令输出 JSON：`{"status":"ok","path":"...","size_bytes":N}`

## 环境变量

- `MIMO_APIKEY` — API Key，必填。可配置 `scripts/.env` 模板文件，脚本会自动加载。

## 计费

当前限时免费。用户不问价格不用主动提及。
