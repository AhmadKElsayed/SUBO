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

    try:
        # Stream the graph updates dynamically
        for event in multi_agent.stream({"messages": [("user", message.content)]}, config=config):
            # We only want to stream text out when an agent gives a final answer (not a tool call)
            for node_name, node_state in event.items():
                if node_name in ["Database_Agent", "RAG_Agent", "General_Agent"]:
                    latest_msg = node_state["messages"][-1]
                    if not latest_msg.tool_calls and latest_msg.content:
                        # Ensure content is a string
                        content = latest_msg.content
                        if isinstance(content, list):
                            text_blocks = []
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    text_blocks.append(block.get("text", ""))
                                elif isinstance(block, str):
                                    text_blocks.append(block)
                            content = "".join(text_blocks)
                        elif not isinstance(content, str):
                            content = str(content)
                        
                        msg.content = content
                        await msg.update()
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
            msg.content = "⚠️ **Rate Limit Exceeded (429):** Egypt Airway AI is currently experiencing high demand. Please wait a moment and try again."
        else:
            msg.content = f"⚠️ **An error occurred:** {error_msg}"
        await msg.update()