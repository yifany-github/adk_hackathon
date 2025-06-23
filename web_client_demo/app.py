#!/usr/bin/env python3
"""
NHL Live Commentary Web Client

Modern Flask web application for the NHL Live Commentary System.
Integrates with live_commentary_pipeline_v3.py for complete real-time processing with audio.

Features:
- Start/stop live commentary using pipeline v3
- Real-time GameBoard status display
- Audio playback for generated commentary
- Game progress visualization
- Performance monitoring
- API key configuration for GEMINI_API_KEY and GOOGLE_API_KEY
- Optimized for Google Cloud deployment

Usage: python web_client_demo/app.py
"""

import os
import sys
import json
import asyncio
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import tempfile

from flask import Flask, render_template, request, jsonify, send_file, session
from flask_socketio import SocketIO, emit
import dotenv

# Add project paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append('src')
sys.path.append('src/board')

# Load environment variables
dotenv.load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nhl_live_commentary_2024_secure_key')
socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False, async_mode='threading')

class LiveCommentaryState:
    """Global state management for live commentary session"""
    
    def __init__(self):
        self.current_game_id: Optional[str] = None
        self.is_running: bool = False
        self.pipeline_process: Optional[subprocess.Popen] = None
        self.duration_minutes: int = 5
        self.start_time: Optional[datetime] = None
        self.processed_files: int = 0
        self.total_audio_files: int = 0
        self.current_score: str = "0-0"
        self.game_teams: Dict[str, str] = {"away": "Away", "home": "Home"}
        self.latest_audio_files: List[Dict] = []
        self.pipeline_logs: List[Dict] = []
        self.gameboard_states: List[Dict] = []
        self.api_keys: Dict[str, str] = {}

    def reset(self):
        """Reset state for new session"""
        self.current_game_id = None
        self.is_running = False
        self.pipeline_process = None
        self.start_time = None
        self.processed_files = 0
        self.total_audio_files = 0
        self.current_score = "0-0"
        self.game_teams = {"away": "Away", "home": "Home"}
        self.latest_audio_files = []
        self.pipeline_logs = []
        self.gameboard_states = []

