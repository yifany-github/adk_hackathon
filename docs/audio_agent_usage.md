# Audio Agent 使用说明

## 简介
Audio Agent 是一个基于 Gemini TTS 的音频生成代理，用于将解说文本转换为语音。它支持多种语音风格，并能处理不同的情感表达。

## 输入格式

### 1. 解说文件格式 (JSON)
```json
{
  "commentary_data": {
    "commentary_data": {
      "commentary_sequence": [
        {
          "speaker": "Host",           // 说话者身份
          "text": "解说文本内容",      // 需要转换的文本
          "emotion": "apologetic",     // 情感类型
          "timing": 1.0,              // 时间点
          "duration_estimate": 8.0,    // 预计持续时间
          "pause_after": 0.5          // 后续暂停时间
        }
      ]
    }
  }
}
```

### 2. 情感类型映射
| 情感类型 (emotion) | 语音风格 (voice_style) |
|-------------------|----------------------|
| apologetic        | calm                 |
| informative       | enthusiastic         |
| excited          | enthusiastic         |
| analytical       | calm                 |
| dramatic         | dramatic             |
| 其他             | enthusiastic (默认)   |

## 输出格式

### 1. 音频文件
- 格式：WAV
- 采样率：24000Hz
- 位深度：16-bit
- 声道：单声道
- 文件命名：`commentary_{序号}_{语音风格}.wav`
- 保存位置：`audio_output/` 目录

### 2. 处理结果
```json
{
  "status": "success",
  "audio_processing": {
    "audio_id": "唯一标识符",
    "text_length": 文本长度,
    "voice_style": "使用的语音风格",
    "language": "en-US"
  },
  "voice_style_used": "实际使用的语音风格",
  "server_status": {
    "websocket_running": true/false,
    "clients_connected": 连接数
  },
  "timestamp": "处理时间戳",
  "message": "处理结果描述"
}
```

## 使用示例

### 1. 基本使用
```python
from src.agents.audio_agent import AudioAgent

# 创建 Audio Agent 实例
agent = AudioAgent(model="gemini-2.5-flash-preview-tts")

# 处理单条解说
result = await agent.process_commentary(
    commentary_text="解说文本",
    voice_style="enthusiastic",
    auto_start_server=True
)
```

### 2. 批量处理
```python
# 读取解说文件
with open("commentary_file.json", 'r') as f:
    commentary_data = json.load(f)

# 获取解说序列
commentary_sequence = commentary_data['commentary_data']['commentary_data']['commentary_sequence']

# 处理每条解说
for commentary in commentary_sequence:
    result = await text_to_speech(
        text=commentary['text'],
        voice_style=commentary['emotion'],
        language="en-US"
    )
```

## 环境要求

1. 必需的环境变量：
```bash
export GEMINI_API_KEY=your_gemini_api_key
```

2. 依赖包：
```bash
pip install pydub numpy
```

## 注意事项

1. 确保 `GEMINI_API_KEY` 已正确设置
2. 音频输出目录 (`audio_output/`) 会自动创建
3. 语音风格会根据情感类型自动映射
4. 生成的音频文件为 WAV 格式，确保有足够的磁盘空间
5. 建议在处理大量文本时添加适当的延时，避免 API 限制

## 错误处理

常见错误及解决方案：

1. API Key 无效
   - 检查 `GEMINI_API_KEY` 环境变量是否正确设置
   - 确认 API Key 是否有效

2. 音频生成失败
   - 检查文本内容是否合法
   - 确认语音风格是否支持
   - 查看网络连接状态

3. 音频保存失败
   - 确认输出目录权限
   - 检查磁盘空间是否充足

## 调试信息

处理过程中会输出以下信息：
- 解说文本内容
- 使用的语音风格
- 音频生成状态
- 文件保存位置
- 错误信息（如果有） 