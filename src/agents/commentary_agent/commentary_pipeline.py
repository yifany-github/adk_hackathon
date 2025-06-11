"""
Commentary Agent Pipeline - Time-stamped Commentary Generation

Processes data agent outputs at each timestamp and generates dialogue commentary
"""

import json
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from .commentary_agent import CommentaryAgent, get_commentary_agent
from .tools import save_commentary_output

class CommentaryPipeline:
    """
    Commentary pipeline that processes data agent outputs and generates 
    timestamped dialogue commentary like the data agent workflow.
    """
    
    def __init__(self, game_id: str):
        self.game_id = game_id
        self.commentary_agent = get_commentary_agent(game_id)
        self.data_agent_dir = f"data/data_agent_outputs"
        self.output_dir = f"data/commentary_agent_outputs"
        
        # Create output directory if needed
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_data_agent_files(self) -> List[str]:
        """Get all data agent output files for this game, sorted by timestamp"""
        try:
            files = []
            for filename in os.listdir(self.data_agent_dir):
                if filename.startswith(f"{self.game_id}_") and filename.endswith("_adk.json"):
                    files.append(filename)
            
            # Sort by timestamp (format: GAMEIED_PERIOD_MM_SS_adk.json)
            files.sort(key=lambda x: self._extract_timestamp(x))
            return files
            
        except Exception as e:
            print(f"❌ Error reading data agent files: {e}")
            return []
    
    def _extract_timestamp(self, filename: str) -> tuple:
        """Extract timestamp from filename for sorting"""
        try:
            # Format: 2024030412_1_00_00_adk.json
            parts = filename.replace("_adk.json", "").split("_")
            if len(parts) >= 4:
                period = int(parts[1])
                minutes = int(parts[2])
                seconds = int(parts[3])
                return (period, minutes, seconds)
            return (0, 0, 0)
        except:
            return (0, 0, 0)
    
    def _format_timestamp(self, period: int, minutes: int, seconds: int) -> str:
        """Format timestamp for output filename"""
        return f"{period}_{minutes:02d}_{seconds:02d}"
    
    async def process_timestamp(self, data_file: str) -> Dict[str, Any]:
        """Process a single data agent output file and generate commentary"""
        try:
            # Read data agent output
            input_path = os.path.join(self.data_agent_dir, data_file)
            with open(input_path, 'r') as f:
                data_agent_output = json.load(f)
            
            print(f"🎙️ Processing {data_file}...")
            
            # Extract timestamp from filename
            timestamp_parts = self._extract_timestamp(data_file)
            timestamp_str = self._format_timestamp(*timestamp_parts)
            
            # Generate commentary using the commentary agent tools
            from .tools import (
                generate_two_person_commentary,
                format_commentary_for_audio,
                analyze_commentary_context
            )
            
            # Create mock context for tools
            static_context = self.commentary_agent.static_context
            
            class MockSession:
                def __init__(self):
                    self.state = {
                        "current_data_agent_output": data_agent_output,
                        "static_context": static_context
                    }
            
            class MockContext:
                def __init__(self):
                    self.session = MockSession()
            
            mock_context = MockContext()
            
            # Step 1: Analyze context
            analysis = analyze_commentary_context(mock_context)
            
            # Step 2: Generate commentary
            if analysis.get('status') == 'success':
                strategy = analysis.get('commentary_strategy', {})
                recommended_type = strategy.get('recommended_type', 'MIXED_COVERAGE')
                
                commentary_result = generate_two_person_commentary(
                    mock_context, 
                    recommended_type
                )
                
                # Step 3: Format for audio
                if commentary_result.get('status') == 'success':
                    audio_result = format_commentary_for_audio(mock_context)
                    
                    # Create output with timestamp info
                    output_data = {
                        "timestamp": {
                            "period": timestamp_parts[0],
                            "minutes": timestamp_parts[1], 
                            "seconds": timestamp_parts[2],
                            "formatted": timestamp_str,
                            "game_time": f"Period {timestamp_parts[0]} - {timestamp_parts[1]:02d}:{timestamp_parts[2]:02d}"
                        },
                        "commentary_data": commentary_result,
                        "audio_format": audio_result,
                        "analysis": analysis,
                        "data_agent_input": data_agent_output,
                        "metadata": {
                            "game_id": self.game_id,
                            "generated_at": datetime.now().isoformat(),
                            "agent_version": "adk_commentary_v1.0",
                            "data_source": data_file
                        }
                    }
                    
                    # Save timestamped commentary output
                    output_filename = f"{self.game_id}_commentary_{timestamp_str}.json"
                    output_path = os.path.join(self.output_dir, output_filename)
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(output_data, f, indent=2, ensure_ascii=False)
                    
                    # Show dialogue sample
                    commentary_sequence = commentary_result.get('commentary_sequence', [])
                    if commentary_sequence:
                        print(f"   📝 Generated {len(commentary_sequence)} dialogue lines:")
                        for i, line in enumerate(commentary_sequence[:2]):  # Show first 2
                            speaker = line.get('speaker', 'unknown').upper()
                            text = line.get('text', '')[:60]
                            emotion = line.get('emotion', 'neutral')
                            print(f"      {i+1}. [{speaker}] ({emotion}): {text}...")
                    
                    print(f"   💾 Saved: {output_filename}")
                    
                    return {
                        "status": "success",
                        "output_file": output_path,
                        "timestamp": timestamp_str,
                        "dialogue_lines": len(commentary_sequence)
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"Commentary generation failed: {commentary_result.get('error', 'Unknown error')}",
                        "timestamp": timestamp_str
                    }
            else:
                return {
                    "status": "error", 
                    "error": f"Context analysis failed: {analysis.get('error', 'Unknown error')}",
                    "timestamp": timestamp_str
                }
                
        except Exception as e:
            print(f"   ❌ Error processing {data_file}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "file": data_file
            }
    
    async def process_all_timestamps(self, max_files: Optional[int] = None) -> Dict[str, Any]:
        """Process all data agent outputs for this game"""
        print(f"🏒 Starting Commentary Pipeline for Game {self.game_id}")
        print("=" * 60)
        
        # Get all data agent files
        data_files = self.get_data_agent_files()
        
        if not data_files:
            print(f"❌ No data agent files found for game {self.game_id}")
            return {"status": "error", "error": "No data files found"}
        
        if max_files:
            data_files = data_files[:max_files]
        
        print(f"📁 Found {len(data_files)} data agent output files")
        
        # Process each timestamp
        results = []
        successful = 0
        failed = 0
        
        for i, data_file in enumerate(data_files, 1):
            print(f"\n[{i}/{len(data_files)}] Processing timestamp...")
            
            result = await self.process_timestamp(data_file)
            results.append(result)
            
            if result['status'] == 'success':
                successful += 1
            else:
                failed += 1
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
        
        # Summary
        print(f"\n🎯 Commentary Pipeline Complete!")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📁 Output directory: {self.output_dir}")
        
        return {
            "status": "success",
            "game_id": self.game_id,
            "processed_files": len(data_files),
            "successful": successful,
            "failed": failed,
            "results": results,
            "output_directory": self.output_dir
        }

async def run_commentary_pipeline(game_id: str, max_files: Optional[int] = None) -> Dict[str, Any]:
    """Convenience function to run commentary pipeline for a game"""
    pipeline = CommentaryPipeline(game_id)
    return await pipeline.process_all_timestamps(max_files)

async def main():
    """Test the commentary pipeline"""
    # Test with first 5 timestamps of the game
    result = await run_commentary_pipeline("2024030412", max_files=5)
    
    if result['status'] == 'success':
        print(f"\n✅ Pipeline completed successfully!")
        print(f"Processed {result['successful']} timestamps")
    else:
        print(f"\n❌ Pipeline failed: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())