#!/usr/bin/env python3
"""
NHL LiveStream Pipeline - 连接三个agents的完整pipeline
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, List
import glob
from datetime import datetime
import base64
import wave
import uuid

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.data_agent.data_agent_adk import create_hockey_agent_for_game
from src.agents.commentary_agent.commentary_agent import create_commentary_agent_for_game
from src.agents.audio_agent.tool import text_to_speech

class NHLPipeline:
    def __init__(self, game_id: str):
        """
        初始化NHL Pipeline
        
        Args:
            game_id: NHL比赛ID (例如: "2024030412")
        """
        self.game_id = game_id
        self.data_agent = None
        self.commentary_agent = None
        self.audio_files = []  # 保存生成的音频文件路径
        
        # 创建音频输出目录
        self.audio_output_dir = "audio_output"
        os.makedirs(self.audio_output_dir, exist_ok=True)
        
    async def initialize_agents(self):
        """初始化所有agents"""
        print("🤖 初始化agents...")
        
        # 创建Data Agent
        self.data_agent = create_hockey_agent_for_game(self.game_id)
        print("✅ Data Agent 创建成功")
        
        # 创建Commentary Agent
        self.commentary_agent = create_commentary_agent_for_game(self.game_id)
        print("✅ Commentary Agent 创建成功")
        
        # 不再创建AudioAgent，直接使用音频工具
        print("✅ 音频处理工具准备就绪")
        
    def save_audio_file(self, audio_base64: str, commentary_text: str, voice_style: str = "enthusiastic") -> str:
        """
        直接保存音频文件到本地
        
        Args:
            audio_base64: Base64编码的音频数据
            commentary_text: 解说文本
            voice_style: 语音风格
            
        Returns:
            保存的文件路径
        """
        try:
            # 解码音频数据
            audio_bytes = base64.b64decode(audio_base64)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%H%M%S")
            audio_id = str(uuid.uuid4())[:8]
            
            # 截取解说的前30个字符作为文件名的一部分
            text_snippet = "".join(c for c in commentary_text[:30] if c.isalnum() or c.isspace()).strip()
            text_snippet = text_snippet.replace(" ", "_")
            
            filename = f"{self.game_id}_{timestamp}_{audio_id}_{voice_style}_{text_snippet}.wav"
            filepath = os.path.join(self.audio_output_dir, filename)
            
            # 创建WAV文件
            with wave.open(filepath, 'wb') as wav_file:
                wav_file.setnchannels(1)      # 单声道
                wav_file.setsampwidth(2)      # 16位
                wav_file.setframerate(24000)  # 24kHz
                wav_file.writeframes(audio_bytes)
            
            print(f"💾 音频已保存: {os.path.basename(filepath)} ({len(audio_bytes):,} 字节)")
            return filepath
            
        except Exception as e:
            print(f"❌ 保存音频失败: {e}")
            return ""
        
    async def process_timestamp(self, timestamp_file: str, voice_style: str = "enthusiastic", language: str = "en-US") -> Dict[str, Any]:
        """
        处理单个时间戳的数据
        
        Args:
            timestamp_file: 时间戳数据文件路径
            voice_style: 语音风格
            language: 语言设置
            
        Returns:
            处理结果字典
        """
        try:
            # 1. 使用Data Agent处理数据
            with open(timestamp_file, 'r') as f:
                data = json.load(f)
            
            # 2. 使用Commentary Agent生成解说
            from google.adk.runners import InMemoryRunner
            from google.genai.types import Part, UserContent
            
            runner = InMemoryRunner(agent=self.commentary_agent)
            session = await runner.session_service.create_session(
                app_name=runner.app_name,
                user_id="game_commentator"
            )
            
            content = UserContent(parts=[Part(text=json.dumps(data))])
            commentary = ""
            
            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=content,
            ):
                if hasattr(event, 'content') and event.content and event.content.parts:
                    if event.content.parts[0].text:
                        commentary = event.content.parts[0].text
            
            # 3. 直接使用音频工具生成音频并保存
            audio_filepath = ""
            if commentary:
                print(f"🎙️ 生成音频: {commentary[:50]}...")
                
                # 使用传入的语音风格，如果没有则智能选择
                final_voice_style = voice_style if voice_style != "auto" else self._analyze_voice_style(commentary)
                
                # 调用TTS工具
                tts_result = await text_to_speech(
                    tool_context=None,
                    text=commentary,
                    voice_style=final_voice_style,
                    language=language
                )
                
                if tts_result["status"] == "success" and "audio_data" in tts_result:
                    # 直接保存音频文件
                    audio_filepath = self.save_audio_file(
                        tts_result["audio_data"], 
                        commentary, 
                        final_voice_style
                    )
                    
                    if audio_filepath:
                        self.audio_files.append(audio_filepath)
                        print(f"✅ 音频生成并保存成功")
                    else:
                        print(f"❌ 音频保存失败")
                else:
                    print(f"❌ 音频生成失败: {tts_result.get('error', '未知错误')}")
            
            return {
                "status": "success",
                "timestamp_file": timestamp_file,
                "commentary": commentary,
                "audio_file": audio_filepath,
                "voice_style": final_voice_style if 'final_voice_style' in locals() else voice_style,
                "language": language,
                "data": data  # 包含原始数据供UI使用
            }
            
        except Exception as e:
            import traceback
            print(f"❌ 处理时间戳失败: {e}")
            traceback.print_exc()
            return {
                "status": "error",
                "timestamp_file": timestamp_file,
                "error": str(e)
            }
    
    def _analyze_voice_style(self, text: str) -> str:
        """
        分析文本内容，智能选择语音风格
        
        Args:
            text: 解说文本
            
        Returns:
            语音风格 (enthusiastic, dramatic, calm)
        """
        text_lower = text.lower()
        
        # 检查是否包含激动词汇
        exciting_words = ['goal', 'score', 'amazing', 'incredible', 'fantastic', 'wow', 'shot', 'save']
        dramatic_words = ['overtime', 'final', 'crucial', 'critical', 'penalty', 'power play', 'empty net']
        
        if any(word in text_lower for word in dramatic_words):
            return "dramatic"
        elif any(word in text_lower for word in exciting_words):
            return "enthusiastic"
        else:
            return "enthusiastic"  # 默认使用热情风格
    
    async def run_pipeline(self, max_files: int = 5):
        """
        运行完整的pipeline
        
        Args:
            max_files: 最大处理文件数
        """
        print(f"🚀 开始NHL Pipeline - 比赛ID: {self.game_id}")
        print("📁 音频将直接保存到本地，不使用audio_client")
        print("=" * 60)
        
        # 初始化agents
        await self.initialize_agents()
        
        # 获取所有时间戳文件
        data_files = glob.glob(f"data/data_agent_outputs/{self.game_id}_*_adk.json")
        data_files.sort()
        
        if not data_files:
            print(f"❌ 未找到比赛 {self.game_id} 的数据文件")
            return
        
        # 限制处理文件数量
        if len(data_files) > max_files:
            data_files = data_files[:max_files]
        
        print(f"📊 找到 {len(data_files)} 个数据文件待处理")
        print()
        
        # 处理每个时间戳
        successful_outputs = []
        for i, data_file in enumerate(data_files, 1):
            print(f"🔄 处理 [{i}/{len(data_files)}]: {os.path.basename(data_file)}")
            
            result = await self.process_timestamp(data_file)
            
            if result["status"] == "success":
                successful_outputs.append(data_file)
                print("✅ 处理成功")
            else:
                print(f"❌ 处理失败: {result.get('error', '未知错误')}")
        
        # 输出总结
        print()
        print("=" * 60)
        print("✅ Pipeline 完成!")
        print(f"✅ 处理文件数: {len(data_files)}")
        print(f"✅ 成功处理: {len(successful_outputs)}")
        print(f"🎵 生成音频文件: {len(self.audio_files)}")
        
        if self.audio_files:
            print("\n📁 生成的音频文件:")
            for audio_file in self.audio_files:
                file_size = os.path.getsize(audio_file) if os.path.exists(audio_file) else 0
                print(f"   - {os.path.basename(audio_file)} ({file_size:,} 字节)")
        
        print(f"\n💡 提示: 所有音频文件保存在 '{self.audio_output_dir}' 目录")
        print()

async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python pipeline.py GAME_ID [MAX_FILES]")
        print("示例: python pipeline.py 2024030412 5")
        sys.exit(1)
    
    game_id = sys.argv[1]
    max_files = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    pipeline = NHLPipeline(game_id)
    await pipeline.run_pipeline(max_files)

if __name__ == "__main__":
    asyncio.run(main()) 