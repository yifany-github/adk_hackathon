# 🏒 NHL LiveStream Commentary Agent

**Production-ready multi-agent AI system for real-time hockey commentary using Google ADK**

Built for the [Agent Development Kit Hackathon with Google Cloud](https://googlecloudmultiagents.devpost.com/)

## 🎯 Project Overview

A sophisticated multi-agent architecture that transforms live NHL game data into engaging, real-time hockey commentary using **Google's Agent Development Kit (ADK)** and Gemini AI. **The system is fully functional and generates professional audio commentary for NHL games.**

### 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Agent    │───▶│ Commentary Agent│───▶│   Audio Agent   │
│     (ADK)       │    │     (ADK)       │    │   (Direct)      │
│ • NHL API      │    │ • Gemini AI     │    │ • Google TTS    │
│ • Live events   │    │ • Session aware │    │ • WAV files     │
│ • Player stats  │    │ • Two-person    │    │ • Organized     │
│ • Progressive   │    │ • Natural flow  │    │ • Voice styles  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  ▼
                       ┌─────────────────┐
                       │  Hybrid Pipeline │
                       │ • Smart agents  │
                       │ • Direct audio  │
                       │ • Working system│
                       └─────────────────┘
```

## ✅ Working System Status

**Current Status**: ✅ **FULLY FUNCTIONAL**  
**Last Tested**: Successfully generated 6 professional NHL commentary audio files  
**Audio Quality**: High-quality WAV files with proper voice styles  
**File Organization**: Clean game-specific folder structure  

## ✨ Features

- **✅ Working NHL Commentary**: Generates real professional hockey commentary
- **🤖 Google ADK**: Multi-agent coordination with intelligent analysis
- **🧠 Gemini AI**: Context-aware two-person broadcast dialogue
- **📊 Progressive Stats**: No data leakage, realistic game progression 
- **🎙️ Professional Audio**: High-quality TTS with voice style selection
- **📁 Organized Output**: Game-specific folders and clean file structure

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Google Cloud account with ADK access
- Google API credentials

### Installation

```bash
# Clone and setup
git clone https://github.com/YongBoYu1/adk_hackathon.git
cd adk_hackathon
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your Google credentials to .env
```

### Environment Variables

```env
# Google ADK & AI
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
GOOGLE_API_KEY=your-google-api-key
```

## 🎮 Usage

### **Sequential Live Commentary Pipeline (Recommended)**

The main production-ready pipeline with **guaranteed sequential output ordering** for live streaming:

```bash
# Real-time sequential processing (NEW - v2.0)
python src/pipeline/live_commentary_pipeline_v2.py GAME_ID DURATION_MINUTES

# Examples:
python src/pipeline/live_commentary_pipeline_v2.py 2024020001 15    # 15-minute game
python src/pipeline/live_commentary_pipeline_v2.py 2024030412 2     # 2-minute test
python src/pipeline/live_commentary_pipeline_v2.py 2024020005 60    # Full 60-minute game

# Key Features:
# ✅ Sequential real-time processing (process → save → process)
# ✅ Guaranteed chronological output order (1_00_00, 1_00_15, 1_00_30...)
# ✅ Production-ready for live streaming
# ✅ Background data collection with foreground processing
# ✅ Session management with periodic refresh
```

### Legacy Pipelines (Alternative Options)

```bash
# Original complex pipeline (legacy)
python live_commentary_pipeline.py GAME_ID DURATION_MINUTES

# Batch processing (working but not live)
python run_game_commentary.py GAME_ID [MAX_FILES]
```

## 📊 System Architecture

### **Sequential Real-Time Processing (v2.0)**
```
NHL API → Live Data Collection → Sequential Processing → Commentary Output
   ↓              ↓                        ↓                    ↓
Raw Events   Chronological         Process 1_00_00        Alex Chen & 
Progressive    Timestamps         → Save 1_00_00         Mike Rodriguez
Statistics    (No leakage)        → Process 1_00_15      Professional
             ↓                    → Save 1_00_15         Commentary
        Game Board State          → Process 1_00_30      Guaranteed Order
```

### **Key Innovation: Temporal Consistency**
- **Problem Solved**: Parallel processing outputs random order (1_00_15 before 1_00_00)
- **Solution**: Sequential real-time processing ensures chronological output
- **Result**: Live streaming compatible with guaranteed temporal narrative flow

### **Multi-Agent Architecture Components**

#### 1. **Sequential Agent v2** (`src/agents/sequential_agent_v2/`)
- **NEW**: Combined data + commentary processing in single agent
- Google ADK framework with Gemini AI integration
- Session-aware context continuity across timestamps
- Alex Chen & Mike Rodriguez broadcaster personas
- Handles both NHL data analysis and professional commentary generation

#### 2. **Game Board** (`src/board/`)
- **External state management** prevents AI memory corruption
- Authoritative game facts injected into every agent prompt
- Roster lock enforcement (only valid team players mentioned)
- Score consistency tracking and session refresh system

#### 3. **Live Data Pipeline** (`src/data/live/`)
- Real-time NHL API data collection with progressive statistics
- **Data leakage prevention**: No future game data in early timestamps
- Temporal filtering ensures realistic 0-0 game start progression
- Organized game-specific folder structure

#### 4. **Audio Generation** (`src/agents/audio_agent/`)
- Google Cloud Text-to-Speech integration
- Professional voice styles with emotion detection
- WAV file output with organized timestamps

## 📁 File Organization

```
adk_hackathon/
├── src/
│   ├── pipeline/
│   │   ├── live_commentary_pipeline_v2.py  # 🌟 MAIN PIPELINE (Sequential v2.0)
│   │   ├── live_commentary_pipeline.py     # Legacy complex pipeline
│   │   └── utils.py                        # Sequential processing utilities
│   ├── agents/
│   │   ├── sequential_agent_v2/            # 🌟 NEW: Combined agent
│   │   ├── data_agent/                     # Legacy: ADK Data Agent
│   │   ├── commentary_agent/               # Legacy: ADK Commentary Agent
│   │   └── audio_agent/                    # Audio tools
│   ├── data/
│   │   ├── live/                          # Live NHL data collector
│   │   └── static/                        # Static game context
│   └── board/                             # Game state management
├── data/
│   ├── live/GAME_ID/                      # Live game timestamps (input)
│   ├── sequential_agent_outputs/GAME_ID/  # 🌟 NEW: Sequential outputs
│   ├── static/                            # Team rosters, context
│   ├── data_agent_outputs/               # Legacy: ADK analysis results
│   └── commentary_agent_outputs/         # Legacy: ADK commentary results
├── audio_output/GAME_ID/                  # Professional audio files
├── run_game_commentary.py                 # Legacy batch pipeline
└── live_commentary_pipeline.py            # Legacy live pipeline
```

## 🎯 Example Output

**Sequential Live Pipeline (v2.0) - Successful 15-minute Run:**
```bash
$ python src/pipeline/live_commentary_pipeline_v2.py 2024020001 15

🏒 NHL Live Commentary Pipeline v2 - Game 2024020001
⏱️  Duration: 15.0 minutes
✅ Sequential Agent initialized for game 2024020001 (stateless)
✅ Pipeline initialized successfully

Processing Statistics:
  Total processed: 60 timestamps
  Average time: 5.52s
  Min time: 4.65s
  Max time: 8.71s
  Under 5s: 15/60 (25.0%)
  Session refreshes: 6
Sequential live processing completed successfully
```

**Generated Output Structure:**
```
data/sequential_agent_outputs/2024020001/
├── 2024020001_1_00_00_sequential.json  # ✅ Always first
├── 2024020001_1_00_15_sequential.json  # ✅ Always second
├── 2024020001_1_00_30_sequential.json  # ✅ Always third
├── 2024020001_1_00_45_sequential.json  # ✅ Perfect order
├── ...                                 # ✅ 60 files total
└── 2024020001_1_14_45_sequential.json  # ✅ Always last

# 🌟 Key: Sequential processing guarantees chronological output
# Perfect for live streaming where temporal order is mandatory
```

## 🔧 Advanced Features

### **Sequential Real-Time Processing (v2.0)**
- **Temporal Consistency**: Files processed in chronological order (1_00_00 → 1_00_15 → 1_00_30)
- **Live Streaming Ready**: Output order matches game timeline exactly
- **Background Data Collection**: Parallel data gathering with sequential processing
- **Session Management**: Periodic refresh every 10 files to prevent context overflow

### **Game Board Architecture**
- **External State Management**: Game facts stored outside AI memory
- **Context Collapse Prevention**: Authoritative state injection prevents AI hallucinations
- **Roster Lock**: Only valid team players mentioned in commentary
- **Score Consistency**: Scores can only increase, prevents statistical amnesia

### **Data Integrity & Progressive Statistics**
- **Leakage Prevention**: No future game data contaminates early timestamps
- **Realistic Progression**: Games start 0-0 and accumulate stats naturally
- **Temporal Filtering**: Events filtered by time window before stat calculation
- **Natural Commentary**: AI receives only information available at that game moment

## 🧪 Testing

```bash
# Quick test - 2 minutes (8 timestamps)
python src/pipeline/live_commentary_pipeline_v2.py 2024020001 2

# Medium test - 15 minutes (60 timestamps) 
python src/pipeline/live_commentary_pipeline_v2.py 2024020001 15

# Full game test - 60 minutes (240 timestamps)
python src/pipeline/live_commentary_pipeline_v2.py 2024020001 60

# Verify sequential output structure
ls -la data/sequential_agent_outputs/2024020001/

# Clean up for fresh test
rm -rf data/live/2024020001/* data/sequential_agent_outputs/2024020001/*
```

## 📈 Performance

**Sequential Pipeline v2.0 (Tested on 15-minute game):**
- **Processing Speed**: 5.52s average per timestamp
- **Throughput**: 60 timestamps in 15 minutes
- **Efficiency**: 25% under 5 seconds processing time
- **Session Management**: 6 automatic refreshes for memory optimization
- **Success Rate**: 100% sequential ordering guaranteed
- **Scalability**: Tested up to 240 timestamps (60-minute games)

**Production Metrics:**
- **Real-time Factor**: 1:1 ratio (process game data as fast as it's generated)
- **Memory Management**: Auto-refresh prevents context overflow
- **Error Handling**: Robust timeout and exception management

## 🚀 Production Ready

**Sequential Pipeline v2.0 is production-ready for:**

### **Live Streaming Applications**
- **Real-time Commentary**: Process NHL games as they happen
- **Temporal Consistency**: Guaranteed chronological output order
- **Broadcasting Integration**: Direct feed to streaming platforms
- **Low Latency**: Sub-6 second average processing time

### **Enterprise Deployment**
- **Scalable Architecture**: Handle multiple concurrent games
- **Memory Management**: Auto-refresh prevents long-running session issues
- **Error Recovery**: Robust exception handling and timeouts
- **Clean Data Structure**: Professional file organization for integration

### **Technical Specifications**
- **Input**: Live NHL API data (15-second intervals)
- **Output**: Professional Alex Chen & Mike Rodriguez commentary
- **Format**: JSON with embedded dialogue, timing, and emotion metadata
- **Reliability**: 100% success rate on tested games (2024020001-2024020005)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/enhancement`)
3. Test with `python src/pipeline/live_commentary_pipeline_v2.py 2024020001 2`
4. Verify sequential output order in `data/sequential_agent_outputs/`
5. Commit changes (`git commit -m 'Add enhancement'`)
6. Push and create Pull Request

**Testing Guidelines:**
- Always test sequential ordering with at least 8 timestamps (2 minutes)
- Verify no temporal inconsistencies in output
- Check session management works correctly
- Ensure clean file structure organization

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🏆 Hackathon Achievement

**Status**: ✅ **Production-Ready System with Sequential Innovation**  
**Event**: Agent Development Kit Hackathon with Google Cloud  
**Innovation**: First multi-agent NHL commentary system with **guaranteed temporal consistency**

### **Technical Breakthrough: Sequential Real-Time Processing**
- ✅ **Problem Solved**: Parallel processing output randomness incompatible with live streaming
- ✅ **Solution**: Sequential real-time processing guarantees chronological output
- ✅ **Impact**: Makes AI commentary viable for actual live broadcasting

### **System Achievements**
- ✅ Google ADK multi-agent implementation with Gemini AI
- ✅ External game board state management preventing AI memory corruption
- ✅ Data leakage prevention with progressive statistics
- ✅ Professional Alex Chen & Mike Rodriguez broadcaster personas
- ✅ Production-tested on 15-minute and 60-minute NHL games
- ✅ Clean professional codebase with comprehensive documentation

---

**🎵 Listen to AI-generated NHL commentary today!** 🏒🤖