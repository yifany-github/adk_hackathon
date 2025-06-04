# NHL Live Streaming Data Architecture

## Overview
This document describes the data architecture for NHL live audio streaming data generation. The system is designed to prevent data leakage while generating structured event data through a multi-stage pipeline.

## Core Architecture Principles

### 1. **Static vs Dynamic Data Separation**
- **Static Context**: Team info, player rosters, historical stats (generated once)
- **Dynamic Data**: Time-windowed play-by-play events (generated continuously)

### 2. **Two-Stage Data Processing**
- **Stage 1**: Raw data collection from NHL API (live stage)
- **Stage 2**: Event extraction and summarization using LLM (processing stage)

### 3. **Time-Windowed Processing**
- Each update contains only the last 30 seconds of events
- Prevents data leakage while maintaining context continuity

## Detailed Data Flow

### Phase 1: Static Context Generation (One-Time Setup)
```
NHL API → Static Context Generator → static_context.json
```

**Output**: `data/static/game_XXXXXX_static_context.json`
- Team information (names, logos, colors, recent performance)
- Complete player rosters with positions and stats
- Historical head-to-head records
- Season standings and statistics
- Arena information and game metadata

**Purpose**: Provides rich background context for downstream processing

### Phase 2: Live Data Processing (Real-Time Loop)

#### Step 2A: Raw Data Collection
```
NHL Live API → Time Filter (30s window) → raw_events_TIMESTAMP.json
```

**Output**: `data/live/raw/game_XXXXXX_raw_TIMESTAMP.json`
- Raw NHL API response for specific time window
- Filtered to show only plays from last 30 seconds
- Maintains original API structure and detail level
- Time format: Period:MM:SS (e.g., "1:05:30" = Period 1, 5:30)

#### Step 2B: Event Extraction & Summarization
```
raw_events_TIMESTAMP.json → LLM Event Extractor → event_summary_TIMESTAMP.json
```

**Output**: `data/live/events/game_XXXXXX_events_TIMESTAMP.json`
- LLM-processed event summaries
- Key information extracted: player names, action types, locations, outcomes
- Structured format optimized for downstream processing
- Condensed but contextually rich descriptions

**Example Event Summary Structure**:
```json
{
  "timestamp": "1:05:30",
  "period": 1,
  "time_window": "1:05:00-1:05:30",
  "events": [
    {
      "type": "shot",
      "player": "Jack Quinn",
      "team": "BUF", 
      "description": "Wrist shot from right circle, saved by goalie",
      "significance": "high-danger scoring chance"
    }
  ],
  "context": "High-intensity play in offensive zone"
}
```

## File Structure

```
data/
├── static/
│   └── game_XXXXXX_static_context.json      # Team/player/historical data
├── live/
│   ├── raw/
│   │   └── game_XXXXXX_raw_TIMESTAMP.json   # Raw NHL API responses  
│   └── events/
│       └── game_XXXXXX_events_TIMESTAMP.json # LLM-extracted event summaries
```

## Key Benefits

### 1. **Data Leakage Prevention**
- 30-second time windows ensure no future events are exposed
- Live processing maintains authentic streaming experience

### 2. **Efficient LLM Usage**
- Focused LLM processing only on event extraction
- Avoids redundant processing of static context
- Structured output for downstream consumption

### 3. **Scalability**
- Static context generated once per game
- Live processing handles only incremental data
- Time-series structure enables parallel processing

### 4. **Clean Data Separation**
- Raw data preserved for debugging and reprocessing
- Structured events ready for downstream applications
- Clear separation between collection and processing

## Implementation Considerations

### Time Management
- **Live Mode**: Use current game time from NHL API
- **Simulation Mode**: Advance through historical game data
- **Window Size**: 30 seconds provides optimal balance of context vs responsiveness

### Error Handling
- Fallback to manual event descriptions if LLM fails
- Graceful degradation when API data is incomplete
- Retry mechanisms for transient failures

### Performance Optimization
- Cache static context to avoid regeneration
- Batch process multiple time windows when catching up
- Compress raw data for storage efficiency

## Usage Examples

### Data Generation Pipeline
```bash
# Generate static context once
python generate_static_context.py GAME_ID

# Start live data collection every 30 seconds  
python collect_live_data.py GAME_ID --interval 30

# Process raw data through LLM for event extraction
python extract_events.py GAME_ID --process-all
```

### Historical Simulation  
```bash
# Simulate live data collection from completed game
python simulate_live.py GAME_ID --start-time "1:00:00" --duration 600 --interval 30

# Extract events from collected raw data
python extract_events.py GAME_ID --time-range "1:00:00-1:10:00"
```

This architecture enables efficient NHL live streaming data generation with proper data leakage prevention and structured event extraction. t t 