import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone, date
SYNC_EVERY_DAYS = 30

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

def ensure_sync_log():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS sync_log ( id SERIAL PRIMARY KEY, synced_at TIMESTAMPTZ NOT NULL DEFAULT now(), fetched INTEGER,inserted INTEGER )")
            conn.commit()
    finally:
        conn.close()

def get_last_sync_time():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(synced_at) FROM sync_log")
            last_sync_time = cur.fetchone()[0]
            return last_sync_time
    finally:
        conn.close()

def record_sync(fetched, inserted):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO sync_log (fetched, inserted) VALUES (%s, %s)" ,
                        (fetched , inserted),
            )
            conn.commit()
    finally:
        conn.close()

def sync_if_due():
    ensure_sync_log()
    last = get_last_sync_time()
    if last is not None and datetime.now(timezone.utc) - last < timedelta(days=SYNC_EVERY_DAYS):
        print(f"Match data synced on {last:%Y-%m-%d}, skipping sync")
        return
    fetched, inserted = run_sync()
    record_sync(fetched, inserted)
    print(f"Sync done: {fetched} fetched, {inserted} new")

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
    response = requests.get(url, headers=headers, params=params, timeout=15)
    response.raise_for_status()
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

def run_sync():
    last = get_last_matchdate()
    if last is None:
        print("premier_league is empty, nothing to continue from")
        return 0 , 0

    matches = fetch_all_matches(last.isoformat(), date.today().isoformat())
    print(f"Fetched {len(matches)} matches since {last}")

    rows = [match_to_row(m) for m in matches]
    inserted = upsert_rows(rows)
    print(f"Inserted {inserted} new matches, {len(rows) - inserted} already in the database")
    return (len(matches), inserted)


if __name__ == "__main__":
    sync_if_due()