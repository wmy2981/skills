---
name: mimo-tts
description: >-
  Speech synthesis using MiMo-V2.5-TTS models. Supports preset voice synthesis,
  text-to-voice design, voice cloning, natural language style control, and
  streaming output. Trigger whenever the user wants to generate speech audio
  from text, especially with Chinese voices and style control. Requires
  MIMO_APIKEY environment variable.
metadata:
  skill_version: "1.0.0"
---

# MiMo-V2.5-TTS Speech Synthesis

Calls the speech synthesis model via OpenAI-compatible API (`/v1/chat/completions`).

## Execution Rule

Run the user's requested command directly without pre-checking dependencies, environment variables, or configuration. If something is wrong, the script will fail with a clear error — check and fix only then.

## Requirements

- Environment variable `MIMO_APIKEY` must be set
- Streaming output: `pip install numpy soundfile`

## API Basics

- **Base URL**: `https://api.xiaomimimo.com/v1`
- **Auth**: HTTP Header `api-key`
- **Endpoint**: `/v1/chat/completions` (OpenAI-compatible)
- **Model & Feature Mapping**:

| Model | Feature | Singing | Voice Design | Voice Clone |
|-------|---------|:-------:|:------------:|:-----------:|
| `mimo-v2.5-tts` | Preset voice synthesis | ✅ | ❌ | ❌ |
| `mimo-v2.5-tts-voicedesign` | Text-to-voice design | ❌ | ✅ | ❌ |
| `mimo-v2.5-tts-voiceclone` | Voice cloning | ❌ | ❌ | ✅ |

## ⚠️ Text Input: Use File Redirection

**All text content (synthesis text, voice descriptions, style prompts) MUST be written to a txt file first and passed via `$(cat)`.**

```bash
# Write text to file first
echo "Text to synthesize" > tts_text.txt
python scripts/tts.py synthesize "$(cat tts_text.txt)" --voice Bingtang
```

---

# Style Control Guide

MiMo-V2.5-TTS offers two complementary style control methods that can be used together.

## 1. Natural Language Control (Recommended)

Place a style description in the `user message`. Describe the desired style in one sentence.

### Simple Examples

```
Speak in a bright, uplifting tone as if reporting good news to a boss, slightly fast pace, with excitement and pride that can't be contained, voice bright and energetic.
```

```
Use a bright, lively teenage voice with the smugness of a successful prank, fast pace with light articulation.
```

### Director Mode (Advanced)

Write like directing an actor, covering **character, scene, and direction**.

```
[Character] The current head of a century-old distinguished family. Has lived in seclusion for years, with a strong sense of class alienation from others.
[Scene] In the shadow of the ancestral hall, watching the man who broke through security to find her.
[Direction] Cold, languid yet commanding low alto. Extremely slow speech, each word as if rolled on the tongue before release. Long silences between sentences. Heavy, solid voice with slight breathiness at tail ends.
```

### Usage

```bash
# Natural language style → --user-prompt parameter
python scripts/tts.py synthesize "$(cat text.txt)" --voice Bingtang --user-prompt "$(cat style.txt)"
```

## 2. Audio Tag Control (Fine-Grained)

Tags go directly in the `assistant content` (the synthesis text).

### Style Tags (at text start)

Add `(style)` at the beginning of the text to set overall style.

**Format**: `(style1 style2)text to synthesize`

| Type | Options |
|------|---------|
| Basic Emotion | 开心/悲伤/愤怒/恐惧/惊讶/兴奋/委屈/平静/冷漠 |
| Compound Emotion | 怅然/欣慰/无奈/愧疚/释然/嫉妒/厌倦/忐忑/动情 |
| Overall Tone | 温柔/高冷/活泼/严肃/慵懒/俏皮/深沉/干练/凌厉 |
| Voice Character | 磁性/醇厚/清亮/空灵/稚嫩/苍老/甜美/沙哑/醇雅 |
| Persona | 夹子音/御姐音/正太音/大叔音/台湾腔 |
| Dialect | 东北话/四川话/河南话/粤语 |
| Character Roleplay | 孙悟空/林黛玉 |
| Singing | 唱歌/sing/singing (must be at the very start) |

**Examples:**
```
(怅然)这么多年过去了，再走过那条街，心里一下子空了一块。
(慵懒)再让我睡五分钟……就五分钟，真的。
(磁性)夜已经深了，我是今晚陪你的人，欢迎收听《午夜电台》。
(东北话)哎呀妈呀，这天儿也忒冷了吧！
(粤语)呢个真係好正啊！食过一次就唔会忘记！
(singing)原谅我这一生不羁放纵爱自由
```

### Audio Tags (insert anywhere in text)

Insert `[tag]` in the text for fine-grained control.

| Type | Options |
|------|---------|
| Pace & Rhythm | 吸气/深呼吸/叹气/长叹一口气/喘息/屏息 |
| Emotional State | 紧张/害怕/激动/疲惫/委屈/撒娇/心虚/震惊/不耐烦 |
| Voice Features | 颤抖/声音颤抖/变调/破音/鼻音/气声/沙哑 |
| Laughing & Crying | 笑/轻笑/大笑/冷笑/抽泣/呜咽/哽咽/嚎啕大哭 |

**Examples:**
```
（紧张，深呼吸）呼……冷静，冷静。不就是一个面试吗……（语速加快）自我介绍已经背了五十遍了。
（极其疲惫，有气无力）师傅……到地方了叫我一声……（长叹一口气）我先眯一会儿。
（提高音量喊话）大姐！这鱼新鲜着呢！早上刚捞上来的！
```

