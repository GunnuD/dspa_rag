# RAG Application Setup

## Prerequisites
- Python 3.10+
- Google Gemini API Key (Free Tier)

## Backend Setup
1. Navigate to `backend/` directory.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Update `.env` file with your `GOOGLE_API_KEY`.
4. To ingest a PDF:
   ```bash
   python ingest_pdf.py path/to/your/document.pdf
   ```
5. Start the backend:
   ```bash
   python main.py
   ```

## Frontend Setup
1. Since Node.js was not detected on the system, a lightweight React implementation is provided in `frontend/index.html`.
2. Open `frontend/index.html` directly in any web browser.
3. Ensure the backend is running at `http://localhost:8000` to allow the frontend to communicate with it.

## Project Structure
- `backend/`: FastAPI, LangChain, and ChromaDB logic.
- `frontend/`: Simple React-based UI.
- `data/`: Stores PDFs and the Chroma vector database.
