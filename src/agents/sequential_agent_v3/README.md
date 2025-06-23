# Sequential Agent V3 - Complete NHL Commentary Pipeline

**完整的三代理整合系统：Data + Commentary + Audio**

## 🎯 功能概述

Sequential Agent V3 是 NHL 实时评论系统的完整版本，整合了：

1. **Data Agent** - NHL 数据分析
2. **Commentary Agent** - 双人播音员对话生成
3. **Audio Agent** - 文本转语音处理

## 🚀 主要特性

- **完整管道整合**：一个代理处理从数据到音频的完整流程
- **智能语音风格**：根据说话人和内容自动选择语音风格
- **播音员特化**：Alex Chen (激情) 和 Mike Rodriguez (分析)
- **音频文件组织**：按游戏和时间戳自动组织音频文件
- **错误处理**：每个阶段的独立错误处理和恢复

## 📁 文件结构

```
src/agents/sequential_agent_v3/
├── __init__.py          # 模块初始化
├── agent.py             # 主要的 Sequential Agent V3 类
├── prompts.py           # 增强的提示模板
├── tools.py             # 音频处理工具函数
└── README.md            # 说明文档（本文件）
```

## 🛠️ 使用方法

### 基本使用

```python
from src.agents.sequential_agent_v3 import create_nhl_sequential_agent_v3

# 创建代理
agent_v3 = create_nhl_sequential_agent_v3("2024030412")
await agent_v3.initialize()

# 代理现在包含三个子代理：data + commentary + audio
print(f"Agent: {agent_v3.agent.name}")
print(f"Sub-agents: {len(agent_v3.agent.sub_agents)}")
```

### 在管道中使用

可以参考 Pipeline V2 的模式创建一个新的 Pipeline V3：

```python
# 替换 Sequential Agent V2
# 原来：
# from src.agents.sequential_agent_v2.agent import create_nhl_sequential_agent

# 现在：
from src.agents.sequential_agent_v3.agent import create_nhl_sequential_agent_v3

class LivePipelineV3:
    async def _create_sequential_agent(self):
        self.sequential_agent = create_nhl_sequential_agent_v3(self.game_id)
        await self.sequential_agent.initialize()
```

## 🎵 音频处理功能

### 语音风格映射

- **Alex Chen** (实况播音员)
  - 进球、射门 → `enthusiastic`
  - 点球、加时 → `dramatic`
  - 默认 → `enthusiastic`

- **Mike Rodriguez** (分析员)
  - 关键分析 → `dramatic`
  - 常规分析 → `calm`

### 音频文件命名

生成的音频文件遵循以下格式：
```
audio_output/GAME_ID/GAME_ID_TIMESTAMP_SPEAKER_STYLE_INDEX.wav

例如：
audio_output/2024030412/2024030412_1_00_15_alexchen_enthusiastic_0.wav
audio_output/2024030412/2024030412_1_00_15_mikerodriguez_calm_1.wav
```

## 📊 输出格式

Sequential Agent V3 生成完整的三阶段输出：

```json
{
  "sequential_agent_v3": {
    "data_analysis": {
      "recommendation": "...",
      "key_points": [...]
    },
    "commentary_generation": {
      "commentary_sequence": [
        {
          "speaker": "Alex Chen",
          "text": "...",
          "emotion": "enthusiastic"
        }
      ]
    },
    "audio_processing": {
      "audio_segments": [
        {
          "segment_index": 0,
          "speaker": "Alex Chen",
          "voice_style": "enthusiastic",
          "saved_file": "audio_output/..."
        }
      ],
      "total_segments": 2,
      "status": "success"
    },
    "pipeline_status": "complete",
    "timestamp": "2024-01-01T12:00:00"
  }
}
```

## 🔧 技术实现

### 代理组合

```python
# 三个子代理的顺序执行
self.agent = SequentialAgent(
    name=f"NHL_Complete_{self.game_id}",
    sub_agents=[data_agent, commentary_agent, audio_agent],
    description="Complete NHL Data + Commentary + Audio Pipeline"
)
```

### 智能语音风格检测

```python
def _get_voice_style_for_speaker(self, speaker: str, text: str) -> str:
    # 基于说话人和内容智能选择语音风格
    # Alex Chen: 更激情
    # Mike Rodriguez: 更分析性
```

## 🆚 与 V2 的区别

| 功能 | Sequential Agent V2 | Sequential Agent V3 |
|------|-------------------|-------------------|
| 数据分析 | ✅ | ✅ |
| 评论生成 | ✅ | ✅ |
| 音频处理 | ❌ | ✅ |
| 完整管道 | 部分 | 完整 |
| 输出文件 | JSON only | JSON + WAV |

## 🎯 使用场景

- **实时比赛评论**：生成完整的音频评论
- **比赛回放**：为历史比赛生成音频
- **内容创作**：自动化体育内容制作
- **无障碍服务**：为视觉障碍用户提供音频解说

## ⚠️ 注意事项

1. **资源消耗**：音频生成比较耗时，建议在性能充足的环境中使用
2. **存储空间**：音频文件会占用较多存储空间
3. **API 配额**：需要确保 Google TTS API 配额充足
4. **网络依赖**：需要稳定的网络连接进行 TTS 调用

## 🔮 未来改进

- 并行音频处理以提高速度
- 更多语音风格选择
- 实时音频流媒体整合
- 多语言支持
- 情感强度调节 