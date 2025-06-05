#!/bin/bash
# Organize NHL Data Structure - Clean up and organize data files

echo "🧹 Organizing NHL data structure..."
echo "=================================================="

# Function to organize live data files by game ID
organize_live_data() {
    echo "📁 Organizing live data files..."
    
    # Check if live data directory exists
    if [ ! -d "data/live" ]; then
        echo "❌ data/live directory not found"
        return
    fi
    
    # Count JSON files to organize
    json_count=$(ls data/live/game_*_live_*.json 2>/dev/null | wc -l)
    
    if [ "$json_count" -eq 0 ]; then
        echo "✅ No live data files to organize"
        return
    fi
    
    echo "📊 Found $json_count JSON files to organize"
    
    # Create game-specific directories and move files
    for file in data/live/game_*_live_*.json; do
        if [ -f "$file" ]; then
            # Extract game ID from filename (e.g., game_2024020001_live_1_00_00.json)
            basename=$(basename "$file")
            game_id=$(echo "$basename" | cut -d'_' -f2)
            
            # Create game directory if it doesn't exist
            game_dir="data/live/$game_id"
            mkdir -p "$game_dir"
            
            # Move file to game directory
            mv "$file" "$game_dir/"
        fi
    done
    
    echo "✅ Live data files organized by game ID"
}

# Function to clean up temporary files
clean_temp_files() {
    echo "🗑️ Cleaning up temporary files..."
    
    # Remove analysis files
    [ -f "narratives_analysis.txt" ] && rm "narratives_analysis.txt" && echo "   🗑️ Removed narratives_analysis.txt"
    [ -f "extract_narratives.py" ] && rm "extract_narratives.py" && echo "   🗑️ Removed extract_narratives.py"
    
    echo "✅ Temporary files cleaned"
}

# Function to show current data structure
show_structure() {
    echo ""
    echo "📊 Current data structure:"
    echo "   📁 data/"
    echo "   ├── 📁 live/"
    
    # Show game directories if they exist
    if [ -d "data/live" ]; then
        for game_dir in data/live/*/; do
            if [ -d "$game_dir" ]; then
                game_id=$(basename "$game_dir")
                file_count=$(ls "$game_dir"/*.json 2>/dev/null | wc -l)
                echo "   │   ├── 📁 $game_id/     ($file_count files)"
            fi
        done
    fi
    
    echo "   ├── 📁 static/           (Static game context)"
    echo "   └── 📁 processed/        (Final processed data)"
}

# Main execution
main() {
    organize_live_data
    clean_temp_files
    show_structure
    
    echo ""
    echo "✅ Data organization complete!"
}

# Run main function
main 