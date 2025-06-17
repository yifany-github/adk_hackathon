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

from flask import Flask, render_template, send_from_directory, jsonify, request
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
            print(f"客户端连接: {client_id}, 总连接数: {len(self.clients)}")
            
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
            
            print(f"客户端断开: {client_id}, 剩余连接数: {len(self.clients)}")
        
        @self.socketio.on('start')
        def handle_start_commentary(data):
            """开始解说"""
            client_id = request.sid
            game_id = data.get('gameId')
            voice_style = data.get('voiceStyle', 'enthusiastic')
            
            if not game_id:
                emit('error', {
                    'type': 'error',
                    'data': {'message': '缺少gameId参数'}
                })
                return
            
            print(f"开始解说: 客户端={client_id}, 比赛={game_id}, 风格={voice_style}")
            
            try:
                # 创建游戏会话
                session_id = f"{client_id}_{game_id}"
                session = {
                    'client_id': client_id,
                    'game_id': game_id,
                    'voice_style': voice_style,
                    'status': 'running',
                    'start_time': datetime.now()
                }
                
                self.game_sessions[session_id] = session
                
                # 启动解说pipeline（在新线程中）
                pipeline_thread = threading.Thread(
                    target=self.run_commentary_pipeline,
                    args=(session_id, game_id, voice_style, client_id)
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
                print(f"启动解说失败: {e}")
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
    
    def run_commentary_pipeline(self, session_id: str, game_id: str, voice_style: str, client_id: str):
        """在单独线程中运行解说pipeline"""
        try:
            print(f"启动解说pipeline: {session_id}")
            
            # 这里集成实际的NHL pipeline
            # 为了演示，我们模拟解说生成
            self.simulate_commentary_pipeline(session_id, game_id, voice_style, client_id)
            
        except Exception as e:
            print(f"解说pipeline错误: {e}")
            self.socketio.emit('error', {
                'type': 'error',
                'data': {'message': f'解说pipeline错误: {str(e)}'}
            }, room=client_id)
    
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