"""
Pipeline utility functions for Sequential Agent V3 processing
Enhanced to support complete Data + Commentary + Audio pipeline
"""

import json
import os
import re
import time
from google.genai.types import Part, UserContent
from typing import Dict, Any, List


async def process_timestamp_with_session_v3(agent, game_id: str, timestamp_file: str, session, runner, board_context: dict, commentary_context: dict = None) -> dict:
    """Process timestamp with ADK session for Sequential Agent V3 (includes audio processing)"""
    try:
        # Load timestamp data
        with open(timestamp_file, 'r') as f:
            timestamp_data = json.load(f)
        
        # Extract timestamp from filename for audio naming
        basename = os.path.basename(timestamp_file).replace('.json', '')
        # Extract timestamp part from filename like "2024030412_1_01_15"
        parts = basename.split('_')
        if len(parts) >= 4:
            timestamp = f"{parts[1]}_{parts[2]}_{parts[3]}"  # "1_01_15"
        else:
            timestamp = "1_00_00"  # fallback
        
        # Set timestamp and context in the sequential agent
        if hasattr(agent, 'set_current_timestamp'):
            agent.set_current_timestamp(timestamp)
            print(f"🕐 Set timestamp for audio naming: {timestamp}")
        
        if hasattr(agent, 'set_current_game_context') and board_context:
            agent.set_current_game_context(board_context)
            print(f"🎮 Set game context for audio processing")
        
        # Create enhanced prompt for V3
        from ..agents.sequential_agent_v3.prompts import get_workflow_prompt_v3
        prompt = get_workflow_prompt_v3(game_id, timestamp_data, board_context, commentary_context)
        
        # Use Sequential Agent V3's custom process_message method for complete pipeline
        print(f"🔄 Processing with Sequential Agent V3 custom pipeline...")
        # agent is our NHLSequentialAgentV3 wrapper, not the inner SequentialAgent
        complete_result = await agent.process_message(prompt)
        
        # Extract commentary dialogue for context continuity
        commentary_dialogue = extract_commentary_dialogue_v3(complete_result)
        
        # Extract audio files information
        audio_files = extract_audio_files_info_v3(complete_result)
        
        timestamp_name = os.path.basename(timestamp_file).replace('.json', '').replace(f'{game_id}_', '')
        
        return {
            "status": "success",
            "timestamp": timestamp_name,
            "response": complete_result,
            "commentary_dialogue": commentary_dialogue,
            "audio_files": audio_files,
            "pipeline_stage": "complete"  # V3 includes all three stages
        }
        
    except Exception as e:
        timestamp_name = os.path.basename(timestamp_file).replace('.json', '').replace(f'{game_id}_', '')
        return {
            "status": "error",
            "timestamp": timestamp_name,
            "error": str(e),
            "pipeline_stage": "error"
        }


async def _run_agent_with_timeout(runner, session, input_content, timeout: float = 45.0) -> str:
    """Run agent with extended timeout for audio processing"""
    import asyncio
    
    async def collect_output():
        output = ""
        unknown_agent_count = 0
        
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=input_content
        ):
            # Handle audio processor events gracefully
            if hasattr(event, 'author'):
                author_str = str(event.author)
                if 'audio_llm_processor' in author_str or 'audio_processor' in author_str:
                    unknown_agent_count += 1
                    if unknown_agent_count <= 2:  # Log first few, then ignore
                        print(f"🔧 Audio processor event: {author_str} (handled)")
                    # Continue processing but don't add to output
                    continue
                
            if hasattr(event, 'content'):
                content_str = str(event.content)
                output += content_str
                
            if len(output) > 8000:  # Increased limit for audio processing
                break
                
        return output
    
    try:
        return await asyncio.wait_for(collect_output(), timeout=timeout)
    except asyncio.TimeoutError:
        return '{"error": "Agent timeout - audio processing may take longer"}'
    except Exception as e:
        return f'{{"error": "Agent exception: {str(e)}"}}'


