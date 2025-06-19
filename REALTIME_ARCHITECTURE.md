# Real-Time NHL Commentary Pipeline Architecture

## 🎯 **Overview**

The Real-Time NHL Commentary Pipeline processes live hockey game data as it arrives, generating professional broadcast commentary with sub-5 second latency. Key innovations include persistent GameBoard caching, adaptive context optimization, and streaming file processing.

## 🏗️ **Core Architecture Principles**

### **1. GameBoard = Persistent Ground Truth (Never Lost)**
```
GameBoard (In-Memory Cache)
├── Game State: Scores, period, time
├── Event History: All goals, penalties, shots  
├── Player Rosters: Validated player lists (roster lock)
├── Processed Events: Deduplication tracking
└── Narrative Context: Compressed game summary

Purpose: Prevents AI hallucinations about scores, players, events
```

### **2. Context = Adaptive Optimization (Cleaned/Compressed)**
```
Agent Session Memory (Temporary)
├── Conversation History: Recent agent interactions
├── Board Context Injection: Current game state
├── Narrative Summary: Compressed game story
└── Processing Instructions: Workflow rules

Purpose: Prevents repetitive commentary, manages memory usage
```

### **3. Real-Time Processing (Streaming, Not Batch)**
```
File Stream: TS1 → TS2 → TS3 → TS4 → ...
Processing:   ↓     ↓     ↓     ↓
             Agent Agent Agent Agent (immediate processing)
```

## 📁 **File Structure**

```
live_commentary_pipeline_realtime.py    # New real-time pipeline
test_realtime_pipeline.py               # Validation tests
requirements.txt                        # Updated with watchdog
src/config/pipeline_config.py           # Enhanced configuration
REALTIME_ARCHITECTURE.md               # This documentation
```

## 🔧 **Key Components**

### **TimestampFileWatcher**
- Monitors live data directory for new JSON files
- Uses `watchdog` library for cross-platform file system events
- Queues new files for immediate processing
- Prevents duplicate processing

### **AdvancedContextManager**
- Analyzes context size in real-time (token estimation)
- Tracks context growth trends
- Triggers optimization when needed
- Prevents memory bloat

### **AdaptiveSessionManager**
- Extends existing SessionManager with smart refresh logic
- Triggers based on: context size, major events, time intervals
- Creates optimized narrative summaries
- Tracks refresh analytics for optimization

### **RealTimeProcessor**
- Processes timestamps as they arrive (not batch)
- Maintains GameBoard persistence
- Coordinates agent processing
- Tracks performance metrics (target <5s per timestamp)

## ⚡ **Real-Time Processing Flow**

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: INITIALIZATION                     │
└─────────────────────────────────────────────────────────────────┘

[NHL API] → [Static Context Generator] → [GameBoard Creation]
    ↓               ↓                           ↓
Team rosters    Player names              Persistent cache
Goalie info     Stadium details           In-memory state
Game info       Team mappings             Truth database

Step 1: Generate static context for game rosters and player validation
Step 2: Create persistent GameBoard cache (ground truth)
Step 3: Initialize real-time agents (Data, Commentary, Audio)
Step 4: Start real-time processor with performance monitoring
```

```
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 2: LIVE DATA COLLECTION START               │
└─────────────────────────────────────────────────────────────────┘

[Live Data Collector] → [File System] → [Timestamp Files]
         ↓                    ↓                ↓
    Background process    data/live/GAME_ID/   *.json files
    Simulates NHL API     Creates files        Every 5 seconds
    Real-time polling     Immediate write      Sequential naming

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Data Collector  │────▶│ File Creation   │────▶│ File Watcher    │
│ (Background)    │     │ (Real-time)     │     │ (Monitoring)    │
│                 │     │                 │     │                 │
│ • NHL API calls │     │ • JSON files    │     │ • Async queue   │
│ • 5s intervals  │     │ • Timestamps    │     │ • Event driven │
│ • Simulation    │     │ • Sequential    │     │ • Immediate     │
└─────────────────┘     └─────────────────┘     └─────────────────┘

Step 5: Start live data collector (background subprocess)
Step 6: Begin file system monitoring (TimestampFileWatcher)
Step 7: Initialize processing queue for incoming files
```

```
┌─────────────────────────────────────────────────────────────────┐
│               PHASE 3: REAL-TIME PROCESSING LOOP               │
│                    (For Each New Timestamp)                    │
└─────────────────────────────────────────────────────────────────┘

