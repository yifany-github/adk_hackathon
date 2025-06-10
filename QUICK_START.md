# NHL Audio Agent - 快速开始

## 🎯 概述
NHL Audio Agent 是基于 Google ADK 的音频代理，使用 Gemini TTS 将冰球解说文本转换为高质量语音。

## 🚀 快速开始

### 1. 配置 Gemini API Key
```bash
python setup_api_key.py
```
按照提示输入您的 Gemini API Key（从 [Google AI Studio](https://aistudio.google.com/app/apikey) 获取）。

### 2. 测试语音生成
```bash
export GEMINI_API_KEY=your_api_key_here
python test_real_tts.py
```

## 📁 核心文件

- **setup_api_key.py** - API Key 配置工具
- **test_real_tts.py** - 语音生成测试脚本
- **src/agents/audio_agent/** - 音频代理核心代码

## 🎙️ 支持的语音风格

- **enthusiastic** - 兴奋解说（使用 Puck 声音）
- **dramatic** - 戏剧性解说（使用 Kore 声音）
- **calm** - 平静解说（使用 Aoede 声音）

## 🎵 输出

- 音频文件保存在 `audio_output/` 目录
- 格式：WAV（24kHz，16位，单声道）
- 文件名：`nhl_{风格}_{音频ID}_{时间戳}.wav`

## 🔧 技术细节

- 使用 Gemini 2.5 Flash TTS 模型
- 符合 Google ADK 标准
- 支持 WebSocket 音频流
- 实时语音生成和广播

## 🏒 NHL 解说示例

```python
from src.agents.audio_agent.tool import text_to_speech

# 进球解说
result = await text_to_speech(
    tool_context=None,
    text="Connor McDavid scores an amazing goal!",
    voice_style="enthusiastic",
    language="en-US"
)
```

## ✅ 验证工作状态

运行测试后，您应该看到：
- ✅ API Key 验证通过
- ✅ 3个不同风格的音频生成成功
- 🔊 音频自动播放
- 📁 文件保存到 audio_output/ 目录

现在您的 NHL Audio Agent 已准备就绪！🏆 