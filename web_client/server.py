#!/usr/bin/env python3
"""
NHL Commentary Web Server
为web client提供HTTP和WebSocket服务
"""

import asyncio
import json
import os
import sys
import threading
from datetime import datetime
from typing import Dict, Set
import signal
import glob
import base64

from flask import Flask, render_template, send_from_directory, jsonify, request, send_file
from flask_socketio import SocketIO, emit, disconnect
import requests

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import NHLPipeline

class NHLWebServer:
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.clients: Set[str] = set()  # 连接的客户端
        self.active_pipelines: Dict[str, NHLPipeline] = {}  # 活跃的pipeline
        self.game_sessions: Dict[str, dict] = {}  # 游戏会话状态
        
        # 创建Flask应用
        self.app = Flask(__name__,
                        static_folder='.',
                        template_folder='.')
        self.app.config['SECRET_KEY'] = 'nhl_commentary_secret_key'
        
        # 创建SocketIO实例
        self.socketio = SocketIO(self.app, 
                               cors_allowed_origins="*",
                               async_mode='threading',
                               logger=True,
                               engineio_logger=True)
        
        # 设置路由和事件处理
        self.setup_routes()
        self.setup_websocket_events()
        
    def setup_routes(self):
        """设置HTTP路由"""
        
        @self.app.route('/')
        def index():
            """主页面"""
            return send_from_directory('.', 'index.html')
        
        @self.app.route('/<path:filename>')
        def serve_static(filename):
            """静态文件服务"""
            return send_from_directory('.', filename)
        
        @self.app.route('/api/audio/<path:filename>')
        def serve_audio(filename):
            """提供音频文件服务"""
            try:
                # 查找音频文件
                audio_output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'audio_output')
                audio_file_path = os.path.join(audio_output_dir, filename)
                
                if os.path.exists(audio_file_path):
                    return send_file(audio_file_path, mimetype='audio/wav')
                else:
                    return jsonify({'error': '音频文件不存在'}), 404
            except Exception as e:
                print(f"❌ 音频文件服务错误: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/games')
        def get_games():
            """获取可用的比赛列表"""
            # 这里可以集成实际的NHL API
            games = [
                {
                    'id': '2024030412',
                    'homeTeam': 'Toronto Maple Leafs',
                    'awayTeam': 'Boston Bruins',
                    'date': '2024-04-15',
                    'status': 'Live'
                },
                {
                    'id': '2024020123',
                    'homeTeam': 'New York Rangers',
                    'awayTeam': 'Philadelphia Flyers',
                    'date': '2024-04-15',
                    'status': 'Scheduled'
                },
                {
                    'id': '2024020456',
                    'homeTeam': 'Edmonton Oilers',
                    'awayTeam': 'Calgary Flames',
                    'date': '2024-04-15',
                    'status': 'Final'
                }
            ]
            return jsonify(games)
        
        @self.app.route('/api/status')
        def get_status():
            """获取服务器状态"""
            return jsonify({
                'status': 'running',
                'clients': len(self.clients),
                'active_games': len(self.active_pipelines),
                'timestamp': datetime.now().isoformat()
            })
    
    def setup_websocket_events(self):
        """设置WebSocket事件处理"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """客户端连接"""
            client_id = request.sid
            self.clients.add(client_id)
            print(f"🔗 客户端连接: {client_id}")
            
            # 发送连接确认
            emit('status', {
                'type': 'connection',
                'data': {
                    'status': 'connected',
                    'clientId': client_id,
                    'timestamp': datetime.now().isoformat()
                }
            })
            
            # 发送初始系统状态
            emit('agentStatus', {
                'type': 'agentStatus',
                'data': {
                    'dataAgent': 'online',
                    'commentaryAgent': 'online',
                    'audioAgent': 'online'
                }
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """客户端断开连接"""
            client_id = request.sid
            if client_id in self.clients:
                self.clients.remove(client_id)
            
            # 清理该客户端的活跃会话
            sessions_to_remove = []
            for session_id, session in self.game_sessions.items():
                if session.get('client_id') == client_id:
                    sessions_to_remove.append(session_id)
            
            for session_id in sessions_to_remove:
                self.stop_game_session(session_id)
            
            print(f"🔌 客户端断开: {client_id}")
        
        @self.socketio.on('start')
        def handle_start_commentary(data):
            """开始解说"""
            client_id = request.sid
            game_id = data.get('gameId')
            voice_style = data.get('voiceStyle', 'enthusiastic')
            language = data.get('language', 'en-US')
            
            if not game_id:
                emit('error', {
                    'type': 'error',
                    'data': {'message': '缺少gameId参数'}
                })
                return
            
            print(f"🏒 开始解说: {game_id} (风格: {voice_style}, 语言: {language})")
            
            try:
                # 创建游戏会话
                session_id = f"{client_id}_{game_id}"
                session = {
                    'client_id': client_id,
                    'game_id': game_id,
                    'voice_style': voice_style,
                    'language': language,
                    'status': 'running',
                    'start_time': datetime.now()
                }
                
                self.game_sessions[session_id] = session
                
                # 启动解说pipeline（在新线程中）
                pipeline_thread = threading.Thread(
                    target=self.run_commentary_pipeline,
                    args=(session_id, game_id, voice_style, language, client_id)
                )
                pipeline_thread.daemon = True
                pipeline_thread.start()
                
                # 发送成功响应
                emit('status', {
                    'type': 'started',
                    'data': {
                        'sessionId': session_id,
                        'gameId': game_id,
                        'status': 'running'
                    }
                })
                
            except Exception as e:
                print(f"❌ 启动解说失败: {e}")
                emit('error', {
                    'type': 'error',
                    'data': {'message': f'启动解说失败: {str(e)}'}
                })
        
        @self.socketio.on('stop')
        def handle_stop_commentary():
            """停止解说"""
            client_id = request.sid
            
            # 找到并停止该客户端的所有会话
            sessions_to_stop = []
            for session_id, session in self.game_sessions.items():
                if session.get('client_id') == client_id:
                    sessions_to_stop.append(session_id)
            
            for session_id in sessions_to_stop:
                self.stop_game_session(session_id)
            
            emit('status', {
                'type': 'stopped',
                'data': {'status': 'stopped'}
            })
        
        @self.socketio.on('pause')
        def handle_pause_commentary():
            """暂停解说"""
            client_id = request.sid
            
            for session_id, session in self.game_sessions.items():
                if session.get('client_id') == client_id:
                    session['status'] = 'paused'
            
            emit('status', {
                'type': 'paused',
                'data': {'status': 'paused'}
            })
        
        @self.socketio.on('resume')
        def handle_resume_commentary():
            """恢复解说"""
            client_id = request.sid
            
            for session_id, session in self.game_sessions.items():
                if session.get('client_id') == client_id:
                    session['status'] = 'running'
            
            emit('status', {
                'type': 'resumed',
                'data': {'status': 'running'}
            })
    
    def run_commentary_pipeline(self, session_id: str, game_id: str, voice_style: str, language: str, client_id: str):
        """在单独线程中运行真实的解说pipeline"""
        try:
            print(f"🚀 启动真实解说pipeline: {session_id}")
            
            # 创建NHLPipeline实例
            pipeline = NHLPipeline(game_id)
            self.active_pipelines[session_id] = pipeline
            
            # 在新的事件循环中运行异步pipeline
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 初始化agents
                loop.run_until_complete(pipeline.initialize_agents())
                
                # 发送Agent状态更新
                self.socketio.emit('agentStatus', {
                    'type': 'agentStatus',
                    'data': {
                        'dataAgent': 'online',
                        'commentaryAgent': 'online', 
                        'audioAgent': 'online'
                    }
                }, room=client_id)
                
                # 获取数据文件列表
                data_dir = f"data/data_agent_outputs"
                if not os.path.exists(data_dir):
                    # 如果没有实际数据，使用演示模式
                    print(f"⚠️ 未找到数据目录: {data_dir}, 使用演示模式")
                    self.simulate_commentary_pipeline(session_id, game_id, voice_style, client_id)
                    return
                
                # 处理实际数据文件 - 查找特定比赛的文件
                data_files = sorted(glob.glob(f"{data_dir}/{game_id}_*.json"))
                if not data_files:
                    print(f"⚠️ 未找到比赛 {game_id} 的数据文件，使用演示模式")
                    self.simulate_commentary_pipeline(session_id, game_id, voice_style, client_id)
                    return
                
                print(f"📁 找到 {len(data_files)} 个数据文件")
                
                # 逐个处理数据文件
                for i, data_file in enumerate(data_files):
                    session = self.game_sessions.get(session_id)
                    if not session or session['status'] == 'stopped':
                        break
                    
                    # 等待暂停恢复
                    while session and session['status'] == 'paused':
                        threading.Event().wait(1)
                        session = self.game_sessions.get(session_id)
                    
                    if not session:
                        break
                    
                    print(f"🔄 处理数据文件 {i+1}/{len(data_files)}: {os.path.basename(data_file)}")
                    
                    # 处理时间戳数据
                    result = loop.run_until_complete(
                        pipeline.process_timestamp(data_file, voice_style, language)
                    )
                    
                    if result['status'] == 'success':
                        commentary = result.get('commentary', '')
                        audio_file = result.get('audio_file', '')
                        
                        if commentary:
                            # 发送解说文本
                            self.socketio.emit('commentary', {
                                'type': 'commentary',
                                'data': {
                                    'text': commentary,
                                    'timestamp': datetime.now().isoformat(),
                                    'style': voice_style,
                                    'language': language
                                }
                            }, room=client_id)
                            
                            # 发送音频数据
                            if audio_file and os.path.exists(audio_file):
                                audio_filename = os.path.basename(audio_file)
                                audio_url = f'/api/audio/{audio_filename}'
                                
                                # 获取音频文件大小和时长估算
                                file_size = os.path.getsize(audio_file)
                                estimated_duration = len(commentary) * 0.05  # 估算时长
                                
                                self.socketio.emit('audio', {
                                    'type': 'audio',
                                    'data': {
                                        'text': commentary,
                                        'style': voice_style,
                                        'url': audio_url,
                                        'duration': estimated_duration,
                                        'size': file_size
                                    }
                                }, room=client_id)
                                
                                print(f"🎵 音频已发送: {audio_filename}")
                        
                        # 模拟比赛数据更新（从实际数据中提取）
                        with open(data_file, 'r') as f:
                            game_data = json.load(f)
                        
                        self.socketio.emit('gameData', {
                            'type': 'gameData',
                            'data': self.extract_game_info(game_data)
                        }, room=client_id)
                    
                    else:
                        print(f"❌ 处理失败: {result.get('error', '未知错误')}")
                    
                    # 等待一段时间再处理下一个文件
                    threading.Event().wait(2)
                
                # 解说完成
                print(f"✅ 解说pipeline完成: {session_id}")
                
            finally:
                loop.close()
                
        except Exception as e:
            print(f"❌ 解说pipeline错误: {e}")
            import traceback
            traceback.print_exc()
            
            self.socketio.emit('error', {
                'type': 'error',
                'data': {'message': f'解说pipeline错误: {str(e)}'}
            }, room=client_id)
        
        finally:
            # 清理
            if session_id in self.active_pipelines:
                del self.active_pipelines[session_id]
            
            if session_id in self.game_sessions:
                del self.game_sessions[session_id]
            
            self.socketio.emit('status', {
                'type': 'completed',
                'data': {'status': 'completed', 'message': '解说已完成'}
            }, room=client_id)
    
    def extract_game_info(self, game_data: dict) -> dict:
        """从原始比赛数据中提取UI需要的信息"""
        try:
            # 从实际的ADK数据结构中提取信息
            commentary_data = game_data.get('for_commentary_agent', {})
            game_context = commentary_data.get('game_context', {})
            
            # 提取基本比赛信息
            period = game_context.get('period', 1)
            time_remaining = game_context.get('time_remaining', '20:00')
            home_score = game_context.get('home_score', 0)
            away_score = game_context.get('away_score', 0)
            game_situation = game_context.get('game_situation', '比赛进行中')
            
            # 提取最新事件
            high_intensity_events = commentary_data.get('high_intensity_events', [])
            last_event = "比赛进行中"
            if high_intensity_events:
                latest_event = high_intensity_events[-1]
                last_event = latest_event.get('summary', '比赛进行中')
            
            # 提取关键信息
            key_talking_points = commentary_data.get('key_talking_points', [])
            momentum_score = commentary_data.get('momentum_score', 0)
            priority_level = commentary_data.get('priority_level', 1)
            
            # 根据文件名推断队伍信息（从比赛ID 2024030412 可以推断）
            # 这里使用固定的队伍信息，实际应用中可以从API获取
            home_team_name = "Edmonton Oilers"
            away_team_name = "Florida Panthers"
            
            # 格式化时间显示
            period_name = f"第{period}节" if period <= 3 else "加时赛" if period == 4 else f"第{period-3}次加时"
            
            return {
                'homeTeam': {
                    'name': home_team_name,
                    'score': home_score,
                    'abbreviation': 'EDM'
                },
                'awayTeam': {
                    'name': away_team_name, 
                    'score': away_score,
                    'abbreviation': 'FLA'
                },
                'period': period_name,
                'time': time_remaining,
                'lastEvent': last_event,
                'gameContext': {
                    'situation': game_situation,
                    'momentum': momentum_score,
                    'priority': priority_level,
                    'recommendation': commentary_data.get('recommendation', 'STANDARD')
                },
                'keyPoints': key_talking_points[:3],  # 只显示前3个要点
                'events': high_intensity_events[-5:] if high_intensity_events else [],  # 最近5个事件
                'intensity': self._calculate_intensity_level(momentum_score, high_intensity_events)
            }
            
        except Exception as e:
            print(f"⚠️ 提取比赛信息失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 返回默认信息
            return {
                'homeTeam': {'name': 'Edmonton Oilers', 'score': 0, 'abbreviation': 'EDM'},
                'awayTeam': {'name': 'Florida Panthers', 'score': 0, 'abbreviation': 'FLA'},
                'period': '第1节',
                'time': '20:00',
                'lastEvent': '比赛进行中',
                'gameContext': {
                    'situation': '比赛进行中',
                    'momentum': 0,
                    'priority': 1,
                    'recommendation': 'STANDARD'
                },
                'keyPoints': [],
                'events': [],
                'intensity': 'low'
            }
    
    def _calculate_intensity_level(self, momentum_score: int, events: list) -> str:
        """计算比赛强度等级"""
        if momentum_score >= 70 or len(events) >= 3:
            return 'high'
        elif momentum_score >= 40 or len(events) >= 2:
            return 'medium'
        else:
            return 'low'
    
    def get_team_info_from_game_id(self, game_id: str) -> tuple:
        """从比赛ID推断队伍信息（简化版本）"""
        # 这里是简化版本，实际应用中应该从NHL API获取
        team_mappings = {
            '2024030412': ('Edmonton Oilers', 'EDM', 'Florida Panthers', 'FLA'),
            '2024020123': ('New York Rangers', 'NYR', 'Philadelphia Flyers', 'PHI'),
            '2024020456': ('Edmonton Oilers', 'EDM', 'Calgary Flames', 'CGY')
        }
        
        return team_mappings.get(game_id, ('Home Team', 'HOME', 'Away Team', 'AWAY'))
    
    def simulate_commentary_pipeline(self, session_id: str, game_id: str, voice_style: str, client_id: str):
        """模拟解说pipeline（用于演示）"""
        demo_commentaries = [
            "比赛开始！多伦多枫叶队对阵波士顿棕熊队，今晚将在加拿大轮胎中心上演激烈对决！",
            "Connor McDavid带球快速突破，他的滑行速度令现场观众惊叹不已！",
            "传球！精彩的配合！Matthews接球后立即起脚射门！",
            "门将Swayman做出了世界级的扑救！这个扑救足以登上今日最佳集锦！",
            "进球！！！Auston Matthews为多伦多枫叶队攻入本场比赛的第一球！",
            "现场观众起立鼓掌，这是一个教科书般的进球配合！",
            "比赛继续进行，波士顿棕熊队正在寻找扳平比分的机会...",
            "David Pastrnak获得单刀机会！这是一个危险的反击！",
            "射门被扑出！Campbell门将展现出了出色的反应速度！",
            "第一节比赛结束，多伦多枫叶队暂时1:0领先波士顿棕熊队。"
        ]
        
        demo_game_data = {
            'homeTeam': {'name': '多伦多枫叶队', 'score': 0},
            'awayTeam': {'name': '波士顿棕熊队', 'score': 0},
            'period': '第1节',
            'time': '20:00',
            'lastEvent': '比赛开始'
        }
        
        commentary_index = 0
        game_time_minutes = 20
        
        while commentary_index < len(demo_commentaries):
            session = self.game_sessions.get(session_id)
            if not session or session['status'] == 'stopped':
                break
            
            if session['status'] == 'paused':
                threading.Event().wait(1)  # 暂停时等待
                continue
            
            commentary = demo_commentaries[commentary_index]
            
            # 发送解说文本
            self.socketio.emit('commentary', {
                'type': 'commentary',
                'data': {
                    'text': commentary,
                    'timestamp': datetime.now().isoformat(),
                    'style': voice_style
                }
            }, room=client_id)
            
            # 模拟音频生成
            audio_data = {
                'text': commentary,
                'style': voice_style,
                'url': f'/api/audio/{session_id}_{commentary_index}.wav',
                'duration': len(commentary) * 0.05  # 模拟音频时长
            }
            
            self.socketio.emit('audio', {
                'type': 'audio',
                'data': audio_data
            }, room=client_id)
            
            # 更新比赛数据
            if commentary_index == 4:  # 进球时
                demo_game_data['homeTeam']['score'] = 1
                demo_game_data['lastEvent'] = '进球 - Auston Matthews'
            
            game_time_minutes -= 2
            demo_game_data['time'] = f"{game_time_minutes}:{30 - (commentary_index * 3):02d}"
            
            self.socketio.emit('gameData', {
                'type': 'gameData',
                'data': demo_game_data
            }, room=client_id)
            
            commentary_index += 1
            threading.Event().wait(3)  # 等待3秒
        
        # 解说结束
        if session_id in self.game_sessions:
            del self.game_sessions[session_id]
        
        self.socketio.emit('status', {
            'type': 'completed',
            'data': {'status': 'completed', 'message': '解说已完成'}
        }, room=client_id)
    
    def stop_game_session(self, session_id: str):
        """停止游戏会话"""
        if session_id in self.game_sessions:
            self.game_sessions[session_id]['status'] = 'stopped'
            print(f"停止游戏会话: {session_id}")
            
            # 清理pipeline
            if session_id in self.active_pipelines:
                del self.active_pipelines[session_id]
    
    def run(self, debug=False):
        """启动服务器"""
        print(f"🏒 NHL Commentary Web Server 启动中...")
        print(f"📡 服务地址: http://{self.host}:{self.port}")
        print(f"🌐 Web界面: http://{self.host}:{self.port}")
        print(f"🔗 WebSocket: ws://{self.host}:{self.port}/socket.io/")
        print(f"⚡ 演示模式已启用 (WebSocket连接失败时自动启动)")
        
        # 设置信号处理
        def signal_handler(sig, frame):
            print("\n🛑 正在关闭服务器...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            self.socketio.run(
                self.app,
                host=self.host,
                port=self.port,
                debug=debug,
                allow_unsafe_werkzeug=True
            )
        except Exception as e:
            print(f"❌ 服务器启动失败: {e}")
            sys.exit(1)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NHL Commentary Web Server')
    parser.add_argument('--host', default='localhost', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=8080, help='服务器端口')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    # 创建并启动服务器
    server = NHLWebServer(host=args.host, port=args.port)
    server.run(debug=args.debug)

if __name__ == '__main__':
    main() 