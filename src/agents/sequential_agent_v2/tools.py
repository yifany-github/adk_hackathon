"""
Clean Sequential Agent - Tools
Simple output processing for NHL commentary pipeline
"""

import json
import os
from datetime import datetime

def save_clean_result(game_id: str, timestamp_name: str, parsed_result: dict) -> str:
    """Save clean Sequential Agent result"""
    
    # Create output directory
    output_dir = f"data/sequential_agent_outputs/{game_id}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output filename
    output_file = f"{output_dir}/{timestamp_name}_sequential.json"
    
    # Create clean, readable result with extracted agent outputs
    clean_result = {
        "timestamp": timestamp_name,
        "game_id": game_id,
        "processed_at": datetime.now().isoformat(),
        "status": "success",
        "data_agent": parsed_result.get("data_agent", {}),
        "commentary_agent": parsed_result.get("commentary_agent", {}),
        "debug_info": {
            "raw_preview": parsed_result.get("raw_debug", ""),
            "extraction_error": parsed_result.get("extraction_error")
        }
    }
    
    # Save clean result
    with open(output_file, 'w') as f:
        json.dump(clean_result, f, indent=2)
    
    print(f"✅ Saved sequential result: {output_file}")
    return output_file

def extract_commentary_from_output(raw_output: str) -> dict:
    """Extract commentary dialogue from raw output"""
    try:
        # Look for commentary sequence in the output
        if "commentary_sequence" in raw_output:
            # Try to find JSON blocks
            lines = raw_output.split('\n')
            for i, line in enumerate(lines):
                if 'commentary_sequence' in line:
                    # Extract surrounding JSON context
                    json_start = max(0, i-5)
                    json_end = min(len(lines), i+15)
                    json_block = '\n'.join(lines[json_start:json_end])
                    
                    # Try to parse
                    try:
                        parsed = json.loads(json_block)
                        if 'commentary_sequence' in parsed:
                            return parsed
                    except:
                        pass
        
        return {"status": "no_commentary_found"}
    except:
        return {"status": "extraction_error"}

def extract_data_analysis(raw_output: str) -> dict:
    """Extract data analysis from raw output"""
    try:
        # Look for momentum score and analysis
        analysis = {}
        
        if "momentum_score" in raw_output:
            # Extract momentum info
            lines = raw_output.split('\n')
            for line in lines:
                if 'momentum_score' in line.lower():
                    analysis['momentum_info'] = line.strip()
                    break
        
        if "high_intensity_events" in raw_output:
            analysis['has_events'] = True
        
        return analysis if analysis else {"status": "no_analysis_found"}
    except:
        return {"status": "extraction_error"}