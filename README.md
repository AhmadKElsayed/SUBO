```markdown
#  🤖  SUBO

A sophisticated, multi-agent customer service assistant for "Egypt Airway." This project implements a production-grade **LangGraph** routing architecture to handle dynamic database operations (flights, bookings, tickets), Retrieval-Augmented Generation (airline policies), and general conversational memory.

## 🌟 Features
* **Multi-Agent Routing:** A Supervisor node intelligently classifies user intent and routes queries to specialized sub-agents.
* **Strict SQL/DB Execution:** Uses custom API tools (via `@tool`) bound to a dedicated Database Agent to safely execute CRUD operations on a PostgreSQL database (book flights, cancel tickets, check seats).
* **Policy RAG:** A dedicated RAG Agent uses FAISS and HuggingFace embeddings to search the airline's *Conditions of Carriage* PDF, providing accurate policy citations with zero hallucination.
* **Conversational Memory:** Maintains user context (like names and customer IDs) across the session.
* **Modern MLOps Tooling:** Managed entirely via `uv` for blazing-fast dependency resolution and Docker for database containerization. 

## 🏗️ Architecture

```mermaid
graph TD
    START((START)) --> Supervisor

    Supervisor -->|Manage DB, Flights, Bookings| Database_Agent
    Supervisor -->|Check Airline Policies| RAG_Agent
    Supervisor -->|Greetings, Memory, Fallback| General_Agent

    Database_Agent -->|Call API Tools| db_tools[(db_tools)]
    db_tools -->|Return Data| Database_Agent
    Database_Agent -->|Final Answer| END((END))

    RAG_Agent -->|Call Vector Search| rag_tools[(rag_tools)]
    rag_tools -->|Return PDF Chunks| RAG_Agent
    RAG_Agent -->|Final Answer| END((END))

    General_Agent -->|Final Answer| END((END))

    %% Styling
    classDef agent fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:#000;
    classDef tool fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#000;
    classDef router fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#000;
    classDef terminal fill:#eeeeee,stroke:#616161,stroke-width:2px,color:#000;
    
    class Supervisor router;
    class Database_Agent,RAG_Agent,General_Agent agent;
    class db_tools,rag_tools tool;
    class START,END terminal;
```

* **Supervisor Agent:** Evaluates the prompt and routes to the correct specialist (Database_Agent, RAG_Agent, or General_Agent).
* **Database Agent:** Has exclusive access to PostgreSQL tools (create_booking_basic, query_flights_by_city, etc.) to execute CRUD operations safely.
* **RAG Agent:** Has exclusive access to the search_airline_policies FAISS retriever tool to read the Conditions of Carriage.
* **General Agent:** Handles greetings, chit-chat, and fallback queries while maintaining conversational memory.

## 🛠️ Tech Stack
* **Framework:** [LangGraph](https://python.langchain.com/v0.2/docs/langgraph/) & LangChain Core
* **LLM:** Google Gemini (`gemini-2.5-flash`) OR Local LLMs via Ollama (e.g., `llama3.1` for local, rate-limit-free execution)
* **Vector Database:** FAISS (Local) + HuggingFace Embeddings (`all-mpnet-base-v2`)
* **Relational Database:** PostgreSQL (via Docker) + Faker (for synthetic data generation)
* **UI Interface:** Chainlit
* **Package Manager:** `uv`

---

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* [uv](https://docs.astral.sh/uv/) installed on your system.
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (to run the PostgreSQL database).
* A [Google Gemini API Key](https://aistudio.google.com/) **OR** [Ollama](https://ollama.com/) installed locally to run `llama3.1`.

### 1. Installation
Clone the repository and use `uv` to instantly build the virtual environment and sync dependencies:
```bash
git clone [https://github.com/AhmadKElsayed/SUBO.git](https://github.com/AhmadKElsayed/SUBO.git)
cd SUBO
uv sync
```

### 2. Environment Setup
Create a `.env` file in the root directory and add your API key and database connection string:
```env
GOOGLE_API_KEY=your_actual_api_key_here
DATABASE_URL=postgresql://airline_admin:supersecretpassword@localhost:5432/egypt_airways
```

### 3. Data Initialization
Place your `ConditionsOfCarriage.pdf` inside the `data/` folder. Then, start the PostgreSQL container and initialize the database schema and synthetic data:
```bash
# Start the Postgres container in the background
docker compose up -d

# Initialize the database tables and populate synthetic data
uv run python src/database.py
```
*(The system will automatically build the FAISS vector index from your PDF on the first run).*

---

## 💻 Usage

### 1. Chainlit UI (Web Interface)
To run the interactive chat interface:
```bash
uv run chainlit run app.py -w
```
Navigate to `http://localhost:8000` in your browser.

### 2. LangGraph Studio (Debugging UI)
To visualize the graph, track state payloads, and replay node executions:
```bash
uv run langgraph dev
```

### 3. CLI Testing
To run the underlying graph tests in the terminal without spinning up a web server:
```bash
uv run python test_agent.py
```

---

## 📂 Project Structure

```text
SUBO/
├── pyproject.toml         # Project metadata and dependencies
├── uv.lock                # Deterministic lockfile
├── docker-compose.yml     # PostgreSQL container configuration
├── .env                   # API Keys and DB URL (Ignored in Git)
├── app.py                 # Chainlit UI server
├── test_agent.py          # CLI testing script
├── chainlit.md            # Chainlit welcome screen
├── data/
│   ├── faiss_index/       # Auto-generated Vector store
│   └── ConditionsOfCarriage.pdf # Source document for RAG
└── src/
    ├── database.py        # PostgreSQL schema and synthetic data generation
    ├── db_tools.py        # Custom API tools for PostgreSQL CRUD
    ├── rag_tools.py       # FAISS retriever setup and tools
    └── agent.py           # LangGraph nodes, edges, and compilation
```
```