"""
NHL Sequential Agent v2 - Persistent Session Management
Properly maintains a single agent and session throughout the game
"""

from google.adk.agents import SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai.types import Part, UserContent
import json
import os
import asyncio
from typing import Dict, Any, Optional

try:
    from .prompts import get_workflow_prompt, get_clean_output_instructions
    from .tools import extract_audio_from_result, save_result, extract_and_save_sequential_audio
    from .output_formatter import SequentialAgentFormatter
except ImportError:
    # For direct execution
    from prompts import get_workflow_prompt, get_clean_output_instructions
    from tools import extract_audio_from_result, save_result, extract_and_save_sequential_audio
    from output_formatter import SequentialAgentFormatter


class PersistentSequentialAgent:
    """Sequential Agent with persistent session management and context pruning"""
    
    def __init__(self, game_id: str, initial_context: Dict[str, Any]):
        self.game_id = game_id
        self.initial_context = initial_context
        self.agent = None
        self.runner = None
        self.session = None
        self.is_initialized = False
        self.formatter = SequentialAgentFormatter()
        self.processed_count = 0
        self.max_context_length = 800000  # Stay well under 1M token limit
        self.refresh_frequency = 6  # Refresh session every 6 timestamps
        
    async def initialize(self):
        """Initialize agent and create persistent session"""
        if self.is_initialized:
            return
            
        # Create the sequential agent
        self.agent = self._create_agent()
        
        # Create runner
        self.runner = InMemoryRunner(agent=self.agent)
        
        # Create persistent session
        self.session = await self.runner.session_service.create_session(
            app_name=self.runner.app_name,
            user_id=f"nhl_{self.game_id}_commentator"
        )
        
        # Initialize session with context if provided
        if self.initial_context:
            await self._initialize_session_context()
            
        self.is_initialized = True
        print(f"✅ Sequential Agent initialized with persistent session: {self.session.id}")
        
    def _create_agent(self) -> SequentialAgent:
        """Create the sequential agent with all sub-agents"""
        import sys
        
        # Add project root to path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        sys.path.append(project_root)
        
        from src.agents.data_agent.data_agent_adk import create_hockey_agent_for_game
        from src.agents.commentary_agent.commentary_agent import create_commentary_agent_for_game
        from src.agents.audio_agent.audio_agent import AudioAgent
        
        # Create agents
        data_agent = create_hockey_agent_for_game(self.game_id, 'gemini-2.0-flash')
        commentary_agent = create_commentary_agent_for_game(self.game_id)
        audio_agent = AudioAgent(game_id=self.game_id)
        
        # Create Sequential Agent
        return SequentialAgent(
            name=f"NHL_{self.game_id}",
            sub_agents=[data_agent, commentary_agent, audio_agent],
            description=f"NHL Commentary Pipeline for {self.game_id}"
        )
        
    async def _initialize_session_context(self):
        """Initialize session with properly engineered game context"""
        game_board = self.initial_context.get('game_board', {})
        static_context = self.initial_context.get('static_context', {})
        
        context_prompt = f"""Initialize NHL Live Commentary Workflow for Game {self.game_id}

=== AUTHORITATIVE GAME STATE (GROUND TRUTH) ===
{json.dumps(game_board, indent=2)}

=== STATIC GAME CONTEXT ===
{json.dumps(static_context, indent=2)}

=== BROADCASTER SETUP ===
- Commentary Agent will handle broadcaster personas (Alex Chen & Mike Rodriguez)
- No need to inject broadcaster names here since commentary agent manages this

=== WORKFLOW ENGINEERING ===
You are a Sequential Agent coordinating 3 sub-agents:

1. DATA AGENT: Must use GameBoard state as absolute truth
   - Analyze timestamp data against authoritative game state
   - Identify key events, momentum shifts, statistical insights
   - Output: Structured analysis for commentary generation

2. COMMENTARY AGENT: Generate professional two-person broadcast dialogue
   - Input: Data agent analysis + current game context
   - Create natural conversation between Alex Chen (PBP) & Mike Rodriguez (Analyst)
   - Output: Timestamped dialogue with speaker, emotion, timing

3. AUDIO AGENT: Convert commentary to TTS audio files
   - Input: Commentary dialogue from previous agent
   - Generate audio files with proper pacing and emotion
   - Output: Audio file paths and metadata

=== SESSION CONTINUITY RULES ===
- Remember previous commentary to avoid repetition
- Build narrative continuity across timestamps
- Commentary agent maintains broadcaster personalities automatically
- Use GameBoard as single source of truth for all facts

Ready to process NHL timestamps with engineered workflow coordination."""

        input_content = UserContent(parts=[Part(text=context_prompt)])
        
        # Send initialization message
        result_text = ""
        async for event in self.runner.run_async(
            user_id=self.session.user_id,
            session_id=self.session.id,
            new_message=input_content
        ):
            if hasattr(event, 'content'):
                result_text += str(event.content)
                
        print("✅ Session context initialized")
        
    async def process_timestamp(self, timestamp_file: str, board_context: str) -> Dict[str, Any]:
        """Process timestamp with persistent session and context management"""
        if not self.is_initialized:
            await self.initialize()
            
        # Check if session refresh is needed
        if self.processed_count > 0 and self.processed_count % self.refresh_frequency == 0:
            print(f"🔄 Refreshing session context (processed {self.processed_count} timestamps)")
            await self._refresh_session_context()
            
        try:
            # Load timestamp data
            with open(timestamp_file, 'r') as f:
                timestamp_data = json.load(f)
            
            # Create engineered prompt with formatting requirements
            prompt = f"""=== NHL TIMESTAMP PROCESSING ===
Game {self.game_id} - Sequential Workflow Execution

=== AUTHORITATIVE GAME STATE (CURRENT) ===
{board_context if board_context else 'No board context provided'}

=== NEW TIMESTAMP DATA TO PROCESS ===
{json.dumps(timestamp_data, indent=2)}

{get_clean_output_instructions()}

=== WORKFLOW EXECUTION INSTRUCTIONS ===

Step 1 - DATA AGENT:
- Compare timestamp data against authoritative game state above
- Use GameBoard state as ground truth for all fact-checking
- Identify significant events, changes, momentum shifts
- OUTPUT: Clean JSON only - no extra text

Step 2 - COMMENTARY AGENT:
- Take data agent analysis as input
- Create natural two-person broadcast dialogue:
  * Alex Chen (Play-by-Play): Calls action, energetic descriptions
  * Mike Rodriguez (Color Analyst): Strategic insights, context
- Build on previous commentary (maintain narrative flow)
- OUTPUT: Clean JSON only - no extra text

Step 3 - AUDIO AGENT:
- Convert commentary dialogue to TTS audio
- Apply appropriate pacing and emotion
- Generate audio files for broadcast
- OUTPUT: Clean JSON only - no extra text

CRITICAL: Each agent must output ONLY clean JSON that can be parsed directly.
EXECUTE SEQUENTIAL WORKFLOW NOW."""
            
            input_content = UserContent(parts=[Part(text=prompt)])
            
            # Process through persistent session and collect all output
            raw_output = ""
            
            async for event in self.runner.run_async(
                user_id=self.session.user_id,
                session_id=self.session.id,  # Use persistent session
                new_message=input_content
            ):
                if hasattr(event, 'content'):
                    raw_output += str(event.content)
            
            # Use formatter to create clean output structure
            timestamp_name = os.path.basename(timestamp_file).replace('.json', '').replace(f'{self.game_id}_', '')
            clean_output = self.formatter.format_sequential_output(raw_output, self.game_id, timestamp_name)
            clean_output["session_id"] = self.session.id
            
            # Save formatted output
            output_file = self.formatter.save_formatted_output(clean_output, self.game_id, timestamp_file)
            
            # Print readable summary
            self.formatter.print_readable_summary(clean_output)
            
            # Extract audio file count
            audio_files = self._extract_audio_count_from_clean_output(clean_output)
            
            # Increment processed count for context management
            self.processed_count += 1
            
            return {
                "status": "success",
                "timestamp": timestamp_name,
                "output_file": output_file,
                "audio_files": len(audio_files),
                "session_id": self.session.id,
                "processed_count": self.processed_count
            }
            
        except Exception as e:
            # Still increment count even on error to track session usage
            self.processed_count += 1
            return {
                "status": "error",
                "timestamp": os.path.basename(timestamp_file),
                "error": str(e),
                "processed_count": self.processed_count
            }
    
    def _extract_audio_count_from_clean_output(self, clean_output: Dict) -> int:
        """Extract audio file count from clean formatted output"""
        try:
            audio_result = clean_output.get('workflow_results', {}).get('audio_agent')
            if audio_result and isinstance(audio_result, dict):
                if 'audio_processing_details' in audio_result:
                    return len(audio_result['audio_processing_details'])
                elif 'audio_files' in audio_result:
                    return audio_result['audio_files']
            return 0
        except:
            return 0
    
    def _extract_content_from_parts(self, content):
        """Extract actual text content from ADK Parts objects"""
        try:
            # Handle if content is already a string
            if isinstance(content, str):
                return content
            
            # Handle if content has parts attribute (typical ADK response)
            if hasattr(content, 'parts'):
                text_parts = []
                for part in content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
                return '\n'.join(text_parts) if text_parts else None
            
            # Handle direct Part object
            if hasattr(content, 'text') and content.text:
                return content.text
            
            # Fallback to string conversion (but clean it up)
            content_str = str(content)
            if content_str.startswith('parts=[Part('):
                # Try to extract text from the Part string representation
                import re
                text_match = re.search(r'text=\'([^\']+)\'', content_str)
                if text_match:
                    return text_match.group(1)
                # Alternative pattern for double quotes
                text_match = re.search(r'text="([^"]+)"', content_str)
                if text_match:
                    return text_match.group(1)
            
            return content_str
            
        except Exception as e:
            print(f"Error extracting content: {e}")
            return str(content)
    
    async def _refresh_session_context(self):
        """Refresh session to prevent context overflow while maintaining continuity"""
        try:
            # Create a new session with condensed context
            old_session_id = self.session.id
            
            # Create new session
            self.session = await self.runner.session_service.create_session(
                app_name=self.runner.app_name,
                user_id=f"nhl_{self.game_id}_commentator_refresh_{self.processed_count}"
            )
            
            # Initialize with condensed context
            condensed_context = self._create_condensed_context_prompt()
            
            input_content = UserContent(parts=[Part(text=condensed_context)])
            
            # Initialize new session
            result_text = ""
            async for event in self.runner.run_async(
                user_id=self.session.user_id,
                session_id=self.session.id,
                new_message=input_content
            ):
                if hasattr(event, 'content'):
                    result_text += str(event.content)
            
            print(f"✅ Session refreshed: {old_session_id} → {self.session.id}")
            
        except Exception as e:
            print(f"⚠️  Session refresh failed: {e}, continuing with existing session")
    
    def _create_condensed_context_prompt(self) -> str:
        """Create condensed context for session refresh"""
        game_board = self.initial_context.get('game_board', {})
        
        return f"""NHL Live Commentary Session Refresh - Game {self.game_id}

=== CONDENSED CONTEXT ===
This is a refreshed session maintaining commentary continuity.
Processed timestamps: {self.processed_count}

=== CURRENT GAME STATE ===
{json.dumps(game_board, indent=2)}

=== WORKFLOW REMINDER ===
Sequential workflow: DATA AGENT → COMMENTARY AGENT → AUDIO AGENT
- Remember previous commentary patterns
- Maintain natural broadcaster conversation flow
- Use GameBoard as authoritative source
- Continue seamless commentary from where we left off

=== SESSION CONTINUATION ===
This session continues the broadcast narrative from timestamp #{self.processed_count}.
Maintain commentary quality and avoid repetition.
Ready to process next NHL timestamp."""
    
    def _extract_json_from_text(self, text: str):
        """Extract JSON from text content, handling code blocks"""
        import re
        
        try:
            # Try to find JSON in code blocks first
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Try to find raw JSON
            json_match = re.search(r'(\{.*?\})', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # If no JSON found, return the text
            return {"raw_text": text}
            
        except Exception as e:
            return {"parsing_error": str(e), "raw_text": text}
    
    def _save_clean_result(self, game_id: str, timestamp_file: str, clean_output: dict) -> str:
        """Save clean, readable result to file"""
        import os
        
        # Create output directory
        output_dir = f"data/sequential_agent_outputs/{game_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate output filename
        timestamp_name = os.path.basename(timestamp_file).replace('.json', '').replace(f'{game_id}_', '')
        output_file = f"{output_dir}/{timestamp_name}_sequential_clean.json"
        
        # Save with proper formatting
        with open(output_file, 'w') as f:
            json.dump(clean_output, f, indent=2, ensure_ascii=False)
        
        return output_file
    
    def _extract_audio_count(self, audio_output) -> int:
        """Extract audio file count from audio agent output"""
        if not audio_output:
            return 0
        
        try:
            if isinstance(audio_output, dict):
                if 'audio_processing_details' in audio_output:
                    return len(audio_output['audio_processing_details'])
                elif 'audio_files' in audio_output:
                    return audio_output['audio_files']
            return 1 if audio_output else 0
        except:
            return 0


def create_nhl_sequential_agent_v2(game_id: str, initial_context: Dict[str, Any]) -> PersistentSequentialAgent:
    """Create Sequential Agent with persistent session management"""
    # Configure environment
    import dotenv
    dotenv.load_dotenv()
    
    # Ensure API key is available
    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise Exception("No API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.")
    
    # Configure genai
    try:
        import google.genai as genai
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"Warning: Could not configure genai: {e}")
    
    return PersistentSequentialAgent(game_id, initial_context)