live_state = LiveCommentaryState()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/config/keys', methods=['GET', 'POST'])
def manage_api_keys():
    """Manage API keys configuration"""
    if request.method == 'GET':
        # Return current key status (without exposing actual keys)
        return jsonify({
            "gemini_configured": bool(live_state.api_keys.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')),
            "google_configured": bool(live_state.api_keys.get('GOOGLE_API_KEY') or os.environ.get('GOOGLE_API_KEY')),
            "session_keys": list(live_state.api_keys.keys())
        })
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            gemini_key = data.get('gemini_api_key', '').strip()
            google_key = data.get('google_api_key', '').strip()
            
            # Update session keys
            if gemini_key:
                live_state.api_keys['GEMINI_API_KEY'] = gemini_key
            if google_key:
                live_state.api_keys['GOOGLE_API_KEY'] = google_key
            
            return jsonify({
                "status": "success",
                "message": "API keys updated successfully",
                "gemini_configured": bool(live_state.api_keys.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')),
                "google_configured": bool(live_state.api_keys.get('GOOGLE_API_KEY') or os.environ.get('GOOGLE_API_KEY'))
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/games/available')
def get_available_games():
    """Get available game data"""
    try:
        # Build correct data directory path
        current_dir = Path(__file__).parent  # web_client_demo directory
        project_root = current_dir.parent    # adk_hackathon directory
        data_dir = project_root / "data" / "live"
        
        if not data_dir.exists():
            return jsonify({"games": [], "message": f"No data directory found at {data_dir}"})
        
        games = []
        for game_dir in data_dir.iterdir():
            if game_dir.is_dir() and len(game_dir.name) == 10 and game_dir.name.isdigit():
                timestamp_files = list(game_dir.glob("*.json"))
                if timestamp_files:
                    # Extract team information from latest file
                    teams_info = {"away_team": "Away", "home_team": "Home"}
                    try:
                        latest_file = max(timestamp_files, key=lambda x: x.stat().st_mtime)
                        with open(latest_file, 'r') as f:
                            data = json.load(f)
                            if 'activities' in data and len(data['activities']) > 0:
                                game_stats = data['activities'][0].get('gameStats', {})
                                if 'home_team' in game_stats and 'away_team' in game_stats:
                                    teams_info = {
                                        "away_team": game_stats['away_team'],
                                        "home_team": game_stats['home_team']
                                    }
                    except Exception as e:
                        print(f"Error reading team info from {latest_file}: {e}")
                    
                    games.append({
                        "game_id": game_dir.name,
                        "timestamp_files": len(timestamp_files),
                        "last_modified": max(f.stat().st_mtime for f in timestamp_files),
                        "teams": teams_info
                    })
        
        # Sort by last modified time (newest first)
        games.sort(key=lambda x: x['last_modified'], reverse=True)
        
        return jsonify({
            "games": games, 
            "data_dir": str(data_dir.absolute()),
            "total_games": len(games)
        })
        
    except Exception as e:
        print(f"Error in get_available_games: {e}")
        return jsonify({"error": str(e), "games": []}), 500

@app.route('/api/commentary/start', methods=['POST'])
def start_commentary():
    """Start live commentary using pipeline v3"""
    try:
        data = request.get_json()
        game_id = data.get('game_id')
        duration = data.get('duration', 5)
        
        if live_state.is_running:
            return jsonify({"error": "Commentary is already running"}), 400
        
        if not game_id:
            return jsonify({"error": "Game ID is required"}), 400
        
        # Validate game ID format
        if len(game_id) != 10 or not game_id.isdigit():
            return jsonify({"error": "Invalid game ID format. Please use a 10-digit game ID."}), 400
        
        # Check API keys
        if not (live_state.api_keys.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')):
            return jsonify({"error": "GEMINI_API_KEY is required. Please configure it in settings."}), 400
        
        if not (live_state.api_keys.get('GOOGLE_API_KEY') or os.environ.get('GOOGLE_API_KEY')):
            return jsonify({"error": "GOOGLE_API_KEY is required. Please configure it in settings."}), 400
        
        # Update state
        live_state.current_game_id = game_id
        live_state.duration_minutes = duration
        live_state.is_running = True
        live_state.start_time = datetime.now()
        live_state.processed_files = 0
        live_state.total_audio_files = 0
        live_state.pipeline_logs = []
        
        # Initialize team info from live data
        try:
            current_dir = Path(__file__).parent
            project_root = current_dir.parent
            live_data_dir = project_root / "data" / "live" / game_id
            if live_data_dir.exists():
                live_json_files = list(live_data_dir.glob("*.json"))
                if live_json_files:
                    with open(live_json_files[0], 'r') as f:
                        live_data = json.load(f)
                        if 'activities' in live_data and len(live_data['activities']) > 0:
                            activity = live_data['activities'][0]
                            if 'gameStats' in activity:
                                stats = activity['gameStats']
                                live_state.game_teams = {
                                    'home': stats.get('home_team', 'Home'),
                                    'away': stats.get('away_team', 'Away')
                                }
                                live_state.current_score = f"{stats.get('away_score', 0)}-{stats.get('home_score', 0)}"
        except Exception as e:
            print(f"Error initializing team info: {e}")
        
        # Start pipeline in background
        threading.Thread(target=run_pipeline_v3_background, args=(game_id, duration)).start()
        
        # Start progress monitoring
        threading.Thread(target=monitor_pipeline_progress, args=(game_id,)).start()
        
        socketio.emit('commentary_started', {
            'game_id': game_id,
            'duration': duration,
            'start_time': live_state.start_time.isoformat()
        })
        
        return jsonify({
            "status": "started",
            "game_id": game_id,
            "duration": duration
        })
        
    except Exception as e:
        print(f"Error in start_commentary: {str(e)}")
        live_state.is_running = False
        return jsonify({"error": str(e)}), 500

@app.route('/api/commentary/stop', methods=['POST'])
def stop_commentary():
    """Stop live commentary"""
    try:
        if not live_state.is_running:
            return jsonify({"error": "No commentary is running"}), 400
        
        # Stop pipeline process
        if live_state.pipeline_process and live_state.pipeline_process.poll() is None:
            live_state.pipeline_process.terminate()
            try:
                live_state.pipeline_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                live_state.pipeline_process.kill()
                live_state.pipeline_process.wait()
        
        live_state.is_running = False
        live_state.pipeline_process = None
        
        socketio.emit('commentary_stopped', {
            'game_id': live_state.current_game_id,
            'duration': time.time() - live_state.start_time.timestamp() if live_state.start_time else 0
        })
        
        return jsonify({"status": "stopped"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/commentary/status')
def get_commentary_status():
    """Get current commentary status"""
    try:
        status = {
            "is_running": live_state.is_running,
            "game_id": live_state.current_game_id,
            "duration_minutes": live_state.duration_minutes,
            "processed_files": live_state.processed_files,
            "total_audio_files": live_state.total_audio_files,
            "current_score": live_state.current_score,
            "game_teams": live_state.game_teams,
            "start_time": live_state.start_time.isoformat() if live_state.start_time else None,
            "runtime_seconds": int(time.time() - live_state.start_time.timestamp()) if live_state.start_time else 0,
            "latest_audio_files": live_state.latest_audio_files[-5:],  # Last 5 files
            "api_keys_configured": {
                "gemini": bool(live_state.api_keys.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')),
                "google": bool(live_state.api_keys.get('GOOGLE_API_KEY') or os.environ.get('GOOGLE_API_KEY'))
            }
        }
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/audio/<game_id>')
def list_audio_files(game_id):
    """List available audio files for a game"""
    try:
        # Build correct audio directory path
        current_dir = Path(__file__).parent  # web_client_demo directory
        project_root = current_dir.parent    # adk_hackathon directory
        audio_dir = project_root / "audio_output"
        
        audio_files = []
        
        # Check main audio_output directory
        if audio_dir.exists():
            # Look for audio files related to this game
            for audio_file in audio_dir.glob(f"*{game_id}*.wav"):
                try:
                    file_stats = audio_file.stat()
                    audio_files.append({
                        "filename": audio_file.name,
                        "size": file_stats.st_size,
                        "created": file_stats.st_mtime,
                        "url": f"/api/audio/{game_id}/{audio_file.name}"
                    })
                except Exception as e:
                    print(f"Error getting stats for {audio_file}: {e}")
        
        # Also check sequential agent outputs for audio files
        sequential_dir = project_root / "data" / "sequential_agent_v3_outputs" / game_id
        
        if sequential_dir.exists():
            for json_file in sequential_dir.glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        if 'audio_agent' in data:
                            audio_segments = data['audio_agent'].get('audio_segments', [])
                            for segment in audio_segments:
                                if segment.get('status') == 'success' and 'saved_file' in segment:
                                    # Build absolute path to audio file
                                    audio_path = project_root / segment['saved_file']
                                    if audio_path.exists():
                                        file_stats = audio_path.stat()
                                        audio_files.append({
                                            "filename": audio_path.name,
                                            "size": file_stats.st_size,
                                            "created": file_stats.st_mtime,
                                            "url": f"/api/audio/{game_id}/{audio_path.name}",
                                            "transcript": segment.get('transcript', '')
                                        })
                except Exception as e:
                    print(f"Error reading audio info from {json_file}: {e}")
        
        # Remove duplicates and sort by filename number
        unique_files = {}
        for file_info in audio_files:
            unique_files[file_info['filename']] = file_info
        
        audio_files = list(unique_files.values())
        
        # Sort by the number at the beginning of filename (1_, 2_, 3_, etc.)
        def extract_number_from_filename(filename):
            try:
                return int(filename.split('_')[0])
            except:
                return 999  # Put files without numbers at the end
        
        audio_files.sort(key=lambda x: extract_number_from_filename(x['filename']))
        
        return jsonify({"audio_files": audio_files})
        
    except Exception as e:
        print(f"Error in list_audio_files: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/audio/<game_id>/<path:filename>')
def serve_audio(game_id, filename):
    """Serve audio files"""
    try:
        # Build correct paths using project root
        current_dir = Path(__file__).parent  # web_client_demo directory
        project_root = current_dir.parent    # adk_hackathon directory
        
        # Try multiple potential locations
        potential_paths = [
            project_root / "audio_output" / filename,
            project_root / "data" / "sequential_agent_v3_outputs" / game_id / filename,
            project_root / "audio_output" / game_id / filename
        ]
        
        for audio_path in potential_paths:
            if audio_path.exists():
                return send_file(
                    str(audio_path),
                    mimetype='audio/wav',
                    as_attachment=False,
                    download_name=filename
                )
        
        return jsonify({"error": "Audio file not found"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs')
def get_logs():
    """Get pipeline logs"""
    try:
        return jsonify({"logs": live_state.pipeline_logs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run_pipeline_v3_background(game_id: str, duration: int):
    """Run pipeline v3 in background thread"""
    try:
        # Prepare environment with API keys
        env = os.environ.copy()
        if live_state.api_keys.get('GEMINI_API_KEY'):
            env['GEMINI_API_KEY'] = live_state.api_keys['GEMINI_API_KEY']
        if live_state.api_keys.get('GOOGLE_API_KEY'):
            env['GOOGLE_API_KEY'] = live_state.api_keys['GOOGLE_API_KEY']
        
        # Build correct pipeline path
        current_dir = Path(__file__).parent  # web_client_demo directory
        project_root = current_dir.parent    # adk_hackathon directory
        pipeline_path = project_root / "src" / "pipeline" / "live_commentary_pipeline_v3.py"
        
        if not pipeline_path.exists():
            raise FileNotFoundError(f"Could not find pipeline at {pipeline_path}")
        
        # Run pipeline v3 from project root directory
        cmd = [
            sys.executable, 
            str(pipeline_path),
            game_id,
            str(duration)
        ]
        
        print(f"Starting pipeline v3 with command: {' '.join(cmd)}")
        print(f"Working directory: {project_root}")
        print(f"Pipeline path: {pipeline_path}")
        
        live_state.pipeline_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            env=env,
            bufsize=1,
            cwd=str(project_root)  # Run from project root
        )
        
        # Read output line by line
        for line in iter(live_state.pipeline_process.stdout.readline, ''):
            if line:
                # Process and improve log messages
                processed_message = process_log_message(line.strip())
                
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "message": processed_message,
                    "level": determine_log_level(processed_message)
                }
                live_state.pipeline_logs.append(log_entry)
                
                # Emit to clients
                socketio.emit('pipeline_log', log_entry)
                
                # Keep only last 200 log entries
                if len(live_state.pipeline_logs) > 200:
                    live_state.pipeline_logs.pop(0)
        
        # Process finished
        return_code = live_state.pipeline_process.wait()
        
        if return_code == 0:
            socketio.emit('pipeline_completed', {'game_id': game_id})
        else:
            socketio.emit('pipeline_error', {'game_id': game_id, 'return_code': return_code})
            
    except Exception as e:
        print(f"Pipeline background error: {e}")
        socketio.emit('pipeline_error', {'error': str(e)})
    finally:
        live_state.is_running = False
        live_state.pipeline_process = None

def monitor_pipeline_progress(game_id: str):
    """Monitor pipeline progress and update statistics"""
    while live_state.is_running:
        try:
            # Build correct output directory path
            current_dir = Path(__file__).parent  # web_client_demo directory
            project_root = current_dir.parent    # adk_hackathon directory
            output_dir = project_root / "data" / "sequential_agent_v3_outputs" / game_id
            
            # Update processed files count
            if output_dir and output_dir.exists():
                live_state.processed_files = len(list(output_dir.glob("*_sequential_v3.json")))
            
                # Update audio files count
                audio_files = []
                for json_file in output_dir.glob("*.json"):
                    try:
                        with open(json_file, 'r') as f:
                            data = json.load(f)
                            if 'audio_agent' in data:
                                audio_segments = data['audio_agent'].get('audio_segments', [])
                                for segment in audio_segments:
                                    if segment.get('status') == 'success' and 'saved_file' in segment:
                                        audio_files.append(segment['saved_file'])
                    except Exception:
                        pass
                
                live_state.total_audio_files = len(set(audio_files))
                live_state.latest_audio_files = audio_files[-10:]  # Keep last 10
                
                # Update game score and teams if available
                try:
                    # First try to get team info from live data
                    live_data_dir = project_root / "data" / "live" / game_id
                    if live_data_dir.exists():
                        live_json_files = list(live_data_dir.glob("*.json"))
                        if live_json_files:
                            with open(live_json_files[0], 'r') as f:
                                live_data = json.load(f)
                                if 'activities' in live_data and len(live_data['activities']) > 0:
                                    activity = live_data['activities'][0]
                                    if 'gameStats' in activity:
                                        stats = activity['gameStats']
                                        live_state.game_teams = {
                                            'home': stats.get('home_team', 'Home'),
                                            'away': stats.get('away_team', 'Away')
                                        }
                                        live_state.current_score = f"{stats.get('away_score', 0)}-{stats.get('home_score', 0)}"
                    
                    # Also try sequential outputs for updated scores
                    json_files = list(output_dir.glob("*_sequential_v3.json"))
                    if json_files:
                        latest_output = max(json_files, key=lambda x: x.stat().st_mtime)
                        with open(latest_output, 'r') as f:
                            data = json.load(f)
                            if 'gameboard_state' in data:
                                board_state = data['gameboard_state']
                                if 'score' in board_state:
                                    live_state.current_score = board_state['score']
                                if 'teams' in board_state:
                                    live_state.game_teams = board_state['teams']
                except Exception as e:
                    print(f"Error updating game info: {e}")
            
            # Emit progress update
            socketio.emit('progress_update', {
                'processed_files': live_state.processed_files,
                'total_audio_files': live_state.total_audio_files,
                'current_score': live_state.current_score,
                'game_teams': live_state.game_teams,
                'runtime_seconds': int(time.time() - live_state.start_time.timestamp()) if live_state.start_time else 0
            })
            
            time.sleep(2)  # Update every 2 seconds
            
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(5)

def process_log_message(message: str) -> str:
    """Process and improve log messages for better user understanding"""
    # Replace confusing API key message
    if "Both GOOGLE_API_KEY and GEMINI_API_KEY are set. Using GOOGLE_API_KEY." in message:
        return message.replace(
            "Both GOOGLE_API_KEY and GEMINI_API_KEY are set. Using GOOGLE_API_KEY.",
            "🎵 Using Google/Gemini API for audio generation"
        )
    
    # Detect fallback audio generation (TTS quota exceeded)
    if "nhl_fallback" in message.lower() and ("generating" in message.lower() or "created" in message.lower()):
        return f"⚠️ TTS quota exceeded, using fallback audio generation - {message}"
    
    return message

def determine_log_level(line: str) -> str:
    """Determine log level from line content"""
    line_lower = line.lower()
    if 'error' in line_lower or '❌' in line:
        return 'error'
    elif 'warning' in line_lower or '⚠️' in line or 'fallback' in line_lower:
        return 'warning'
    elif 'success' in line_lower or '✅' in line or '🎵' in line:
        return 'success'
    elif 'info' in line_lower or '📊' in line or '🏒' in line:
        return 'info'
    else:
        return 'debug'

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    emit('connected', {'status': 'Connected to NHL Live Commentary'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    print('Client disconnected')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"🏒 NHL Live Podcast System")
    print(f"   Running on port: {port}")
    print(f"   Debug mode: {debug}")
    print(f"   Using pipeline: live_commentary_pipeline_v3.py")
    
    socketio.run(app, host='0.0.0.0', port=port, debug=debug) 