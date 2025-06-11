# NHL Commentary Agent - Google ADK Implementation

Professional two-person broadcast commentary generation using Google ADK framework.

## Files Structure

### Core Files
- **`commentary_agent.py`** - Main commentary agent implementation with ADK BaseAgent pattern
- **`commentary_pipeline.py`** - Timestamped commentary processing pipeline 
- **`tools.py`** - ADK tools for context analysis, commentary generation, and audio formatting
- **`prompts.py`** - Commentary prompts and instructions for different scenarios
- **`__init__.py`** - Package initialization

### Output Directory
- **`data/commentary_agent_outputs/`** - Timestamped commentary JSON files
  - Format: `{GAME_ID}_commentary_{PERIOD}_{MM}_{SS}.json`
  - Example: `2024030412_commentary_1_00_00.json`

## Usage

### Basic Commentary Generation
```python
from src.agents.commentary_agent.commentary_agent import get_commentary_agent, generate_game_commentary

# Create agent for specific game
agent = get_commentary_agent("2024030412")

# Generate commentary from data agent output
result = await generate_game_commentary("2024030412", data_agent_output)
```

### Timestamped Pipeline Processing
```python
from src.agents.commentary_agent.commentary_pipeline import run_commentary_pipeline

# Process all timestamps for a game
result = await run_commentary_pipeline("2024030412")

# Process first N timestamps only
result = await run_commentary_pipeline("2024030412", max_files=10)
```

## Commentary Types

- **FILLER_CONTENT**: Color commentator leads (60-70% speaking time) - low momentum
- **MIXED_COVERAGE**: Balanced dialogue (50-50 speaking time) - medium momentum  
- **HIGH_INTENSITY**: PBP dominates (70-80% speaking time) - high momentum/action

## Output Format

Each timestamp generates:
- **Commentary dialogue**: Speaker, text, emotion, timing, duration
- **Audio format**: Voice style, pause timing, TTS-ready segments
- **Analysis data**: Strategy, momentum score, recommendations
- **Metadata**: Game ID, timestamp, agent version, source data

## Integration

The commentary agent integrates with:
- **Data Agent**: Consumes timestamped analysis outputs
- **Audio Agent**: Provides formatted dialogue for TTS processing
- **Live Pipeline**: Processes real-time game data streams