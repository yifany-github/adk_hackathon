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
    """Extract and save audio from Sequential Agent output (legacy)"""
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


def extract_and_save_sequential_audio(result_text: str, game_id: str, timestamp_name: str):
    """Extract audio from Sequential Agent and save with proper naming for live commentary"""
    
    # First, extract the commentary sequence to get proper speaker ordering
    commentary_sequence = []
    commentary_pattern = r'```json\n(\{[^`]*"commentary_sequence"[^`]*\})\n```'
    commentary_match = re.search(commentary_pattern, result_text, re.DOTALL)
    
    if commentary_match:
        try:
            commentary_output = commentary_match.group(1)
            commentary_output = commentary_output.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
            commentary_json = json.loads(commentary_output)
            commentary_sequence = commentary_json.get('commentary_sequence', [])
        except Exception as e:
            print(f"⚠️ Failed to parse commentary sequence: {e}")
    
    # Look for audio files mentioned in the Sequential Agent output
    audio_pattern = r'"audio_files":\s*\[([^\]]*)\]'
    audio_files_match = re.search(audio_pattern, result_text)
    
    if audio_files_match:
        # Parse the audio files list from the result
        audio_files_text = audio_files_match.group(1)
        # Extract individual file paths
        file_pattern = r'"([^"]*\.wav)"'
        existing_audio_files = re.findall(file_pattern, audio_files_text)
        
        if existing_audio_files and commentary_sequence:
            # Rename existing files to proper format
            output_dir = f"audio_output/{game_id}"
            os.makedirs(output_dir, exist_ok=True)
            renamed_files = []
            
            for i, (original_file, segment) in enumerate(zip(existing_audio_files, commentary_sequence)):
                if os.path.exists(original_file):
                    speaker = segment.get('speaker', f'speaker_{i+1}')
                    speaker_clean = speaker.replace(" ", "_").replace(".", "")
                    
                    # Format: 2024030412_1_00_00_Alex_Chen_01.wav
                    new_filename = f"{game_id}_{timestamp_name}_{speaker_clean}_{i+1:02d}.wav"
                    new_filepath = os.path.join(output_dir, new_filename)
                    
                    # Copy/move the file to the new location with proper naming
                    import shutil
                    shutil.copy2(original_file, new_filepath)
                    renamed_files.append(new_filepath)
                    print(f"💾 Renamed audio: {new_filename} (speaker: {speaker})")
            
            return renamed_files
    
    # Fallback: Look for audio_data patterns and create properly named files
    audio_pattern = r'"audio_data":\s*"([A-Za-z0-9+/=]+)"'
    audio_matches = re.findall(audio_pattern, result_text)
    
    if not audio_matches:
        print("⚠️ No audio data found in Sequential Agent output")
        return []
    
    output_dir = f"audio_output/{game_id}"
    os.makedirs(output_dir, exist_ok=True)
    saved_files = []
    
    # Use commentary sequence for proper speaker names and ordering
    for i, audio_base64 in enumerate(audio_matches):
        try:
            audio_bytes = base64.b64decode(audio_base64)
            
            # Get speaker from commentary sequence if available
            if i < len(commentary_sequence):
                speaker = commentary_sequence[i].get('speaker', f'speaker_{i+1}')
            else:
                # Fallback to pattern matching
                speaker_pattern = r'"speaker":\s*"([^"]+)"'
                speakers = re.findall(speaker_pattern, result_text)
                speaker = speakers[i] if i < len(speakers) else f"speaker_{i+1}"
            
            speaker_clean = speaker.replace(" ", "_").replace(".", "")
            
            # Format: 2024030412_1_00_00_Alex_Chen_01.wav
            filename = f"{game_id}_{timestamp_name}_{speaker_clean}_{i+1:02d}.wav"
            filepath = os.path.join(output_dir, filename)
            
            with wave.open(filepath, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(24000)
                wav_file.writeframes(audio_bytes)
            
            saved_files.append(filepath)
            print(f"💾 Saved audio: {filename} (speaker: {speaker})")
            
        except Exception as e:
            print(f"⚠️ Failed to save audio {i}: {e}")
            continue
    
    return saved_files


def save_result(game_id: str, timestamp_file: str, result_text: str):
    """Save Sequential Agent result and extract intermediate outputs"""
    output_dir = f"data/sequential_agent_outputs/{game_id}"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp_name = os.path.basename(timestamp_file).replace('.json', '').replace(f'{game_id}_', '')
    output_file = f"{output_dir}/{timestamp_name}_sequential.json"
    
    # Extract and save intermediate outputs for visibility
    save_intermediate_outputs(game_id, timestamp_name, result_text)
    
    result = {
        "game_id": game_id,
        "timestamp": timestamp_name,
        "workflow_output": result_text,
        "status": "success"
    }
    
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    return output_file


def save_intermediate_outputs(game_id: str, timestamp_name: str, result_text: str):
    """Extract and save intermediate data and commentary outputs for visibility"""
    
    # Extract data agent output
    data_pattern = r'parts=\[Part\([^}]*text=\'([^}]*"for_commentary_agent"[^}]*)\''
    data_match = re.search(data_pattern, result_text, re.DOTALL)
    
    if data_match:
        try:
            data_output = data_match.group(1)
            # Clean up escaped characters
            data_output = data_output.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
            
            # Parse as JSON
            data_json = json.loads(data_output)
            
            # Save data agent output
            data_dir = f"data/data_agent_outputs/{game_id}"
            os.makedirs(data_dir, exist_ok=True)
            data_file = f"{data_dir}/{timestamp_name}_sequential_data.json"
            
            with open(data_file, 'w') as f:
                json.dump(data_json, f, indent=2)
            
            print(f"💾 Saved data agent output: {data_file}")
            
        except Exception as e:
            print(f"⚠️ Failed to extract data agent output: {e}")
    
    # Extract commentary agent output
    commentary_pattern = r'```json\n(\{[^`]*"commentary_sequence"[^`]*\})\n```'
    commentary_match = re.search(commentary_pattern, result_text, re.DOTALL)
    
    if commentary_match:
        try:
            commentary_output = commentary_match.group(1)
            # Clean up escaped characters
            commentary_output = commentary_output.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
            
            # Parse as JSON
            commentary_json = json.loads(commentary_output)
            
            # Save commentary agent output
            commentary_dir = f"data/commentary_agent_outputs/{game_id}"
            os.makedirs(commentary_dir, exist_ok=True)
            commentary_file = f"{commentary_dir}/{timestamp_name}_sequential_commentary.json"
            
            with open(commentary_file, 'w') as f:
                json.dump(commentary_json, f, indent=2)
            
            print(f"💾 Saved commentary agent output: {commentary_file}")
            print(f"   📝 {len(commentary_json.get('commentary_sequence', []))} commentary segments")
            
        except Exception as e:
            print(f"⚠️ Failed to extract commentary agent output: {e}")
    
    print(f"🔄 Intermediate outputs processed for {timestamp_name}")