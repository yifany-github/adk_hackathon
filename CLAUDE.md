# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NHL LiveStream Commentary Agent is a real-time AI-powered hockey commentary system built with Google's Agent Development Kit (ADK). The system uses a 3-agent architecture to transform live NHL game data into engaging audio commentary.

## Architecture

The system implements a **multi-agent architecture** with:

1. **Data Agent** (`src/agents/data_agent/`) - NHL API data processing with ADK-powered analysis
2. **Commentary Agent** (`src/agents/commentary_agent/`) - Gemini AI-powered professional two-person commentary generation  
3. **Audio Agent** (`src/agents/audio_agent/`) - Text-to-speech and WebSocket audio streaming

Data flows through a **3-stage pipeline** with **data leakage prevention**:
- **Static Context**: Pre-game team/player information generation with full rosters and player name mapping
- **Live Data Collection**: Real-time NHL API polling with progressive stats calculation (prevents future data leakage)
- **Agent Processing**: Multi-agent coordination for timestamped commentary generation

### Key Data Flow
```
NHL API → Live Data Collector → Data Agent → Commentary Agent → Audio Agent
         (Progressive stats)  (ADK Analysis)  (Two-person)    (TTS Stream)
         (No leakage)         (Realistic)     (Natural flow)
```

### Data Integrity Features
- **Progressive Statistics**: Game stats calculated from time-filtered events only
- **Leakage Prevention**: No future game data contaminates early timestamps  
- **Realistic Progression**: Games start 0-0 and accumulate stats naturally

### Live Game Board Architecture (v4.0)
- **Context Collapse Prevention**: External state management prevents AI memory corruption
- **Authoritative State Injection**: Game facts maintained outside AI sessions, injected into every prompt
- **Roster Lock Enforcement**: Only valid team players can be mentioned, prevents phantom players
- **Score Consistency Tracking**: Scores can only increase, prevents statistical amnesia
- **Session Refresh System**: Periodic context refresh with narrative compaction
- **Board-Integrated Pipeline**: `live_commentary_pipeline_v2.py` with full state management

### Pipeline Improvements (v3.0) 
- **Live Commentary Pipeline**: Single-command end-to-end processing (`live_commentary_pipeline.py`)
- **Shared Session Management**: Persistent ADK sessions for penalty tracking and game state continuity
- **Session Initialization**: Proper broadcaster name establishment (Alex Chen & Mike Rodriguez)
- **Organized File Structure**: Game-specific subfolders for outputs (`data/*/GAME_ID/`)
- **Real-time Processing**: Live data → Data agent → Commentary agent → Audio agent in parallel
- **Fixed Penalty Tracking**: Shared sessions solve Kane+Kulak=5-on-3 game state discipline issues

### Pipeline Redesign (v6.0 - Planned)
- **Simplified Architecture**: Remove 200+ lines of complex session management (see `PIPELINE_REDESIGN.md`)
- **Sequential Agent Fix**: Single persistent agent per game vs creating new agent per timestamp
- **Sequential Output Ordering**: Chronological audio generation even with parallel processing
- **Clean Context Injection**: GameBoard + static context injected at agent creation, not per timestamp
- **Maintained Parallel Processing**: Background data collection + async file monitoring + sequential output

## Key Commands

### Setup and Configuration
```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys (Google ADK, Gemini)
python setup_api_key.py
```

### Running the System

#### **Complete NHL Commentary Pipeline (v5.0 - with Live Audio Streaming)**
```bash
# Full pipeline: Data → Commentary → Audio with live WebSocket streaming
python live_commentary_pipeline.py GAME_ID [DURATION_MINUTES]

# Examples:
python live_commentary_pipeline.py 2024030413 2    # 2-minute test with live audio
python live_commentary_pipeline.py 2024030412 1    # 1-minute quick test

# Clients can connect to live audio stream:
# ws://localhost:8765
```

#### **Individual Components (Advanced)**
```bash
# Live data collection (simulation mode)
python src/data/live/live_data_collector.py simulate GAME_ID --game_duration_minutes 3

# Generate static context (full)
python src/data/static/static_info_generator.py GAME_ID

# Generate light static context (90% smaller, 2 teams only)
python src/data/static/light_static_info_generator.py GAME_ID
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

### Complete Pipeline Workflow (Production-Ready)
```bash
# Option 1: Original Pipeline (complex session management)
python live_commentary_pipeline.py GAME_ID DURATION_MINUTES

