#!/usr/bin/env python3
"""
NHL API Explorer
Discovers what metadata is available from various NHL API endpoints
"""
import requests
import json
from pprint import pprint

def explore_endpoint(url, description):
    """Explore an NHL API endpoint and show what data it provides"""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"🌐 {url}")
    print('='*60)
    
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        # Show top-level structure
        print(f"📊 Top-level keys: {list(data.keys())}")
        
        # Show sample data for interesting keys
        for key in list(data.keys())[:5]:
            print(f"\n🔸 {key}:")
            if isinstance(data[key], list) and len(data[key]) > 0:
                print(f"   Type: List with {len(data[key])} items")
                print(f"   Sample item keys: {list(data[key][0].keys()) if isinstance(data[key][0], dict) else 'Not a dict'}")
            elif isinstance(data[key], dict):
                print(f"   Type: Dict with keys: {list(data[key].keys())[:8]}")
            else:
                print(f"   Type: {type(data[key]).__name__}, Value: {str(data[key])[:100]}")
        
        return data
        
    except Exception as e:
        print(f"❌ Failed to fetch: {e}")
        return None

def main():
    """Explore key NHL API endpoints for metadata"""
    
    # Core endpoints to explore
    endpoints = [
        # Player data
        ("https://api-web.nhle.com/v1/player/8479318/landing", "Player Profile (Auston Matthews)"),
        ("https://api-web.nhle.com/v1/player/8479318/game-log/now", "Player Game Log"),
        
        # Team data  
        ("https://api-web.nhle.com/v1/club-stats/TOR/now", "Team Stats (TOR)"),
        ("https://api-web.nhle.com/v1/club-schedule-season/TOR/now", "Team Schedule"),
        
        # League data
        ("https://api-web.nhle.com/v1/schedule/now", "Current Schedule"),
        ("https://api-web.nhle.com/v1/standings/now", "Current Standings"),
        
        # Stats endpoints
        ("https://api.nhle.com/stats/rest/en/skater/summary", "Skater Stats Summary"),
        ("https://api.nhle.com/stats/rest/en/goalie/summary", "Goalie Stats Summary"),
        
        # Game data
        ("https://api-web.nhle.com/v1/gamecenter/2024020001/boxscore", "Game Boxscore Sample"),
    ]
    
    print("🏒 NHL API METADATA EXPLORATION")
    print("Discovering what data is available for commentary...")
    
    results = {}
    
    for url, description in endpoints:
        data = explore_endpoint(url, description)
        if data:
            results[description] = {
                'url': url,
                'keys': list(data.keys()),
                'data_sample': data
            }
    
    # Summary
    print(f"\n{'='*60}")
    print("📋 METADATA AVAILABILITY SUMMARY")
    print('='*60)
    
    for desc, info in results.items():
        print(f"✅ {desc}")
        print(f"   Keys: {', '.join(info['keys'][:5])}{'...' if len(info['keys']) > 5 else ''}")
    
    print(f"\n🎯 Total endpoints explored: {len(results)}")
    print("📊 This gives us a complete picture of available metadata!")

if __name__ == "__main__":
    main() 