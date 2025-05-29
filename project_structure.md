# Hockey Livestream Agent - Project Structure

## Root Directory Structure
```
hockey-livestream-agent/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py         # Configuration management
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py       # Base agent class
│   │   ├── data_agent.py       # Fetches and processes game data
│   │   ├── commentary_agent.py # Generates natural language commentary
│   │   ├── tts_agent.py        # Text-to-speech conversion
│   │   └── orchestrator.py     # Coordinates all agents
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── scrapers/
│   │   │   ├── __init__.py
│   │   │   ├── nhl_api.py      # NHL API client
│   │   │   ├── espn_scraper.py # ESPN scraper
│   │   │   └── playwright_scraper.py # Backup scraper
│   │   ├── processors/
│   │   │   ├── __init__.py
│   │   │   ├── game_parser.py  # Parse game events
│   │   │   └── stats_calculator.py # Calculate statistics
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── game_event.py   # Data models
│   │       └── player_stats.py
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── gemini_client.py    # Google Gemini integration
│   │   ├── prompts/
│   │   │   ├── __init__.py
│   │   │   ├── commentary_prompts.py
│   │   │   └── analysis_prompts.py
│   │   └── response_parser.py
│   │
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── tts_engine.py       # Text-to-speech engine
│   │   ├── audio_mixer.py      # Mix audio streams
│   │   └── stream_manager.py   # Manage live audio stream
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py           # Logging configuration
│   │   ├── cache.py            # Caching utilities
│   │   └── helpers.py          # Common utilities
│   │
│   └── web/
│       ├── __init__.py
│       ├── app.py              # Flask/FastAPI web interface
│       ├── static/
│       │   ├── css/
│       │   ├── js/
│       │   └── audio/
│       └── templates/
│           ├── index.html
│           └── stream.html
│
├── tests/
│   ├── __init__.py
│   ├── test_agents/
│   ├── test_data/
│   └── test_integration/
│
├── scripts/
│   ├── setup.sh               # Environment setup
│   ├── run_dev.sh            # Development runner
│   └── deploy.sh             # Deployment script
│
├── data/
│   ├── sample_games/         # Sample game data for testing
│   ├── cache/               # Cached data
│   └── audio_output/        # Generated audio files
│
├── docs/
│   ├── architecture.md      # System architecture
│   ├── api_docs.md         # API documentation
│   └── deployment.md       # Deployment guide
│
└── deployment/
    ├── Dockerfile
    ├── kubernetes/
    └── terraform/           # Google Cloud infrastructure
```

## Development Phases

### Phase 1: MVP (Days 1-10)
- Basic data fetching (NHL API)
- Simple commentary generation
- Basic TTS output
- Web interface for demo

### Phase 2: Enhancement (Days 11-15)
- Add Google Cloud integration
- Improve commentary quality
- Add real-time streaming
- Error handling and resilience

### Phase 3: Polish (Days 16-20)
- Performance optimization
- UI/UX improvements
- Documentation and demo video
- Final testing and deployment

## Key Technologies
- **ADK**: Agent orchestration framework
- **Google Cloud**: Gemini AI, Cloud Run, BigQuery
- **Data Sources**: NHL API, ESPN
- **TTS**: Google Cloud Text-to-Speech
- **Web Framework**: FastAPI or Flask
- **Deployment**: Docker + Google Cloud Run 