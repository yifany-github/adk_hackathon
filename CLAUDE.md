# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NHL LiveStream Commentary Agent is a real-time AI-powered hockey commentary system built with Google's Agent Development Kit (ADK). The system uses a 3-agent architecture to transform live NHL game data into engaging audio commentary.

## Architecture

The system implements a **multi-agent architecture** with:

1. **Data Agent** (`src/agents/data_agent/`) - NHL API data processing with ADK-powered analysis
2. **Commentary Agent** (`src/agents/commentary_agent/`) - Gemini AI-powered professional two-person commentary generation  
3. **Audio Agent** (`src/agents/audio_agent/`) - Text-to-speech and WebSocket audio streaming

Data flows through a **3-stage pipeline**:
- **Static Context**: Pre-game team/player information generation with full rosters and player name mapping
- **Live Data Collection**: Real-time NHL API polling with enhanced player name resolution
- **Agent Processing**: Multi-agent coordination for timestamped commentary generation

### Key Data Flow
```
NHL API → Live Data Collector → Data Agent → Commentary Agent → Audio Agent
         (Enhanced names)    (ADK Analysis)  (Two-person)    (TTS Stream)
```

## Key Commands

### Setup and Configuration
```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys (Google ADK, Gemini)
python setup_api_key.py
```

### Running the System
```bash
# Complete game pipeline
python src/data/game_pipeline.py GAME_ID [DURATION_MINUTES]

# Live data collection (simulation mode)
python src/data/live/live_data_collector.py simulate GAME_ID --game_duration_minutes 3

# Generate static context
python src/data/static/static_info_generator.py GAME_ID
```

### Testing
```bash
# Test data agent functionality (regenerates all data with proper player names)
python test_data_agent_adk.py

# Test commentary agent with session awareness (eliminates repetitive commentary)
python test_commentary_session_aware.py --max-files 5

# Test single agent functionality (same file, different mode)
python test_commentary_session_aware.py --test-session

# Test audio agent
python src/agents/audio_agent/test_audio_agent.py

# Test real TTS functionality
python test_real_tts.py

# Basic audio agent tests
python src/agents/audio_agent/test_audio_agent_basic.py

# Extract and view commentary dialogue
python extract_commentary_dialogue.py --continuous
python extract_commentary_dialogue.py --output game_commentary.txt
```

### Commentary Pipeline Testing Workflow
```bash
# 1. Generate enhanced live data with player names
python src/data/live/live_data_collector.py simulate GAME_ID --game_duration_minutes 3

# 2. Process with data agent (creates ADK analysis)
python test_data_agent_adk.py

# 3. Generate commentary from data agent outputs
python test_commentary_session_aware.py --max-files 5

# 4. Extract and review clean dialogue summary  
python extract_commentary_dialogue.py --output game_commentary_cleaned.txt
```

### Data Management
```bash
# Clean data files
./scripts/clean_data.sh

# Organize data structure
./scripts/organize_data.sh
```

## Required Environment Variables

```env
# Google ADK & AI
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
GOOGLE_API_KEY=your-google-api-key

# NHL API Settings
NHL_API_BASE_URL=https://api-web.nhle.com/v1
POLLING_INTERVAL=5

# Audio Settings
DEFAULT_COMMENTARY_STYLE=enthusiastic
ENABLE_AUDIO_STREAMING=true
```

## ADK Session Management for Commentary Continuity

### Session-Aware Commentary Pipeline
The commentary agent uses Google ADK sessions to maintain context across timestamps, eliminating repetitive commentary and ensuring natural conversation flow.

#### Key Concepts:
- **Session**: Maintains conversation history across multiple agent calls
- **Context Continuity**: Agent remembers previous commentary to avoid repetition
- **Production Ready**: Sessions can be persisted to databases for live deployment

