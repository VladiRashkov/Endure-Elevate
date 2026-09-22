import requests

def get_access_token(client_id, client_secret, code):
    url = "https://www.strava.com/oauth/token"
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code'
    }
    response = requests.post(url, data=data)
    if response.status_code != 200:
        raise RuntimeError(f"Strava token exchange failed: {response.status_code}, {response.text}")
    return response.json()

def get_strava_authorization_url(client_id, redirect_uri):
    auth_url = (
        f"https://www.strava.com/oauth/authorize?"
        f"client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&"
        f"approval_prompt=force&scope=activity:read_all"
    )
    return auth_url


def access_activity_data(access_token, params):
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers, params=params)
    print("Strava status:", response.status_code, response.text[:200])  # temporary
    if response.status_code == 200:
        return response.json()
    return None