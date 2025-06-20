# NHL Live Commentary Pipeline Redesign Plan

## Current State Analysis

### Problems with Current Pipeline (`live_commentary_pipeline.py`)
1. **Over-Complicated Architecture**: 540+ lines with complex session management that's largely unused
2. **Sequential Agent Misuse**: Creates new Sequential Agent per timestamp (line 299), defeating session persistence
3. **Dead Code**: `AdaptiveSessionManager` (~90 lines) and `AdvancedContextManager` (~65 lines) provide complex logic that Sequential Agent handles automatically
4. **Missing Sequential Ordering**: Parallel processing without timestamp ordering could cause out-of-order audio output

### What's Working Well
- ✅ **Parallel Data Collection**: Background subprocess generating timestamp files
- ✅ **Real-time File Monitoring**: Async detection of new timestamp files  
- ✅ **GameBoard Integration**: Clean game state management and context injection
- ✅ **Static Context Generation**: Team rosters and player name mapping

## Redesigned Architecture

### Core Design Principles
1. **Simplicity**: Remove unnecessary complexity while maintaining functionality
2. **Sequential Output**: Ensure chronological ordering of commentary/audio
3. **Parallel Processing**: Maintain concurrent data collection and processing
4. **Single Sequential Agent**: One agent per game with persistent sessions
5. **Proper Context Injection**: GameBoard + static context injected at agent creation

### New Pipeline Flow

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Static Setup  │    │   GameBoard      │    │  Sequential Agent   │
│                 │    │                  │    │                     │
│ • Generate      │    │ • Team rosters   │    │ • Data Agent        │
│   static context│───▶│ • Player names   │───▶│ • Commentary Agent  │
│ • Team info     │    │ • Game state     │    │ • Audio Agent       │
│ • Player roster │    │ • Score tracking │    │ • Session persistence│
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                                │                           ▲
                                ▼                           │
                    ┌──────────────────┐    ┌─────────────────────┐
                    │ Live Data        │    │ Sequential          │
                    │ Collection       │    │ Processing Queue    │
                    │                  │    │                     │
                    │ • NHL API        │    │ • Timestamp ordering│
                    │ • Real-time      │    │ • Parallel detect   │
                    │ • Progressive    │───▶│ • Sequential output │
                    │   stats          │    │ • Audio file order  │
                    └──────────────────┘    └─────────────────────┘
```

### Key Components

#### 1. Static Context & GameBoard (Keep Existing)
```python
# Generate static context
await generate_static_context(game_id)

# Initialize GameBoard with team rosters, player names
game_board = create_live_game_board(game_id, static_context_file)
```

#### 2. Sequential Agent Setup (Major Fix)
```python
# Create ONE Sequential Agent per game with full context
sequential_agent = create_nhl_sequential_agent(
    game_id=game_id,
    game_board_context=game_board.get_full_context(),
    static_context=static_context,
    broadcaster_names={"play_by_play": "Alex Chen", "analyst": "Mike Rodriguez"}
)

# Agent persists throughout entire game with session continuity
```

#### 3. Parallel Processing with Sequential Output
```python
# Data collection runs in background (parallel)
data_process = start_live_data_collection(game_id, duration_minutes)

# File monitoring detects new timestamps (parallel)  
file_watcher = TimestampFileWatcher(game_id, timestamp_queue)

# Processing queue ensures sequential output (ordered)
timestamp_queue = TimestampOrderingQueue()
processor = SequentialProcessor(sequential_agent, timestamp_queue)
```

#### 4. Timestamp Ordering System (New Component)
```python
class TimestampOrderingQueue:
    """Ensures chronological processing even with parallel file detection"""
    
    def __init__(self):
        self.pending_files = {}  # {timestamp: file_path}
        self.next_expected = None
        self.processing_lock = asyncio.Lock()
    
    async def add_file(self, file_path: str):
        """Add file to queue, process if it's next in sequence"""
        timestamp = extract_timestamp(file_path)
        self.pending_files[timestamp] = file_path
        
        # Process files in order
        await self._process_sequential_files()
    
    async def _process_sequential_files(self):
        """Process files in chronological order"""
        while self.next_expected in self.pending_files:
            file_path = self.pending_files.pop(self.next_expected)
            await self.processor.process_timestamp_ordered(file_path)
            self.next_expected = self._calculate_next_timestamp()