New File Detected → GameBoard Update → Context Analysis → Agent Processing
        ↓                  ↓                ↓                 ↓
   File Queue        Sequential Update   Adaptive Refresh   Parallel Agents

Detailed Flow for Each Timestamp:

┌─────────────────┐
│ 8. File Event   │ ← TimestampFileWatcher detects new JSON
│   Detection     │   2024030412_1_00_05.json created
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ 9. GameBoard    │ ← Sequential update (thread-safe)
│    Update       │   • Parse timestamp data
│                 │   • Update scores, goals, events
│                 │   • Maintain persistent state
│                 │   • Prevent hallucinations
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ 10. Context     │ ← AdvancedContextManager analysis
│     Analysis    │   • Measure context size
│                 │   • Check growth trends
│                 │   • Detect major events
│                 │   • Recommend optimization
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ 11. Adaptive    │ ← AdaptiveSessionManager decision
│     Session     │   Triggers:
│     Refresh     │   • Context oversized (>30k tokens)
│                 │   • Major events (goals, penalties)
│                 │   • Growth trend (increasing fast)
│                 │   • Time-based fallback
└─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 12. PARALLEL AGENT PROCESSING                                   │
│                                                                 │
│    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│    │ Data Agent  │───▶│Commentary   │───▶│ Audio Agent │       │
│    │             │    │ Agent       │    │             │       │
│    │ • NHL data  │    │ • Two-person│    │ • TTS gen   │       │
│    │ • Board     │    │ • Dialogue  │    │ • Audio     │       │
│    │   context   │    │ • Natural   │    │   files     │       │
│    │ • Analysis  │    │   flow      │    │ • Streaming │       │
│    └─────────────┘    └─────────────┘    └─────────────┘       │
│                                                                 │
│ Each agent receives:                                            │
│ • Complete GameBoard context (ground truth)                    │
│ • Optimized narrative summary                                  │
│ • Processing instructions                                       │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ 13. Performance │ ← Record metrics
│     Tracking    │   • Processing time (<5s target)
│                 │   • Context size monitoring
│                 │   • Refresh analytics
│                 │   • Queue status
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ 14. Continue    │ ← Return to file monitoring
│     Monitoring  │   Wait for next timestamp file...
└─────────────────┘

Performance Target: Complete steps 8-13 in <5 seconds per timestamp
```

```
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 4: COMPLETION & ANALYTICS                   │
└─────────────────────────────────────────────────────────────────┘

Data Collection End → Stop Monitoring → Final Statistics → State Export
        ↓                  ↓                ↓               ↓
   Process waits      Cancel file       Analytics      GameBoard
   Background ends    watcher task      Summary        Backup

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 15. Collection  │────▶│ 16. Stop        │────▶│ 17. Statistics  │
│     Complete    │     │     Monitoring  │     │     Display     │
│                 │     │                 │     │                 │
│ • Data process  │     │ • Cancel tasks  │     │ • Total processed│
│   finished      │     │ • Stop watcher  │     │ • Avg time      │
│ • All files     │     │ • Clean queue   │     │ • Performance % │
│   processed     │     │                 │     │ • Refresh count │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │ 18. State       │
                                                │     Export      │
                                                │                 │
                                                │ • GameBoard     │
                                                │   final state   │
                                                │ • JSON backup   │
                                                │ • Recovery data │
                                                └─────────────────┘

Final Output:
📊 Timestamps processed: 24
⚡ Avg processing time: 3.8s  
🎭 Performance ratio: 92% (under 5s target)
🔄 Session refreshes: 3 (2 context, 1 major_events)
💾 GameBoard state: data/board_states/game_2024030412_realtime_final.json
```

## 🔄 **Real-Time Data Flow Architecture**

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTINUOUS STREAMING FLOW                   │
└─────────────────────────────────────────────────────────────────┘

NHL API Stream → Live Data Collector → File Creation → Processing Pipeline
     ↓                   ↓                  ↓               ↓
  Real events       Background process   JSON files    Real-time agents
  Every 5 sec       Simulates live       Queued        <5s latency
  Game state        NHL polling          Immediate     Audio output

┌─────────────────────────────────────────────────────────────────┐
│                      MEMORY ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────────┘

GameBoard (Persistent Cache):          Agent Sessions (Temporary):
┌─────────────────┐                   ┌─────────────────┐
│ GROUND TRUTH    │                   │ WORKING MEMORY  │
│                 │                   │                 │
│ • Scores: 2-1   │ ────injection───▶ │ • Conversation  │
│ • Goals: [...]  │                   │   history       │
│ • Players: Lock │                   │ • Context size  │
│ • Events: All   │                   │ • Processing    │
│ • State: Live   │                   │   instructions  │
│                 │                   │                 │
│ NEVER LOST      │                   │ REFRESHED       │
│ (Authoritative) │                   │ (Optimized)     │
└─────────────────┘                   └─────────────────┘

Result: Perfect accuracy + Efficient processing
```

