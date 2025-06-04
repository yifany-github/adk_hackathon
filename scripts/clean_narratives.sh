#!/bin/bash

# Clean NHL Narrative Descriptions
# Removes all generated narrative files to start fresh testing

echo "🧹 Cleaning NHL Narrative Descriptions..."

# Navigate to project root
cd "$(dirname "$0")/.."

# Check if descriptions directory exists
if [ -d "data/live/descriptions" ]; then
    # Count existing files
    file_count=$(find data/live/descriptions -name "*.json" | wc -l)
    
    if [ $file_count -gt 0 ]; then
        echo "📁 Found $file_count narrative files in data/live/descriptions/"
        echo "🗑️  Removing all narrative files..."
        
        # Remove all JSON files in descriptions directory
        rm -f data/live/descriptions/*.json
        
        echo "✅ Cleaned data/live/descriptions/ directory"
    else
        echo "📭 No narrative files found in data/live/descriptions/"
    fi
else
    echo "📁 Creating data/live/descriptions/ directory..."
    mkdir -p data/live/descriptions
    echo "✅ Directory created"
fi

echo "🎯 Ready for fresh narrative generation testing!"
echo ""
echo "Next steps:"
echo "  1. Run: cd src/data/pipeline && python3 nhl_game_pipeline.py GAME_ID 2"
echo "  2. Or: cd src/data/live && python3 nhl_moment_describer.py GAME_ID"
echo "" 