```

## Implementation Plan

### Phase 1: Create New Pipeline File
- **File**: `live_commentary_pipeline_simple.py`
- **Lines**: ~300 (vs current 540+)
- **Focus**: Clean, readable architecture

### Phase 2: Remove Complex Components
```python
# DELETE these classes (200+ lines of dead code):
# - AdaptiveSessionManager
# - AdvancedContextManager  
# - Complex session refresh logic
# - Context compression algorithms
# - Token estimation systems
```

### Phase 3: Fix Sequential Agent Usage
```python
# BEFORE (wrong - creates agent per timestamp):
sequential_agent = create_nhl_sequential_agent(game_id)  # Line 299
result = await process_timestamp(sequential_agent, timestamp_file, game_id)

# AFTER (correct - single persistent agent):
sequential_agent = create_nhl_sequential_agent_with_context(
    game_id, game_board, static_context
)  # Created once at startup
result = await sequential_agent.process_timestamp(timestamp_file)
```

### Phase 4: Add Sequential Ordering
```python
# Ensure audio files are generated in chronological order
# Even if 1:00:05 processes before 1:00:00, audio output maintains order
timestamp_queue = TimestampOrderingQueue()
processor = SequentialProcessor(sequential_agent, timestamp_queue)
```

### Phase 5: Maintain Parallel Processing
```python
# Keep existing parallel architecture:
# 1. Data collection subprocess (background)
# 2. File monitoring async (parallel detection)  
# 3. Processing queue (sequential output)

async def run_simplified_pipeline():
    # Parallel data collection
    data_process = start_live_data_collection(game_id, duration_minutes)
    
    # Parallel file monitoring
    monitoring_task = start_file_monitoring(game_id, timestamp_queue)
    
    # Sequential processing
    processing_task = start_sequential_processing(sequential_agent, timestamp_queue)
```

## Expected Benefits

### Code Quality
- **~200 lines removed**: Complex session management code elimination
- **Improved readability**: Clear separation of concerns
- **Maintainability**: Simplified logic flow

### Functionality
- **Sequential ordering**: Guaranteed chronological audio output
- **Session continuity**: Proper Sequential Agent usage with persistent sessions
- **Parallel efficiency**: Maintained concurrent data collection and processing
- **Context integration**: GameBoard and static context properly injected

### Performance
- **Single agent creation**: No per-timestamp agent overhead
- **Optimized sessions**: Sequential Agent handles session management efficiently
- **Ordered output**: No audio synchronization issues

## Risk Mitigation

### Preserve Working Components
- Keep existing GameBoard integration
- Maintain parallel data collection subprocess
- Preserve real-time file monitoring
- Retain static context generation

### Test Migration Path
1. Create new pipeline alongside existing
2. Test with same game data
3. Compare outputs for functionality parity
4. Gradually migrate to simplified version

### Rollback Plan
- Keep current `live_commentary_pipeline.py` as backup
- New pipeline in separate file for safe testing
- Can revert to current version if issues arise

## Success Criteria

### Technical
- [ ] ~300 line pipeline (vs current 540+)
- [ ] Single Sequential Agent with persistent sessions
- [ ] Chronological audio output ordering
- [ ] Parallel data collection maintained
- [ ] GameBoard context properly integrated

### Functional  
- [ ] Same commentary quality as current system
- [ ] Proper broadcaster names (Alex Chen & Mike Rodriguez)
- [ ] No audio timing/ordering issues
- [ ] Session continuity across timestamps
- [ ] Real-time processing performance maintained

This redesign maintains all working functionality while dramatically simplifying the codebase and fixing the core Sequential Agent usage issues.