## 🧠 **Context Management Strategy**

### **What Gets Cached (Persistent)**
- ✅ **Game Facts**: Scores, goals, rosters, events (GameBoard)
- ✅ **Truth Data**: Everything preventing AI hallucinations
- ✅ **Processing History**: Event deduplication, board state

### **What Gets Optimized (Temporary)**
- 🔄 **Agent Memory**: ADK session conversation history
- 🔄 **Context Size**: Monitored and compressed when needed
- 🔄 **Narrative**: Summarized to prevent repetition

### **Adaptive Refresh Triggers**
1. **Context Size**: When approaching token limits (30k tokens)
2. **Major Events**: Goals, penalties, period changes
3. **Growth Trend**: Rapidly increasing context size
4. **Time-Based**: Fallback every N timestamps (configurable)

### **Context Compression Levels**
- **Standard**: Recent events + core facts
- **High**: Essential facts only (score, period, key goals)
- **Emergency**: Minimal context to prevent overflow

## 📊 **Performance Monitoring**

### **Key Metrics Tracked**
- Processing time per timestamp (target: <5 seconds)
- Context size growth over time
- Session refresh frequency and triggers
- Agent processing latency
- GameBoard update performance

### **Performance Optimizations**
- Parallel agent processing (after sequential board update)
- Adaptive session refresh (not fixed intervals)
- Context compression based on size analysis
- File processing queue management

## 🚀 **Usage**

### **Real-Time Pipeline**
```bash
# Start real-time commentary generation
python live_commentary_pipeline_realtime.py 2024030412 5

# Monitor live data directory for new files
# Process each timestamp as it arrives
# Generate commentary with <5s latency
```

### **Testing & Validation**
```bash
# Test all components before running pipeline
python test_realtime_pipeline.py

# Validates:
# - Import dependencies
# - Configuration values
# - Context management
# - File watching
# - GameBoard persistence
```

### **Configuration**
```env
# Real-time processing settings
REALTIME_MODE=True
FILE_WATCH_TIMEOUT=30.0
CONTEXT_SIZE_THRESHOLD=30000
ADAPTIVE_REFRESH=True
MAX_PROCESSING_TIME=5.0
```

## 🔍 **Monitoring & Debugging**

### **Real-Time Logs**
```
📁 New timestamp file detected: 2024030412_1_00_05.json
⚡ Processing: 2024030412_1_00_05.json (realtime)
🔄 Adaptive session refresh triggered: context_oversized
✅ Completed: 2024030412_1_00_05.json (3.2s)
```

### **Performance Warnings**
```
⚠️  Processing time exceeded 5s target: 6.7s
```

### **Final Statistics**
```
🎯 Real-time pipeline completed!
📊 Timestamps processed: 24
⚡ Avg processing time: 3.8s
🎭 Performance ratio: 92%  (under 5s)
🔄 Session refreshes: 3
```

## 🎭 **Benefits Over Batch Processing**

| Aspect | Batch Pipeline | Real-Time Pipeline |
|--------|----------------|-------------------|
| **Latency** | Minutes (wait for all data) | Seconds (process immediately) |
| **Memory** | High (all data loaded) | Optimized (adaptive management) |
| **Streaming** | ❌ No | ✅ Yes |
| **Context** | Fixed refresh | Adaptive optimization |
| **Monitoring** | End-of-batch only | Real-time metrics |
| **Scalability** | Limited by batch size | Scales with processing speed |

## 🎉 **Expected Outcomes**

1. **Sub-5 Second Latency**: From NHL event to audio commentary
2. **Perfect Accuracy**: GameBoard prevents all hallucinations  
3. **Natural Commentary**: Adaptive context prevents repetition
4. **Scalable Performance**: Handles full 3-period games
5. **Production Ready**: Monitoring, analytics, error handling

This architecture delivers professional-quality live NHL commentary with broadcast-level performance and accuracy.