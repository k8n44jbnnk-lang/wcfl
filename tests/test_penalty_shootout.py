import pytest
import json
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_penalty_shootout_points_calculation(client):
    """Verify points calculation for a knockout match won on penalties."""
    match_data = {
        "team1": "Germany",
        "team2": "Uruguay",
        "score1": 1,
        "score2": 1,
        "stage": "r32",
        "extra": {
            "penalties": True,
            "winner": "Germany"
        }
    }

    # Points Calculation Expectations:
    # Win (R32): 4 pts
    # Goals (1): 1 pt
    # Won on penalties bonus: 2 pts
    # Total Germany: 4 + 1 + 2 = 7 points
    # Total Uruguay: 0 (Loss) + 1 (Goal) = 1 point

    response = client.post('/api/match/add', json=match_data)
    assert response.status_code == 200
    res_json = json.loads(response.data)
    assert res_json['ok'] is True

    match_result = res_json['match']['result']
    assert match_result['team1']['points'] == 7
    assert match_result['team2']['points'] == 1
    
    # Assert breakdown has "Won on penalties"
    assert any(item['event'] == "Won on penalties" and item['pts'] == 2 for item in match_result['team1']['breakdown'])

    # Cleanup
    match_id = res_json['match']['id']
    client.delete(f'/api/match/{match_id}')

def test_penalty_shootout_validation_failures(client):
    """Verify input validation fails for invalid shootout configurations."""
    # 1. Non-draw score
    bad_data_1 = {
        "team1": "Germany",
        "team2": "Uruguay",
        "score1": 2,
        "score2": 1,
        "stage": "r32",
        "extra": {
            "penalties": True,
            "winner": "Germany"
        }
    }
    response = client.post('/api/match/add', json=bad_data_1)
    assert response.status_code == 400
    assert b"must end in a draw" in response.data

    # 2. Group stage
    bad_data_2 = {
        "team1": "Germany",
        "team2": "Uruguay",
        "score1": 1,
        "score2": 1,
        "stage": "group",
        "extra": {
            "penalties": True,
            "winner": "Germany"
        }
    }
    response = client.post('/api/match/add', json=bad_data_2)
    assert response.status_code == 400
    assert b"cannot occur in the group stage" in response.data

    # 3. Invalid winner name
    bad_data_3 = {
        "team1": "Germany",
        "team2": "Uruguay",
        "score1": 1,
        "score2": 1,
        "stage": "r32",
        "extra": {
            "penalties": True,
            "winner": "France"
        }
    }
    response = client.post('/api/match/add', json=bad_data_3)
    assert response.status_code == 400
    assert b"winner must be one of the playing teams" in response.data
