"""
NHL Audio Agent - 基于Google ADK的音频解说代理

这个模块包含：
1. AudioAgent类 - 主要的音频处理代理
2. 音频工具函数 - TTS、WebSocket流、状态监控
3. 便捷接口函数 - 简化使用的包装函数

使用示例：
    from src.agents.audio_agent import audio_agent, process_commentary_text
    
    # 处理解说文本
    result = await process_commentary_text("Goal scored by Connor McDavid!")
    
    # 或使用完整的代理
    agent = AudioAgent()
    result = await agent.process_commentary("Amazing save by the goalie!")
"""

from .audio_agent import (
    AudioAgent,
    audio_agent,
    default_audio_agent,
    process_commentary_text,
    start_audio_streaming_service
)

from .tool import (
    AUDIO_TOOLS,
    text_to_speech_tool,
    stream_audio_tool,
    audio_status_tool,
    audio_processor
)

__all__ = [
    # 主要类和实例
    "AudioAgent",
    "audio_agent", 
    "default_audio_agent",
    
    # 便捷函数
    "process_commentary_text",
    "start_audio_streaming_service",
    
    # 工具
    "AUDIO_TOOLS",
    "text_to_speech_tool",
    "stream_audio_tool", 
    "audio_status_tool",
    "audio_processor"
] 