import psycopg2
import sqlite3
from psycopg2.extras import execute_values

sqlite_conn = sqlite3.connect("premier_league.db")
rows = sqlite_conn.execute("SELECT * FROM premier_league").fetchall()
sqlite_conn.close()
print(f"Read {len(rows)} rows from SQLite")

pg_conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="myproject",
    user="mateuszciesielczyk",
)
cur = pg_conn.cursor()
cur.execute("DROP TABLE IF EXISTS premier_league")
cur.execute("""
    CREATE TABLE premier_league (
        season TEXT,
        matchdate DATE,
        hometeam TEXT,
        awayteam TEXT,
        fulltimehomegoals INTEGER,
        fulltimeawaygoals INTEGER,
        fulltimeresult TEXT,
        halftimehomegoals INTEGER,
        halftimeawaygoals INTEGER,
        halftimeresult TEXT,
        homeshots INTEGER,
        awayshots INTEGER,
        hometshotsontarget INTEGER,
        awayshotsontarget INTEGER,
        homecorners INTEGER,
        awaycorners INTEGER,
        homefouls INTEGER,
        awayfouls INTEGER,
        homeyellowcards INTEGER,
        awayyellowcards INTEGER,
        homeredcards INTEGER,
        awayredcards INTEGER
    )
""")

execute_values(cur, "INSERT INTO premier_league VALUES %s", rows)

pg_conn.commit()
cur.execute("SELECT COUNT(*) FROM premier_league")
print("Rows in Postgres:", cur.fetchone()[0])

cur.close()
pg_conn.close()