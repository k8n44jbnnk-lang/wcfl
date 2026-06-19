import pytest
import json
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_canada_hattrick_points(client):
    """Verify points calculation for Canada with a hattrick."""
    match_data = {
        "team1": "Canada",
        "team2": "Switzerland",
        "score1": 4,
        "score2": 0,
        "stage": "group",
        "extra": {
            "hattrick_t1": True
        }
    }

    # Assuming points_defaults:
    # Win: 4, Goal: 1, Clean sheet: 2, Hat-trick: 3
    # Canada: 4 (Win) + 4 (Goals) + 2 (Clean sheet) + 3 (Hat-trick) = 13 points
    
    response = client.post('/api/match/add', json=match_data)
    assert response.status_code == 200
    res_json = json.loads(response.data)
    assert res_json['ok'] is True
    
    match_result = res_json['match']['result']
    
    # Assert breakdown has hattrick
    assert any(item['event'] == "Hat-trick" and item['pts'] == 3 for item in match_result['team1']['breakdown'])
    assert match_result['team1']['points'] == 13

    # Cleanup
    match_id = res_json['match']['id']
    client.delete(f'/api/match/{match_id}')
