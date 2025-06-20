"""
Clean Sequential Agent - NHL Commentary Pipeline
Simple, minimal implementation
"""

import asyncio
from google.adk.agents import SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai.types import Part, UserContent
import json
import os

from .prompts import get_workflow_prompt
from .tools import save_clean_result


class NHLSequentialAgent:
    """Stateless Sequential Agent for NHL Commentary"""
    
    def __init__(self, game_id: str):
        self.game_id = game_id
        self.agent = None
        # No persistent runner or session - create fresh each time
        
    async def initialize(self):
        """Initialize agent (no session management)"""
        # Create sub-agents (data + commentary only)
        from ..data_agent.data_agent_adk import create_hockey_agent_for_game
        from ..commentary_agent.commentary_agent import create_commentary_agent_for_game
        
        data_agent = create_hockey_agent_for_game(self.game_id, 'gemini-2.0-flash')
        commentary_agent = create_commentary_agent_for_game(self.game_id)
        
        # Create Sequential Agent (stateless)
        self.agent = SequentialAgent(
            name=f"NHL_{self.game_id}",
            sub_agents=[data_agent, commentary_agent],
            description=f"NHL Data + Commentary Pipeline for {self.game_id}"
        )
        
        print(f"✅ Sequential Agent initialized for game {self.game_id} (stateless)")
        
    async def process_with_session(self, timestamp_file: str, session, runner, board_context: dict, continuity_context: dict = None) -> dict:
        """Process timestamp with provided session and runner (for batching)"""
        try:
            # Load timestamp data
            with open(timestamp_file, 'r') as f:
                timestamp_data = json.load(f)
            
            # Create prompt with continuity context
            prompt = self._build_smart_prompt(timestamp_data, board_context, continuity_context)
            input_content = UserContent(parts=[Part(text=prompt)])
            
            # Process through provided session
            raw_output = ""
            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=input_content
            ):
                if hasattr(event, 'content'):
                    raw_output += str(event.content)
            
            # Extract clean results
            clean_result = self._extract_agent_outputs(raw_output)
            
            # Save clean result
            timestamp_name = os.path.basename(timestamp_file).replace('.json', '').replace(f'{self.game_id}_', '')
            output_file = save_clean_result(self.game_id, timestamp_name, clean_result)
            
            return {
                "status": "success",
                "timestamp": timestamp_name,
                "output_file": output_file,
                "clean_result": clean_result
            }
            
        except Exception as e:
            timestamp_name = os.path.basename(timestamp_file).replace('.json', '').replace(f'{self.game_id}_', '')
            return {
                "status": "error",
                "timestamp": timestamp_name,
                "error": str(e)
            }

    async def process_timestamp_stateless(self, timestamp_file: str, board_context: dict, continuity_context: dict = None) -> dict:
        """Process a single timestamp with fresh session (no accumulation)"""
        try:
            # Load timestamp data
            with open(timestamp_file, 'r') as f:
                timestamp_data = json.load(f)
            
            # Create fresh runner and session for this timestamp only
            runner = InMemoryRunner(agent=self.agent)
            session = await runner.session_service.create_session(
                app_name=runner.app_name,
                user_id=f"temp_{self.game_id}_{os.path.basename(timestamp_file)}"
            )
            
            # Create smart prompt with continuity context
            prompt = self._build_smart_prompt(timestamp_data, board_context, continuity_context)
            input_content = UserContent(parts=[Part(text=prompt)])
            
            # Process through Sequential Agent (fresh session = no accumulation)
            raw_output = ""
            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=input_content
            ):
                if hasattr(event, 'content'):
                    raw_output += str(event.content)
            
            # Extract clean results using working regex approach
            clean_result = self._extract_agent_outputs(raw_output)
            
            # Save clean result
            timestamp_name = os.path.basename(timestamp_file).replace('.json', '').replace(f'{self.game_id}_', '')
            output_file = save_clean_result(self.game_id, timestamp_name, clean_result)
            
            return {
                "status": "success",
                "timestamp": timestamp_name,
                "output_file": output_file,
                "clean_result": clean_result
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "error": str(e)
            }
    
    async def process_timestamp(self, timestamp_file: str, board_context: dict) -> dict:
        """Legacy method for backwards compatibility"""
        return await self.process_timestamp_stateless(timestamp_file, board_context, None)
    
    def _build_smart_prompt(self, timestamp_data: dict, board_context: dict, continuity_context: dict) -> str:
        """Build minimal prompt with just board context"""
        # Just the basic prompt - no continuity context
        base_prompt = get_workflow_prompt(self.game_id, timestamp_data, board_context)
        return base_prompt
    
    def _extract_agent_outputs(self, raw_output: str) -> dict:
        """Extract step by step with broadcaster name fixing"""
        import re
        
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
                        parsed_commentary = self._fix_broadcaster_names(parsed_commentary)
                        result["commentary_agent"] = parsed_commentary
                    except json.JSONDecodeError as e:
                        result["commentary_agent"] = {"error": f"Commentary parse error: {str(e)[:100]}..."}
            
            return result
            
        except Exception as e:
            result["extraction_error"] = str(e)
            return result
    
    def _fix_broadcaster_names(self, commentary_data: dict) -> dict:
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
    
    def _parse_sequential_output(self, raw_output: str) -> dict:
        """Parse raw Sequential Agent output into clean JSON structure"""
        import re
        
        result = {
            "data_agent_output": None,
            "commentary_agent_output": None,
            "raw_debug": raw_output if len(raw_output) < 500 else raw_output[:500] + "..."
        }
        
        try:
            import re
            
            # Extract text content from ADK Parts
            text_patterns = [
                r"text='([^']*)'",
                r'text="([^"]*)"'
            ]
            
            all_text_content = []
            for pattern in text_patterns:
                matches = re.findall(pattern, raw_output, re.DOTALL)
                all_text_content.extend(matches)
            
            for text_content in all_text_content:
                # Clean up escaped characters
                clean_text = text_content.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
                
                # Try direct JSON parsing for data agent
                try:
                    parsed = json.loads(clean_text)
                    if 'for_commentary_agent' in parsed:
                        result["data_agent_output"] = parsed
                except json.JSONDecodeError:
                    # Try extracting commentary from markdown JSON
                    if '```json' in clean_text and 'commentary_sequence' in clean_text:
                        json_start = clean_text.find('```json') + 7
                        json_end = clean_text.find('```', json_start)
                        
                        if json_end > json_start:
                            json_content = clean_text[json_start:json_end].strip()
                            try:
                                parsed = json.loads(json_content)
                                if 'commentary_sequence' in parsed:
                                    result["commentary_agent_output"] = parsed
                            except json.JSONDecodeError:
                                pass
            
            return result
            
        except Exception as e:
            result["parse_error"] = str(e)
            return result


def create_nhl_sequential_agent(game_id: str) -> NHLSequentialAgent:
    """Create NHL Sequential Agent"""
    # Configure API
    import dotenv
    dotenv.load_dotenv()
    
    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise Exception("GOOGLE_API_KEY not found in environment")
    
    try:
        import google.genai as genai
        genai.configure(api_key=api_key)
    except:
        pass  # Ignore genai config errors
        
    return NHLSequentialAgent(game_id)


async def test_sequential_agent(game_id: str):
    """Simple test"""
    agent = create_nhl_sequential_agent(game_id)
    await agent.initialize()
    
    # Find a test file
    test_files = [f for f in os.listdir(f"data/live/{game_id}") if f.endswith('.json')]
    if test_files:
        test_file = f"data/live/{game_id}/{test_files[0]}"
        result = await agent.process_timestamp(test_file, "Test context")
        print("Test result:", result)
        return result["status"] == "success"
    return False