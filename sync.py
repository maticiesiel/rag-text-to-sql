import os
import json
import requests
from dotenv import load_dotenv
from datetime import date
import psycopg2
from psycopg2.extras import execute_values

from db import get_connection

load_dotenv()









NAME_MAP = {
    "Brighton Hove": "Brighton",
    "Nottingham": "Nott'm Forest",
    "Wolverhampton": "Wolves",
    "Leeds United" : "Leeds" ,
}

def clean_team(name):
    return NAME_MAP.get(name, name)

def match_to_row(match):
    start_year = int(match["season"]["startDate"][:4])
    season = f"{start_year}/{str(start_year+1)[2:]}"
    matchdate = match["utcDate"][:10]
    hometeam = clean_team(match["homeTeam"]["shortName"])
    awayteam = clean_team(match["awayTeam"]["shortName"])
    ft_home = match["score"]["fullTime"]["home"]
    ft_away = match["score"]["fullTime"]["away"]
    if ft_home > ft_away:
        ft_result = "H"
    elif ft_away > ft_home:
        ft_result = "A"
    else:
        ft_result = "D"
    ht_home = None
    ht_away = None
    ht_result = None
    no_stats = (None,) * 12
    return (season, matchdate, hometeam, awayteam, ft_home, ft_away, ft_result,
            ht_home, ht_away, ht_result) + no_stats

'''
rows = [match_to_row(m) for m in matches]
conn = get_connection()
try:
    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO premier_league VALUES %s ON CONFLICT DO NOTHING",
            rows,
        )
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM premier_league")
        print("Rows in test table:", cur.fetchone()[0])
finally:
    conn.close()
'''

def get_last_matchdate():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(MatchDate) FROM premier_league")
            date = cur.fetchone()[0]
            return date
    finally:
        conn.close()

def fetch_all_matches(date_from , date_today):
    url = "https://api.football-data.org/v4/competitions/PL/matches"
    headers = {"X-Auth-Token": os.getenv("FOOTBALL_DATA_API_KEY")}
    params = {"status": "FINISHED", "dateFrom": date_from, "dateTo": date_today}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(response.json())
        return []
    return response.json()["matches"]

def upsert_rows(rows):
    if not rows:
        return 0
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            inserted = execute_values(
                cur,
                "INSERT INTO premier_league VALUES %s ON CONFLICT DO NOTHING RETURNING 1",
                rows,
                fetch=True,
            )
        conn.commit()
        return len(inserted)
    finally:
        conn.close()

def main():
    last = get_last_matchdate()
    if last is None:
        print("There are no new matches to insert")
        return 0

    matches = fetch_all_matches(last.isoformat(), date.today().isoformat())
    print(f"Fetched {len(matches)} matches since {last}")

    rows = [match_to_row(m) for m in matches]
    inserted = upsert_rows(rows)
    print(f"Inserted {inserted} new matches, {len(rows) - inserted} already in the database")


if __name__ == "__main__":
    main()