"""
Sequential Agent Tools - Simple utilities
"""

import json
import os
import re
import base64
import wave
from datetime import datetime


def extract_audio_from_result(result_text: str, game_id: str, timestamp_name: str):
    """Extract and save audio from Sequential Agent output"""
    audio_pattern = r'"audio_data":\s*"([A-Za-z0-9+/=]+)"'
    audio_matches = re.findall(audio_pattern, result_text)
    
    if not audio_matches:
        return []
    
    output_dir = f"audio_output/{game_id}"
    os.makedirs(output_dir, exist_ok=True)
    saved_files = []
    
    for i, audio_base64 in enumerate(audio_matches):
        try:
            audio_bytes = base64.b64decode(audio_base64)
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"sequential_{timestamp_name}_{i}_{timestamp}.wav"
            filepath = os.path.join(output_dir, filename)
            
            with wave.open(filepath, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(24000)
                wav_file.writeframes(audio_bytes)
            
            saved_files.append(filepath)
        except:
            continue
    
    return saved_files


def save_result(game_id: str, timestamp_file: str, result_text: str):
    """Save Sequential Agent result"""
    output_dir = f"data/sequential_agent_outputs/{game_id}"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp_name = os.path.basename(timestamp_file).replace('.json', '')
    output_file = f"{output_dir}/{timestamp_name}_sequential.json"
    
    result = {
        "game_id": game_id,
        "timestamp": timestamp_name,
        "workflow_output": result_text,
        "status": "success"
    }
    
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    return output_file