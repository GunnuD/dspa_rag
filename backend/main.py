import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA

load_dotenv()

app = FastAPI(title="RAG Chat API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from the frontend directory
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("../frontend/index.html")

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "../data/chroma_db")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/embedding-001")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize LLM and VectorStore
embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL, google_api_key=GOOGLE_API_KEY)
vectorstore = Chroma(persist_directory=CHROMA_DB_PATH, embedding_function=embeddings)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        print(f"Received message: {request.message}")
        
        # Check for greeting
        greetings = ["hi", "hello", "hey", "hello there", "greetings"]
        if request.message.lower().strip() in greetings:
            welcome_msg = (
                "Welcome to VML Enterprises Technolgy\n"
                "How can I help you today and what is the issue ?\n"
                "- 🛒 laptop not working\n"
                "- ℹ️ OKta not login\n"
                "- 📦 Password not Working\n"
                "- 👥 Teams not working"
            )
            return ChatResponse(response=welcome_msg)

        llm = ChatGoogleGenerativeAI(
            model=MODEL_NAME, 
            google_api_key=GOOGLE_API_KEY, 
            temperature=0,
            convert_system_message_to_human=True,
            max_retries=1
        )
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(),
            return_source_documents=True
        )
        
        result = qa_chain.invoke(request.message)
        answer = result["result"]
        
        # Check if the answer indicates no context found
        no_context_phrases = ["i don't know", "no context", "not found", "does not mention", "don't have information"]
        if any(phrase in answer.lower() for phrase in no_context_phrases) or not result.get("source_documents"):
            print("Answer not found in context, falling back to Gemini LLM...")
            # Direct LLM call without RAG context
            fallback_response = llm.invoke(request.message)
            return ChatResponse(response=fallback_response.content)

        print(f"Result: {result}")
        return ChatResponse(response=answer)
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        if "429" in error_msg or "ResourceExhausted" in error_msg:
            return ChatResponse(response="Gemini API rate limit reached (429). The Free Tier allows 15 requests per minute and 1 million tokens per minute. Please wait 60 seconds and try again.")
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
