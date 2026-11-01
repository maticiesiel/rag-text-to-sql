#text_to_sql
#
from database_setup import get_schema
from llm_connection import connect_to_llm
import sqlite3
import sys
import io
import os
import psycopg2
from dotenv import load_dotenv
from contextlib import redirect_stderr, redirect_stdout
from langsmith import traceable
load_dotenv()

def load_schema():
    raw_schema = []
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="myproject",
        user="mateuszciesielczyk",
    )
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'premier_league'
            ORDER BY ordinal_position
                                    """)
        raw_schema = cur.fetchall()
        cur.close()
    except Exception as e:
        print(f"Error occured: {e}")
    finally:
        conn.close()

    return raw_schema

def clean_schema(schema):
    final_schema = "Column exact name and type info : "
    for name, data_type in schema:
        final_schema += f"{name} -> {data_type} , "
    return final_schema


@traceable(name="gemini_sql_generation")
def get_sql_from_ai(user_question,similar_question):    #must return an sql only code that must have only code
    client = connect_to_llm()
    system_rules = f"""You are an sql analyst expert. Here is the exact schema of my database named premier_league you're required to know perfectly: {clean_schema(load_schema())} , 
    Rules: 
    - Points are calculated as 3 for a Win ('H' or 'A'), 1 for a Draw ('D'), and 0 for a Loss. 
    - Seasons are formatted as YYYY/YY (e.g., 2012/13).
    - The database is PostgreSQL. Use ILIKE for case-insensitive text matching,
        EXTRACT(YEAR FROM matchdate) for dates, and cast to numeric before ROUND, e.g. ROUND(AVG(col)::numeric, 2).
    Here are some examples of correct SQL queries for similar questions: 
    {similar_question}
    
    
    Based on the schema and examples above, write an Postgresql query to answer the user's question. 
    Return ONLY the raw SQL code, nothing more. """

    devnull = io.StringIO()
    with redirect_stderr(devnull), redirect_stdout(devnull):
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=user_question,
            config={"system_instruction": system_rules}
        )
    return response.text

def clean_ai_response(ai_response):    # a function for cleaning if the ai put a markdown or behave unpredictable
    ai_response = ai_response.replace("```sql","")
    ai_response = ai_response.replace("```","")
    ai_response = ai_response.strip()
    return ai_response

def get_data_from_sql(sql_query):            # return raw sql data that was produced from the AI sql code prompt
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="myproject",
        user="mateuszciesielczyk",
    )
    conn.set_session(readonly=True)
    try:
        cur = conn.cursor()
        cur.execute(sql_query)
        return cur.fetchall()

    except Exception as e:
        raise e
    finally:
        conn.close()

def generate_final_answer(user_question , sql_data):
    client = connect_to_llm()
    prompt = f"The user asked this question : {user_question} , the database returned this exact answer : {sql_data} . Write a short natural summary: answering their question using only this data"
    devnull = io.StringIO()
    with redirect_stderr(devnull), redirect_stdout(devnull):
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt
        )
    return response.text

def repair_sql_with_ai(user_question, failed_sql, error_message):
    client = connect_to_llm()
    schema = clean_schema(load_schema())

    repair_prompt = f"""You are an expert SQL debugger. 
        The user asked: "{user_question}"

        You previously wrote this Postgresql query:
        {failed_sql}

        But it failed and returned this exact database error:
        {error_message}

        Here is the database schema again: {schema}

        Fix the SQL query so it runs successfully. 
        Return ONLY the raw, corrected SQL code, nothing more. Do not include markdown formatting."""

    devnull = io.StringIO()
    with redirect_stderr(devnull), redirect_stdout(devnull):
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=repair_prompt
        )
    return response.text
