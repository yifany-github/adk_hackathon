#!/usr/bin/env python3
"""
NHL Commentary Server - Cloud Run Deployment
Web server that runs the commentary pipeline and displays generated dialogue
"""

import os
import sys
import json
import asyncio
import subprocess
import time
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

app = Flask(__name__)

# Available test games
TEST_GAMES = ["2024020001", "2024030412", "2024030413"]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>NHL Commentary System - ADK Multi-Agent Demo</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background: #1f4e79; color: white; padding: 20px; border-radius: 8px; }
        .game-buttons { margin: 20px 0; }
        .game-btn { 
            background: #2e7bc6; color: white; padding: 12px 20px; 
            margin: 10px; border: none; border-radius: 5px; cursor: pointer;
            text-decoration: none; display: inline-block;
        }
        .game-btn:hover { background: #1f4e79; }
        .commentary { 
            background: #f8f9fa; padding: 20px; border-left: 4px solid #2e7bc6; 
            margin: 20px 0; border-radius: 4px;
        }
        .speaker { font-weight: bold; color: #1f4e79; }
        .timestamp { color: #666; font-size: 0.9em; }
        .loading { color: #2e7bc6; font-style: italic; }
        .error { color: #d32f2f; }
        .stats { background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏒 NHL Commentary System</h1>
        <p>Multi-Agent Hockey Commentary Generation using Google ADK</p>
        <p><strong>Architecture:</strong> SequentialAgent → Data Agent → Commentary Agent</p>
    </div>
    
    <div class="game-buttons">
        <h2>Test Commentary Generation</h2>
        {% for game_id in games %}
        <a href="/generate/{{ game_id }}" class="game-btn">Generate Commentary: Game {{ game_id }}</a>
        {% endfor %}
    </div>
    
    {% if commentary_data %}
    <div class="commentary">
        <h2>🎙️ Generated Commentary - Game {{ game_id }}</h2>
        <div class="stats">
            <strong>Processing Stats:</strong> {{ stats.total_processed }} timestamps processed 
            in {{ "%.1f"|format(stats.total_time) }}s
        </div>
        
        {% for dialogue in commentary_data %}
        <div style="margin: 15px 0; padding: 10px; border-bottom: 1px solid #ddd;">
            <div class="timestamp">{{ dialogue.timestamp }}</div>
            {% for line in dialogue.commentary %}
            <p><span class="speaker">{{ line.speaker }}:</span> {{ line.text }}</p>
            {% endfor %}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    {% if error %}
    <div class="error">
        <h3>Error</h3>
        <p>{{ error }}</p>
    </div>
    {% endif %}
    
    {% if loading %}
    <div class="loading">
        <h3>🔄 Generating Commentary...</h3>
        <p>Multi-agent system processing NHL data. This may take 30-60 seconds.</p>
    </div>
    {% endif %}
</body>
</html>
"""

@app.route('/')
def home():
    """Homepage with game selection"""
    return render_template_string(HTML_TEMPLATE, games=TEST_GAMES)

@app.route('/generate/<game_id>')
def generate_commentary(game_id):
    """Generate commentary for a specific game"""
    if game_id not in TEST_GAMES:
        return render_template_string(HTML_TEMPLATE, 
                                    games=TEST_GAMES, 
                                    error=f"Game {game_id} not available. Available games: {', '.join(TEST_GAMES)}")
    
    try:
        # Show loading state
        start_time = time.time()
        
        # Run the commentary pipeline
        print(f"Starting commentary generation for game {game_id}")
        result = subprocess.run([
            'python', 'src/pipeline/live_commentary_pipeline_v2.py', 
            game_id, '4'  # 1 minute duration for demo
        ], capture_output=True, text=True, timeout=300)
        
        end_time = time.time()
        
        if result.returncode != 0:
            error_msg = f"Pipeline failed: {result.stderr}"
            print(f"Pipeline error: {error_msg}")
            return render_template_string(HTML_TEMPLATE, 
                                        games=TEST_GAMES, 
                                        error=error_msg)
        
        # Read generated commentary
        commentary_data = read_commentary_files(game_id)
        
        stats = {
            "total_processed": len(commentary_data),
            "total_time": end_time - start_time
        }
        
        return render_template_string(HTML_TEMPLATE, 
                                    games=TEST_GAMES,
                                    commentary_data=commentary_data,
                                    game_id=game_id,
                                    stats=stats)
        
    except subprocess.TimeoutExpired:
        return render_template_string(HTML_TEMPLATE, 
                                    games=TEST_GAMES, 
                                    error="Commentary generation timed out (5 minutes). System may need more time.")
    except Exception as e:
        print(f"Error generating commentary: {str(e)}")
        return render_template_string(HTML_TEMPLATE, 
                                    games=TEST_GAMES, 
                                    error=f"Error: {str(e)}")

def read_commentary_files(game_id):
    """Read and format generated commentary files"""
    commentary_data = []
    
    # Look for sequential agent outputs (primary)
    sequential_dir = Path(f"data/sequential_agent_outputs/{game_id}")
    if sequential_dir.exists():
        files = sorted(sequential_dir.glob("*_sequential.json"))
        for file_path in files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    formatted = format_commentary_data(data, file_path.name)
                    if formatted:
                        commentary_data.append(formatted)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    
    # Fallback: Look for commentary agent outputs
    if not commentary_data:
        commentary_dir = Path(f"data/commentary_agent_outputs/{game_id}")
        if commentary_dir.exists():
            files = sorted(commentary_dir.glob("*_commentary_session_aware.json"))
            for file_path in files:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        formatted = format_commentary_data(data, file_path.name)
                        if formatted:
                            commentary_data.append(formatted)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    return commentary_data

def format_commentary_data(data, filename):
    """Format commentary data for display"""
    try:
        # Extract timestamp from filename
        timestamp = filename.replace('_sequential.json', '').replace('_commentary_session_aware.json', '')
        
        # Handle different data structures
        commentary_lines = []
        
        if isinstance(data, dict):
            # Check for sequential agent format first
            if 'commentary_agent' in data:
                commentary_agent = data['commentary_agent']
                if 'commentary_sequence' in commentary_agent:
                    # Sequential agent format with Alex Chen & Mike Rodriguez
                    for item in commentary_agent['commentary_sequence']:
                        if isinstance(item, dict) and 'speaker' in item and 'text' in item:
                            commentary_lines.append({
                                'speaker': item['speaker'],
                                'text': item['text']
                            })
            elif 'dialogue' in data:
                # Commentary agent format
                dialogue = data['dialogue']
                if isinstance(dialogue, list):
                    for item in dialogue:
                        if isinstance(item, dict) and 'speaker' in item and 'text' in item:
                            commentary_lines.append({
                                'speaker': item['speaker'],
                                'text': item['text']
                            })
            elif 'commentary' in data:
                # Alternative format
                commentary = data['commentary']
                if isinstance(commentary, str):
                    # Parse string commentary into speaker/text pairs
                    lines = commentary.split('\n')
                    for line in lines:
                        if ':' in line:
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                commentary_lines.append({
                                    'speaker': parts[0].strip(),
                                    'text': parts[1].strip()
                                })
            else:
                # Generic text output
                if 'text' in data:
                    commentary_lines.append({
                        'speaker': 'System',
                        'text': str(data['text'])
                    })
        
        # If no specific format found, try to extract any text
        if not commentary_lines and isinstance(data, dict):
            text_content = str(data)
            if len(text_content) > 50:  # Only if substantial content
                commentary_lines.append({
                    'speaker': 'Commentary System',
                    'text': text_content[:500] + "..." if len(text_content) > 500 else text_content
                })
        
        if commentary_lines:
            return {
                'timestamp': timestamp,
                'commentary': commentary_lines
            }
        
    except Exception as e:
        print(f"Error formatting commentary data: {e}")
    
    return None

@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "nhl-commentary-system"}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)