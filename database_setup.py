import sqlite3
import pandas as pd


def prepare_league_data():
    premier_league_dataset = pd.read_csv('epl_final.csv')
    premier_league_dataset['MatchDate'] = pd.to_datetime(premier_league_dataset['MatchDate']).dt.date

    return premier_league_dataset

def load_to_sql(conn, premier_league_dataset):
    premier_league_dataset.to_sql('premier_league', conn , if_exists = 'replace' , index = False)

def get_schema(cur):
    cur.execute("PRAGMA table_info(premier_league)")
    return cur.fetchall()

def testing(cur, premier_league_dataset):
    pass


if __name__ == "__main__":
    conn = sqlite3.connect('premier_league.db')
    try:
        premier_league_dataset = prepare_league_data()
        load_to_sql(conn, premier_league_dataset)
        cur = conn.cursor()
        testing(cur, premier_league_dataset)
    except Exception as e:
        print(f"Error occured: {e}")
    finally:
        conn.close()
