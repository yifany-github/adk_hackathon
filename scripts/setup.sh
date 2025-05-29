#!/bin/bash

echo "🏒 Setting up Hockey Livestream Agent Project..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Create virtual environment with uv
echo "Creating virtual environment with uv..."
uv venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies with uv (much faster!)
echo "Installing dependencies with uv..."
uv pip install -r requirements.txt

# Install playwright browsers
echo "Installing Playwright browsers..."
uv run playwright install

# Create necessary __init__.py files
echo "Creating __init__.py files..."
find src -type d -exec touch {}/__init__.py \;

# Copy environment template
echo "Setting up environment variables..."
cp env.example .env
echo "Please edit .env file with your API keys and configuration"

# Create basic main.py
cat > src/main.py << 'EOF'
"""
Main entry point for Hockey Livestream Agent
"""
import asyncio
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__)))

from agents.data_agent import DataAgent

async def main():
    print("🏒 Starting Hockey Livestream Agent...")
    
    # Initialize data agent
    data_agent = DataAgent()
    
    if await data_agent.initialize():
        print("✅ Data agent initialized")
        
        # Test basic functionality
        state = await data_agent.get_current_game_state()
        print(f"Current game: {state}")
        
        events = await data_agent.get_new_events()
        print(f"Found {len(events)} events")
        
    await data_agent.cleanup()
    print("🏒 Hockey Livestream Agent stopped")

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Create a quick run script
cat > scripts/run_dev.sh << 'EOF'
#!/bin/bash
echo "🏒 Running Hockey Livestream Agent in development mode..."
source .venv/bin/activate
cd src && python main.py
EOF

chmod +x scripts/run_dev.sh

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/
env/

# Environment variables
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project specific
data/cache/
data/audio_output/
*.log
*.wav
*.mp3

# Google Cloud
service-account.json
*.json
EOF

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source .venv/bin/activate"
echo "2. Edit .env file with your API keys"
echo "3. Test the setup: ./scripts/run_dev.sh"
echo "4. Or run directly: cd src && python main.py"
echo ""
echo "🚀 Quick commands:"
echo "  - Run project: ./scripts/run_dev.sh"
echo "  - Activate env: source .venv/bin/activate"
echo "  - Install new package: uv pip install <package>"
echo ""
echo "🏒 Good luck with your hackathon project!" 