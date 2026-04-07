import os
import sys
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "../data/chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def ingest_file(file_path: str, clear: bool = False):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    print(f"Loading {file_path}...")
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        loader = PyPDFLoader(file_path)
    elif ext == '.md':
        loader = UnstructuredMarkdownLoader(file_path)
    elif ext == '.txt':
        loader = TextLoader(file_path)
    else:
        print(f"Unsupported file extension: {ext}")
        return

    documents = loader.load()

    print("Splitting documents...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)

    print(f"Creating embeddings and saving to {CHROMA_DB_PATH}...")
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL, google_api_key=GOOGLE_API_KEY)
    
    if clear and os.path.exists(CHROMA_DB_PATH):
        import shutil
        print(f"Clearing existing database at {CHROMA_DB_PATH}...")
        # Note: In a production app, you might want to use vectorstore.delete_collection() 
        # but for this script, removing the directory is a clean reset.
        shutil.rmtree(CHROMA_DB_PATH)

    # Create or update ChromaDB
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=CHROMA_DB_PATH
    )
    print("Ingestion complete.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <path_to_file> [--clear]")
    else:
        file_path = sys.argv[1]
        clear = "--clear" in sys.argv
        ingest_file(file_path, clear)
