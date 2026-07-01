from app import score_analyser, POINTS_DEFAULTS

def test_red_card_deduction_default():
    # With default red_card = -1
    result = score_analyser("Germany", "Paraguay", 2, 1, "group", extra={"red_card_t1": 1})
    # Germany wins (4), goals scored 2 (2), Paraguay cleansheet (0), red card (1 * -1 = -1) -> 5 pts
    assert result["team1"]["points"] == 5
    # Breakdown entry check
    red_card_entry = next(item for item in result["team1"]["breakdown"] if "Red cards" in item["event"])
    assert red_card_entry["pts"] == -1

def test_red_card_deduction_custom_negative():
    # With custom config red_card = -2
    cfg = POINTS_DEFAULTS.copy()
    cfg["red_card"] = -2
    result = score_analyser("Germany", "Paraguay", 2, 1, "group", extra={"red_card_t1": 2}, pts_config=cfg)
    # Germany wins (4), goals scored 2 (2), red cards 2 (2 * -2 = -4) -> 2 pts
    assert result["team1"]["points"] == 2
    red_card_entry = next(item for item in result["team1"]["breakdown"] if "Red cards" in item["event"])
    assert red_card_entry["pts"] == -4

def test_red_card_deduction_custom_positive_fallback():
    # If the user sets red_card = 2 in the config (mistakenly positive), we force it to -2
    cfg = POINTS_DEFAULTS.copy()
    cfg["red_card"] = 2
    result = score_analyser("Germany", "Paraguay", 2, 1, "group", extra={"red_card_t1": 1}, pts_config=cfg)
    # Germany wins (4), goals scored 2 (2), red card 1 (1 * -2 = -2) -> 4 pts
    assert result["team1"]["points"] == 4
    red_card_entry = next(item for item in result["team1"]["breakdown"] if "Red cards" in item["event"])
    assert red_card_entry["pts"] == -2
