# NHL Live Commentary Web Client

Modern web application for the NHL Live Commentary System v3, featuring complete real-time processing with audio generation.

## 🎯 Features

### Core Functionality
- **🎬 Live Commentary Control**: Start/stop live commentary using pipeline v3
- **🎮 Real-time GameBoard**: Live game state and score tracking
- **🎵 Audio Playback**: Stream generated AI commentary audio
- **📊 Performance Monitoring**: Real-time pipeline performance metrics
- **🔧 API Configuration**: Secure API key management for GEMINI and Google APIs
- **📱 Responsive Design**: Optimized for desktop and mobile devices

### Pipeline Integration
- **🤖 Pipeline v3**: Uses `live_commentary_pipeline_v3.py` for complete Data → Commentary → Audio processing
- **⚡ Real-time Processing**: Sequential file processing with live updates
- **🎵 Audio Generation**: Automatic TTS generation with organized file management
- **📈 Progress Tracking**: Live statistics and processing metrics

## 🚀 Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional, can be configured via web UI)
export GEMINI_API_KEY=your_gemini_api_key
export GOOGLE_API_KEY=your_google_api_key

# Run the web client
python app.py
```

### Access the Application
Open your browser to: http://localhost:5000

## ☁️ Google Cloud Deployment

### Method 1: Google App Engine (Recommended)

1. **Create `app.yaml`**:
```yaml
runtime: python39
service: nhl-commentary

basic_scaling:
  max_instances: 10
  idle_timeout: 10m

resources:
  cpu: 2
  memory_gb: 4
  disk_size_gb: 20

env_variables:
  FLASK_ENV: production
  
handlers:
- url: /static
  static_dir: static
- url: /.*
  script: auto
```

2. **Deploy**:
```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Initialize project
gcloud init
gcloud config set project YOUR_PROJECT_ID

# Deploy application
gcloud app deploy app.yaml

# View deployed app
gcloud app browse
```

### Method 2: Google Cloud Run

1. **Create `Dockerfile`**:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV FLASK_ENV=production

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "300", "--worker-class", "eventlet", "app:app"]
```

2. **Deploy to Cloud Run**:
```bash
# Build and push container
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/nhl-commentary

# Deploy to Cloud Run
gcloud run deploy nhl-commentary \
  --image gcr.io/YOUR_PROJECT_ID/nhl-commentary \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 3600 \
  --max-instances 10

# Get service URL
gcloud run services describe nhl-commentary --platform managed --region us-central1 --format 'value(status.url)'
```

### Method 3: Google Compute Engine

1. **Create VM instance**:
```bash
gcloud compute instances create nhl-commentary-vm \
  --image-family ubuntu-2004-lts \
  --image-project ubuntu-os-cloud \
  --machine-type e2-standard-4 \
  --zone us-central1-a \
  --tags http-server,https-server
```

2. **Setup and deploy**:
```bash
# SSH into instance
gcloud compute ssh nhl-commentary-vm --zone us-central1-a

# Install Python and dependencies
sudo apt update
sudo apt install -y python3 python3-pip git nginx

# Clone and setup application
git clone YOUR_REPOSITORY
cd adk_hackathon/web_client_demo
pip3 install -r requirements.txt

# Configure nginx and systemd service
# (Add your nginx and systemd configuration)

# Start services
sudo systemctl start nginx
sudo systemctl start nhl-commentary
```

## 🔧 Configuration

### API Keys Setup

The application requires two API keys that can be configured via the web interface:

