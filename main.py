#final working procedure
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from text_to_sql import get_sql_from_ai, clean_ai_response, get_data_from_sql, generate_final_answer

persistent_directory = "db/chroma_db"
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

db = Chroma(
    persist_directory=persistent_directory ,
    embedding_function=embedding_model ,
    collection_metadata={"hnsw:space": "cosine"} ,
    collection_name="sql_examples"
)

retriever = db.as_retriever(search_kwargs={"k" : 3})
query = "Which team conceded the fewest goals overall in the 2003/04 season?"



if __name__ == "__main__":
    print("Welcome to the AI premier league analyst, ask a question relating premier league seasons 2000/01 to 2024/25. \n")
    print("To leave type quit")
    while True:

        print("Your question :")
        question = input()
        if(question.lower() == "quit"):
            break
        else:
            retrieved_docs = retriever.invoke(question)
            similar_question = "\n\n".join([doc.page_content for doc in retrieved_docs])
            raw_sql = get_sql_from_ai(question, similar_question)
            clean_sql_code =clean_ai_response(raw_sql)

            data = get_data_from_sql(clean_sql_code)
            if data:
                final_answer = generate_final_answer(question, data)
                print("[AI] : ", final_answer)
            else:
                print("[AI] : A problem occured, invalid or insufficient data")
