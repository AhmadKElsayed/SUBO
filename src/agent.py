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
You are SUBO, the expert Database Assistant for Egypt Airway Airlines.
You have exclusive access to the airline's reservation and customer databases via your tools.

CRITICAL RULES:
1. NO ASSUMPTIONS: Never guess a customer ID, flight number, or booking ID. If you don't have it, ask the user or use `get_customer` / `query_flights_by_city` to find it.
2. BOOKING WORKFLOW: Before calling `create_booking_basic`, you MUST verify the flight has `seats_remaining`.
3. DATA INTEGRITY: Never invent or hallucinate data. If a tool returns no results, politely inform the user that the information was not found.
4. CLARIFICATION: If the user makes a vague request (e.g., "book a flight to London"), ask for the missing details (departure city, dates, travel class) before calling tools.
5. TONE: Be professional, concise, and helpful. Format prices with a dollar sign ($) and dates clearly.
""")

llm_with_db_tools = llm.bind_tools(db_tools_list)

def db_agent_node(state: State):
    return {"messages": [llm_with_db_tools.invoke([db_prompt] + state["messages"])]}

# --- 2. RAG Agent Node ---
rag_prompt = SystemMessage(content="""
You are the strict Policy Expert for Egypt Airway Airlines.
Your sole responsibility is answering questions about airline policies, baggage, rules, and conditions of carriage.

CRITICAL RULES:
1. TOOL USAGE: You MUST use the `search_airline_policies` tool to retrieve official documents for EVERY policy question.
2. NO HALLUCINATION: Base your answer EXCLUSIVELY on the retrieved text. Do not use your pre-trained outside knowledge. 
3. ADMIT IGNORANCE: If the tool returns "No relevant policies found," or if the retrieved text does not contain the answer, state clearly: "I'm sorry, but I cannot find that specific policy in our current Conditions of Carriage."
4. CITATION: Quote or reference the policy directly when appropriate, but keep the overall response conversational and easy to understand for a passenger.
""")
llm_with_rag_tools = llm.bind_tools(rag_tools_list)

def rag_agent_node(state: State):
    return {"messages": [llm_with_rag_tools.invoke([rag_prompt] + state["messages"])]}

# --- 3. General Agent Node ---
general_prompt = SystemMessage(content="""
You are SUBO, the welcoming front-desk ambassador for Egypt Airway Airlines.
Your job is to handle casual conversation, greetings, and general assistance.

CRITICAL RULES:
1. SCOPE: Do NOT attempt to answer policy questions, book flights, or check statuses. You do not have the tools for this.
2. TONE: Be warm, empathetic, and exceptionally polite. 
3. GUIDANCE: If the user is just saying hello, warmly welcome them and ask how you can assist them with their travels, bookings, or airline questions today.
""")

def general_agent_node(state: State):
    return {"messages": [llm.invoke([general_prompt] + state["messages"])]}

# --- 4. Supervisor Router ---
class Route(BaseModel):
    next_node: Literal["Database_Agent", "RAG_Agent", "General_Agent"]

supervisor_prompt = """You are the Chief Routing Supervisor for Egypt Airway Airlines.
Your job is to analyze the user's input and route it to the correct specialist agent.

ROUTING RULES:
- 'Database_Agent': Choose this if the user wants to book a flight, check flight status, cancel a ticket, look up their profile, check seat availability, or file a complaint. Look for intent regarding: booking, schedules, profiles, or cancellations.
- 'RAG_Agent': Choose this if the user asks about airline policies, rules, baggage limits, pets, refunds, or terms of service. Look for intent regarding: rules, allowances, or legal conditions.
- 'General_Agent': Choose this for standard greetings (hello, how are you), casual conversation, thanking you, or questions completely unrelated to the airline.

Always default to 'General_Agent' if the request is ambiguous or conversational.
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