#### Implementation Pattern:
```python
# Create ONE session for entire game (not per timestamp)
from google.adk.runners import InMemoryRunner

runner = InMemoryRunner(agent=commentary_agent)
session = await runner.session_service.create_session(
    app_name=runner.app_name, 
    user_id="game_commentator"
)

# Use SAME session across all timestamps
for timestamp_data in game_timestamps:
    response = await runner.run_async(
        user_id=session.user_id,
        session_id=session.id,  # Same session = context preserved
        new_message=timestamp_data
    )
```

#### Session Storage Options:
- **Development**: `InMemorySessionService` (data lost on restart)
- **Production**: Persistent storage backends (Firebase/Firestore, Cloud SQL, etc.)
- **Live Deployment**: Managed sessions via Vertex AI Agent Engine

#### Configuration for Production:
```python
# Example: Custom persistent session service
class FirestoreSessionService(SessionService):
    def __init__(self, firestore_client):
        self.db = firestore_client
    
    async def create_session(self, app_name: str, user_id: str) -> Session:
        # Implement Firestore persistence
        pass
    
    async def get_session(self, session_id: str) -> Session:
        # Restore session from Firestore
        pass
```

#### Best Practices:
- Use session-aware pipeline for natural commentary flow
- Initialize session context at game start
- Persist sessions for live broadcast continuity
- Monitor session memory usage for long games

## Key Dependencies

- `google-adk>=0.1.0` - Google Agent Development Kit
- `google-genai>=0.3.0` - Modern Google AI SDK for Gemini
- `google-cloud-texttospeech>=2.16.0` - Google Cloud TTS
- `websockets>=11.0` - Real-time audio streaming
- `requests>=2.31.0` - NHL API access

## Data Structure

The system generates structured data files:
- **Static Context**: `data/static/game_XXXXXX_static_context.json` (team rosters, player name mappings)
- **Live Data**: `data/live/GAME_ID/game_XXXXXX_live_TIMESTAMP.json` (enhanced with player names)
- **Data Agent Outputs**: `data/data_agent_outputs/GAME_ID_PERIOD_MM_SS_adk.json` (ADK analysis with proper player names)
- **Commentary Outputs**: `data/commentary_agent_outputs/GAME_ID_commentary_PERIOD_MM_SS.json` (timestamped dialogue)
- **Audio Files**: `audio_output/nhl_style_audioID_timestamp.wav`

### Clean Summary Generation
Generate readable commentary summaries:
```bash
# The system automatically creates clean dialogue summaries
# Example: data/commentary_agent_outputs/GAME_ID_dialogue_summary_clean.json
```

## NHL API Integration

Uses NHL Official API (`https://api-web.nhle.com/v1`) for:
- Real-time play-by-play events
- Team rosters and player statistics
- Live game state tracking
- Spatial event conversion

## Audio System

The Audio Agent supports:
- Multiple voice styles (enthusiastic, dramatic, calm)
- Real-time WebSocket streaming on port 8765
- Google TTS integration with audio processing via pydub

## Testing Framework

Uses pytest with comprehensive test coverage:
- Unit tests for individual agent functionality
- Integration tests for multi-agent workflows
- Audio tests for TTS and streaming
- End-to-end pipeline validation

## Development Notes

### Player Name Resolution System
- Live data collector automatically enhances player IDs with human-readable names
- Static context provides comprehensive player mappings for each game
- Data agent uses enhanced player names in commentary talking points
- Format: `"committedByPlayerName": "E. Kane (home)"` in live data

### Commentary Agent Architecture
- Professional two-person broadcast dialogue (Play-by-Play + Color Commentary)
- Context-aware commentary types: FILLER_CONTENT, MIXED_COVERAGE, PLAY_BY_PLAY
- Timestamped dialogue generation with emotion and timing metadata
- Audio-ready formatting with duration estimates and speaker alternation

### Data Pipeline Flow
- Time-windowed data processing prevents future event leakage
- ADK agents coordinate through Google's multi-agent framework
- WebSocket connections handle real-time audio streaming
- System designed for sub-5 second total latency from NHL API to audio output

### Debugging and Quality Assessment
- Clean dialogue summaries automatically generated for commentary quality review
- Bloated debug files with technical data are separated from user-facing outputs
- Timestamp-based file organization for easy navigation and testing