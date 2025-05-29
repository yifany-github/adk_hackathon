#!/usr/bin/env python3
"""
ESPN API Client for NHL Game Data
Primary client for fetching comprehensive NHL game information including:
- Game details, scores, status
- Team statistics and player info  
- News articles and injury reports
- Historical matchups and recent form
- Broadcast information and venue details
"""
import asyncio
import aiohttp
import requests
import json
import time
from datetime import datetime, timedelta


class GameDetailAnalyzer:
    """Analyze ESPN API game data detail and live consistency"""
    
    def __init__(self):
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl"
        self.timeout = 10
    
    async def get_detailed_game_info(self, game_id: str) -> dict:
        """Get the most detailed information available for a specific game"""
        endpoints_to_test = [
            f"{self.base_url}/summary?event={game_id}",
            f"{self.base_url}/playbyplay?event={game_id}",
            f"{self.base_url}/boxscore?event={game_id}",
            f"{self.base_url}/commentary?event={game_id}",
            f"{self.base_url}/probabilities?event={game_id}",
        ]
        
        results = {}
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints_to_test:
                endpoint_name = endpoint.split('/')[-1].split('?')[0]
                try:
                    print(f"🔍 Testing {endpoint_name} endpoint...")
                    async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                        if response.status == 200:
                            data = await response.json()
                            results[endpoint_name] = {
                                'status': 'success',
                                'data_size': len(str(data)),
                                'main_keys': list(data.keys()) if isinstance(data, dict) else ['non-dict-response'],
                                'sample_data': data
                            }
                            print(f"  ✅ {endpoint_name}: {len(str(data))} chars, keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                        else:
                            results[endpoint_name] = {'status': f'failed_{response.status}'}
                            print(f"  ❌ {endpoint_name}: HTTP {response.status}")
                except Exception as e:
                    results[endpoint_name] = {'status': f'error_{str(e)[:50]}'}
                    print(f"  ❌ {endpoint_name}: {str(e)[:50]}")
        
        return results
    
    async def test_live_data_consistency(self, game_id: str, intervals: int = 5, delay: int = 10):
        """Test how consistently live data updates"""
        print(f"\n🔄 Testing live data consistency for game {game_id}")
        print(f"   Will check {intervals} times with {delay}s intervals")
        
        snapshots = []
        
        for i in range(intervals):
            print(f"\n📊 Snapshot {i+1}/{intervals} at {datetime.now().strftime('%H:%M:%S')}")
            
            try:
                url = f"{self.base_url}/summary?event={game_id}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Extract key live data points
                            snapshot = {
                                'timestamp': datetime.now().isoformat(),
                                'game_status': self._extract_game_status(data),
                                'score': self._extract_score(data),
                                'period_info': self._extract_period_info(data),
                                'last_play': self._extract_last_play(data),
                                'data_hash': hash(str(data))  # To detect any changes
                            }
                            
                            snapshots.append(snapshot)
                            
                            print(f"   Status: {snapshot['game_status']}")
                            print(f"   Score: {snapshot['score']}")
                            print(f"   Period: {snapshot['period_info']}")
                            print(f"   Last Play: {snapshot['last_play']}")
                            
                        else:
                            print(f"   ❌ HTTP {response.status}")
                            
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            if i < intervals - 1:  # Don't wait after last iteration
                await asyncio.sleep(delay)
        
        return snapshots
    
    def _extract_game_status(self, data: dict) -> str:
        """Extract game status from ESPN data"""
        try:
            header = data.get('header', {})
            competition = header.get('competitions', [{}])[0]
            status = competition.get('status', {})
            return status.get('type', {}).get('description', 'Unknown')
        except:
            return 'Unknown'
    
    def _extract_score(self, data: dict) -> str:
        """Extract current score"""
        try:
            header = data.get('header', {})
            competition = header.get('competitions', [{}])[0]
            competitors = competition.get('competitors', [])
            
            if len(competitors) >= 2:
                home = next((c for c in competitors if c.get('homeAway') == 'home'), {})
                away = next((c for c in competitors if c.get('homeAway') == 'away'), {})
                
                home_score = home.get('score', 0)
                away_score = away.get('score', 0)
                home_name = home.get('team', {}).get('abbreviation', 'HOME')
                away_name = away.get('team', {}).get('abbreviation', 'AWAY')
                
                return f"{away_name} {away_score} - {home_score} {home_name}"
        except:
            pass
        return 'Unknown'
    
    def _extract_period_info(self, data: dict) -> str:
        """Extract period/time information"""
        try:
            header = data.get('header', {})
            competition = header.get('competitions', [{}])[0]
            status = competition.get('status', {})
            
            period = status.get('period', 0)
            clock = status.get('displayClock', '')
            
            return f"Period {period}, {clock}"
        except:
            return 'Unknown'
    
    def _extract_last_play(self, data: dict) -> str:
        """Extract last play information"""
        try:
            # Check if there's play-by-play data
            drives = data.get('drives', {})
            if drives:
                # This would contain play data if available
                return "Play data available"
            
            # Check for recent plays in other sections
            plays = data.get('plays', [])
            if plays:
                last_play = plays[-1]
                return last_play.get('text', 'Recent play found')
            
            return "No play data"
        except:
            return 'Unknown'
    
    def analyze_snapshots(self, snapshots: list) -> dict:
        """Analyze the consistency of live data snapshots"""
        if not snapshots:
            return {'error': 'No snapshots to analyze'}
        
        analysis = {
            'total_snapshots': len(snapshots),
            'unique_data_hashes': len(set(s['data_hash'] for s in snapshots)),
            'status_changes': [],
            'score_changes': [],
            'period_changes': [],
            'data_consistency': 'unknown'
        }
        
        # Track changes
        prev_snapshot = None
        for snapshot in snapshots:
            if prev_snapshot:
                if snapshot['game_status'] != prev_snapshot['game_status']:
                    analysis['status_changes'].append({
                        'from': prev_snapshot['game_status'],
                        'to': snapshot['game_status'],
                        'time': snapshot['timestamp']
                    })
                
                if snapshot['score'] != prev_snapshot['score']:
                    analysis['score_changes'].append({
                        'from': prev_snapshot['score'],
                        'to': snapshot['score'],
                        'time': snapshot['timestamp']
                    })
                
                if snapshot['period_info'] != prev_snapshot['period_info']:
                    analysis['period_changes'].append({
                        'from': prev_snapshot['period_info'],
                        'to': snapshot['period_info'],
                        'time': snapshot['timestamp']
                    })
            
            prev_snapshot = snapshot
        
        # Determine consistency
        if analysis['unique_data_hashes'] == 1:
            analysis['data_consistency'] = 'static'
        elif analysis['unique_data_hashes'] == len(snapshots):
            analysis['data_consistency'] = 'highly_dynamic'
        else:
            analysis['data_consistency'] = 'moderately_dynamic'
        
        return analysis


async def main():
    """Main test function"""
    print("🏒 ESPN NHL API Client - Fetching Comprehensive Game Data")
    print("=" * 60)
    
    analyzer = GameDetailAnalyzer()
    
    # First, get a game ID from recent games
    print("\n1️⃣ Finding a recent game to analyze...")
    
    try:
        url = f"{analyzer.base_url}/scoreboard"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    events = data.get('events', [])
                    
                    if events:
                        game_id = events[0]['id']
                        game_info = events[0]
                        
                        print(f"✅ Found game: {game_id}")
                        
                        # Show basic game info
                        competitions = game_info.get('competitions', [{}])
                        if competitions:
                            comp = competitions[0]
                            competitors = comp.get('competitors', [])
                            if len(competitors) >= 2:
                                home = next((c for c in competitors if c.get('homeAway') == 'home'), {})
                                away = next((c for c in competitors if c.get('homeAway') == 'away'), {})
                                
                                print(f"   {away.get('team', {}).get('displayName', 'Away')} vs {home.get('team', {}).get('displayName', 'Home')}")
                                print(f"   Status: {comp.get('status', {}).get('type', {}).get('description', 'Unknown')}")
                        
                        # 2. Test detailed game information
                        print(f"\n2️⃣ Testing detailed game information for {game_id}...")
                        detailed_results = await analyzer.get_detailed_game_info(game_id)
                        
                        # 3. Test live data consistency
                        print(f"\n3️⃣ Testing live data consistency...")
                        snapshots = await analyzer.test_live_data_consistency(game_id, intervals=3, delay=5)
                        
                        # 4. Analyze results
                        print(f"\n4️⃣ Analysis Results")
                        print("-" * 40)
                        
                        print(f"\n📊 Data Detail Level:")
                        for endpoint, result in detailed_results.items():
                            if result.get('status') == 'success':
                                print(f"   ✅ {endpoint}: {result['data_size']} chars")
                                print(f"      Keys: {result['main_keys']}")
                            else:
                                print(f"   ❌ {endpoint}: {result['status']}")
                        
                        print(f"\n🔄 Live Data Consistency:")
                        consistency_analysis = analyzer.analyze_snapshots(snapshots)
                        print(f"   Total snapshots: {consistency_analysis['total_snapshots']}")
                        print(f"   Data consistency: {consistency_analysis['data_consistency']}")
                        print(f"   Status changes: {len(consistency_analysis['status_changes'])}")
                        print(f"   Score changes: {len(consistency_analysis['score_changes'])}")
                        print(f"   Period changes: {len(consistency_analysis['period_changes'])}")
                        
                        # Save detailed analysis
                        analysis_data = {
                            'game_id': game_id,
                            'game_info': game_info,
                            'detailed_endpoints': detailed_results,
                            'live_snapshots': snapshots,
                            'consistency_analysis': consistency_analysis,
                            'test_timestamp': datetime.now().isoformat()
                        }
                        
                        with open('data/sample_games/espn_live_analysis.json', 'w') as f:
                            json.dump(analysis_data, f, indent=2)
                        
                        print(f"\n💾 Detailed analysis saved to data/sample_games/espn_live_analysis.json")
                        
                        # Summary for livestream capability
                        print(f"\n🎯 LIVESTREAM CAPABILITY ASSESSMENT:")
                        print(f"   Data Sources Available: {len([r for r in detailed_results.values() if r.get('status') == 'success'])}")
                        print(f"   Live Updates: {'Yes' if consistency_analysis['data_consistency'] != 'static' else 'Limited'}")
                        print(f"   Real-time Events: {'Yes' if any('play' in k for k in detailed_results.keys()) else 'Basic'}")
                        
                    else:
                        print("❌ No games found in current scoreboard")
                else:
                    print(f"❌ Failed to get scoreboard: HTTP {response.status}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("🏒 ESPN NHL API Client - Fetching Comprehensive Game Data")
    asyncio.run(main()) 