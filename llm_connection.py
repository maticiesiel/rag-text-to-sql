from google import genai
import os
from dotenv import load_dotenv
load_dotenv()

def connect_to_llm():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return client

'''chat = client.chats.create(model="gemini-3.1-flash-lite")


while True:
    message = input("> ")
    if message == "exit":
        break

    res = chat.send_message(message)
    print(res.text)'''