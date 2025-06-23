"""
Sequential Agent V3 - Tools
Enhanced tools for complete data + commentary + audio processing
"""

import json
import os
from typing import Dict, Any, List
from datetime import datetime


def extract_complete_agent_outputs(raw_output: str) -> dict:
    """Extract outputs from all three agents (data, commentary, audio)"""
    result = {
        "data_agent": {},
        "commentary_agent": {},
        "audio_agent": {},
        "raw_debug": raw_output if len(raw_output) < 500 else raw_output[:500] + "..."
    }
    
    try:
        # Similar extraction logic as Sequential Agent V2 but extended for audio
        import re
        
        # Extract data agent output (first text field)
        first_text_pattern = r"text='(.*?)'\)"
        all_texts = re.findall(first_text_pattern, raw_output, re.DOTALL)
        
        if all_texts:
            # First text should be data agent
            data_json_str = all_texts[0]
            clean_data = data_json_str.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            try:
                parsed_data = json.loads(clean_data)
                if 'for_commentary_agent' in parsed_data:
                    result["data_agent"] = parsed_data
            except json.JSONDecodeError as e:
                result["data_agent"] = {"error": f"Data agent parse error: {str(e)}"}
        
        # Extract commentary agent output
        if '```json' in raw_output and 'commentary_sequence' in raw_output:
            json_start = raw_output.find('```json') + 7
            json_end = raw_output.find('```', json_start)
            
            if json_end > json_start:
                commentary_json = raw_output[json_start:json_end].strip()
                clean_commentary = commentary_json.replace('\\n', '\n').replace('\\"', '"')
                clean_commentary = clean_commentary.replace("\\'", "'")
                clean_commentary = clean_commentary.replace('\\\\', '\\')
                clean_commentary = clean_commentary.replace('\\u2019', "'")
                
                try:
                    parsed_commentary = json.loads(clean_commentary)
                    parsed_commentary = fix_broadcaster_names(parsed_commentary)
                    result["commentary_agent"] = parsed_commentary
                except json.JSONDecodeError as e:
                    result["commentary_agent"] = {"error": f"Commentary parse error: {str(e)[:100]}..."}
        
        # Extract audio agent output (look for audio processing results)
        if 'audio' in raw_output.lower() and ('status' in raw_output or 'processing' in raw_output):
            # Look for audio processing results in various formats
            audio_patterns = [
                r'"audio_agent":\s*({[^}]+})',
                r'"audio_segments":\s*(\[[^\]]+\])',
                r'"status":\s*"success".*?"audio_id":\s*"([^"]+)"'
            ]
            
            for pattern in audio_patterns:
                matches = re.findall(pattern, raw_output, re.DOTALL | re.IGNORECASE)
                if matches:
                    try:
                        if pattern.endswith('([^"]+)"'):  # audio_id pattern
                            result["audio_agent"] = {"audio_id": matches[0], "status": "success"}
                        else:
                            result["audio_agent"] = json.loads(matches[0])
                        break
                    except json.JSONDecodeError:
                        continue
        
        # If no audio output found, check for error messages
        if not result["audio_agent"]:
            if 'audio' in raw_output.lower() and 'error' in raw_output.lower():
                result["audio_agent"] = {"error": "Audio processing error detected", "status": "error"}
            else:
                result["audio_agent"] = {"status": "not_processed", "message": "Audio processing not detected"}
        
        return result
        
    except Exception as e:
        result["extraction_error"] = str(e)
        return result


def fix_broadcaster_names(commentary_data: dict) -> dict:
    """Fix broadcaster names to Alex Chen & Mike Rodriguez"""
    if "commentary_sequence" in commentary_data:
        for segment in commentary_data["commentary_sequence"]:
            if "speaker" in segment:
                speaker = segment["speaker"]
                # Map generic names to specific broadcasters
                if speaker in ["Commentator 1", "Play-by-play", "PBP", "Host", "Analyst1"]:
                    segment["speaker"] = "Alex Chen"
                elif speaker in ["Commentator 2", "Analyst", "Analyst2", "Color", "Color Commentator"]:
                    segment["speaker"] = "Mike Rodriguez"
    
    return commentary_data


def create_audio_processing_metadata(commentary_sequence: List[Dict], game_id: str, timestamp: str) -> Dict[str, Any]:
    """Create metadata for audio processing"""
    
    audio_segments_info = []
    
    for i, segment in enumerate(commentary_sequence):
        speaker = segment.get("speaker", "Unknown")
        text = segment.get("text", "")
        
        # Determine voice style
        voice_style = "enthusiastic"  # default
        if "alex chen" in speaker.lower():
            if any(word in text.lower() for word in ["goal", "score", "shot"]):
                voice_style = "enthusiastic"
            elif any(word in text.lower() for word in ["penalty", "overtime"]):
                voice_style = "dramatic"
        elif "mike rodriguez" in speaker.lower():
            if any(word in text.lower() for word in ["critical", "crucial"]):
                voice_style = "dramatic"
            else:
                voice_style = "calm"
        
        audio_segments_info.append({
            "segment_index": i,
            "speaker": speaker,
            "text": text,
            "voice_style": voice_style,
            "estimated_duration": len(text) * 0.05,  # rough estimate
            "game_id": game_id,
            "timestamp": timestamp
        })
    
    return {
        "game_id": game_id,
        "timestamp": timestamp,
        "total_segments": len(audio_segments_info),
        "audio_segments": audio_segments_info,
        "processing_time": datetime.now().isoformat()
    }


def format_complete_output(data_result: dict, commentary_result: dict, audio_result: dict) -> dict:
    """Format the complete output from all three agents"""
    
    return {
        "sequential_agent_v3": {
            "data_analysis": data_result,
            "commentary_generation": commentary_result,
            "audio_processing": audio_result,
            "pipeline_status": "complete" if all(
                r.get("status") == "success" for r in [data_result, commentary_result, audio_result]
            ) else "partial",
            "timestamp": datetime.now().isoformat()
        }
    }


def extract_audio_files_info(audio_result: dict) -> List[str]:
    """Extract list of generated audio files from audio processing result"""
    
    files = []
    
    if audio_result.get("status") == "success":
        # Check different possible structures
        if "audio_segments" in audio_result:
            for segment in audio_result["audio_segments"]:
                if "saved_file" in segment:
                    files.append(segment["saved_file"])
                elif "audio_file" in segment:
                    files.append(segment["audio_file"])
        
        elif "saved_file" in audio_result:
            files.append(audio_result["saved_file"])
    
    return files 