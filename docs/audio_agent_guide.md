# 🎙️ NHL Audio Agent 使用指南

## 概述

Audio Agent是基于[Google ADK](https://github.com/google/adk-python)构建的智能音频代理，负责将NHL比赛解说文本转换为高质量的语音输出，并通过WebSocket实时流式传输。

## 🏗️ 架构特点

### 基于Google ADK
- 继承自`google.adk.agents.BaseAgent`
- 完全兼容ADK多智能体协调系统
- 支持智能体间通信和任务分配

### 核心功能
- **Google Cloud TTS集成**：使用Google Cloud Text-to-Speech API
- **实时WebSocket流**：支持多客户端同时连接
- **多语音配置**：5种专业体育解说语音
- **多音频格式**：MP3、WAV、OGG Opus支持
- **智能缓存**：音频队列管理和文件保存

## 🚀 快速开始

### 1. 环境配置

```bash
# 安装依赖
pip install -r requirements.txt

# 设置Google Cloud凭据
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

### 2. 独立运行Audio Agent

```bash
# 基本使用 - 启动实况解说服务器
python src/agents/run_audio_agent.py --scenario live_game

# 使用分析师语音
python src/agents/run_audio_agent.py --scenario analysis --voice analyst

# 自定义端口和时长
python src/agents/run_audio_agent.py --scenario highlights --port 9000 --duration 300
```

### 3. 与NHL解说系统集成

```bash
# 完整的NHL音频解说系统
python src/agents/nhl_audio_integration.py 2024020001 --duration 10

# 使用竞技场播音员语音的精彩集锦
python src/agents/nhl_audio_integration.py 2024020001 --scenario highlights --voice arena_announcer
```

## 🎵 语音配置

### 可用语音类型

| 语音类型 | 声音特点 | 适用场景 | 语速 |
|---------|---------|---------|------|
| `play_by_play` | 深沉权威 | 实况解说 | 1.1x |
| `color_commentary` | 温暖对话 | 分析评论 | 0.95x |
| `arena_announcer` | 雄浑激昂 | 进球宣告 | 0.9x |
| `radio_host` | 清晰电台 | 电台解说 | 1.0x |
| `analyst` | 专业分析 | 数据分析 | 1.05x |

### 场景设置

```python
# 查看可用语音和场景
python src/agents/run_audio_agent.py --list-voices
python src/agents/run_audio_agent.py --list-scenarios
```

## 🌐 WebSocket客户端

### Web客户端
在浏览器中打开 `examples/audio_client.html` 来测试和监控音频流：

- **实时连接监控**
- **音频流播放**
- **手动解说测试**
- **连接统计显示**

### JavaScript客户端示例

```javascript
const socket = new WebSocket('ws://localhost:8765');

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'audio_stream') {
        // 解码并播放音频
        const audioData = atob(data.audio_data);
        const blob = new Blob([audioData], { type: 'audio/mpeg' });
        const audioUrl = URL.createObjectURL(blob);
        
        const audio = new Audio(audioUrl);
        audio.play();
    }
};

// 发送测试解说
socket.send(JSON.stringify({
    type: 'request_audio',
    text: 'Connor McDavid scores an amazing goal!'
}));
```

## 🔧 API接口

### Audio Agent主要方法

```python
from agents.audio_agent import AudioAgent

# 创建Audio Agent
agent = AudioAgent(
    name="nhl_commentator",
    voice_name="en-US-Studio-M",
    audio_encoding="MP3",
    speaking_rate=1.1,
    websocket_port=8765
)

# 处理解说文本
result = await agent.process_commentary(
    "McDavid breaks away and scores!",
    metadata={"game_time": "2:15:30", "event": "goal"}
)

# 启动WebSocket服务器
await agent.start_websocket_server()
```

### 消息协议

#### 客户端到服务器

```json
{
    "type": "request_audio",
    "text": "解说文本",
    "metadata": {
        "game_time": "1:15:30",
        "event_type": "goal"
    }
}
```

#### 服务器到客户端

```json
{
    "type": "audio_stream",
    "text": "解说文本",
    "audio_data": "base64编码的音频数据",
    "encoding": "MP3",
    "timestamp": "2024-01-15T10:30:00",
    "metadata": {}
}
```

## 🏒 与NHL系统集成

### 集成架构

```
LiveDataCollector → Commentary Files → Audio Agent → WebSocket Stream
      ↓                    ↓                ↓              ↓
   NHL API数据         文本解说         TTS音频       实时播放
```

### 使用NHLAudioIntegration

```python
from agents.nhl_audio_integration import NHLAudioIntegration

# 创建集成系统
integration = NHLAudioIntegration(
    game_id="2024020001",
    scenario="live_game",
    voice_type="play_by_play"
)

# 启动完整系统
await integration.start_integrated_system(duration_minutes=10)
```

## 📊 性能指标

### 基准测试结果

- **TTS延迟**：~0.5-1.5秒（取决于文本长度）
- **WebSocket传输**：~50-100ms
- **音频质量**：64kbps MP3 / 1411kbps WAV
- **并发连接**：支持多客户端同时连接
- **内存使用**：~50-100MB（包含音频缓存）

### 优化建议

```python
# 高性能配置
agent = AudioAgent(
    voice_name="en-US-Neural2-D",  # 延迟较低的Neural2系列
    audio_encoding="OGG_OPUS",     # 更小的文件大小
    speaking_rate=1.2              # 加快语速
)
```

## 🐛 故障排除

### 常见问题

1. **Google Cloud凭据错误**
   ```bash
   # 检查凭据设置
   echo $GOOGLE_APPLICATION_CREDENTIALS
   gcloud auth list
   ```

2. **WebSocket连接失败**
   ```bash
   # 检查端口是否被占用
   netstat -an | grep 8765
   ```

3. **音频播放问题**
   - 确保浏览器支持音频播放
   - 检查音频编码格式兼容性
   - 验证base64解码正确性

### 调试模式

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 启用详细日志
agent = AudioAgent(name="debug_agent")
```

## 🧪 测试

### 单元测试

```bash
# 测试Audio Agent基本功能
python -m pytest tests/test_audio_agent.py

# 集成测试
python -m pytest tests/test_nhl_integration.py
```

### CLI测试模式

```bash
# 交互式测试
python src/agents/run_audio_agent.py --test-cli
```

## 📈 扩展开发

### 自定义语音配置

```python
from agents.audio_config import VoiceConfig, VOICE_CONFIGS

# 添加新语音
VOICE_CONFIGS["custom_voice"] = VoiceConfig(
    name="en-US-Wavenet-A",
    language_code="en-US",
    gender="FEMALE",
    description="Custom female voice",
    speaking_rate=1.0,
    pitch=2.0
)
```

### 集成其他TTS服务

```python
class CustomAudioAgent(AudioAgent):
    async def _text_to_speech(self, text: str) -> Optional[bytes]:
        # 实现自定义TTS逻辑
        return await custom_tts_service.synthesize(text)
```

## 🤝 贡献

欢迎为Audio Agent贡献代码！请参考：

1. [贡献指南](../CONTRIBUTING.md)
2. [代码规范](../docs/coding_standards.md)
3. [测试指南](../docs/testing_guide.md)

---

**构建于Google ADK之上的专业级NHL音频解说系统** 🏒🎙️ 