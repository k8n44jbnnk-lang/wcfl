import json
import os

# Auction results from user input
# Format: Player - Team - Price
auction_results = [
    # Piyush
    ("Piyush", "Brazil", 850),
    ("Piyush", "Netherlands", 850),
    ("Piyush", "Canada", 150),
    ("Piyush", "Sweden", 150),
    
    # Deepanshu
    ("Deepanshu", "Turkey", 300),
    ("Deepanshu", "Japan", 450),
    ("Deepanshu", "Argentina", 1000),
    ("Deepanshu", "Ivory Coast", 250),
    
    # Dima
    ("Dima", "USA", 300),
    ("Dima", "Iran", 100),
    ("Dima", "France", 1200),
    ("Dima", "Austria", 400),
    
    # Bhavya
    ("Bhavya", "Ecuador", 200),
    ("Bhavya", "Uruguay", 400),
    ("Bhavya", "Portugal", 950),
    ("Bhavya", "Croatia", 450),
    
    # Lalit
    ("Lalit", "Morocco", 750),
    ("Lalit", "Norway", 250),
    ("Lalit", "England", 750),
    ("Lalit", "Egypt", 250),
    
    # Gabu
    ("Gabu", "Belgium", 600),
    ("Gabu", "Spain", 1050),
    ("Gabu", "Colombia", 300),
    ("Gabu", "Algeria", 50),
    
    # Jai
    ("Jai", "Mexico", 300),
    ("Jai", "Switzerland", 250),
    ("Jai", "Germany", 750),
    ("Jai", "South Korea", 450),
]

PLAYERS = ["Piyush", "Deepanshu", "Dima", "Bhavya", "Lalit", "Gabu", "Jai"]

# Calculate budgets spent for each player
budgets_spent = {}
for player, team, price in auction_results:
    if player not in budgets_spent:
        budgets_spent[player] = 0
    budgets_spent[player] += price

# Budget remaining = 1000 - spent
BUDGET_TOTAL = 2000
budgets = {p: BUDGET_TOTAL - budgets_spent.get(p, 0) for p in PLAYERS}

# Build ownership data
ownership = {}
for player, team, price in auction_results:
    if player not in ownership:
        ownership[player] = []
    ownership[player].append(team)

# Build team_sold data
team_sold = {}
for player, team, price in auction_results:
    team_sold[team] = player

# Build league data structure
data = {
    "league_name": "WC2026 Fantasy League",
    "budget": BUDGET_TOTAL,
    "players": [{"name": p} for p in PLAYERS],
    "teams_per_player": 4,
    "tiers": {
        "1": ["France", "Spain", "England", "Germany", "Portugal", "Netherlands", "Argentina", "Brazil"],
        "2": ["Belgium", "Croatia", "Uruguay", "Colombia", "USA", "Japan", "Morocco", "Senegal"],
        "3": ["Switzerland", "Austria", "South Korea", "Mexico", "Canada", "Ecuador", "Ivory Coast", "Egypt"],
        "4": ["Norway", "Scotland", "Sweden", "Türkiye", "Czechia", "Bosnia and Herzegovina", "Paraguay", "Australia"],
        "5": ["Saudi Arabia", "Iran", "Ghana", "Tunisia", "Algeria", "South Africa", "Panama", "Qatar"],
        "6": ["Jordan", "Uzbekistan", "Cape Verde", "New Zealand", "Curaçao", "Haiti", "DR Congo", "Iraq"],
    },
    "tier_prices": {"1": 200, "2": 150, "3": 100, "4": 70, "5": 40, "6": 20},
    "started": True,
    "auction_done": True,
    "budgets": budgets,
    "points": {p: 0 for p in PLAYERS},
    "ownership": ownership,
    "team_sold": team_sold,
    "auction_queue": [],
    "auction_idx": 0,
    "current_bidder": 0,
    "current_bid": 0,
    "current_high_bidder": None,
    "auction_active_bidders": [],
    "auction_active_team": None,
    "matches": [],
}

# Save to league.json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "league.json")

os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

with open(DATA_FILE, "w") as f:
    json.dump(data, f, indent=2)

print(f"League initialized with {len(PLAYERS)} players:")
for p in PLAYERS:
    teams = ownership.get(p, [])
    spent = budgets_spent.get(p, 0)
    remaining = budgets.get(p, 0)
    print(f"  {p}: {len(teams)} teams, spent {spent}, remaining {remaining}")
print(f"\nLeague data saved to: {DATA_FILE}")
print(f"Total teams auctioned: {len(team_sold)}")
