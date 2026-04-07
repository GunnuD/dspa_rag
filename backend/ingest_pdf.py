import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "../data/chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/embedding-001")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def ingest_pdf(pdf_path: str):
    if not os.path.exists(pdf_path):
        print(f"Error: File {pdf_path} not found.")
        return

    print(f"Loading {pdf_path}...")
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    print("Splitting documents...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)

    print(f"Creating embeddings and saving to {CHROMA_DB_PATH}...")
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL, google_api_key=GOOGLE_API_KEY)
    
    # Create or update ChromaDB
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=CHROMA_DB_PATH
    )
    print("Ingestion complete.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ingest_pdf.py <path_to_pdf>")
    else:
        pdf_path = sys.argv[1]
        ingest_pdf(pdf_path)
