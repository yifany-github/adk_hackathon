# NHL Commentary Agent - Quick Start

## 🎯 Overview
Production-ready NHL LiveStream Commentary Agent that generates professional hockey commentary using Google ADK and Gemini AI.

## 🚀 Quick Start

### 1. Installation
```bash
# Clone and install
git clone https://github.com/YongBoYu1/adk_hackathon.git
cd adk_hackathon
pip install -r requirements.txt
```

### 2. Configure Google Credentials
```bash
# Set up environment variables
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
export GOOGLE_API_KEY=your-google-api-key
```

### 3. Run NHL Commentary
```bash
# Generate professional NHL commentary
python run_game_commentary.py 2024030412 3

# Output: Professional audio files in audio_output/2024030412/
```

## 📁 Core Files

- **run_game_commentary.py** - Main working pipeline (recommended)
- **live_commentary_pipeline.py** - Full live pipeline with data collection
- **src/agents/** - ADK agents (data, commentary, audio)
- **src/data/** - NHL data processing components

## 🎙️ Audio Features

- **Enthusiastic** - Regular play, goals, saves
- **Dramatic** - Penalties, crucial moments, overtime
- **Professional Quality** - WAV format, 24kHz, organized output

## 🎵 Output Structure

```
audio_output/
└── GAME_ID/
    ├── TIMESTAMP_00_enthusiastic_TIME.wav
    ├── TIMESTAMP_01_dramatic_TIME.wav
    └── ...
```

## 🔧 System Architecture

```
Data Agent (ADK) → Commentary Agent (ADK) → Audio Generation
     ↓                      ↓                      ↓
   Analysis            Two-Person Dialogue      WAV Files
```

## 🏒 Example NHL Commentary

**Input**: Live NHL game data  
**Output**: Professional two-person broadcast dialogue
```
Alex Chen: "Welcome to Rogers Place! The Florida Panthers are visiting..."
Mike Rodriguez: "That's right Alex, this is a crucial matchup..."
```

## ✅ Verification

Successful run shows:
- ✅ ADK agents initialized
- ✅ NHL data processed
- ✅ Commentary generated
- 🎵 Professional audio files created
- 📁 Organized in game-specific folders

**Your NHL Commentary Agent is ready for professional broadcasting!** 🏆