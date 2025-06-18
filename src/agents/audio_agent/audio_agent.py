from google.adk.agents import LlmAgent
from google.adk.runners import BaseAgent, InvocationContext
from google.adk.events import Event
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from .tool import AUDIO_TOOLS, audio_processor
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime


class AudioAgent(BaseAgent):
    """
    NHL解说音频代理 - 负责将解说文本转换为语音并进行流式传输
    
    基于Google ADK构建的音频处理代理，专门用于：
    1. 接收commentary agent生成的解说文本
    2. 使用Google Cloud TTS转换为高质量语音
    3. 通过WebSocket实时流式传输音频
    4. 支持多种语音风格和语言
    """
    
    def __init__(self, name: str = "nhl_audio_agent", model: str = "gemini-2.0-flash", **kwargs):
        # 调用父类构造函数
        super().__init__(name=name, **kwargs)
        
        # 将自定义属性存储在私有变量中
        self._model = model
        self._websocket_server_running = False
        
        # 创建内部LLM代理用于文本处理
        self._llm_agent = self._create_llm_agent()
        
    @property
    def model(self) -> str:
        """获取模型名称"""
        return self._model
    
    @property 
    def websocket_server_running(self) -> bool:
        """获取WebSocket服务器运行状态"""
        return self._websocket_server_running
        
    @websocket_server_running.setter
    def websocket_server_running(self, value: bool):
        """设置WebSocket服务器运行状态"""
        self._websocket_server_running = value
        
    @property
    def llm_agent(self):
        """获取内部LLM代理"""
        return self._llm_agent
        
    def _create_llm_agent(self) -> LlmAgent:
        """创建ADK LLM代理实例"""
        
        agent_instruction = """
你是NHL冰球比赛的专业音频代理，负责将解说文本转换为高质量的语音输出。

## 核心职责：
1. **文本转语音**: 使用text_to_speech工具将解说文本转换为语音
2. **文件保存**: 使用save_audio_file工具将生成的音频保存到文件
3. **音频流管理**: 使用stream_audio_websocket工具启动WebSocket服务器
4. **状态监控**: 使用get_audio_status工具监控音频系统状态

## 工具使用指南：

### text_to_speech 工具
- 用于将commentary agent生成的解说文本转换为语音
- 支持多种语音风格：enthusiastic（热情）、dramatic（戏剧性）、calm（平静）
- 根据解说内容选择合适的语音风格：
  - 进球、精彩扑救 → enthusiastic
  - 点球、关键时刻 → dramatic  
  - 一般比赛解说 → enthusiastic（默认）
- 自动处理SSML标记以增强语音表现力

### stream_audio_websocket 工具
- 在收到第一个音频生成请求时自动启动WebSocket服务器
- 默认端口8765，可以自定义
- 向所有连接的客户端实时广播音频数据

### save_audio_file 工具
- 将生成的音频数据保存为WAV文件
- 自动组织到game_id子文件夹中 (audio_output/GAME_ID/)
- 包含音频ID、时间戳和语音风格的文件名
- **重要**: 每次生成音频后必须调用此工具进行文件保存

### get_audio_status 工具
- 用于监控音频系统状态
- 显示连接的客户端数量、音频队列状态、历史记录等
- 在出现问题时用于诊断

## 处理流程：
1. 接收解说文本输入
2. 分析文本内容，选择合适的语音风格
3. 使用text_to_speech转换为音频
4. **立即使用save_audio_file保存音频文件**
5. 确保WebSocket服务器运行中
6. 自动广播音频到所有连接的客户端
7. 返回处理状态、音频ID和文件路径

## 错误处理：
- 如果TTS失败，返回详细错误信息并建议重试
- 如果WebSocket服务器启动失败，尝试使用备用端口
- 监控客户端连接状态，自动清理断开的连接

## 语音质量优化：
- 针对冰球解说优化语速（1.1x-1.2x）
- 使用适合体育解说的男性声音
- 根据解说内容动态调整音调和音量
- 支持SSML增强表现力

记住：你的目标是为NHL比赛提供高质量、实时的语音解说服务，让听众感受到比赛的激情和紧张感。

**关键要求**: 
- 每次使用text_to_speech生成音频后，必须立即调用save_audio_file保存文件
- save_audio_file需要这些参数：audio_base64（从text_to_speech响应获取）、audio_id、voice_style、game_id
- 文件保存是强制性的，不是可选的
"""

        return LlmAgent(
            name="nhl_audio_llm_agent",
            model=self.model,
            instruction=agent_instruction,
            description="NHL冰球比赛音频代理 - 专业的文本转语音和音频流服务",
            tools=AUDIO_TOOLS
        )
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        实现自定义音频代理的核心逻辑
        
        这个方法定义了音频代理的执行流程：
        1. 检查输入文本
        2. 智能选择语音风格
        3. 启动WebSocket服务器（如果需要）
        4. 生成音频并流式传输
        5. 返回处理结果
        """
        try:
            print(f"🎯 [{self.name}] 开始音频处理工作流...")
            
            # 从session state获取输入文本
            input_text = ctx.session.state.get("commentary_text") or ctx.session.state.get("text")
            
            if not input_text:
                # 如果没有找到文本，尝试从最后的用户消息中获取
                if hasattr(ctx, 'user_message') and ctx.user_message:
                    input_text = str(ctx.user_message)
                else:
                    # 创建错误事件
                    error_event = Event(
                        id="audio_error",
                        type="error",
                        content="未找到需要转换为音频的文本内容",
                        author=self.name
                    )
                    yield error_event
                    return
            
            print(f"🎙️ [{self.name}] 处理文本: {input_text[:50]}...")
            
            # 智能分析语音风格
            voice_style = self._analyze_voice_style(input_text)
            
            # 设置处理参数到session state
            ctx.session.state["current_text"] = input_text
            ctx.session.state["voice_style"] = voice_style
            ctx.session.state["audio_processing_status"] = "started"
            
            # Step 1: 确保WebSocket服务器运行
            if not self.websocket_server_running:
                yield Event(
                    id="websocket_start",
                    type="info", 
                    content="正在启动WebSocket音频流服务器...",
                    author=self.name
                )
                
                # 通过LLM agent调用工具
                async for event in self.llm_agent.run_async(ctx):
                    # 检查工具调用事件
                    if hasattr(event, 'tool_call') and event.tool_call:
                        if event.tool_call.function.name == "stream_audio_websocket":
                            self.websocket_server_running = True
                    yield event
            
            # Step 2: 生成音频
            yield Event(
                id="audio_generation",
                type="info",
                content=f"正在生成音频，使用{voice_style}风格...",
                author=self.name
            )
            
            # 让LLM agent处理音频生成
            async for event in self.llm_agent.run_async(ctx):
                yield event
            
            # Step 3: 检查处理结果
            audio_result = ctx.session.state.get("last_audio_generation", {})
            
            if audio_result.get("status") == "success":
                success_message = f"音频处理完成！音频ID: {audio_result.get('audio_id', 'unknown')}"
                ctx.session.state["audio_processing_status"] = "completed"
                
                yield Event(
                    id="audio_success",
                    type="success",
                    content=success_message,
                    author=self.name,
                    final_response=True
                )
            else:
                error_message = f"音频处理失败: {audio_result.get('error', '未知错误')}"
                ctx.session.state["audio_processing_status"] = "failed"
                
                yield Event(
                    id="audio_error",
                    type="error", 
                    content=error_message,
                    author=self.name,
                    final_response=True
                )
                
        except Exception as e:
            error_msg = f"音频代理执行失败: {str(e)}"
            print(f"❌ [{self.name}] {error_msg}")
            
            ctx.session.state["audio_processing_status"] = "error"
            ctx.session.state["audio_error"] = error_msg
            
            yield Event(
                id="audio_agent_error",
                type="error",
                content=error_msg,
                author=self.name,
                final_response=True
            )

    def _analyze_voice_style(self, text: str) -> str:
        """智能分析文本内容，选择合适的语音风格"""
        text_lower = text.lower()
        
        # 检查关键词来确定语音风格
        exciting_keywords = ["goal", "score", "save", "shot", "penalty", "power play", "amazing", "incredible"]
        dramatic_keywords = ["overtime", "final", "crucial", "critical", "game-winning", "timeout"]
        
        exciting_count = sum(1 for keyword in exciting_keywords if keyword in text_lower)
        dramatic_count = sum(1 for keyword in dramatic_keywords if keyword in text_lower)
        
        if dramatic_count > 0:
            return "dramatic"
        elif exciting_count > 0:
            return "enthusiastic"
        else:
            return "enthusiastic"  # 默认热情风格
    
    # 保持向后兼容的便捷方法
    async def process_commentary(
        self, 
        commentary_text: str, 
        voice_style: str = "enthusiastic",
        auto_start_server: bool = True
    ) -> Dict[str, Any]:
        """
        处理解说文本，转换为语音并进行流式传输
        
        Args:
            commentary_text: 从commentary agent接收的解说文本
            voice_style: 语音风格 (enthusiastic, dramatic, calm)
            auto_start_server: 是否自动启动WebSocket服务器
            
        Returns:
            处理结果和状态信息
        """
        try:
            print(f"🎯 Audio Agent: 开始处理解说文本 - {commentary_text[:50]}...")
            
            # 1. 如果需要，启动WebSocket服务器
            if auto_start_server and not self.websocket_server_running:
                server_result = await self._ensure_websocket_server()
                if server_result["status"] == "success":
                    self.websocket_server_running = True
            
            # 2. 分析文本内容，智能选择语音风格
            if voice_style == "auto":
                voice_style = self._analyze_voice_style(commentary_text)
            
            # 3. 生成语音
            audio_result = await self._generate_audio(commentary_text, voice_style)
            
            # 4. 获取当前状态
            status_result = await self._get_current_status()
            
            return {
                "status": "success",
                "audio_processing": audio_result,
                "voice_style_used": voice_style,
                "server_status": {
                    "websocket_running": self.websocket_server_running,
                    "clients_connected": status_result.get("audio_agent_status", {}).get("connected_clients", 0)
                },
                "timestamp": datetime.now().isoformat(),
                "message": f"解说音频处理完成，使用{voice_style}风格"
            }
            
        except Exception as e:
            error_msg = f"音频处理失败: {str(e)}"
            print(f"❌ Audio Agent: {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "text": commentary_text[:100]
            }

    async def _ensure_websocket_server(self) -> Dict[str, Any]:
        """确保WebSocket服务器运行"""
        try:
            # 使用agent的工具来启动服务器
            from .tool import stream_audio_websocket
            
            result = stream_audio_websocket(port=8765, host="localhost")
            return result
            
        except Exception as e:
            # 尝试备用端口
            try:
                result = stream_audio_websocket(port=8766, host="localhost")
                return result
            except Exception as e2:
                return {
                    "status": "error",
                    "error": f"无法启动WebSocket服务器: {str(e)}, 备用端口也失败: {str(e2)}"
                }
    
    async def _generate_audio(self, text: str, voice_style: str) -> Dict[str, Any]:
        """生成音频"""
        try:
            from .tool import text_to_speech
            
            result = await text_to_speech(
                text=text,
                voice_style=voice_style,
                language="en-US"
            )
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"音频生成失败: {str(e)}"
            }
    
    async def _get_current_status(self) -> Dict[str, Any]:
        """获取当前音频系统状态"""
        try:
            from .tool import get_audio_status
            
            result = get_audio_status()
            return result.get("audio_agent_status", {})
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"状态获取失败: {str(e)}"
            }
    
    async def start_audio_service(self, port: int = 8765) -> Dict[str, Any]:
        """启动完整的音频服务"""
        try:
            print(f"🚀 Audio Agent: 启动音频服务...")
            
            # 启动WebSocket服务器
            server_result = await self._ensure_websocket_server()
            
            if server_result["status"] == "success":
                self.websocket_server_running = True
                print(f"✅ Audio Agent: 音频服务已启动，WebSocket端口: {port}")
                
                return {
                    "status": "success",
                    "message": "NHL音频解说服务已启动",
                    "websocket_url": f"ws://localhost:{port}",
                    "services": {
                        "text_to_speech": "ready",
                        "websocket_streaming": "running",
                        "client_connections": "accepting"
                    }
                }
            else:
                return server_result
                
        except Exception as e:
            return {
                "status": "error",
                "error": f"音频服务启动失败: {str(e)}"
            }
    
    async def stop_audio_service(self) -> Dict[str, Any]:
        """停止音频服务"""
        try:
            # 导入停止函数
            from .tool import stop_websocket_server
            
            # 停止WebSocket服务器
            await stop_websocket_server()
            
            # 断开所有客户端连接
            for client in audio_processor.connected_clients.copy():
                try:
                    await client.close()
                except:
                    pass
            
            audio_processor.connected_clients.clear()
            self.websocket_server_running = False
            
            return {
                "status": "success",
                "message": "音频服务已停止"
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": f"停止服务失败: {str(e)}"
            }
    
    def get_agent(self) -> LlmAgent:
        """获取ADK代理实例 - 保持向后兼容性"""
        return self.llm_agent


# 创建默认的音频代理实例
default_audio_agent = AudioAgent()

# 导出ADK兼容的代理实例
audio_agent = default_audio_agent

# 导出便捷函数
async def process_commentary_text(text: str, style: str = "enthusiastic") -> Dict[str, Any]:
    """便捷函数：处理解说文本"""
    return await default_audio_agent.process_commentary(text, style)

async def start_audio_streaming_service(port: int = 8765) -> Dict[str, Any]:
    """便捷函数：启动音频流服务"""
    return await default_audio_agent.start_audio_service(port)