def extract_commentary_dialogue_v3(complete_result: dict) -> list:
    """Extract commentary dialogue for context continuity (V3 enhanced)"""
    try:
        if ("commentary_agent" in complete_result and 
            "commentary_sequence" in complete_result["commentary_agent"]):
            
            sequence = complete_result["commentary_agent"]["commentary_sequence"]
            dialogue = []
            
            for segment in sequence:
                if "speaker" in segment and "text" in segment:
                    dialogue.append({
                        "speaker": segment["speaker"],
                        "text": segment["text"],
                        "voice_style": segment.get("voice_style", "enthusiastic")  # V3 addition
                    })
            
            return dialogue[-5:]  # Keep last 5 exchanges
        
        return []
        
    except Exception:
        return []


def extract_audio_files_info_v3(complete_result: dict) -> List[str]:
    """Extract list of generated audio files from V3 processing result"""
    
    files = []
    
    try:
        # Check audio_agent section
        if "audio_agent" in complete_result:
            audio_result = complete_result["audio_agent"]
            
            if audio_result.get("status") == "success":
                # Check for audio segments
                if "audio_segments" in audio_result:
                    for segment in audio_result["audio_segments"]:
                        if "saved_file" in segment:
                            files.append(segment["saved_file"])
                        elif "audio_file" in segment:
                            files.append(segment["audio_file"])
                
                # Check for single file
                elif "saved_file" in audio_result:
                    files.append(audio_result["saved_file"])
        
        return files
        
    except Exception as e:
        print(f"Error extracting audio files info: {e}")
        return []


def create_commentary_context_v3(recent_dialogues: list) -> dict:
    """Create enhanced commentary context for V3 (includes voice style info)"""
    all_dialogue = []
    
    for dialogue_list in recent_dialogues:
        if dialogue_list:
            all_dialogue.extend(dialogue_list)
    
    recent_dialogue = all_dialogue[-5:] if all_dialogue else []
    
    # Extract voice style patterns for continuity
    voice_style_patterns = {}
    for exchange in recent_dialogue:
        speaker = exchange.get("speaker", "Unknown")
        voice_style = exchange.get("voice_style", "enthusiastic")
        if speaker not in voice_style_patterns:
            voice_style_patterns[speaker] = []
        voice_style_patterns[speaker].append(voice_style)
    
    return {
        "recent_dialogue": recent_dialogue,
        "context_size": len(str(recent_dialogue)),
        "exchange_count": len(recent_dialogue),
        "voice_style_patterns": voice_style_patterns  # V3 enhancement
    }


def format_v3_processing_stats(processing_stats: dict, audio_files_count: int) -> dict:
    """Format processing statistics for V3 pipeline (includes audio metrics)"""
    
    if not processing_stats.get("processing_times"):
        return {"error": "No processing data available"}
    
    times = processing_stats["processing_times"]
    avg_time = sum(times) / len(times)
    under_10s = sum(1 for t in times if t < 10.0)  # More lenient for audio processing
    
    return {
        "total_processed": processing_stats["total_processed"],
        "average_time": round(avg_time, 2),
        "min_time": round(min(times), 2),
        "max_time": round(max(times), 2),
        "under_10s_count": under_10s,
        "under_10s_percentage": round(under_10s / len(times) * 100, 1),
        "session_refreshes": processing_stats.get("total_processed", 0) // 10,
        "total_audio_files": audio_files_count,
        "avg_audio_per_timestamp": round(audio_files_count / len(times), 1) if times else 0
    }


def save_audio_files_manifest(game_id: str, audio_files: List[str]) -> str:
    """Save a manifest of all generated audio files"""
    
    try:
        output_dir = f"data/sequential_agent_v3_outputs/{game_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        manifest_file = f"{output_dir}/audio_files_manifest.json"
        
        manifest_data = {
            "game_id": game_id,
            "total_files": len(audio_files),
            "audio_files": audio_files,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(manifest_file, 'w') as f:
            json.dump(manifest_data, f, indent=2)
        
        print(f"📄 Audio manifest saved: {manifest_file}")
        return manifest_file
        
    except Exception as e:
        print(f"❌ Failed to save audio manifest: {e}")
        return None 