# Option 2: Simplified Pipeline v2 (with Sequential Agent v2)
python live_commentary_pipeline_v2.py GAME_ID DURATION_MINUTES

# Extract commentary summary for review
python extract_commentary_dialogue.py --output game_GAME_ID_summary.txt

# Example workflows:
python live_commentary_pipeline_v2.py 2024030412 2    # Sequential Agent v2
python live_commentary_pipeline.py 2024030412 2      # Original complex pipeline
python extract_commentary_dialogue.py --output game_2024030412_summary.txt
```

### Legacy Testing Workflow (Manual Steps)
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

The system generates structured data files with **progressive statistics** and **organized game-specific folders**:

### File Organization (v4.0)
- **Static Context**: `data/static/game_XXXXXX_static_context.json` (full team rosters, player name mappings)
- **Light Static Context**: `data/static/game_XXXXXX_minimal_context.json` (90% smaller, 2 teams only)
- **Live Data**: `data/live/GAME_ID/GAME_ID_PERIOD_MM_SS.json` (progressive stats, no data leakage)
- **Sequential Agent Outputs**: `data/sequential_agent_outputs/GAME_ID/PERIOD_MM_SS_sequential.json` (clean combined output)
- **Data Agent Outputs**: `data/data_agent_outputs/GAME_ID/PERIOD_MM_SS_adk.json` (realistic game context)
- **Commentary Outputs**: `data/commentary_agent_outputs/GAME_ID/PERIOD_MM_SS_commentary_session_aware.json` (natural dialogue flow)
- **Audio Files**: `audio_output/nhl_style_audioID_timestamp.wav`

### Example Structure
```
data/
├── static/
│   ├── game_2024030412_static_context.json (125KB - full context)
│   └── game_2024030412_minimal_context.json (9KB - 90% smaller, 2 teams only)
├── live/
│   ├── 2024030412/
│   │   ├── 2024030412_1_00_00.json
│   │   └── 2024030412_1_00_05.json
│   ├── 2024020001/
│   │   └── 2024020001_1_00_00.json
│   └── ...
├── sequential_agent_outputs/2024030412/
│   ├── 1_00_00_sequential.json (clean combined data + commentary)
│   └── 1_00_05_sequential.json
├── data_agent_outputs/2024030412/
│   ├── 1_00_00_adk.json
│   └── 1_00_05_adk.json
└── commentary_agent_outputs/2024030412/
    ├── 1_00_00_commentary_session_aware.json
    └── 1_00_05_commentary_session_aware.json
```

### Data Integrity Improvements (v4.0)
- **Fixed Data Leakage**: Live data now calculates progressive stats from filtered events only
- **Realistic Game Progression**: Games start 0-0, scores/shots accumulate naturally over time
- **Temporal Consistency**: No future stats contaminate early timestamps
- **Light Static Context**: 90% size reduction focusing on 2 teams playing only
- **Sequential Agent Integration**: Clean combined output with proper Alex Chen/Mike Rodriguez personas
- **Multiple Game Support**: Pipeline tested with 5 different NHL games (2024020001-2024020005)

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

### Data Pipeline Flow (v2.1 - Data Leakage Fixed)
- **Progressive Statistics**: Game stats calculated from time-filtered events only (no boxscore injection)
- **Temporal Integrity**: Activities filtered by time window, stats calculated from filtered events
- **ADK agents coordinate** through Google's multi-agent framework with realistic game context
- **WebSocket connections** handle real-time audio streaming
- **System designed** for sub-5 second total latency from NHL API to audio output

### Critical Fix: Data Leakage Prevention
**Problem Solved**: Previously, live data collector injected final game stats into all timestamps
**Solution**: Replace boxscore injection with progressive stats calculation from filtered activities
**Result**: Games now start 0-0 and progress naturally, enabling realistic commentary generation

### Debugging and Quality Assessment
- Clean dialogue summaries automatically generated for commentary quality review
- Bloated debug files with technical data are separated from user-facing outputs
- Timestamp-based file organization for easy navigation and testing