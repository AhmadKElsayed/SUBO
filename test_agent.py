from src.rag_tools import init_rag_index
from src.agent import multi_agent
import time

# --- 1. Bootstrapping ---
print("System Boot: Checking dependencies...")
print("Checking RAG index...")
init_rag_index()
print("System Ready!\n")

# --- 2. Test Configuration ---
# The thread_id allows the agent to remember context between test queries
config = {"configurable": {"thread_id": "cli_test_session_1"}}

def run_test(query: str):
    print(f"\n👤 USER: {query}")
    print("=" * 60)
    
    # Stream the graph to see exactly what decisions it makes
    for event in multi_agent.stream({"messages": [("user", query)]}, config=config):
        for node_name, node_state in event.items():
            print(f"🟢 [Node Executed: {node_name}]")
            
            if "messages" in node_state and node_state["messages"]:
                latest_msg = node_state["messages"][-1]
                
                # Check if it's an AI message (Thoughts or Tool Calls)
                if latest_msg.type == "ai":
                    if latest_msg.tool_calls:
                        for tool in latest_msg.tool_calls:
                            print(f"   🛠️  Action: Calling '{tool['name']}' -> {tool['args']}")
                    if latest_msg.content:
                        print(f"   🤖 AI: {latest_msg.content}")
                        
                # Check if it's a Tool message (Database/FAISS results)
                elif latest_msg.type == "tool":
                    output = str(latest_msg.content).strip()
                    display_out = output[:200] + "... [TRUNCATED]" if len(output) > 200 else output
                    print(f"   ✅ Data Returned:\n      {display_out}")
    print("-" * 60)

# --- 3. Execute Tests ---
if __name__ == "__main__":
    print("🚀 STARTING MULTI-AGENT TESTS...\n")
    
    run_test("Hello! My name is Kamel. I am testing the system.")
    time.sleep(2)
    
    run_test("What is my name?")
    time.sleep(2)
    
    run_test("What is the free baggage allowance policy?")
    time.sleep(2)
    
    run_test("Can you show me the next available flights from Dubai to London?")
    time.sleep(2)
    
    run_test("I would like to make a booking on the earliest one")
    time.sleep(2)
    
    run_test("Economy")
    time.sleep(2)
    
    run_test("My customer ID is 144")
    time.sleep(2)
    
    run_test("Confirm booking")