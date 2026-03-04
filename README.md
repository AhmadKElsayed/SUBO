#  🤖  SUBO

A sophisticated, multi-agent customer service assistant for "Light Airlines." This project implements a production-grade **LangGraph** routing architecture to handle dynamic database operations (flights, bookings, tickets), Retrieval-Augmented Generation (airline policies), and general conversational memory.



## 🌟 Features
* **Multi-Agent Routing:** A Supervisor node intelligently classifies user intent and routes queries to specialized sub-agents.
* **Strict SQL/DB Execution:** Uses custom API tools (via `@tool`) bound to a dedicated Database Agent to safely execute CRUD operations on a SQLite database (book flights, cancel tickets, check seats).
* **Policy RAG:** A dedicated RAG Agent uses FAISS and HuggingFace embeddings to search the airline's *Conditions of Carriage* PDF, providing accurate policy citations with zero hallucination.
* **Conversational Memory:** Maintains user context (like names and customer IDs) across the session.
* **Modern MLOps Tooling:** Managed entirely via `uv` for blazing-fast dependency resolution. 

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

Supervisor Agent: Evaluates the prompt and routes to the correct specialist (Database_Agent, RAG_Agent, or General_Agent).

Database Agent: Has exclusive access to sqlite3 tools (create_booking_basic, query_flights_by_city, etc.) to execute CRUD operations safely.

RAG Agent: Has exclusive access to the search_airline_policies FAISS retriever tool to read the Conditions of Carriage.

General Agent: Handles greetings, chit-chat, and fallback queries while maintaining conversational memory.


## 🛠️ Tech Stack
* **Framework:** [LangGraph](https://python.langchain.com/v0.2/docs/langgraph/) & LangChain Core
* **LLM:** Google Gemini (`gemini-2.5-flash` / `gemini-3.0-flash`)
* **Vector Database:** FAISS (Local) + HuggingFace Embeddings (`all-mpnet-base-v2`)
* **Relational Database:** SQLite3 + Faker (for synthetic data generation)
* **UI Interface:** Chainlit
* **Package Manager:** `uv`

---

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* [uv](https://docs.astral.sh/uv/) installed on your system.
* A [Google Gemini API Key](https://aistudio.google.com/).

### 1. Installation
Clone the repository and use `uv` to instantly build the virtual environment and sync dependencies:
```bash
git clone [https://github.com/YOUR_USERNAME/light-airlines-agent.git](https://github.com/YOUR_USERNAME/light-airlines-agent.git)
cd light-airlines-agent
uv sync

```

### 2. Environment Setup

Create a `.env` file in the root directory and add your Google API key:

```env
GOOGLE_API_KEY=your_actual_api_key_here

```

### 3. Data Initialization

Place your `ConditionsOfCarriage.pdf` inside the `data/` folder. The system will automatically detect if the database (`airline.db`) and vector index (`faiss_index`) are missing and build them from scratch on the first run.

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
light-airlines-agent/
├── pyproject.toml         # Project metadata and dependencies
├── uv.lock                # Deterministic lockfile
├── .env                   # API Keys (Ignored in Git)
├── app.py                 # Chainlit UI server
├── test_agent.py          # CLI testing script
├── chainlit.md            # Chainlit welcome screen
├── data/
│   ├── airline.db         # Auto-generated SQLite database
│   ├── faiss_index/       # Auto-generated Vector store
│   └── ConditionsOfCarriage.pdf # Source document for RAG
└── src/
    ├── database.py        # Schema and synthetic data generation
    ├── db_tools.py        # Custom API tools for SQLite CRUD
    ├── rag_tools.py       # FAISS retriever setup and tools
    └── agent.py           # LangGraph nodes, edges, and compilation

```

```

This acts as a perfect portfolio piece. It clearly defines the problem, the architectural solution, and gives flawless reproduction steps. 

Once you paste this in, you can add it to your git tracking (`git add README.md`, `git commit -m "docs: add comprehensive README"`, `git push`). How is the migration to the local environment looking?

```
