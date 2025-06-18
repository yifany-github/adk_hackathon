# NHL Audio Agent 使用说明

## 概述
NHL Audio Agent 可以生成高质量的NHL解说音频，使用Google Gemini TTS进行语音合成。

## 快速使用

### 1. 生成随机NHL解说音频
```bash
python generate_audio.py
```

### 2. 使用Audio Agent (编程方式)
```python
from src.agents.audio_agent.tool import text_to_speech

# 生成音频
result = await text_to_speech(
    text="McDavid scores! What a goal!",
    voice_style="enthusiastic",  # enthusiastic, dramatic, calm
    language="en-US"
)

# 音频自动保存到 audio_output/ 目录
print(f"Audio saved to: {result['saved_file']}")
```

### 3. 通过Audio Agent (ADK方式)
```python
from src.agents.audio_agent.audio_agent import create_audio_agent_for_game

agent = create_audio_agent_for_game("2024030412")
# 使用ADK Runner运行agent...
```

## 文件保存

### 自动保存位置
- **目录**: `audio_output/`
- **格式**: 标准WAV格式 (24kHz, 16-bit, 单声道)
- **命名**: `nhl_commentary_YYYYMMDD_HHMMSS_<audio_id>_<style>.wav`

### 文件示例
```
audio_output/
├── nhl_commentary_20250618_150129_358c02ed_enthusiastic.wav
├── mcdavid_fixed_20250618_145557.wav
└── ...
```

## 语音风格

| 风格 | 描述 | 适用场景 |
|------|------|----------|
| `enthusiastic` | 热情播音员 | 进球、精彩扑救 |
| `dramatic` | 戏剧性强调 | 关键时刻、加时赛 |
| `calm` | 冷静专业 | 常规解说、分析 |

## API Key 配置
确保设置了环境变量:
```bash
export GEMINI_API_KEY="your_api_key_here"
```

## 特性
- ✅ 自动保存为标准WAV格式
- ✅ 支持多种语音风格
- ✅ 智能语音风格分析
- ✅ WebSocket实时流媒体支持
- ✅ 错误处理和降级备选方案

## 生成的文件信息
每个生成的音频文件包含:
- 正确的WAV文件头
- 24kHz采样率
- 16-bit采样精度
- 单声道音频
- 可用任何标准音频播放器播放 