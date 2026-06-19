import json
import os

# Mock or Import from app
# Since we are running on the server, we can import from app.py
from app import score_analyser, DATA_FILE, save_data, load_data

def fix_argentina_match():
    data = load_data()
    
    match_found = False
    for m in data['matches']:
        if m['team1'] == "Argentina" and m['team2'] == "Algeria":
            print("Found Argentina match. Updating with hat-trick...")
            if not m.get('extra'): m['extra'] = {}
            m['extra']['hattrick_t1'] = True
            
            # Recalculate result
            old_pts = m['result']['team1']['points']
            new_result = score_analyser(m['team1'], m['team2'], m['score1'], m['score2'], m['stage'], m['extra'], data.get('points_config'))
            new_pts = new_result['team1']['points']
            
            m['result'] = new_result
            
            # Update owner points
            owner = m['owner1']
            if owner:
                data['points'][owner] = data['points'].get(owner, 0) - old_pts + new_pts
                print(f"Updated {owner}'s ({m['team1']} owner) total points by {new_pts - old_pts} (Hat-trick addition).")
            
            match_found = True
            break
    
    if match_found:
        save_data(data)
        print("Successfully updated league data on server.")
    else:
        print("Match not found.")

if __name__ == "__main__":
    fix_argentina_match()
