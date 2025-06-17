#!/usr/bin/env python3
"""
NHL Commentary Web Server 启动脚本
简化的启动器，包含依赖检查和错误处理
"""

import os
import sys
import subprocess
import importlib
from pathlib import Path

def check_dependencies():
    """检查并安装必要的依赖"""
    required_packages = [
        'flask',
        'flask_socketio',
        'eventlet'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package} 已安装")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} 未安装")
    
    if missing_packages:
        print(f"\n📦 正在安装缺失的依赖包...")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install',
                'Flask>=2.3.0',
                'Flask-SocketIO>=5.3.0', 
                'eventlet>=0.33.0'
            ])
            print("✅ 依赖安装完成!")
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败: {e}")
            print("请手动运行: pip install Flask Flask-SocketIO eventlet")
            return False
    
    return True

class SimpleNHLWebServer:
    """简化的NHL Web服务器"""
    
    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.clients = set()
        self.game_sessions = {}
        
    def create_app(self):
        """创建Flask应用"""
        from flask import Flask, send_from_directory, jsonify, request
        from flask_socketio import SocketIO, emit
        import threading
        from datetime import datetime
        import json
        
        app = Flask(__name__, static_folder='.')
        app.config['SECRET_KEY'] = 'nhl_commentary_secret'
        
        # 创建SocketIO
        socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
        
        @app.route('/')
        def index():
            return send_from_directory('.', 'index.html')
        
        @app.route('/<path:filename>')
        def serve_static(filename):
            return send_from_directory('.', filename)
        
        @app.route('/api/status')
        def get_status():
            return jsonify({
                'status': 'running',
                'clients': len(self.clients),
                'timestamp': datetime.now().isoformat()
            })
        
        @socketio.on('connect')
        def handle_connect():
            client_id = request.sid
            self.clients.add(client_id)
            print(f"🔗 客户端连接: {client_id}")
            
            emit('status', {
                'type': 'connection',
                'data': {'status': 'connected', 'clientId': client_id}
            })
        
        @socketio.on('disconnect')
        def handle_disconnect():
            client_id = request.sid
            if client_id in self.clients:
                self.clients.remove(client_id)
            print(f"🔌 客户端断开: {client_id}")
        
        @socketio.on('start')
        def handle_start(data):
            client_id = request.sid
            game_id = data.get('gameId', '2024030412')
            voice_style = data.get('voiceStyle', 'enthusiastic')
            language = data.get('language', 'zh-CN')  # 添加语言参数
            
            print(f"🏒 开始解说: {game_id} (风格: {voice_style}, 语言: {language})")
            
            # 启动演示解说
            thread = threading.Thread(
                target=self.run_demo_commentary,
                args=(client_id, game_id, voice_style, language, socketio)
            )
            thread.daemon = True
            thread.start()
            
            emit('status', {
                'type': 'started',
                'data': {'gameId': game_id, 'status': 'running'}
            })
        
        @socketio.on('stop')
        def handle_stop():
            client_id = request.sid
            if client_id in self.game_sessions:
                self.game_sessions[client_id]['status'] = 'stopped'
            
            emit('status', {
                'type': 'stopped', 
                'data': {'status': 'stopped'}
            })
        
        @socketio.on('pause')
        def handle_pause():
            client_id = request.sid
            if client_id in self.game_sessions:
                self.game_sessions[client_id]['status'] = 'paused'
            
            emit('status', {
                'type': 'paused',
                'data': {'status': 'paused'}
            })
        
        @socketio.on('resume')
        def handle_resume():
            client_id = request.sid
            if client_id in self.game_sessions:
                self.game_sessions[client_id]['status'] = 'running'
            
            emit('status', {
                'type': 'resumed',
                'data': {'status': 'running'}
            })
        
        self.app = app
        self.socketio = socketio
        return app, socketio
    
    def run_demo_commentary(self, client_id, game_id, voice_style, language, socketio):
        """运行演示解说"""
        import time
        from datetime import datetime
        
        # 设置会话状态
        self.game_sessions[client_id] = {'status': 'running'}
        
        # 根据语言选择解说内容
        if language == 'en-US':
            commentaries = [
                "🏒 Game on! Toronto Maple Leafs hosting the Boston Bruins at home!",
                "⚡ McDavid with a lightning-fast breakaway, incredible speed!",
                "🎯 Matthews takes the shot!",
                "🥅 What a spectacular save by the goaltender!",
                "⚽ GOAL!!! Toronto Maple Leafs light the lamp!",
                "🎉 The crowd erupts in celebration!",
                "🏒 Play continues as Boston looks for the equalizer...",
                "💨 Pastrnak on a blazing counterattack!",
                "🛡️ Defensive coverage comes through just in time!",
                "⏰ End of the first period!"
            ]
            
            game_data = {
                'homeTeam': {'name': 'Toronto Maple Leafs', 'score': 0},
                'awayTeam': {'name': 'Boston Bruins', 'score': 0},
                'period': '1st Period',
                'time': '20:00',
                'lastEvent': 'Game Start'
            }
        else:  # 中文
            commentaries = [
                "🏒 比赛开始！多伦多枫叶队主场迎战波士顿棕熊队！",
                "⚡ McDavid带球快速突破，速度惊人！",
                "🎯 Matthews起脚射门！",
                "🥅 门将做出精彩扑救！",
                "⚽ 进球！！！多伦多枫叶队得分！",
                "🎉 现场观众起立鼓掌！",
                "🏒 比赛继续，波士顿寻找扳平机会...",
                "💨 Pastrnak高速反击！",
                "🛡️ 防守球员及时回防！",
                "⏰ 第一节比赛结束！"
            ]
            
            game_data = {
                'homeTeam': {'name': '多伦多枫叶队', 'score': 0},
                'awayTeam': {'name': '波士顿棕熊队', 'score': 0},
                'period': '第1节',
                'time': '20:00',
                'lastEvent': '比赛开始'
            }
        
        for i, commentary in enumerate(commentaries):
            session = self.game_sessions.get(client_id, {})
            if session.get('status') == 'stopped':
                break
            
            # 等待暂停状态
            while session.get('status') == 'paused':
                time.sleep(1)
                session = self.game_sessions.get(client_id, {})
                if session.get('status') == 'stopped':
                    return
            
            # 发送解说
            socketio.emit('commentary', {
                'type': 'commentary',
                'data': {
                    'text': commentary,
                    'timestamp': datetime.now().isoformat(),
                    'style': voice_style
                }
            }, room=client_id)
            
            # 发送模拟音频
            socketio.emit('audio', {
                'type': 'audio',
                'data': {
                    'text': commentary,
                    'style': voice_style,
                    'url': f'data:audio/wav;base64,{commentary}',  # 占位符
                    'duration': 3
                }
            }, room=client_id)
            
            # 更新比赛数据
            if i == 4:  # 进球
                game_data['homeTeam']['score'] = 1
                game_data['lastEvent'] = '进球 - Auston Matthews'
            
            game_data['time'] = f"{20 - i * 2}:{(30 - i * 5) % 60:02d}"
            
            socketio.emit('gameData', {
                'type': 'gameData',
                'data': game_data
            }, room=client_id)
            
            time.sleep(3)  # 间隔3秒
        
        # 清理会话
        if client_id in self.game_sessions:
            del self.game_sessions[client_id]
        
        socketio.emit('status', {
            'type': 'completed',
            'data': {'status': 'completed', 'message': '演示解说完成'}
        }, room=client_id)
    
    def run(self):
        """启动服务器"""
        print(f"""
🏒 NHL Commentary Web Client
=============================
📍 服务地址: http://{self.host}:{self.port}
🌐 打开浏览器访问上述地址开始使用
⚡ 支持演示模式 (无需后端API)
🎮 键盘快捷键:
   Ctrl+Space: 开始/暂停
   Ctrl+S: 停止
   Ctrl+M: 静音
=============================
        """)
        
        try:
            app, socketio = self.create_app()
            socketio.run(app, host=self.host, port=self.port, debug=False)
        except Exception as e:
            print(f"❌ 服务器启动失败: {e}")
            sys.exit(1)

def main():
    """主函数"""
    print("🏒 NHL Commentary Web Server")
    print("=" * 40)
    
    # 检查依赖
    if not check_dependencies():
        print("⚠️  请先安装必要的依赖包")
        sys.exit(1)
    
    # 检查文件
    required_files = ['index.html', 'styles.css', 'script.js']
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 缺少必要文件: {', '.join(missing_files)}")
        print("请确保所有文件都在当前目录中")
        sys.exit(1)
    
    # 启动服务器
    server = SimpleNHLWebServer()
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n👋 服务器已关闭")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == '__main__':
    main() 