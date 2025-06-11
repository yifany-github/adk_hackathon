# NHL Commentary Agent - Simplified ADK Implementation

Professional two-person broadcast commentary generation using Google ADK framework.
Follows the simple Agent pattern like the data agent.

## Files Structure

### Core Files
- **`commentary_agent.py`** - Main commentary agent implementation using simple ADK Agent pattern
- **`tools.py`** - ADK tools for context analysis, commentary generation, and audio formatting
- **`prompts.py`** - Commentary prompts and instructions for different scenarios
- **`__init__.py`** - Package initialization

### Output Directory
- **`data/commentary_agent_outputs/`** - Commentary JSON files
  - Format: `{GAME_ID}_commentary_{TIMESTAMP}.json`
  - Example: `2024030412_commentary_20250611_1430.json`

## Usage

### Basic Commentary Generation
```python
from src.agents.commentary_agent.commentary_agent import create_commentary_agent_for_game

# Create agent for specific game
agent = create_commentary_agent_for_game("2024030412")

# Use agent with data agent output
result = agent.run(data_agent_output)
```

### Simple Function Access
```python
from src.agents.commentary_agent.commentary_agent import get_commentary_agent

# Get agent for game
agent = get_commentary_agent("2024030412")
```

## Commentary Types

- **FILLER_CONTENT**: General discussion during quiet moments
- **MIXED_COVERAGE**: Balanced analysis and play-by-play
- **HIGH_INTENSITY**: Immediate reactions to action sequences

## Output Format

Generated commentary includes:
- **Commentary dialogue**: Speaker (pbp/color), text, emotion, timing, duration
- **Audio format**: Voice style, pause timing, TTS-ready segments
- **Analysis data**: Strategy, momentum assessment, recommendations
- **Metadata**: Game ID, timestamp, agent version

## Integration

The commentary agent integrates with:
- **Data Agent**: Consumes analysis outputs
- **Audio Agent**: Provides formatted dialogue for TTS processing
- **Live Pipeline**: Processes real-time game data

## Simplified Architecture

This agent follows the same simple pattern as the data agent:
- Single `Agent` factory function
- Direct tool integration
- Callback-based response formatting
- No complex orchestration or managers