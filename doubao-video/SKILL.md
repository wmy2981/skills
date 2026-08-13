---
name: doubao-video
description: >-
  Generate AI videos with Doubao (豆包) on doubao.com via Chrome automation. Trigger when the user asks
  用豆包生成视频 or similar wording.
metadata:
  skill_version: "1.0.0"
---

# Doubao Video Generation (Web)

Generate AI videos on the Doubao web app (doubao.com) using the chrome-devtools MCP. Two modes: text-to-video (prompt only) and image-to-video (reference image + motion prompt).

> **Read [guide](references/guide.md)** — the verified operating guide (last tested 2026-08-13) with exact snapshot texts, menu contents, the paid-tier matrix, and the complete MCP tool sequence for every step. This file is the condensed workflow; open the guide for precise selectors and verified details before operating the page, and consult it whenever a step needs specifics.

## Execution Rule

Run the user's request directly without pre-checking prerequisites; if an action fails, take a snapshot, diagnose, and fix. Do not ask for confirmation before each step.

## Requirements

- **chrome-devtools MCP** available. It runs in self-launch mode: the first browser tool call auto-launches a windowed Chrome with a dedicated persistent profile (doubao login persists across sessions).
- **Doubao account** logged in at doubao.com.
- **Free tier limits** (verified 2026-08-13): models Seedance 2.0 Mini / 2.0 Fast, durations ≤10s, all 7 aspect ratios, image upload — free. Models Seedance 2.0 / 2.5 and durations >10s trigger a "订阅豆包专业版" dialog. For paid requests, inform the user of the subscription requirement and the free fallback instead of proceeding.

## Workflow

1. **Navigate**: `navigate_page` → `https://www.doubao.com/chat`.
2. **Enter the video panel**: `take_snapshot`, find the quick toolbar below the input box, click the **「视频生成」** button. If the window is narrow, the toolbar collapses to just 「快速」/「更多」 — click **「更多」** first to expand the menu, then 「视频生成」.
3. **Confirm the panel** via snapshot: button `模型 Seedance 2.0 Mini`, button `自动 · 10s`, and a multi-line textbox appear above the input area.
4. **Configure** (optional, click-based, button labels update live — verify each with a snapshot):
   - *Model*: click `模型 <current>` → menu with 4 Seedance models → click the target. Mini/Fast apply instantly; 2.0/2.5 open a subscription dialog — close it ("返回") and fall back.
   - *Aspect ratio & duration*: click `自动 · 10s` → menu with 7 ratio buttons + a duration slider. Ratios apply instantly; durations >10s are paid (the slider will visually move but never applies for free users).
   - *Reference image* (image-to-video): the upload button is a **text-less button directly above the 「视频生成」 title** (visible in the snapshot as a nameless button; use its uid). Upload directly with `upload_file` → that button uid → local image path — do NOT click it via `evaluate_script` (that opens a native file-picker window). Remove an uploaded image via its delete button (`evaluate_script` clicking the `.delete-btn-*` element is safe). Beware: the nameless button on the **input-box row is the SEND button** — clicking it submits immediately. Details in `references/guide.md`.
5. **Prompt & submit**: fill the textbox with the video description (subject + action + scene + style + quality, e.g. "一只戴宇航员头盔的橘猫在月球表面漫步，远处是蔚蓝的地球，阳光洒落，3D 动画电影感镜头，高清画质"), then `press_key` Enter. A new conversation is auto-created.
6. **Wait for the async result**: the reply confirms "视频生成已提交…预计等待 10 分钟". Generation is a queue; poll the conversation (snapshot/wait_for) until the video appears. Be patient — this is minutes, not seconds.
7. **Deliver**: tell the user the video is ready in the Doubao conversation (with the prompt summary, e.g. "橘猫月球漫步视频生成"), then download it locally following the Downloading section below.

## Downloading Generated Videos

The finished video renders inside a message card as an **xgplayer** player. There is no reliable page-level download button exposed to the accessibility tree, so download via the CDN direct link:

1. **Poll for the video element** — the xgplayer `<video>` may mount with significant delay after "你的视频生成好了。" appears (observed up to minutes; React renders cards lazily). Repeatedly run `evaluate_script` with `() => [...document.querySelectorAll('video')].map(v => v.currentSrc || v.src)` until the count matches the number of completed generations.
2. **Collect the CDN URLs** — `currentSrc` returns a signed douyin CDN direct link (e.g. `https://v26-default.douyin.com/.../video/tos/cn/...?l=...&rc=...`). The signature is tied to the login session and may expire — download promptly.
3. **Download with curl, referencing doubao.com** — the CDN rejects bare requests:
   ```bash
   curl -o "<target-dir>/<name>.mp4" -H "Referer: https://www.doubao.com/" "<video-src-url>"
   ```
   Save into the directory the user asked for (if none specified, use a temp dir — never the repo).
4. **Verify each file** — check the MP4 magic bytes `ftyp` (hex `66 74 79 70`) and report the size. E.g. via PowerShell: `[System.IO.File]::ReadAllBytes($f)[4..7]`.
5. **Report** — give the user the local file path(s); if a generation was blocked by content review ("生成内容中疑似包含侵权/违规内容，无法返回该内容…生成额度未扣除"), report that no video exists and the quota was not consumed.

## Failure Handling

- **Subscription dialog appears** (paid model or >10s): the user is on the free tier — close the dialog and use the free fallback (Mini/Fast, ≤10s). Report what happened.
- **Captcha** ("验证码" iframe, e.g. rmc.bytedance.com/verifycenter, "请选择所有符合描述的图片并拖拽到下方"): pause automation and ask the user to solve it manually in the browser. It typically doesn't reappear afterwards.
- **Toolbar collapsed**: don't guess — expand 「更多」 before looking for 「视频生成」.
- **Snapshot doesn't show expected controls**: the page UI may have changed (it's a live product). Adapt from the snapshot; the button texts in [guide](references/guide.md) are the verified baseline.

## References

- [guide](references/guide.md) — full verified operating guide: exact snapshot texts for every menu, the complete MCP tool sequences (model switch, ratio/duration, image upload, submit), paid-tier matrix, and captcha handling. Read it before operating the page the first time in a session, and consult it whenever a step needs precise selectors.
