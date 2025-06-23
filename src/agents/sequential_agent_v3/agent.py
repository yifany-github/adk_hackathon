"""
Complete Sequential Agent V3 - NHL Commentary Pipeline
Integrates Data + Commentary + Audio processing in a single agent
"""

import os
import json
from typing import Dict, Any, Optional
from google.adk.agents import SequentialAgent


class NHLSequentialAgentV3:
    """Complete Sequential Agent for NHL Commentary with Audio Integration"""
    
    def __init__(self, game_id: str):
        self.game_id = game_id
        self.agent = None
        
    async def initialize(self):
        """Initialize agent with all three sub-agents"""
        from ..data_agent.data_agent_adk import create_hockey_agent_for_game
        from ..commentary_agent.commentary_agent import create_commentary_agent_for_game
        from ..audio_agent.audio_agent import create_audio_agent_for_game
        
        # Create the three sub-agents following existing patterns
        data_agent = create_hockey_agent_for_game(self.game_id, 'gemini-2.0-flash')
        commentary_agent = create_commentary_agent_for_game(self.game_id)
        
        # Create audio agent with specific configuration for Sequential Agent integration
        audio_agent = create_audio_agent_for_game(self.game_id, 'gemini-2.0-flash')
        
        # Configure audio agent to prevent unknown agent events
        if hasattr(audio_agent, '_llm_agent'):
            # Ensure the internal LLM agent has a proper name that won't conflict
            audio_agent._llm_agent.name = f"audio_processor_{self.game_id}"
            print(f"🔧 Configured audio processor: {audio_agent._llm_agent.name}")
        
        # Try to minimize audio agent complexity for Sequential Agent
        try:
            # Disable audio agent's internal WebSocket server for Sequential processing
            if hasattr(audio_agent, '_websocket_server_running'):
                audio_agent._websocket_server_running = False
        except Exception as e:
            print(f"⚠️ Audio agent configuration warning: {e}")
        
        # Store sub-agents for custom processing logic
        self.data_agent = data_agent
        self.commentary_agent = commentary_agent
        self.audio_agent = audio_agent
        
        # Create Sequential Agent with only Data + Commentary agents
        # Audio will be processed separately using our custom logic
        self.agent = SequentialAgent(
            name=f"NHL_Complete_{self.game_id}",
            sub_agents=[data_agent, commentary_agent],
            description=f"Complete NHL Data + Commentary + Audio Pipeline for {self.game_id}"
        )
        
        print(f"✅ Sequential Agent V3 initialized for game {self.game_id} (Data + Commentary + Audio)")
        print(f"📊 Sub-agents: {[agent.name for agent in self.agent.sub_agents]}")

    async def process_message(self, message: str) -> Dict[str, Any]:
        """
        Process message through complete Data + Commentary + Audio pipeline
        
        Args:
            message: Input message/data to process
            
        Returns:
            Complete results with data, commentary, and audio components
        """
        result = {
            "data_agent": {},
            "commentary_agent": {},
            "audio_agent": {},
            "raw_debug": ""
        }
        
        try:
            # Step 1: Process through individual agents manually
            print(f"🔄 Processing through Data Agent...")
            
            # Process with Data Agent first
            data_response = await self._call_agent_with_message(self.data_agent, message)
            result["data_agent"] = data_response
            
            print(f"🔄 Processing through Commentary Agent...")
            
            # Process with Commentary Agent using data agent output
            commentary_input = self._prepare_commentary_input(message, data_response)
            commentary_response = await self._call_agent_with_message(self.commentary_agent, commentary_input)
            result["commentary_agent"] = commentary_response
            
            # Step 2: Generate audio if commentary was successful
            commentary_data = result.get("commentary_agent", {})
            
            if commentary_data.get("status") == "success":
                print(f"🎵 Starting audio generation...")
                audio_result = await self.process_commentary_to_audio(commentary_data)
                result["audio_agent"] = audio_result
                
                if audio_result.get("status") == "success":
                    print(f"✅ Audio generation completed: {audio_result.get('successful_segments', 0)} segments")
                else:
                    print(f"⚠️ Audio generation failed: {audio_result.get('error', 'Unknown error')}")
            else:
                result["audio_agent"] = {
                    "status": "skipped",
                    "message": "Commentary failed, skipping audio generation"
                }
                print(f"⚠️ Commentary failed, skipping audio generation")
            
            # Store raw debug info
            result["raw_debug"] = f"Data: {str(data_response)[:200]}... Commentary: {str(commentary_response)[:200]}..."
            
            return result
            
        except Exception as e:
            print(f"❌ Sequential Agent V3 processing failed: {e}")
            return {
                "data_agent": {"error": f"Processing failed: {str(e)}"},
                "commentary_agent": {"error": f"Processing failed: {str(e)}"},
                "audio_agent": {"error": f"Processing failed: {str(e)}"},
                "raw_debug": str(e)
            }
    
    async def _call_agent_with_message(self, agent, message: str) -> Dict[str, Any]:
        """
        Call an individual agent with a message using a temporary session
        
        Args:
            agent: The agent to call
            message: The input message
            
        Returns:
            Parsed response from the agent
        """
        try:
            from google.adk.runners import InMemoryRunner
            from google.genai.types import Part, UserContent
            
            # Create temporary runner and session for this agent
            runner = InMemoryRunner(agent=agent)
            session = await runner.session_service.create_session(
                app_name=runner.app_name,
                user_id=f"temp_{self.game_id}_{agent.name}"
            )
            
            # Prepare input
            input_content = UserContent(parts=[Part(text=message)])
            
            # Collect response
            output = ""
            async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=input_content
            ):
                if hasattr(event, 'content'):
                    output += str(event.content)
                if len(output) > 8000:
                    break
            
            # Clean up session
            try:
                await runner.session_service.delete_session(session.id)
            except Exception:
                pass
            
            # Parse output
            return self._parse_agent_output(output, agent.name)
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Agent call failed: {str(e)}",
                "agent_name": agent.name
            }
    
    def _prepare_commentary_input(self, original_message: str, data_response: Dict[str, Any]) -> str:
        """
        Prepare input for commentary agent based on data agent output
        
        Args:
            original_message: Original input message
            data_response: Data agent response
            
        Returns:
            Formatted input for commentary agent
        """
        try:
            # If data agent was successful, include its output
            if data_response.get("status") == "success":
                combined_input = f"""
{original_message}

Data Agent Analysis:
{json.dumps(data_response, indent=2)}
"""
            else:
                # If data agent failed, just use original message
                combined_input = original_message
            
            return combined_input
            
        except Exception:
            return original_message
    
    def _parse_agent_output(self, output: str, agent_name: str) -> Dict[str, Any]:
        """
        Parse individual agent output
        
        Args:
            output: Raw agent output
            agent_name: Name of the agent
            
        Returns:
            Parsed response
        """
        try:
            # Handle ADK agent response format (parts=[Part(...)])
            if "parts=[Part(" in output:
                # Extract text content from parts structure
                import re
                # Use a more sophisticated regex to handle escaped quotes
                text_match = re.search(r"text='([^']*?(?:\\'[^']*?)*)'", output)
                if not text_match:
                    text_match = re.search(r'text="([^"]*?(?:\\"[^"]*?)*)"', output)
                if not text_match:
                    text_match = re.search(r'text=([^)]+)', output)
                
                if text_match:
                    text_content = text_match.group(1)
                    
                    # Handle escaped JSON
                    text_content = text_content.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\').replace("\\'", "'")
                    
                    # Try to extract JSON from the text content
                    if text_content.strip().startswith('```json'):
                        # Remove markdown code block
                        json_content = text_content.replace('```json', '').replace('```', '').strip()
                        try:
                            parsed = json.loads(json_content)
                            parsed["status"] = "success"
                            return parsed
                        except json.JSONDecodeError:
                            pass
                    
                    # Try direct JSON parsing
                    json_match = re.search(r'\{.*\}', text_content, re.DOTALL)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group())
                            parsed["status"] = "success"
                            return parsed
                        except json.JSONDecodeError:
                            pass
            
            # Try to parse as direct JSON
            if output.strip().startswith('{') and output.strip().endswith('}'):
                parsed = json.loads(output.strip())
                parsed["status"] = "success"
                return parsed
            
            # Look for JSON within the output
            import re
            json_match = re.search(r'\{.*\}', output, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    parsed["status"] = "success"
                    return parsed
                except json.JSONDecodeError:
                    pass
            
            # If no JSON found, return as text
            return {
                "status": "success",
                "text_output": output,
                "agent_name": agent_name
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Parse error: {str(e)}",
                "raw_output": output[:500],
                "agent_name": agent_name
            }

    def _parse_sequential_response(self, response) -> Dict[str, Any]:
        """
        Parse Sequential Agent response to extract data and commentary components
        
        Args:
            response: Raw response from Sequential Agent
            
        Returns:
            Parsed data and commentary components
        """
        result = {
            "data_agent": {},
            "commentary_agent": {}
        }
        
        try:
            # If response is a string, try to parse as JSON
            if isinstance(response, str):
                try:
                    response_data = json.loads(response)
                except json.JSONDecodeError:
                    # If not JSON, treat as raw text
                    result["commentary_agent"] = {
                        "status": "error",
                        "error": "Failed to parse response as JSON",
                        "raw_text": response[:500]
                    }
                    return result
            else:
                response_data = response
            
            # Try to extract data agent output (usually first)
            if isinstance(response_data, dict):
                # Look for data agent indicators
                if "generated_at" in response_data or "data_agent_version" in response_data:
                    result["data_agent"] = response_data
                    # Commentary might be nested
                    commentary = response_data.get("commentary_agent", {})
                    if commentary:
                        result["commentary_agent"] = commentary
                    else:
                        result["commentary_agent"] = {
                            "status": "error",
                            "error": "Commentary not found in response"
                        }
                elif "commentary_sequence" in response_data:
                    # This looks like commentary output
                    result["commentary_agent"] = response_data
                    result["data_agent"] = {
                        "status": "not_extracted",
                        "message": "Data agent output not separately identified"
                    }
                else:
                    # Unknown format
                    result["commentary_agent"] = response_data
                    result["data_agent"] = {
                        "status": "unknown_format",
                        "message": "Could not identify data agent output"
                    }
            else:
                result["commentary_agent"] = {
                    "status": "error",
                    "error": f"Unexpected response type: {type(response_data)}"
                }
            
        except Exception as e:
            result["data_agent"] = {"error": f"Parse error: {str(e)}"}
            result["commentary_agent"] = {"error": f"Parse error: {str(e)}"}
        
        return result

    async def process_commentary_to_audio(self, commentary_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process commentary data to generate audio files
        
        Args:
            commentary_data: Commentary agent output with dialogue sequence
            
        Returns:
            Audio processing results
        """
        try:
            audio_results = []
            
            # Extract commentary sequence
            commentary_sequence = commentary_data.get("commentary_sequence", [])
            
            if not commentary_sequence:
                return {
                    "status": "error",
                    "error": "No commentary sequence found in commentary data",
                    "game_id": self.game_id
                }
            
            print(f"🎵 Processing {len(commentary_sequence)} commentary segments for audio...")
            
            for i, segment in enumerate(commentary_sequence):
                speaker = segment.get("speaker", "Unknown")
                text = segment.get("text", "")
                
                if text.strip():
                    # Determine voice style based on speaker and content
                    voice_style = self._get_voice_style_for_speaker(speaker, text)
                    
                    # Process to audio with enhanced error handling
                    try:
                        # Use direct audio tool instead of complex agent processing
                        from ..audio_agent.tool import text_to_speech
                        
                        # Generate audio using direct tool call  
                        # Get proper game timestamp from the filename or context
                        proper_timestamp = self._get_proper_game_timestamp()
                        
                        print(f"🎙️ Generating audio for {speaker}: {text[:50]}...")
                        
                        audio_result = await text_to_speech(
                            tool_context=None,
                            text=text,
                            voice_style=voice_style,
                            language="en-US",
                            speaker=speaker,
                            game_id=self.game_id,
                            game_timestamp=proper_timestamp,
                            segment_index=i
                        )
                        
                        # Add metadata
                        audio_result["segment_index"] = i
                        audio_result["speaker"] = speaker
                        audio_result["original_text"] = text
                        audio_result["game_id"] = self.game_id
                        audio_result["voice_style"] = voice_style
                        
                        audio_results.append(audio_result)
                        
                        if audio_result.get("status") == "success":
                            saved_file = audio_result.get("saved_file")
                            print(f"✅ Audio generated: {saved_file}")
                        else:
                            print(f"⚠️ Audio generation failed: {audio_result.get('error', 'Unknown error')}")
                        
                    except Exception as e:
                        print(f"⚠️ Audio processing failed for segment {i}: {e}")
                        # Continue with other segments
                        audio_results.append({
                            "segment_index": i,
                            "speaker": speaker,
                            "status": "error",
                            "error": str(e),
                            "original_text": text[:50] + "..." if len(text) > 50 else text
                        })
            
            # 保存音频文件清单
            successful_files = 0
            try:
                from ..audio_agent.audio_file_manager import save_audio_files_manifest_for_game, get_audio_sequence_info
                
                # Count successful files
                successful_files = len([r for r in audio_results if r.get("status") == "success"])
                
                if successful_files > 0:
                    manifest_path = save_audio_files_manifest_for_game(self.game_id)
                    sequence_info = get_audio_sequence_info(self.game_id)
                    
                    print(f"📋 Audio manifest saved: {manifest_path}")
                    print(f"🔢 Total files in sequence: {sequence_info.get('global_sequence', 0)}")
                
            except Exception as e:
                print(f"⚠️ Failed to save audio manifest: {e}")
            
            return {
                "status": "success",
                "audio_segments": audio_results,
                "total_segments": len(audio_results),
                "successful_segments": successful_files,
                "game_id": self.game_id,
                "manifest_saved": successful_files > 0
            }
            
        except Exception as e:
            print(f"❌ Audio processing failed: {str(e)}")
            return {
                "status": "error",
                "error": f"Audio processing failed: {str(e)}",
                "game_id": self.game_id
            }
    
    def _get_voice_style_for_speaker(self, speaker: str, text: str) -> str:
        """
        Determine appropriate voice style based on speaker and content
        
        Args:
            speaker: Speaker name (Alex Chen, Mike Rodriguez, etc.)
            text: Commentary text
            
        Returns:
            Voice style (enthusiastic, dramatic, calm)
        """
        text_lower = text.lower()
        
        # Alex Chen (Play-by-play) - more energetic
        if "alex chen" in speaker.lower() or "play-by-play" in speaker.lower():
            if any(word in text_lower for word in ["goal", "score", "shot", "save"]):
                return "enthusiastic"
            elif any(word in text_lower for word in ["penalty", "overtime", "final"]):
                return "dramatic"
            else:
                return "enthusiastic"
        
        # Mike Rodriguez (Analyst) - more measured
        elif "mike rodriguez" in speaker.lower() or "analyst" in speaker.lower():
            if any(word in text_lower for word in ["critical", "crucial", "important"]):
                return "dramatic"
            else:
                return "calm"
        
        # Default
        return "enthusiastic"

    def _get_proper_game_timestamp(self) -> str:
        """
        Get proper game timestamp for audio file naming
        
        Returns:
            Proper timestamp format like "1_00_00" instead of "segment_0"
        """
        # Try to get timestamp from current processing context
        # Check if we have access to current timestamp info from the pipeline
        try:
            # Try to get from instance variable if set by pipeline
            if hasattr(self, '_current_timestamp'):
                return self._current_timestamp
            
            # Try to extract from game context if available
            if hasattr(self, '_current_game_context'):
                context = self._current_game_context
                period = context.get('period', 1)
                time_remaining = context.get('time_remaining', '20:00')
                
                # Convert time_remaining to our format
                if ':' in time_remaining:
                    minutes, seconds = time_remaining.split(':')
                    # Convert to elapsed time (20:00 - time_remaining)
                    total_seconds = 20 * 60  # 20 minutes in a period
                    remaining_seconds = int(minutes) * 60 + int(seconds)
                    elapsed_seconds = total_seconds - remaining_seconds
                    
                    elapsed_minutes = elapsed_seconds // 60
                    elapsed_secs = elapsed_seconds % 60
                    
                    return f"{period}_{elapsed_minutes:02d}_{elapsed_secs:02d}"
            
            # Default fallback - use current time as approximation
            import time
            current_time = int(time.time()) % 1200  # Use last 20 minutes
            minutes = current_time // 60
            seconds = current_time % 60
            return f"1_{minutes:02d}_{seconds:02d}"
            
        except Exception as e:
            print(f"⚠️ Failed to get proper timestamp: {e}")
            # Final fallback
            return "1_00_00"
    
    def set_current_timestamp(self, timestamp: str):
        """Set the current timestamp for audio file naming"""
        self._current_timestamp = timestamp
        
    def set_current_game_context(self, context: dict):
        """Set the current game context for timestamp calculation"""
        self._current_game_context = context


def create_nhl_sequential_agent_v3(game_id: str) -> NHLSequentialAgentV3:
    """Create NHL Sequential Agent V3 with complete integration"""
    import dotenv
    dotenv.load_dotenv()
    
    # Clean up environment variables to avoid conflicts
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        raise Exception("Neither GOOGLE_API_KEY nor GEMINI_API_KEY found in environment")
    
    # Set a single API key to avoid conflicts
    os.environ['GOOGLE_API_KEY'] = api_key
    if 'GEMINI_API_KEY' in os.environ and os.environ['GEMINI_API_KEY'] != api_key:
        print("🔧 Cleaned up duplicate GEMINI_API_KEY environment variable")
    
    try:
        import google.genai as genai
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"⚠️ Google GenAI configuration warning: {e}")
        pass
        
    return NHLSequentialAgentV3(game_id) 