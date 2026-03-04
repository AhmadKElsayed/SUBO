import os
from typing import Annotated, Literal, TypedDict
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama import ChatOllama

from src.db_tools import db_tools_list
from src.rag_tools import rag_tools_list

load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1, google_api_key=google_api_key)

llm = ChatOllama(model="llama3.1", temperature=0.1)

class State(TypedDict):
    messages: Annotated[list, add_messages]

# --- 1. DB Agent Node ---
# PROMPT UPDATED to use API tools instead of raw SQL
db_prompt = SystemMessage(content="""
You are SUBO, the database assistant for Egypt Airlines.
You have access to specific API tools to manage flights, bookings, and customers.
RULES:
1. Do not guess customer IDs or flight numbers. Use `get_customer` or `query_flights_by_city` first.
2. Before creating a booking, you MUST check `seats_remaining`.
3. Never invent data. If an operation fails, tell the user gracefully.
""")
llm_with_db_tools = llm.bind_tools(db_tools_list)

def db_agent_node(state: State):
    return {"messages": [llm_with_db_tools.invoke([db_prompt] + state["messages"])]}

# --- 2. RAG Agent Node ---
rag_prompt = SystemMessage(content="""
You are the Policy Librarian for Egypt Airlines.
Search the Conditions of Carriage document using your tool to answer user questions.
If the answer isn't in the document, say you don't know.
""")
llm_with_rag_tools = llm.bind_tools(rag_tools_list)

def rag_agent_node(state: State):
    return {"messages": [llm_with_rag_tools.invoke([rag_prompt] + state["messages"])]}

# --- 3. General Agent Node ---
general_prompt = SystemMessage(content="""
You are a friendly customer service assistant for Egypt Airlines.
Chat with the user, answer general questions, and remember details they share.
""")

def general_agent_node(state: State):
    return {"messages": [llm.invoke([general_prompt] + state["messages"])]}

# --- 4. Supervisor Router ---
class Route(BaseModel):
    next_node: Literal["Database_Agent", "RAG_Agent", "General_Agent"]

supervisor_prompt = """You are a Supervisor routing a user's request.
- Route to 'Database_Agent' for checking flights, seats, customers, bookings, or tickets.
- Route to 'RAG_Agent' for airline rules, baggage policies, or conditions of carriage.
- Route to 'General_Agent' for greetings, small talk, or remembering names.
"""

def supervisor_node(state: State):
    return {"messages": []}

def supervisor_router(state: State) -> str:
    router = llm.with_structured_output(Route)
    decision = router.invoke([SystemMessage(content=supervisor_prompt)] + state["messages"])
    return decision.next_node

# --- 5. Compile Graph ---
builder = StateGraph(State)

builder.add_node("Supervisor", supervisor_node)
builder.add_node("Database_Agent", db_agent_node)
builder.add_node("RAG_Agent", rag_agent_node)
builder.add_node("General_Agent", general_agent_node)
builder.add_node("db_tools", ToolNode(db_tools_list))
builder.add_node("rag_tools", ToolNode(rag_tools_list))

builder.add_edge(START, "Supervisor")
builder.add_conditional_edges("Supervisor", supervisor_router)

builder.add_conditional_edges("Database_Agent", tools_condition, {"tools": "db_tools", END: END})
builder.add_edge("db_tools", "Database_Agent")

builder.add_conditional_edges("RAG_Agent", tools_condition, {"tools": "rag_tools", END: END})
builder.add_edge("rag_tools", "RAG_Agent")

builder.add_edge("General_Agent", END)

memory = MemorySaver()
multi_agent = builder.compile(checkpointer=memory)