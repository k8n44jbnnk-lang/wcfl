import json, sys
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('data/league.json', encoding='utf-8'))

TEAM_NAMES = {
    "France","Spain","England","Germany","Portugal","Netherlands","Belgium","Croatia",
    "Switzerland","Norway","Scotland","Austria","Bosnia and Herzegovina","Sweden","Türkiye","Czechia",
    "Argentina","Brazil","Colombia","Ecuador","Paraguay","Uruguay",
    "USA","Canada","Mexico","Panama","Curaçao","Haiti",
    "Japan","Iran","Jordan","South Korea","Uzbekistan","Australia","Qatar","Saudi Arabia",
    "Algeria","Cape Verde","Egypt","Ghana","Ivory Coast","Morocco","Senegal","South Africa","Tunisia",
    "New Zealand","DR Congo","Iraq",
}

all_owned = [t for teams in data['ownership'].values() for t in teams]
missing = [t for t in all_owned if t not in TEAM_NAMES]

print("=== League Sanity Check ===")
print(f"Players: {[p['name'] for p in data['players']]}")
print(f"Auction done: {data['auction_done']}")
print(f"Budget: {data['budget']}")
print()
print("Teams in ownership NOT in TEAM_NAMES:", missing if missing else "None — all good")
print()
for player, teams in data['ownership'].items():
    spent = data['budget'] - data['budgets'].get(player, 0)
    print(f"  {player}: {teams} (budget remaining: {data['budgets'].get(player, 0)})")