---

# Voice Design Guide

## How to Write a Good Voice Description

When using `mimo-v2.5-tts-voicedesign`, the `user message` text IS the voice design description. The more vivid and specific, the better.

### Key Dimensions

| Dimension | Example |
|-----------|---------|
| Gender & Age | "young woman in her mid-20s"、"五十多岁的中年男性" |
| Timbre / Texture | "deep and gravelly"、"丝滑醇厚、带着磁性" |
| Emotion / Tone | "warm and confident"、"温柔但带着一丝疲惫" |
| Pace / Rhythm | "slow and deliberate"、"语速极快，像连珠炮" |

### Additional Dimensions for Richness

- **Character / Persona**: narrator, podcast host, 评书先生, 深夜电台DJ
- **Speaking Style**: casual and colloquial, 一本正经, 压低嗓音像在密谋
- **Scene Description**: narrating a nature documentary, 在给投资人路演
- **Era Reference**: 1940s film noir, 八十年代译制片配音

### Writing Styles

**Concise description:**
```
Heavy Russian accent, gruff middle-aged male, blunt and matter-of-fact.
```

**Professional description:**
```
一位年迈的老先生，说带北方口音的普通话，语速缓慢而沉稳，嗓音略带沙哑和沧桑感，仿佛一位饱经风霜的老爷爷在讲故事，充满岁月的智慧。
```

### Notes

1. **Length**: 1-4 sentences — core features matter more than exhaustiveness
2. **Avoid conflicts**: Don't request contradictory features (e.g. "child-like voice + CEO presence")
3. **Avoid DSP terms**: Don't mention reverb, echo, EQ, compression, etc.
4. **Avoid vague words**: Don't use "normal", "ordinary", etc.
5. **Chinese or English**: Use whichever expresses the idea most precisely
6. **Match text to voice**: The synthesized text in `assistant` should match the voice description

---

# Commands & Usage

## 1. Preset Voice Synthesis (synthesize)

```bash
python scripts/tts.py synthesize "$(cat text.txt)" --voice <voice_id> [--output <path>]
```

With natural language style control:
```bash
python scripts/tts.py synthesize "$(cat text.txt)" --voice Bingtang --user-prompt "$(cat style.txt)"
```

With audio tag control (tags in text.txt directly):
```bash
# text.txt content: (温柔)夜已经深了，欢迎收听我的节目。
python scripts/tts.py synthesize "$(cat text.txt)" --voice Bingtang
```

Singing mode (requires mimo-v2.5-tts model):
```bash
# text.txt content: (singing)原谅我这一生不羁放纵爱自由
python scripts/tts.py synthesize "$(cat text.txt)" --voice Bingtang
```

## 2. Voice Design from Text (design)

```bash
python scripts/tts.py design "$(cat voice_desc.txt)" --text "$(cat speech.txt)"
```

Without `--text`, auto-generates matching text:
```bash
python scripts/tts.py design "$(cat voice_desc.txt)"
```

## 3. Voice Cloning (clone)

```bash
python scripts/tts.py clone <sample.wav> "$(cat text.txt)"
```

With style control:
```bash
python scripts/tts.py clone <sample.wav> "$(cat text.txt)" --user-prompt "$(cat style.txt)"
```

## 4. Streaming Output

Add `--stream` to any synthesis command. Streaming requires `--format pcm16`:

```bash
python scripts/tts.py synthesize "$(cat text.txt)" --voice Bingtang --stream --format pcm16
python scripts/tts.py design "$(cat voice_desc.txt)" --text "$(cat speech.txt)" --stream --format pcm16
python scripts/tts.py clone sample.wav "$(cat text.txt)" --stream --format pcm16
```

## 5. List Available Voices

```bash
# Default JSON output
python scripts/tts.py voices

# Plain text output
python scripts/tts.py voices --format text

# Also available via the "tts" alias:
python scripts/tts.py tts "$(cat text.txt)" --voice Bingtang
```

## Preset Voice List

| Voice ID | Name | Language | Gender |
|----------|------|----------|--------|
| `mimo_default` | MiMo-Default | auto (zh-CN=Bingtang, else=Mia) | — |
| `冰糖` | Bingtang | Chinese | Female |
| `茉莉` | Moli | Chinese | Female |
| `苏打` | Soda | Chinese | Male |
| `白桦` | Birch | Chinese | Male |
| `Mia` | Mia | English | Female |
| `Chloe` | Chloe | English | Female |
| `Milo` | Milo | English | Male |
| `Dean` | Dean | English | Male |

## Output

- Audio saved to `~/.wmyskills/mimo-tts/outputs/` by default (use `--output` / `-o` to specify a custom path or directory)
- **Non-streaming**: JSON `{"status":"ok","path":"...","size_bytes":N}`
- **Streaming**: JSON `{"status":"ok","path":"...","samples":N}` (uses `samples` instead of `size_bytes`)
- **Error**: JSON `{"error": true, "status": 4XX, "message": "..."}`
- All commands output JSON

## Environment

- `MIMO_APIKEY` — API Key, required. The script loads it from `~/.wmyskills/.env` (shared across skills) or `scripts/.env` (takes priority) automatically. Use `scripts/.env.example` as the template — add the variable to `~/.wmyskills/.env`, never overwriting an existing file.
