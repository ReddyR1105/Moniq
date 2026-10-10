def test_goal_contributions_plans_and_assistant_do_not_change_cash(empty_client):
    client = empty_client
    before = client.get('/api/dashboard').json()['balance']
    assert client.put('/api/goals/1', json={'name':'Laptop fund','target':300,'saved':0}).status_code == 200
    result = client.put('/api/goals/1/plan', json={'monthly_contribution':100})
    assert result.status_code == 200
    assert result.json()[0]['projected_completion'] == '2027-01-07'
    body = {'amount':'50.00','date':'2026-10-09','request_key':'contribution-0001'}
    assert client.post('/api/goals/1/contributions',json=body).status_code == 201
    assert client.post('/api/goals/1/contributions',json=body).json()[0]['saved'] == 50
    assert client.post('/api/goals/1/contributions',json={**body,'amount':51}).status_code == 409
    assert client.post('/api/goals/1/contributions',json={**body,'request_key':'future-contribution','date':'2026-10-10'}).status_code == 422
    assert client.get('/api/dashboard').json()['balance'] == before
    reply=client.post('/api/assistant',json={'question':'Am I on track with my savings goal?'}).json()
    assert reply['evidence']['goals'][0]['saved'] == 50
    assert '2026-12-23' in reply['answer']
    assert len(client.get('/api/export').json()['goal_contributions']) == 1


def test_goal_without_plan_or_paycheck_does_not_invent_values(empty_client):
    client=empty_client
    assert client.post('/api/assistant',json={'question':'When was my last confirmed paycheck?'}).json()['evidence']['last_paycheck'] is None
    client.put('/api/goals/1',json={'name':'Emergency fund','target':100,'saved':0})
    assert client.get('/api/goals').json()[0]['projected_completion'] is None
    assert client.put('/api/goals/1/plan',json={'monthly_contribution':'0.001'}).status_code == 422
    assert client.put('/api/goals/999/plan',json={'monthly_contribution':100}).status_code == 404
