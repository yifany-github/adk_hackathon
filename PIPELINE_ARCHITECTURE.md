# NHL Live Commentary Pipeline - Detailed Architecture

Based on: `/Users/yongboyu/Desktop/adk_hackathon/live_commentary_pipeline_sequential.py`

## 🏗️ How the Sequential Agent + GameBoard Pipeline Works

### Phase-by-Phase Breakdown

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: SETUP & DATA COLLECTION            │
└─────────────────────────────────────────────────────────────────┘

[NHL API] → [Static Context Generator] → [Live Data Collector]
    ↓               ↓                           ↓
Game rosters    Team info, players      Timestamp files (*.json)
Player names    Goalie names            Every 5 seconds for N minutes
Team info       Stadium info            2024030412_1_00_00.json
                                       2024030412_1_00_05.json
                                       2024030412_1_00_10.json
                                       ...

Example timestamp file content:
{
  "game_time": "1_00_05", 
  "activities": [
    {"typeDescKey": "shot-on-goal", "details": {...}},
    {"typeDescKey": "goal", "details": {"scoringPlayerId": 123, ...}}
  ],
  "current_score": {"away": 1, "home": 0},
  "shots": {"away": 3, "home": 2}
}
```

```
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 2: GAMEBOARD STATE BUILDING                 │
│                    (Sequential Processing)                      │
└─────────────────────────────────────────────────────────────────┘

This is the CRITICAL innovation - we process timestamps sequentially 
through GameBoard to build authoritative state, then use that state 
in parallel processing.

GameBoard Creation:
┌─────────────────┐
│  LiveGameBoard  │  ← Created with static context
│                 │
│ current_score:  │    Initial state: 0-0
│   away: 0       │    No goals yet
│   home: 0       │    Empty penalty list
│                 │    Full team rosters loaded
│ goals: []       │
│ penalties: []   │
│ team_rosters:   │
│   away: [...]   │
│   home: [...]   │
└─────────────────┘

Sequential Board Updates:
Timestamp 1 (1_00_00.json) → GameBoard.update_from_timestamp()
┌─────────────────┐         │
│  LiveGameBoard  │         │
│                 │         ▼
│ current_score:  │    Board examines activities:
│   away: 0       │    - No goals, no penalties
│   home: 0       │    - Updates period/time
│                 │    
│ goals: []       │    Board State: Still 0-0
│ processed_events│    
│   = {1001}      │    ← Tracks processed events
└─────────────────┘

Timestamp 2 (1_00_05.json) → GameBoard.update_from_timestamp()  
┌─────────────────┐         │
│  LiveGameBoard  │         │
│                 │         ▼
│ current_score:  │    Board examines activities:
│   away: 1       │    - GOAL! Player 123 scores for away team
│   home: 0       │    - Updates score: away: 0→1
│                 │    - Adds goal to goals list
│ goals: [        │    
│   {scorer: 123, │    Board State: Now 1-0
│    team: away,  │    
│    time: 1_00_05│    Enhanced Context Created:
│   }]            │    {
│ processed_events│      "original_timestamp": {...},
│   = {1001,1002} │      "board_state": {score: {away:1, home:0}},
└─────────────────┘      "board_prompt": "AUTHORITATIVE STATE: Score 1-0...",
                         "board_update": {new_goals: [...]},
                         "sequence_number": 1
                       }

Continue for ALL timestamps sequentially...
Final result: Array of enriched timestamps with complete board context
```

```
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 3: PARALLEL AGENT PROCESSING                │
│                  (Performance Optimization)                     │
└─────────────────────────────────────────────────────────────────┘

Now we have enriched timestamps, each containing:
1. Original NHL API data
2. Complete GameBoard state AT THAT MOMENT
3. Board prompt injection text
4. Sequence information

