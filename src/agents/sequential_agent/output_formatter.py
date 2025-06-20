"""
Clean output formatting for Sequential Agent
"""

import json
import re
from typing import Dict, Any, Optional, List


class SequentialAgentFormatter:
    """Formats Sequential Agent outputs into clean, readable structure"""
    
    def __init__(self):
        self.patterns = {
            'data_agent': [
                r'"for_commentary_agent"[^}]*}',
                r'data_agent_version[^}]*}',
                r'recommendation[^}]*}'
            ],
            'commentary': [
                r'"commentary_sequence"\s*:\s*\[[^\]]*\]',
                r'"speaker"\s*:[^}]*}',
                r'Alex Chen[^}]*}'
            ],
            'audio': [
                r'"audio_processing_details"[^}]*}',
                r'audio_file_path[^}]*}',
                r'TTS[^}]*}'
            ]
        }
    
    def extract_clean_json(self, text: str) -> Optional[Dict]:
        """Extract valid JSON from text, handling various formats and getting FULL content"""
        if not text:
            return None
            
        try:
            # First try: Direct JSON parsing
            if text.strip().startswith('{'):
                return json.loads(text.strip())
            
            # Second try: Extract from code blocks (improved to handle nested braces)
            json_matches = re.finditer(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            for match in json_matches:
                try:
                    json_content = match.group(1)
                    # Handle nested braces properly
                    brace_count = 0
                    end_pos = 0
                    for i, char in enumerate(json_content):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_pos = i + 1
                                break
                    
                    if end_pos > 0:
                        full_json = json_content[:end_pos]
                        return json.loads(full_json)
                except:
                    continue
            
            # Third try: Find complete JSON objects (handle nested braces)
            json_start = text.find('{')
            if json_start >= 0:
                brace_count = 0
                end_pos = 0
                for i in range(json_start, len(text)):
                    if text[i] == '{':
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                
                if end_pos > 0:
                    potential_json = text[json_start:end_pos]
                    # Clean up common issues
                    potential_json = potential_json.replace('\\"', '"').replace('\\n', '\n')
                    return json.loads(potential_json)
            
            # Fourth try: Extract from quotes (improved)
            json_match = re.search(r'"(\{.*?\})"', text, re.DOTALL)
            if json_match:
                clean_json = json_match.group(1).replace('\\"', '"').replace('\\n', '\n')
                return json.loads(clean_json)
                
        except json.JSONDecodeError as e:
            # Return full raw text instead of truncated version
            return {"parsing_error": str(e), "raw_text": text}
        
        return {"raw_text": text}
    
    def categorize_content(self, content: str) -> str:
        """Categorize content by agent type"""
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ['data_agent', 'for_commentary_agent', 'momentum', 'priority_level']):
            return 'data_agent'
        elif any(keyword in content_lower for keyword in ['commentary_sequence', 'speaker', 'alex chen', 'mike rodriguez']):
            return 'commentary'
        elif any(keyword in content_lower for keyword in ['audio_processing', 'tts', 'voice_style', 'audio_file']):
            return 'audio'
        else:
            return 'general'
    
    def format_sequential_output(self, raw_output: str, game_id: str, timestamp: str) -> Dict[str, Any]:
        """Format raw Sequential Agent output into clean structure"""
        
        # Extract text content from ADK Parts format
        text_contents = self._extract_text_from_parts(raw_output)
        
        # Categorize and parse content
        data_agent_output = None
        commentary_output = None
        audio_output = None
        general_content = []
        
        for content in text_contents:
            category = self.categorize_content(content)
            parsed_content = self.extract_clean_json(content)
            
            if category == 'data_agent' and not data_agent_output:
                data_agent_output = parsed_content
            elif category == 'commentary' and not commentary_output:
                commentary_output = parsed_content
            elif category == 'audio' and not audio_output:
                audio_output = parsed_content
            else:
                # Don't truncate content - keep it full for debugging
                general_content.append({
                    "category": category,
                    "content": content
                })
        
        # Create clean output structure
        clean_output = {
            "game_id": game_id,
            "timestamp": timestamp,
            "processing_time": self._extract_game_time(raw_output),
            "status": "success",
            "workflow_results": {
                "data_agent": data_agent_output,
                "commentary_agent": commentary_output,
                "audio_agent": audio_output
            },
            "additional_content": general_content if general_content else None
        }
        
        return clean_output
    
    def _extract_text_from_parts(self, raw_output: str) -> List[str]:
        """Extract text content from ADK Parts format"""
        text_contents = []
        
        # Pattern for text within ADK Parts
        text_patterns = [
            r"text='([^']*)'",
            r'text="([^"]*)"',
            r"text=([^,\)]*)",
        ]
        
        for pattern in text_patterns:
            matches = re.findall(pattern, raw_output)
            text_contents.extend(matches)
        
        # Clean up and filter meaningful content
        cleaned_contents = []
        for content in text_contents:
            # Skip empty or very short content
            if len(content.strip()) < 10:
                continue
            
            # Unescape content
            content = content.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
            cleaned_contents.append(content)
        
        return cleaned_contents
    
    def _extract_game_time(self, raw_output: str) -> str:
        """Extract game time from raw output"""
        time_match = re.search(r'(\d+:\d+:\d+)', raw_output)
        if time_match:
            return time_match.group(1)
        return "Unknown"
    
    def save_formatted_output(self, formatted_output: Dict, game_id: str, timestamp_file: str) -> str:
        """Save formatted output to file"""
        import os
        
        output_dir = f"data/sequential_agent_outputs/{game_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp_name = os.path.basename(timestamp_file).replace('.json', '').replace(f'{game_id}_', '')
        output_file = f"{output_dir}/{timestamp_name}_sequential_clean.json"
        
        with open(output_file, 'w') as f:
            json.dump(formatted_output, f, indent=2, ensure_ascii=False)
        
        return output_file
    
    def print_readable_summary(self, formatted_output: Dict):
        """Print a readable summary of the formatted output"""
        print(f"\n📋 Game {formatted_output['game_id']} - Timestamp {formatted_output['timestamp']}")
        print("=" * 60)
        
        results = formatted_output.get('workflow_results', {})
        
        # Data Agent Summary
        data_result = results.get('data_agent')
        if data_result:
            print("\n📊 DATA AGENT:")
            if isinstance(data_result, dict) and 'for_commentary_agent' in data_result:
                agent_data = data_result['for_commentary_agent']
                print(f"   Recommendation: {agent_data.get('recommendation', 'N/A')}")
                print(f"   Priority Level: {agent_data.get('priority_level', 'N/A')}")
                print(f"   Momentum Score: {agent_data.get('momentum_score', 'N/A')}")
            else:
                print(f"   {str(data_result)[:100]}...")
        
        # Commentary Agent Summary
        commentary_result = results.get('commentary_agent')
        if commentary_result:
            print("\n🎙️ COMMENTARY AGENT:")
            if isinstance(commentary_result, dict) and 'commentary_sequence' in commentary_result:
                sequence = commentary_result['commentary_sequence']
                print(f"   Generated {len(sequence)} commentary segments:")
                for i, segment in enumerate(sequence[:3]):  # Show first 3
                    speaker = segment.get('speaker', 'Unknown')
                    text = segment.get('text', '')[:100]
                    emotion = segment.get('emotion', 'neutral')
                    print(f"   [{i+1}] {speaker} ({emotion}): \"{text}...\"")
            else:
                print(f"   {str(commentary_result)[:100]}...")
        
        # Audio Agent Summary
        audio_result = results.get('audio_agent')
        if audio_result:
            print("\n🎧 AUDIO AGENT:")
            if isinstance(audio_result, dict) and 'audio_processing_details' in audio_result:
                details = audio_result['audio_processing_details']
                print(f"   Processed {len(details)} audio segments")
                for detail in details[:2]:  # Show first 2
                    speaker = detail.get('speaker', 'Unknown')
                    style = detail.get('voice_style', 'default')
                    print(f"   - {speaker}: {style} style")
            else:
                print(f"   {str(audio_result)[:100]}...")