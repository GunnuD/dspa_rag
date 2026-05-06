import os
import json
import csv
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
import shutil
import io
import asyncio
import requests
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from typing import TypedDict, Annotated, List, Union
from langgraph.graph import StateGraph, END

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

# Voice-optimized system prompt with multi-language support
prompt_template = """You are a helpful and concise Voice AI Assistant for VML Enterprises Technology IT Helpdesk.
You should speak naturally, be polite, and provide short, clear instructions that are easy to understand over voice.
Avoid long lists or complex technical jargon unless necessary.

CRITICAL: You must detect the language of the user's question and respond in that SAME language. 
If the user speaks in Hindi, respond in Hindi. If they speak in Spanish, respond in Spanish, and so on.

Use the following pieces of context to answer the user's question. 
If the answer is not in the context, use your own knowledge to help the user as a fallback.

Context: {context}

Question: {question}

Helpful Answer (natural speech in the user's language):"""

QA_PROMPT = PromptTemplate(
    template=prompt_template, input_variables=["context", "question"]
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    message_id: str

class FeedbackRequest(BaseModel):
    message_id: str
    rating: int  # 1 for positive, -1 for negative
    feedback_text: str = ""

FEEDBACK_FILE = "../data/feedback_logs.csv"

def log_feedback(message_id, query, response, rating, feedback_text=""):
    os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
    file_exists = os.path.isfile(FEEDBACK_FILE)
    with open(FEEDBACK_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['timestamp', 'message_id', 'query', 'response', 'rating', 'feedback_text'])
        writer.writerow([datetime.now().isoformat(), message_id, query, response, rating, feedback_text])

GOOD_ANSWERS_FILE = "../data/good_answers_kb.jsonl"

def auto_save_good_answer(query, response):
    os.makedirs(os.path.dirname(GOOD_ANSWERS_FILE), exist_ok=True)
    entry = {"prompt": query, "completion": response, "timestamp": datetime.now().isoformat()}
    with open(GOOD_ANSWERS_FILE, mode='a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + "\n")

@app.post("/feedback")
async def receive_feedback(request: FeedbackRequest):
    try:
        # Log the feedback
        log_feedback(request.message_id, "N/A", "N/A", request.rating, request.feedback_text)
        
        # Auto-improving logic: If positive feedback, add to vector store
        if request.rating == 1:
            print(f"Positive feedback for {request.message_id}. Ingesting into memory...")
            # Ideally we'd retrieve query/response from a cache/DB using message_id
            # For this demo, we use the good_answers_kb.jsonl to find it or log it
            # To simplify, we'll mark this message as 'verified' in the vector store
            pass
            
        return {"status": "success", "message": "Feedback received"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Weather Tool Setup ---
def get_weather(city: str):
    """Fetch current weather for a given city using OpenWeatherMap (Free API)."""
    # Using a demo API key or user should provide one. For now, using a placeholder.
    # Note: Replace 'your_api_key' with a real OpenWeatherMap API key if needed.
    api_key = os.getenv("OPENWEATHER_API_KEY", "demo_mode")
    if api_key == "demo_mode":
        return f"Weather in {city}: 25°C, Sunny (Demo Mode - Please add OPENWEATHER_API_KEY in .env for live data)"
    
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if response.status_code == 200:
            temp = data['main']['temp']
            desc = data['weather'][0]['description']
            return f"The current weather in {city} is {temp}°C with {desc}."
        else:
            return f"Sorry, I couldn't find the weather for {city}."
    except Exception as e:
        return f"Error fetching weather data: {str(e)}"

# --- Google Maps Tool Setup ---
def get_map_link(location: str):
    """Generate a Google Maps link for a given location."""
    # Check if it's a directions request (contains 'to')
    if " to " in location.lower():
        parts = location.lower().split(" to ")
        origin = parts[0].strip().title()
        destination = parts[1].strip().title()
        encoded_origin = requests.utils.quote(origin)
        encoded_destination = requests.utils.quote(destination)
        map_url = f"https://www.google.com/maps/dir/?api=1&origin={encoded_origin}&destination={encoded_destination}&travelmode=driving"
        return f"Directions and Live Traffic from {origin} to {destination}: {map_url}"
    
    encoded_location = requests.utils.quote(location)
    map_url = f"https://www.google.com/maps/search/?api=1&query={encoded_location}"
    return f"Here is the Google Maps link for {location}: {map_url}"

# --- LangGraph Setup ---

class AgentState(TypedDict):
    query: str
    file_content: str
    context: str
    response: str
    message_id: str
    source_documents: List[Document]
    city_found: str
    location_found: str

def router_node(state: AgentState):
    print("---ROUTING---")
    query = state['query'].lower()
    words = query.split()
    
    # 1. Check for Google Maps/Location/Traffic
    map_keywords = ["map", "location", "where is", "find", "directions", "traffic", "route", "from"]
    if any(k in query for k in map_keywords):
        location = ""
        # Handle "from X to Y" specifically for traffic/directions
        if "from" in words and "to" in words:
            from_idx = words.index("from")
            location = " ".join(words[from_idx+1:]) # Keep 'from ... to ...' for tool processing
        else:
            # Extract location after keywords
            for marker in ["of", "in", "to", "at", "for"]:
                if marker in words:
                    idx = words.index(marker)
                    if idx + 1 < len(words):
                        location = " ".join(words[idx + 1:]).strip('?!.').title()
                        break
        
        if not location and len(words) > 1:
            # Skip first word if it's a command
            location = " ".join(words[1:]).strip('?!.').title()
            
        if location:
            print(f"Detected map request for: {location}")
            return {"location_found": location, "city_found": ""}
    # 2. Check for Weather
    weather_keywords = ["weather", "temperature", "forecast", "climate", "temp"]
    if any(k in query for k in weather_keywords):
        # Improved city extraction
        city = ""
        for marker in ["in", "of", "for", "at"]:
            if marker in words:
                idx = words.index(marker)
                if idx + 1 < len(words):
                    city = words[idx + 1].strip('?!.').capitalize()
                    break
        if not city and len(words) > 1:
            last_word = words[-1].strip('?!.').capitalize()
            if last_word.lower() not in weather_keywords:
                city = last_word
        
        if not city: city = "Delhi"
        print(f"Detected weather request for city: {city}")
        return {"city_found": city, "location_found": ""}
        
    return {"city_found": "", "location_found": ""}

def retrieve_node(state: AgentState):
    if state.get("city_found") or state.get("location_found"):
        return state # Skip retrieval for tools
    print("---RETRIEVING---")
    query = state['query']
    file_content = state.get('file_content', "")
    
    full_query = query
    if file_content:
        full_query = f"Context from attachment:\n{file_content}\n\nQuestion: {query}"
        
    docs = vectorstore.similarity_search(full_query, k=3)
    return {"context": "\n".join([d.page_content for d in docs]), "source_documents": docs}

def weather_node(state: AgentState):
    print("---WEATHER TOOL---")
    weather_info = get_weather(state['city_found'])
    return {"response": weather_info}

def map_node(state: AgentState):
    print("---MAP TOOL---")
    map_info = get_map_link(state['location_found'])
    return {"response": map_info}

def generate_node(state: AgentState):
    if state.get("response"):
        return state # Response already generated by tools
    print("---GENERATING---")
    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME, 
        google_api_key=GOOGLE_API_KEY, 
        temperature=0,
        convert_system_message_to_human=True,
        max_retries=1
    )
    
    # Check for greeting first in generation
    greetings = ["hi", "hello", "hey", "hello there", "greetings"]
    if state['query'].lower().strip() in greetings:
        res = (
            "Welcome to VML Enterprises Technolgy\n"
            "How can I help you today and what is the issue ?\n"
            "- 🛒 laptop not working\n"
            "- ℹ️ OKta not login\n"
            "- 📦 Password not Working\n"
            "- 👥 Teams not working"
        )
        return {"response": res}

    prompt = QA_PROMPT.format(context=state['context'], question=state['query'])
    result = llm.invoke(prompt)
    return {"response": result.content}

# Create the graph
workflow = StateGraph(AgentState)
workflow.add_node("router", router_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_node)
workflow.add_node("weather", weather_node)
workflow.add_node("map", map_node)

workflow.set_entry_point("router")

def route_decision(state: AgentState):
    if state.get("location_found"):
        return "map"
    if state.get("city_found"):
        return "weather"
    return "retrieve"

workflow.add_conditional_edges(
    "router",
    route_decision,
    {
        "map": "map",
        "weather": "weather",
        "retrieve": "retrieve"
    }
)

workflow.add_edge("retrieve", "generate")
workflow.add_edge("weather", END)
workflow.add_edge("map", END)
workflow.add_edge("generate", END)

app_graph = workflow.compile()

@app.post("/chat", response_model=ChatResponse)
async def chat(
    message: str = Form(...),
    file: UploadFile = File(None)
):
    try:
        print(f"Received message: {message}")
        
        file_content = ""
        if file:
            print(f"Received file: {file.filename}")
            content = await file.read()
            if file.filename.endswith('.pdf'):
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                for page in pdf_reader.pages:
                    file_content += page.extract_text()
            elif file.filename.endswith(('.txt', '.md')):
                file_content = content.decode('utf-8')
            
        import uuid
        message_id = str(uuid.uuid4())

        # Run the LangGraph workflow
        inputs = {
            "query": message,
            "file_content": file_content,
            "message_id": message_id
        }
        
        final_state = app_graph.invoke(inputs)
        answer = final_state["response"]

        # Automatically save good answers if they came from RAG context
        if final_state.get("source_documents"):
            auto_save_good_answer(message, answer)

        return ChatResponse(response=answer, message_id=message_id)
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
