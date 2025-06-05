#!/usr/bin/env python3
"""
Spatial Converter - Converts coordinates to real hockey spatial language
"""

def coords_to_hockey_language(x_coord: float, y_coord: float, zone_code: str, home_defending_side: str = "right") -> str:
    """
    Convert x,y coordinates to real hockey spatial descriptions
    
    Args:
        x_coord: X coordinate (-100 to +100, 0 = center ice)
        y_coord: Y coordinate (~-43 to +43, 0 = center of rink width)
        zone_code: "N" (neutral), "D" (defensive), "O" (offensive)
        home_defending_side: "right" or "left" (which side home team defends)
    
    Returns:
        Hockey spatial description like "near the blue line", "along the boards"
    """
    
    # Determine side of rink
    if abs(y_coord) > 30:
        side = "along the boards"
    elif abs(y_coord) > 15:
        if y_coord > 0:
            side = "near the right-wing boards"
        else:
            side = "near the left-wing boards"
    else:
        side = ""  # Central area
    
    # Determine depth/position based on zone and x-coordinate
    if zone_code == "N":  # Neutral zone
        if abs(x_coord) < 10:
            position = "at center ice"
        elif abs(x_coord) < 30:
            position = "near the blue line"
        else:
            position = "in the neutral zone"
    
    elif zone_code == "D":  # Defensive zone
        if abs(x_coord) > 80:
            position = "deep in the corner"
        elif abs(x_coord) > 60:
            position = "behind the net"
        elif abs(x_coord) > 40:
            position = "in the defensive zone"
        else:
            position = "near the blue line"
    
    elif zone_code == "O":  # Offensive zone  
        if abs(x_coord) > 80:
            position = "deep in the corner"
        elif abs(x_coord) > 60:
            position = "behind the net"
        elif abs(x_coord) > 40 and abs(y_coord) < 20:
            position = "in the slot"
        elif abs(x_coord) > 40:
            position = "from the point"
        else:
            position = "near the blue line"
    
    else:
        position = f"in the {zone_code.lower()} zone"
    
    # Combine position and side
    if side and position:
        if "at center ice" in position:
            return position  # "at center ice" doesn't need side
        elif "along the boards" in side:
            return f"{position} {side}"
        else:
            return f"{position} {side}"
    elif position:
        return position
    else:
        return f"in the {zone_code.lower()} zone"


def get_game_situation(situation_code: str) -> str:
    """Convert situation code to readable game state"""
    situation_map = {
        "1551": "even strength",
        "1560": "power play", 
        "1451": "even strength",
        "1540": "penalty kill",
        "1550": "even strength",
        # Add more as we discover them
    }
    return situation_map.get(situation_code, "")


def format_time_remaining(time_remaining: str) -> str:
    """Format time remaining for natural language"""
    if not time_remaining or time_remaining == "20:00":
        return ""
    
    # Convert "18:23" to "18:23 remaining"
    try:
        mins, secs = time_remaining.split(":")
        if int(mins) == 0:
            return f"{int(secs)}s remaining"
        else:
            return f"{mins}:{secs} remaining"
    except:
        return ""


# Example usage and testing
if __name__ == "__main__":
    # Test coordinate conversion
    test_cases = [
        (1, -37, "N", "center ice"),           # Center ice penalty
        (-80, -39, "N", "neutral zone boards"), # Neutral zone hit
        (-41, 38, "D", "defensive zone"),       # Defensive zone hit  
        (60, 10, "O", "slot area"),            # Offensive zone shot
        (-85, 35, "D", "corner"),              # Deep corner
    ]
    
    print("🏒 Testing Coordinate Conversion:")
    for x, y, zone, expected_area in test_cases:
        result = coords_to_hockey_language(x, y, zone)
        print(f"({x:3}, {y:3}) {zone} → {result}")
    
    print("\n🎮 Testing Game Situations:")
    situations = ["1551", "1560", "1451", "unknown"]
    for sit in situations:
        result = get_game_situation(sit)
        print(f"{sit} → {result}") 