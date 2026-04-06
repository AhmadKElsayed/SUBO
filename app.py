import chainlit as cl
from src.rag_tools import init_rag_index
from src.agent import multi_agent

# --- Initialization Checks ---
# These run exactly once when the server starts
print("Checking RAG index...")
init_rag_index()
print("UI Server Ready!")

# --- Chainlit UI Hooks ---
@cl.on_chat_start
async def on_chat_start():
    # Use Chainlit's user session to track LangGraph memory thread
    cl.user_session.set("config", {"configurable": {"thread_id": cl.user_session.get("id")}})
    
    # Updated branding to match your new repository!
    await cl.Message(content="Welcome to Egypt Airway Airlines! I am SUBO, your AI Assistant. How can I help you today?").send()

@cl.on_message
async def on_message(message: cl.Message):
    config = cl.user_session.get("config")
    
    msg = cl.Message(content="")
    await msg.send()

    # Stream the graph updates dynamically
    for event in multi_agent.stream({"messages": [("user", message.content)]}, config=config):
        # We only want to stream text out when an agent gives a final answer (not a tool call)
        for node_name, node_state in event.items():
            if node_name in ["Database_Agent", "RAG_Agent", "General_Agent"]:
                latest_msg = node_state["messages"][-1]
                if not latest_msg.tool_calls and latest_msg.content:
                    msg.content = latest_msg.content
                    await msg.update()