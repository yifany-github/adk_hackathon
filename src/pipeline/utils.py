"""
Pipeline utility functions for Sequential Agent processing
"""

import json
import os
import re
from google.genai.types import Part, UserContent


async def process_timestamp_with_session(agent, game_id: str, timestamp_file: str, session, runner, board_context: dict, continuity_context: dict = None) -> dict:
    """Process timestamp with provided session and runner (for batching)"""
    try:
        print(f"🔍 DEBUG: Starting process_timestamp_with_session for {timestamp_file}")
        
        # Load timestamp data
        with open(timestamp_file, 'r') as f:
            timestamp_data = json.load(f)
        print(f"🔍 DEBUG: Loaded timestamp data")
        
        # Create prompt with continuity context
        from ..agents.sequential_agent_v2.prompts import get_workflow_prompt
        prompt = get_workflow_prompt(game_id, timestamp_data, board_context)
        input_content = UserContent(parts=[Part(text=prompt)])
        print(f"🔍 DEBUG: Created prompt and input content")
        
        # Process through provided session
        print(f"🔍 DEBUG: About to start runner.run_async loop")
        raw_output = ""
        
        try:
            # Try with timeout to prevent hanging
            import asyncio
            async def run_with_timeout():
                output = ""
                async for event in runner.run_async(
                    user_id=session.user_id,
                    session_id=session.id,
                    new_message=input_content
                ):
                    print(f"🔍 DEBUG: Got event: {type(event)}")
                    if hasattr(event, 'content'):
                        content = str(event.content)
                        output += content
                        print(f"🔍 DEBUG: Content: {content[:100]}...")
                    # Break after reasonable output
                    if len(output) > 5000:
                        print(f"🔍 DEBUG: Got enough output, breaking")
                        break
                return output
                        
            raw_output = await asyncio.wait_for(run_with_timeout(), timeout=30.0)
            print(f"🔍 DEBUG: Completed with output length: {len(raw_output)}")
            
        except asyncio.TimeoutError:
            print(f"🔍 DEBUG: Timeout after 30s, using partial output")
            if not raw_output:
                raw_output = '{"error": "Timeout - no response from agent"}'
        except Exception as e:
            print(f"🔍 DEBUG: Exception in runner.run_async: {e}")
            raw_output = f'{{"error": "Exception: {str(e)}"}}'
        
        # Extract clean results
        clean_result = extract_agent_outputs(raw_output)
        
        # Save clean result
        from ..agents.sequential_agent_v2.tools import save_clean_result
        timestamp_name = os.path.basename(timestamp_file).replace('.json', '').replace(f'{game_id}_', '')
        output_file = save_clean_result(game_id, timestamp_name, clean_result)
        
        return {
            "status": "success",
            "timestamp": timestamp_name,
            "output_file": output_file,
            "clean_result": clean_result
        }
        
    except Exception as e:
        timestamp_name = os.path.basename(timestamp_file).replace('.json', '').replace(f'{game_id}_', '')
        return {
            "status": "error",
            "timestamp": timestamp_name,
            "error": str(e)
        }


def extract_agent_outputs(raw_output: str) -> dict:
    """Extract step by step with broadcaster name fixing"""
    result = {
        "data_agent": {},
        "commentary_agent": {},
        "raw_debug": raw_output if len(raw_output) < 400 else raw_output[:400] + "..."
    }
    
    try:
        # Step 1: Extract first text field (data agent)
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