1. **Gemini API Key**:
   - Required for AI commentary generation
   - Get from: [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Used by: Commentary Agent

2. **Google API Key**:
   - Required for Text-to-Speech audio generation
   - Get from: [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Used by: Audio Agent

### Environment Variables

```bash
# Optional: Set via environment (can also be configured via web UI)
export GEMINI_API_KEY=your_gemini_api_key_here
export GOOGLE_API_KEY=your_google_api_key_here

# Optional: Custom configuration
export SECRET_KEY=your_secret_key_here
export PORT=5000
export FLASK_ENV=production
```

## 📖 User Guide

### 1. API Configuration
- Click the **Settings** button in the top navigation
- Enter your Gemini API Key and Google API Key
- Keys are stored securely in your session
- Status indicators show configuration status

### 2. Game Selection
- **Available Games**: Select from automatically loaded game data
- **Manual Input**: Enter a 10-digit NHL Game ID (format: YYYYMMDDGG)
- Game cards show team names, file counts, and last modified times

### 3. Start Commentary
- Select duration (1-15 minutes)
- Click **Start Commentary** to begin processing
- Monitor real-time progress via statistics and logs

### 4. Monitor Progress
- **Scoreboard**: Live team scores and game status
- **Statistics**: File processing count, audio generation, runtime
- **Logs**: Real-time pipeline execution logs with color coding
- **Audio Player**: Stream generated commentary audio files

### 5. Audio Playback
- Audio files appear automatically as they're generated
- Built-in HTML5 audio player with controls
- Shows transcript when available
- Files sorted by creation time (newest first)

## 🎮 Interface Overview

### Top Navigation
- **Connection Status**: Real-time server connection indicator
- **Settings Button**: Access API key configuration

### Left Column: Controls
- **API Status**: Visual indicators for configured API keys
- **Game Selection**: Choose from available games or manual input
- **Control Panel**: Duration selection and start/stop controls

### Middle Column: Live Display
- **Scoreboard**: Dynamic game score and team display
- **Statistics**: Real-time processing metrics
- **Audio Player**: Generated commentary playback

### Right Column: Monitoring
- **Pipeline Logs**: Color-coded real-time execution logs
- **Log Controls**: Clear logs functionality

## 🔧 Technical Details

### Architecture
- **Backend**: Flask with WebSocket support via Flask-SocketIO
- **Frontend**: Bootstrap 5 + vanilla JavaScript
- **Real-time**: WebSocket communication for live updates
- **Pipeline**: Subprocess integration with `live_commentary_pipeline_v3.py`

### API Endpoints
```
GET  /                           # Main dashboard
GET  /api/config/keys           # API key status
POST /api/config/keys           # Configure API keys
GET  /api/games/available       # Available games list
POST /api/commentary/start      # Start commentary
POST /api/commentary/stop       # Stop commentary
GET  /api/commentary/status     # Commentary status
GET  /api/audio/<game_id>       # Audio files list
GET  /api/audio/<game_id>/<file> # Serve audio file
GET  /api/logs                  # Pipeline logs
```

### WebSocket Events
```
connect              # Client connection
disconnect           # Client disconnection
commentary_started   # Commentary session started
commentary_stopped   # Commentary session stopped
pipeline_log         # Real-time pipeline log
pipeline_completed   # Pipeline execution completed
pipeline_error       # Pipeline execution error
progress_update      # Statistics update
```

## 🛡️ Security

### API Key Management
- Keys stored only in server session memory
- Never persisted to disk or database
- Separate from environment variables
- Configurable via secure web interface

### Production Considerations
- Use HTTPS in production deployments
- Configure proper firewall rules
- Set secure session keys
- Monitor resource usage and costs

## 📊 Performance

### Resource Requirements
- **Memory**: 2-4 GB recommended for audio processing
- **CPU**: 2+ cores for concurrent pipeline execution
- **Storage**: Temporary space for audio files
- **Network**: Sufficient bandwidth for audio streaming

### Optimization
- Audio files are streamed, not downloaded
- Real-time updates use efficient WebSocket communication
- Processing statistics updated every 2 seconds
- Log entries limited to prevent memory issues

## 🐛 Troubleshooting

### Common Issues

1. **API Keys Not Working**:
   - Verify keys are correct and have proper permissions
   - Check API quotas and billing in Google Cloud Console
   - Ensure services are enabled (AI Platform, Text-to-Speech)

2. **Pipeline Errors**:
   - Check logs for specific error messages
   - Verify game ID format (10 digits)
   - Ensure all project dependencies are installed

3. **Audio Not Playing**:
   - Check browser audio permissions
   - Verify audio files are being generated (check logs)
   - Try different browsers (Chrome recommended)

4. **Connection Issues**:
   - Check WebSocket support in browser
   - Verify network connectivity
   - Check firewall settings for WebSocket traffic

### Log Analysis
- **Error** (Red): Critical issues requiring attention
- **Warning** (Yellow): Non-critical issues or notifications
- **Success** (Green): Successful operations
- **Info** (Blue): General information messages
- **Debug** (White): Detailed execution information

## 📈 Monitoring

### Health Checks
- Connection status indicator in navigation
- Real-time WebSocket connectivity
- Pipeline process monitoring
- Error tracking and reporting

### Metrics
- Files processed per session
- Audio files generated
- Session runtime tracking
- Processing speed statistics

## 🚀 Production Deployment Tips

1. **Resource Sizing**:
   - Start with 2 CPU / 4GB RAM
   - Monitor and scale based on usage
   - Consider burst capacity for peak times

2. **Monitoring**:
   - Setup Google Cloud Monitoring
   - Configure alerts for errors and resource usage
   - Monitor API quotas and costs

3. **Security**:
   - Use IAM roles for service authentication
   - Enable Cloud Security Center
   - Regular security updates

4. **Backup**:
   - Audio files are temporary (not backed up)
   - Configuration and logs can be monitored via Cloud Logging
   - Consider data retention policies

## 📝 License

This web client is part of the NHL Live Commentary System project. See the main project LICENSE file for details. 