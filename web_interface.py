import os
import signal
import streamlit as st
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import warnings
from dotenv import load_dotenv
load_dotenv()
warnings.filterwarnings("ignore", category=UserWarning)

from text_to_sql import get_sql_from_ai, clean_ai_response, get_data_from_sql, generate_final_answer , repair_sql_with_ai

#setting up
st.set_page_config(page_title="Premier League AI Analyst", page_icon="⚽")
st.title("⚽ Premier League AI Analyst")
st.write("Ask a question relating to Premier League seasons 2000/01 to 2024/25.")
with st.sidebar:
    st.header("Admin Controls")
    if st.button("🛑 Shut Down App"):
        st.error("Shutting down server... You can now close this browser tab.")
        os.kill(os.getpid(), signal.SIGTERM)
#vector db store to not reload every time a user types a letter
def load_retriever():
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma(
        persist_directory="db/chroma_db",
        embedding_function=embedding_model,
        collection_metadata={"hnsw:space": "cosine"} ,
        collection_name="sql_examples"
    )
    return db.as_retriever(search_kwargs={"k": 3})

retriever = load_retriever()

#chat history

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

#user input
user_question = st.chat_input("E.g., Who had the most clean sheets in 2008/09?")

if user_question:
    # Show the user's message immediately
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    #  Generate the AI response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing database..."):  #shows a loading spinner
            try:
                #retrieve examples
                retrieved_docs = retriever.invoke(user_question)
                similar_question = "\n\n".join([doc.page_content for doc in retrieved_docs])

                #run the pipeline
                raw_sql = get_sql_from_ai(user_question, similar_question)
                clean_sql_code = clean_ai_response(raw_sql)
                data = get_data_from_sql(clean_sql_code)
                # prepare the retry - loop
                max_attempts = 3
                data = None
                current_sql = ""
                error_msg = ""
                for attempt in range(max_attempts):
                    try:
                        if attempt == 0:
                            # standard generation
                            raw_sql = get_sql_from_ai(user_question, similar_question)
                        else:
                            # send the broken SQL and error to the repair agent
                            st.toast(f"SQL Error detected. AI attempting self-repair (Attempt {attempt + 1}/3)...",
                                     icon="🛠️")
                            raw_sql = repair_sql_with_ai(user_question, current_sql, error_msg)

                        current_sql = clean_ai_response(raw_sql)

                        # Try to execute against SQLite
                        data = get_data_from_sql(current_sql)

                        # If it reaches this line, it succeeded! Break the loop immediately.
                        break
                    except Exception as e:
                        error_msg = str(e)
                #generate answer
                if not data == None:
                    final_answer = generate_final_answer(user_question, data)
                else:
                    final_answer = f"The database encountered an error it couldn't resolve after {max_attempts} attempts. Last error: {error_msg}"

                #display and save the AI's answer
                st.markdown(final_answer)
                st.session_state.messages.append({"role": "assistant", "content": final_answer})

            except Exception as e:
                st.error(f"An error occurred: {e}")