# Backward compatibility functions
async def process_timestamp_v2(agent: PersistentSequentialAgent, timestamp_file: str, 
                              game_id: str, board_context: str = None) -> Dict[str, Any]:
    """Process timestamp using persistent agent"""
    return await agent.process_timestamp(timestamp_file, board_context)


async def test_sequential_agent_v2(game_id: str = "2024030412"):
    """Test the persistent Sequential Agent"""
    try:
        # Create agent with test context
        test_context = {
            "game_board": {"home_team": "EDM", "away_team": "FLA", "score": "0-0"},
            "static_context": {"teams": ["EDM", "FLA"]},
            "broadcaster_names": {"play_by_play": "Alex Chen", "analyst": "Mike Rodriguez"}
        }
        
        agent = create_nhl_sequential_agent_v2(game_id, test_context)
        await agent.initialize()
        
        # Find test files
        timestamp_files = sorted([f for f in os.listdir(f"data/live/{game_id}") if f.endswith('.json')])[:3]
        
        if not timestamp_files:
            print("❌ No timestamp files found")
            return False
        
        # Process multiple timestamps with same session
        for i, filename in enumerate(timestamp_files):
            test_file = f"data/live/{game_id}/{filename}"
            print(f"\n📄 Processing file {i+1}/{len(timestamp_files)}: {filename}")
            
            result = await agent.process_timestamp(test_file, "Test board context")
            
            if result["status"] == "success":
                print(f"✅ Processed successfully! Audio files: {result['audio_files']}")
                print(f"   Session ID: {result['session_id']}")
            else:
                print(f"❌ Failed: {result['error']}")
                
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_sequential_agent_v2())
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")