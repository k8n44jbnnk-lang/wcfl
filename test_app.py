import pytest
import json
import os
from app import app, DATA_FILE, default_data, save_data

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client

def test_index_page(client):
    """Test that the index page loads."""
    response = client.get('/')
    assert response.status_code == 200
    # In new UI, title is "WC2026 Fantasy" in the brand
    assert b"WC2026 Fantasy" in response.data

def test_fixtures_page(client):
    """Test that the tournament hub loads."""
    response = client.get('/fixtures')
    assert response.status_code == 200
    assert b"Tournament Hub" in response.data

def test_standings_page(client):
    """Test that the standings page loads."""
    response = client.get('/standings')
    assert response.status_code == 200
    assert b"Standings" in response.data

def test_groups_page(client):
    """Test that the groups page loads."""
    response = client.get('/groups')
    assert response.status_code == 200
    assert b"World Cup Groups" in response.data

def test_team_leaderboard_page(client):
    """Test that the team leaderboard loads."""
    response = client.get('/team-leaderboard')
    assert response.status_code == 200
    assert b"Team Leaderboard" in response.data

def test_api_data(client):
    """Test the API data endpoint."""
    response = client.get('/api/data')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'players' in data
    assert 'ownership' in data

def test_admin_login_page(client):
    """Test that the admin login page loads."""
    response = client.get('/admin/login')
    assert response.status_code == 200
    assert b"Admin Access" in response.data

def test_add_match_with_extras(client):
    """Test adding a match with red cards and hat-tricks and verify points."""
    match_data = {
        "team1": "Germany",
        "team2": "Ecuador",
        "score1": 3,
        "score2": 0,
        "stage": "group",
        "extra": {
            "red_card_t1": 1,
            "hattrick_t1": True
        }
    }
    
    # German owner should get:
    # Win: +4
    # 3 Goals: +3
    # Clean Sheet: +2
    # Hat-trick: +3
    # Red Card: -1
    # Total: 4 + 3 + 2 + 3 - 1 = 11
    
    response = client.post('/api/match/add', json=match_data)
    assert response.status_code == 200
    res_json = json.loads(response.data)
    assert res_json['ok'] is True
    
    match_id = res_json['match']['id']
    match_result = res_json['match']['result']
    
    assert match_result['team1']['points'] == 11
    assert any(item['event'] == "Red cards (1)" and item['pts'] == -1 for item in match_result['team1']['breakdown'])
    assert any(item['event'] == "Hat-trick" and item['pts'] == 3 for item in match_result['team1']['breakdown'])
    
    # Cleanup
    client.delete(f'/api/match/{match_id}')

def test_api_match_fetch(client):
    """Test fetching match results from the external API."""
    fetch_data = {
        "team1": "France",
        "team2": "Brazil"
    }
    response = client.post('/api/match/fetch', json=fetch_data)
    assert response.status_code == 200
    res_json = json.loads(response.data)
    assert 'no_result' in res_json or 'team1' in res_json or 'error' in res_json
