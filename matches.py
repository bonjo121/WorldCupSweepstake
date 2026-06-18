import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def clean_team_name(team):
    name_map = {
        "Czech Republic": "Czechia",
        "Bosnia-Herzegovina": "Bosnia and Herzegovina",
        "United States": "USA",
        "Curaçao": "Curacao",
        "Democratic Republic of the Congo": "DR Congo",
    }

    return name_map.get(team, team)


def get_finished_matches():
    url = "https://worldcup26.ir/get/games"

    session = requests.Session()

    retries = Retry(
        total=5,
        backoff_factor=1,
        allowed_methods=["GET"]
    )

    session.mount("https://", HTTPAdapter(max_retries=retries))

    response = session.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20
    )

    data = response.json()
    events = data["games"]

    matches = []

    for event in events:
        if str(event["finished"]).upper() == "TRUE":
            matches.append({
                "home": clean_team_name(event["home_team_name_en"]),
                "away": clean_team_name(event["away_team_name_en"]),
                "home_score": int(event["home_score"]),
                "away_score": int(event["away_score"]),
                "round": int(event["matchday"]),
                "group": event["group"],
                "type": event["type"]
            })

    return pd.DataFrame(matches)