┌─────────────────────────────────────────────────────────────────┐
│                    PARALLEL PROCESSING                         │
└─────────────────────────────────────────────────────────────────┘

           Enriched Timestamps (with board context)
                            │
                    ┌───────┼───────┐
                    ▼       ▼       ▼
            
     Worker 1          Worker 2          Worker 3
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Sequential Agent│ │ Sequential Agent│ │ Sequential Agent│
│                 │ │                 │ │                 │
│ Input:          │ │ Input:          │ │ Input:          │
│ - Timestamp A   │ │ - Timestamp B   │ │ - Timestamp C   │
│ - Board State A │ │ - Board State B │ │ - Board State C │
│ - Board Prompt A│ │ - Board Prompt B│ │ - Board Prompt C│
│                 │ │                 │ │                 │
│ Workflow:       │ │ Workflow:       │ │ Workflow:       │
│ Data Agent      │ │ Data Agent      │ │ Data Agent      │
│      ▼          │ │      ▼          │ │      ▼          │
│ Commentary Agent│ │ Commentary Agent│ │ Commentary Agent│
│      ▼          │ │      ▼          │ │      ▼          │
│ Audio Agent     │ │ Audio Agent     │ │ Audio Agent     │
│                 │ │                 │ │                 │
│ Output:         │ │ Output:         │ │ Output:         │
│ - Audio files   │ │ - Audio files   │ │ - Audio files   │
│ - Commentary    │ │ - Commentary    │ │ - Commentary    │
└─────────────────┘ └─────────────────┘ └─────────────────┘

Key: Each worker processes INDEPENDENTLY - no shared state!
```

## 🔄 Detailed Agent Workflow (Inside Each Sequential Agent)

```
┌─────────────────────────────────────────────────────────────────┐
│           INSIDE EACH SEQUENTIAL AGENT WORKER                  │
└─────────────────────────────────────────────────────────────────┘

Input: Enhanced timestamp with board context
{
  "original_timestamp": {NHL API data},
  "board_state": {current score, goals, players, etc.},
  "board_prompt": "AUTHORITATIVE STATE: Rangers lead 2-1, Kane scored at...",
  "board_update": {what changed in this timestamp}
}

Step 1: Enhanced Prompt Creation
enhanced_prompt = f"""
ENHANCED NHL COMMENTARY PIPELINE with GAMEBOARD INTEGRATION

=== AUTHORITATIVE GAME STATE (GameBoard) ===
{board_prompt}
Current Score: NYR 2 - FLA 1
Last Goal: E. Kane (NYR) at 14:32 of 1st period
Active Players: [Kane, Panarin, Barkov, Reinhart...]
Shots: NYR 15 - FLA 12
Period: 2, 15:30 remaining

=== TIMESTAMP DATA ===
{original NHL API timestamp data}

=== BOARD UPDATE CONTEXT ===
{what events happened in this specific timestamp}

CRITICAL: Use the GameBoard state as SINGLE SOURCE OF TRUTH
- Never contradict board facts
- Build on established game narrative
- Reference previous events from board context
"""

Step 2: Sequential Agent Processing
┌─────────────────┐
│   Data Agent    │ ← Receives enhanced prompt
│                 │
│ Analyzes:       │
│ - NHL API data  │
│ - Board context │
│ - Game situation│
│                 │
│ Output:         │
│ "Key play: Shot │
│ by Panarin saved│
│ by Bobrovsky.   │
│ Building on     │
│ Kane's earlier  │ ← References board context!
│ goal..."        │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│Commentary Agent │ ← Receives data agent output + board context
│                 │
│ Creates:        │
│ Two-person      │
│ broadcast       │
│ dialogue        │
│                 │
│ Output:         │
│ "Alex: Great    │
│ save by Bob!    │
│ Mike: That's his│
│ 12th save, and  │
│ Rangers still   │ ← Knows score from board!
│ lead 2-1 thanks │
│ to Kane's goal" │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  Audio Agent    │ ← Receives commentary + board context
│                 │
│ Converts:       │
│ Text → Speech   │
│ Multiple voices │
│ Emotion/timing  │
│                 │
│ Output:         │
│ alex_segment1.wav
│ mike_segment1.wav
│ alex_segment2.wav
└─────────────────┘
```

## 🔑 Key Advantages of This Architecture

### 1. **No Race Conditions**
```
❌ PROBLEM: Multiple workers updating shared GameBoard simultaneously
Thread 1: score = 1, writes score = 2
Thread 2: score = 1, writes score = 2  ← Should be 3!

✅ SOLUTION: Sequential board updates, parallel processing with pre-built context
Phase 1: Build all board states sequentially (thread-safe)
Phase 2: Each worker gets its own copy of board context (no sharing)
```

### 2. **Performance + Quality**
```
Current Pipeline Performance:
Timestamp 1: 30 seconds (board + 3 agents)
Timestamp 2: 30 seconds (board + 3 agents)  
Timestamp 3: 30 seconds (board + 3 agents)
Total: 90 seconds

