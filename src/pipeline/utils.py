"""
Pipeline utility functions for Sequential Agent processing
"""

import json
import os
import re
import time
from google.genai.types import Part, UserContent


async def process_timestamp_with_session(agent, game_id: str, timestamp_file: str, session, runner, board_context: dict, commentary_context: dict = None) -> dict:
    """Process timestamp with ADK session"""
    try:
        # Load timestamp data
        with open(timestamp_file, 'r') as f:
            timestamp_data = json.load(f)
        
        # Create prompt
        from ..agents.sequential_agent_v2.prompts import get_workflow_prompt
        prompt = get_workflow_prompt(game_id, timestamp_data, board_context, commentary_context)
        input_content = UserContent(parts=[Part(text=prompt)])
        
        # Process through session with timeout
        raw_output = await _run_agent_with_timeout(runner, session, input_content)
        
        # Extract clean results
        clean_result = extract_agent_outputs(raw_output)
        commentary_dialogue = extract_commentary_dialogue(clean_result)
        
        timestamp_name = os.path.basename(timestamp_file).replace('.json', '').replace(f'{game_id}_', '')
        
        return {
            "status": "success",
            "timestamp": timestamp_name,
            "response": clean_result,
            "commentary_dialogue": commentary_dialogue
        }
        
    except Exception as e:
        timestamp_name = os.path.basename(timestamp_file).replace('.json', '').replace(f'{game_id}_', '')
        return {
            "status": "error",
            "timestamp": timestamp_name,
            "error": str(e)
        }


async def _run_agent_with_timeout(runner, session, input_content, timeout: float = 30.0) -> str:
    """Run agent with timeout and output collection"""
    import asyncio
    
    async def collect_output():
        output = ""
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=input_content
        ):
            if hasattr(event, 'content'):
                output += str(event.content)
            if len(output) > 5000:
                break
        return output
    
    try:
        return await asyncio.wait_for(collect_output(), timeout=timeout)
    except asyncio.TimeoutError:
        return '{"error": "Agent timeout"}'
    except Exception as e:
        return f'{{"error": "Agent exception: {str(e)}"}}'


def extract_agent_outputs(raw_output: str) -> dict:
    """Extract step by step with broadcaster name fixing"""
    result = {
        "data_agent": {},
        "commentary_agent": {},
        "raw_debug": raw_output if len(raw_output) < 400 else raw_output[:400] + "..."
    }
    
    try:
        # Extract data agent output (first text field)
        first_text_pattern = r"text='(.*?)'\)"
        all_texts = re.findall(first_text_pattern, raw_output, re.DOTALL)
        
        if all_texts:
            # First text should be data agent
            data_json_str = all_texts[0]
            # Clean escaped characters
            clean_data = data_json_str.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            try:
                parsed_data = json.loads(clean_data)
                if 'for_commentary_agent' in parsed_data:
                    result["data_agent"] = parsed_data
            except json.JSONDecodeError as e:
                result["data_agent"] = {"error": f"Data agent parse error: {str(e)}"}
        
        # Step 2: Shrink output - find everything after first text field
        if all_texts:
            first_text_end = raw_output.find("text='") + len("text='") + len(all_texts[0]) + 2
            remaining_output = raw_output[first_text_end:]
        else:
            remaining_output = raw_output
        
        # Step 3: Focus on commentary part and fix broadcaster names
        if '```json' in remaining_output and 'commentary_sequence' in remaining_output:
            json_start = remaining_output.find('```json') + 7
            json_end = remaining_output.find('```', json_start)
            
            if json_end > json_start:
                commentary_json = remaining_output[json_start:json_end].strip()
                # Clean escaped characters
                clean_commentary = commentary_json.replace('\\n', '\n').replace('\\"', '"')
                clean_commentary = clean_commentary.replace("\\'", "'")
                clean_commentary = clean_commentary.replace('\\\\', '\\')
                # Fix Unicode apostrophes
                clean_commentary = clean_commentary.replace('\\u2019', "'")
                
                try:
                    parsed_commentary = json.loads(clean_commentary)
                    # Fix broadcaster names
                    parsed_commentary = fix_broadcaster_names(parsed_commentary)
                    result["commentary_agent"] = parsed_commentary
                except json.JSONDecodeError as e:
                    result["commentary_agent"] = {"error": f"Commentary parse error: {str(e)[:100]}..."}
        
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


def extract_commentary_dialogue(clean_result: dict) -> list:
    """Extract commentary dialogue for context continuity"""
    try:
        if ("commentary_agent" in clean_result and 
            "commentary_sequence" in clean_result["commentary_agent"]):
            
            sequence = clean_result["commentary_agent"]["commentary_sequence"]
            dialogue = []
            
            for segment in sequence:
                if "speaker" in segment and "text" in segment:
                    dialogue.append({
                        "speaker": segment["speaker"],
                        "text": segment["text"]
                    })
            
            return dialogue[-5:]  # Keep last 5 exchanges
        
        return []
        
    except Exception:
        return []


def create_commentary_context(recent_dialogues: list) -> dict:
    """Create commentary context from recent dialogues"""
    all_dialogue = []
    
    for dialogue_list in recent_dialogues:
        if dialogue_list:
            all_dialogue.extend(dialogue_list)
    
    recent_dialogue = all_dialogue[-5:] if all_dialogue else []
    
    return {
        "recent_dialogue": recent_dialogue,
        "context_size": len(str(recent_dialogue)),
        "exchange_count": len(recent_dialogue)
    }


