import json
from app import score_analyser, DATA_FILE, save_data

def fix_mexico_match():
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
    
    # Target the specific match
    match_found = False
    for m in data['matches']:
        if m['team1'] == "Mexico" and m['team2'] == "South Africa":
            print("Found Mexico match. Updating with red card...")
            m['extra'] = {"red_card_t1": 1}
            
            # Recalculate result
            old_pts = m['result']['team1']['points']
            new_result = score_analyser(m['team1'], m['team2'], m['score1'], m['score2'], m['stage'], m['extra'], data.get('points_config'))
            new_pts = new_result['team1']['points']
            
            m['result'] = new_result
            
            # Update owner points
            owner = m['owner1']
            if owner:
                data['points'][owner] = data['points'].get(owner, 0) - old_pts + new_pts
                print(f"Updated {owner}'s total points by {new_pts - old_pts} (Red Card deduction).")
            
            match_found = True
            break
    
    if match_found:
        save_data(data)
        print("Successfully updated league data.")
    else:
        print("Match not found.")

if __name__ == "__main__":
    fix_mexico_match()