New Pipeline Performance:
Phase 1 (sequential): 10 seconds (board updates only)
Phase 2 (parallel): 30 seconds (3 timestamps × 3 agents in parallel)
Total: 40 seconds (56% faster!)
```

### 3. **Perfect Context**
```
Old Sequential Agent (no board):
"A shot is taken..." ← Doesn't know game score/context

New Sequential Agent (with board):
"With Rangers leading 2-1 thanks to Kane's first period goal, 
Panarin takes a shot that could extend their lead!" 
← Perfect context awareness!
```

## 🧠 Agent Context & Memory Management

### ADK Session Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT MEMORY STRUCTURE                      │
└─────────────────────────────────────────────────────────────────┘

Each Sequential Agent Worker has:
┌─────────────────┐
│ ADK Session     │
│                 │
│ Session Memory: │
│ ┌─────────────┐ │
│ │ Initial     │ │ ← Enhanced prompt with board context
│ │ Context     │ │   - Authoritative game state
│ │             │ │   - Game rules & constraints
│ │ - Game ID   │ │   - Player rosters (roster lock)
│ │ - Board     │ │   - Current score/situation
│ │   State     │ │
│ │ - Rules     │ │
│ │ - Rosters   │ │
│ └─────────────┘ │
│                 │
│ Conversation    │
│ History:        │
│ ┌─────────────┐ │
│ │ Msg 1: NHL  │ │ ← Enhanced prompt with board context
│ │ workflow    │ │
│ │ request     │ │
│ │             │ │
│ │ Response 1: │ │ ← Data→Commentary→Audio result
│ │ Complete    │ │
│ │ processed   │ │
│ │ output      │ │
│ └─────────────┘ │
└─────────────────┘

Key: Each worker = Independent session = No shared memory
```

### Context Injection Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│               ENHANCED PROMPT STRUCTURE                        │
└─────────────────────────────────────────────────────────────────┘

For each Sequential Agent call:

Enhanced Prompt = {
  ┌─────────────────────────────────────────┐
  │ AUTHORITATIVE GAME STATE (GameBoard)   │ ← Injected board context
  │ ═══════════════════════════════════════ │
  │ • Current Score: NYR 2 - FLA 1         │
  │ • Last Goal: E. Kane (NYR) at 14:32    │
  │ • Active Players: [Kane, Panarin, ...] │ ← Roster lock
  │ • Shots: NYR 15 - FLA 12               │
  │ • Period: 2, 15:30 remaining           │
  │ • Active Penalties: [...]              │
  │ • Recent Goals: [goal1, goal2, ...]    │
  └─────────────────────────────────────────┘
  
  ┌─────────────────────────────────────────┐
  │ TIMESTAMP DATA (NHL API)               │ ← Current event data
  │ ═══════════════════════════════════════ │
  │ • Game Time: 1_15_30                   │
  │ • Activities: [shot, save, ...]        │
  │ • Event Details: {...}                 │
  └─────────────────────────────────────────┘
  
  ┌─────────────────────────────────────────┐
  │ PROCESSING INSTRUCTIONS                │ ← Agent workflow rules
  │ ═══════════════════════════════════════ │
  │ • WORKFLOW: Data→Commentary→Audio      │
  │ • CRITICAL: Use board state as truth   │
  │ • Never contradict board facts         │
  │ • Reference previous events from board │
  └─────────────────────────────────────────┘
}
```

### Memory Isolation & Independence

```
┌─────────────────────────────────────────────────────────────────┐
│                 PARALLEL WORKER ISOLATION                      │
└─────────────────────────────────────────────────────────────────┘

Worker 1 Memory:                Worker 2 Memory:
┌─────────────────┐            ┌─────────────────┐
│ Session A       │            │ Session B       │
│                 │            │                 │
│ Board Context:  │            │ Board Context:  │
│ - Timestamp A   │            │ - Timestamp B   │
│ - Game State A  │            │ - Game State B  │
│ - Sequence: 0   │            │ - Sequence: 1   │
│                 │            │                 │
│ Processing:     │            │ Processing:     │
│ - Input: A      │            │ - Input: B      │
│ - Output: A     │            │ - Output: B     │
└─────────────────┘            └─────────────────┘
       │                              │
       ▼                              ▼
No shared memory!           Independent processing!

