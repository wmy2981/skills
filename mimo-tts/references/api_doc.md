# 语音合成 (https://www.mimo-v2.com/zh/docs/usage-guide/tts)

import { Callout } from 'fumadocs-ui/components/callout';

MiMo-V2.5-TTS 可以把文本转成自然语音。调用格式按小米 MiMo 官方文档走：使用 Chat Completions。

<Callout type="info">
  语音合成功能目前**限时免费**。
</Callout>

## API 端点

```http
POST https://api.mimo-v2.com/v1/chat/completions
```

## 调用规则

* 要合成的文本放在 `assistant` 消息里。
* `user` 消息可选，用来写语气、风格等要求。
* 输出音频格式和音色放在 `audio` 对象里。

## 示例

```python
import base64
from openai import OpenAI

client = OpenAI(
    api_key="your_mimo_api_key",
    base_url="https://api.mimo-v2.com/v1"
)

completion = client.chat.completions.create(
    model="mimo-v2.5-tts",
    messages=[
        {
            "role": "assistant",
            "content": "你好！欢迎使用 Mimo API 服务。很高兴为你提供服务。"
        }
    ],
    audio={
        "format": "wav",
        "voice": "mimo_default"
    }
)

audio_bytes = base64.b64decode(completion.choices[0].message.audio.data)
with open("output.wav", "wb") as f:
    f.write(audio_bytes)
```

## 参数说明

| 参数             | 类型     | 必填 | 说明                                                                         |
| -------------- | ------ | -- | -------------------------------------------------------------------------- |
| `model`        | string | 是  | 可用 `mimo-v2.5-tts`、`mimo-v2.5-tts-voicedesign`、`mimo-v2.5-tts-voiceclone`。 |
| `messages`     | array  | 是  | 要合成的文本放在 `assistant` 消息里。                                                  |
| `audio.format` | string | 否  | 输出格式，可用 `wav`、`mp3`、`pcm16`。                                               |
| `audio.voice`  | string | 否  | 内置音色 ID，默认 `mimo_default`。                                                 |

## 兼容说明

`/v1/audio/speech` 仍然兼容 OpenAI 语音客户端，但推荐使用官方的 `/v1/chat/completions` 格式。
