# Data Directory Structure

This directory contains the organized file structure for NHL Live Commentary Agent outputs.

## 📁 Directory Structure

```
data/
├── live/                          # Live NHL game data (input)
│   └── GAME_ID/                   # Game-specific live data
│       ├── GAME_ID_1_00_00.json   # Timestamp files (auto-generated)
│       ├── GAME_ID_1_00_15.json
│       └── ...
├── static/                        # Static game context
│   ├── game_GAME_ID_static_context.json      # Full team rosters
│   └── game_GAME_ID_minimal_context.json     # Light context (90% smaller)
├── sequential_agent_outputs/      # 🌟 MAIN OUTPUT (Sequential Pipeline v2.0)
│   └── GAME_ID/                   # Game-specific sequential outputs
│       ├── GAME_ID_1_00_00_sequential.json   # Sequential commentary
│       ├── GAME_ID_1_00_15_sequential.json   # Always in chronological order
│       └── ...
├── data_agent_outputs/            # Legacy: Data agent ADK outputs
│   └── GAME_ID/
│       ├── GAME_ID_1_00_00_adk.json
│       └── ...
└── commentary_agent_outputs/      # Legacy: Commentary agent outputs
    └── GAME_ID/
        ├── GAME_ID_1_00_00_commentary_session_aware.json
        └── ...
```

## 🎯 Key Features

### **Sequential Outputs (Recommended)**
- **Location**: `sequential_agent_outputs/GAME_ID/`
- **Content**: Combined data analysis + professional commentary
- **Order**: Guaranteed chronological sequence (1_00_00 → 1_00_15 → 1_00_30...)
- **Format**: Alex Chen & Mike Rodriguez dialogue with timing metadata

### **File Naming Convention**
- `GAME_ID_PERIOD_MM_SS.json`
- Example: `2024020001_1_00_15.json` = Game 2024020001, Period 1, 0:15

### **Pipeline Workflow**
1. **Live Data Collection**: `data/live/GAME_ID/` (NHL API → JSON)
2. **Sequential Processing**: `data/sequential_agent_outputs/GAME_ID/` (ADK Agent → Commentary)
3. **Audio Generation**: `audio_output/GAME_ID/` (TTS → WAV files)

## 🚀 Usage

```bash
# Run sequential pipeline (recommended)
python src/pipeline/live_commentary_pipeline_v2.py GAME_ID DURATION_MINUTES

# Output will be saved to:
# data/sequential_agent_outputs/GAME_ID/GAME_ID_*_sequential.json
```

## 📝 Important Notes

- **JSON files are ignored by git** (see .gitignore)
- **Directory structure is preserved** with .gitkeep files
- **Users get clean folder structure** without file conflicts
- **Example GAME_ID directories** show expected organization