Result: No race conditions, perfect isolation
```

### Context Lifecycle Management

```
┌─────────────────────────────────────────────────────────────────┐
│              SESSION LIFECYCLE (Per Worker)                    │
└─────────────────────────────────────────────────────────────────┘

1. Session Creation:
   ┌──────────────────────────────────────┐
   │ InMemoryRunner.create_session()      │
   │                                      │
   │ • user_id: "nhl_{game_id}_enhanced"  │
   │ • session_id: unique_generated_id    │
   │ • app_name: sequential_agent.name    │
   └──────────────────────────────────────┘

2. Context Initialization:
   ┌──────────────────────────────────────┐
   │ UserContent(enhanced_prompt)         │
   │                                      │
   │ Contains:                            │
   │ • Complete board state               │
   │ • NHL API timestamp data             │
   │ • Processing instructions            │
   │ • Workflow rules                     │
   └──────────────────────────────────────┘

3. Agent Processing:
   ┌──────────────────────────────────────┐
   │ Sequential Agent Execution           │
   │                                      │
   │ Data Agent:                          │
   │ • Receives: enhanced_prompt          │
   │ • Context: board + timestamp         │
   │ • Output: analyzed game state        │
   │                                      │
   │ Commentary Agent:                    │
   │ • Receives: data_output + context    │
   │ • Context: board + game situation    │
   │ • Output: broadcast dialogue         │
   │                                      │
   │ Audio Agent:                         │
   │ • Receives: commentary + context     │
   │ • Context: speaker + emotion info    │
   │ • Output: audio files                │
   └──────────────────────────────────────┘

4. Session Cleanup:
   ┌──────────────────────────────────────┐
   │ Automatic cleanup after processing   │
   │                                      │
   │ • Session ends when worker completes │
   │ • Memory released automatically      │
   │ • No persistent state maintained     │
   └──────────────────────────────────────┘
```

### Memory Management Features

```
┌─────────────────────────────────────────────────────────────────┐
│                   MEMORY MANAGEMENT BENEFITS                   │
└─────────────────────────────────────────────────────────────────┘

1. **Context Collapse Prevention**:
   ✅ Board state injected into every agent call
   ✅ Authoritative facts prevent AI memory drift
   ✅ Consistent game narrative across all workers

2. **Memory Isolation**:
   ✅ Each worker has independent ADK session
   ✅ No shared mutable state between workers
   ✅ Parallel processing without interference

3. **Efficient Resource Usage**:
   ✅ Sessions created only when needed
   ✅ Automatic cleanup after processing
   ✅ No persistent memory bloat

4. **Perfect Context Injection**:
   ✅ Complete game state in every prompt
   ✅ No context loss between agents
   ✅ Cumulative game awareness maintained
```

### Board Context vs Session Memory

```
┌─────────────────────────────────────────────────────────────────┐
│                 BOARD CONTEXT vs SESSION MEMORY                │
└─────────────────────────────────────────────────────────────────┘

GameBoard (External State):           ADK Session (AI Memory):
┌─────────────────┐                  ┌─────────────────┐
│ Authoritative   │                  │ Conversation    │
│ Game State      │                  │ Context         │
│                 │                  │                 │
│ • Scores        │ ────injection──► │ • Enhanced      │
│ • Goals         │                  │   prompts       │
│ • Players       │                  │ • Agent         │
│ • Penalties     │                  │   responses     │
│ • Timeline      │                  │ • Processing    │
│                 │                  │   history       │
│ PERSISTENT      │                  │ TEMPORARY       │
│ (Truth source)  │                  │ (AI working     │
│                 │                  │  memory)        │
└─────────────────┘                  └─────────────────┘

Flow: Board facts → Injected into → AI session context
Result: AI never contradicts authoritative game state
```

## 📊 Data Flow Summary

```
1. NHL API Data → 2. Live Data Collection → 3. GameBoard Sequential Updates
                                                      ↓
   8. Audio Files ← 7. Parallel Sequential Agents ← 4. Enhanced Timestamps
                          ↑
                   5. Board Context Injection
                   6. Independent ADK Sessions
```

**The magic happens in steps 3→4→5**: We build authoritative game state sequentially (safe), then inject that context into independent ADK sessions for parallel processing (fast + accurate + isolated).

This gives you **maximum performance**, **maximum commentary quality**, AND **perfect memory management**!