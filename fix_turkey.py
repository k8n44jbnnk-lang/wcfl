import json
import os

def fix_turkey():
    # Base dir of app
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(base_dir, "data", "league.json")
    
    if not os.path.exists(data_file):
        print("Database file not found.")
        return
        
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    updated = False
    
    # Fix ownership list for Deepanshu
    ownership = data.get("ownership", {})
    for player, teams in ownership.items():
        if "Turkey" in teams:
            idx = teams.index("Turkey")
            teams[idx] = "Türkiye"
            print(f"Updated ownership list for {player}: replaced Turkey with Türkiye")
            updated = True
            
    # Fix team_sold mapping just in case
    team_sold = data.get("team_sold", {})
    if "Turkey" in team_sold:
        player = team_sold.pop("Turkey")
        team_sold["Türkiye"] = player
        print(f"Updated team_sold: mapped Türkiye to {player}")
        updated = True
        
    if updated:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Successfully updated database on the server.")
    else:
        print("No changes needed in database.")

if __name__ == "__main__":
    fix_turkey()
