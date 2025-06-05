#!/bin/bash

# NHL Live Streaming Data Cleanup Script
# Cleans up accumulated test data and prepares fresh directories

echo "🧹 NHL Live Streaming Data Cleanup"
echo "=================================="

# Navigate to project root
cd "$(dirname "$0")/.."

echo ""
echo "🏒 Cleaning Live Data..."

# Remove entire live directory and recreate fresh
if [ -d "data/live" ]; then
    file_count=$(find data/live -type f -name "*.json" | wc -l)
    game_dirs=$(find data/live -type d -name "202*" | wc -l)
    
    if [ $file_count -gt 0 ]; then
        echo "🗂️  Found $file_count flow files in $game_dirs game directories"
        echo "   Removing all live data..."
        rm -rf data/live/*
        echo "   ✅ Live directory emptied"
    else
        echo "   ✅ Live directory already empty"
    fi
else
    echo "   📁 Creating live data directory"
    mkdir -p "data/live"
fi

echo ""
echo "📊 Managing Static Data..."
if [ -d "data/static" ]; then
    static_count=$(find data/static -name "*.json" | wc -l)
    echo "🗂️  Found $static_count static context files"
    echo "   ✅ Keeping static data (contains player rosters)"
else
    echo "   📁 Creating static data directory"
    mkdir -p "data/static"
fi

echo ""
echo "🗃️  Creating Fresh Directory Structure..."
mkdir -p data/live
mkdir -p data/static
mkdir -p data/processed

# Create .gitkeep to preserve empty directories
touch data/live/.gitkeep
touch data/processed/.gitkeep

echo ""
echo "📋 Data Directory Summary:"
echo "   📁 data/live/               - Flow commentary files (organized by game_id)"
echo "   📁 data/static/             - Static game context and player rosters"  
echo "   📁 data/processed/          - Final processed data"

echo ""
echo "✅ Data cleanup complete!"
echo "🎯 Ready for flow-descriptive live data collection"
echo ""
echo "Usage:"
echo "   python3 src/data/live/live_data_collector.py GAME_ID [DURATION_MINUTES]"
echo "   Example: python3 src/data/live/live_data_collector.py 2024020001 3" 