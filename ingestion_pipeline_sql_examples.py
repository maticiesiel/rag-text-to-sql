from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


def open_txt(file_path):
    document = open(file_path)
    return document


def split(docs):
    splitter = CharacterTextSplitter(
        chunk_size=250,
        is_separator_regex=False ,
        separator="===" ,
        chunk_overlap=0
    )

    chunks = splitter.split_text(docs)
    return chunks


def create_vector_store(chunks, persistent_directory="db/chromadb"):
    print("Creating vectors and storing in chromadb")
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    vector_store = Chroma.from_texts(
        texts=chunks,
        embedding=embedding_model,
        persist_directory=persistent_directory,
        collection_metadata={"hnsw:space": "cosine"} ,
        collection_name="sql_examples"
    )
    print(f"Vector store created and saved into {persistent_directory}")
    return vector_store

def ingestion_pipeline(file_path):
    document = open_txt(file_path)
    chunks = split(document.read())
    vector_store = create_vector_store(chunks , persistent_directory="db/chroma_db")

if __name__ == "__main__":
    ingestion_pipeline("sql_examples.txt")