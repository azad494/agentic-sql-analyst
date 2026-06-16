import os
from dotenv import load_dotenv

# Load variables from .env file immediately upon module loading
load_dotenv()

from typing import Annotated, Literal
from typing_extensions import TypedDict

# Core LangChain & LangGraph Orchestration Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AnyMessage, SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# Import the analytical tools built in Phase 2
from src.tools.db_tools import list_tables, get_table_schema, execute_sql

# ==========================================
# 1. DEFINE AGENT STATE
# ==========================================
class AgentState(TypedDict):
    """
    Tracks the conversational graph state. The add_messages operator ensures 
    subsequent steps append new messages rather than overwriting history.
    """
    messages: Annotated[list[AnyMessage], add_messages]

# ==========================================
# 2. DEFINE SYSTEM INSTRUCTIONS & BIND TOOLS
# ==========================================
SYSTEM_PROMPT = """You are an expert Enterprise SQL Data Analyst. Your job is to answer business questions by querying the local Northwind relational database.

You have access to three specific tools to interact with the database:
1. `list_tables` - Lists available tables.
2. `get_table_schema` - Inspects columns and data types for a table.
3. `execute_sql` - Executes a read-only SQL statement.

CRITICAL PIPELINE RULES:
1. ALWAYS use `list_tables` or `get_table_schema` to check the actual schema before writing a query. Do not guess table or column names.
2. DuckDB SQL syntax matches standard ANSI SQL. 
3. Formulate highly optimized analytical queries. If a user asks for top items, calculate metrics using aggregations (e.g., `SUM()`, `COUNT()`, `GROUP BY`) and sort appropriately.
4. When you have collected all the factual data rows needed to thoroughly answer the user's inquiry, formulate a clear, polished summary answer. Do not output raw unformatted JSON or text tables to the final user response.
"""

# Group tools together and build the operational node
tools = [list_tables, get_table_schema, execute_sql]
tool_node = ToolNode(tools)

# Initialize Gemini 2.5 Flash as our core reasoning model with deterministic settings
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    temperature=0.0
).bind_tools(tools)

# ==========================================
# 3. DEFINE GRAPH CONDITIONAL ROUTING NODES
# ==========================================
def call_model(state: AgentState) -> dict:
    """Executes the Gemini reasoning step based on current conversational state."""
    messages = state["messages"]
    
    # Inject our system rules if this is a fresh conversation state
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
    response = model.invoke(messages)
    return {"messages": [response]}

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """
    Determines whether the agent needs to execute an engineering tool or 
    finalize its response for the end user.
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # TYPE FIX: Explicitly confirm to Pylance that this is an AIMessage containing tool calls
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
        
    return "__end__"

# ==========================================
# 4. CONSTRUCT THE ORCHESTRATION GRAPH
# ==========================================
workflow = StateGraph(AgentState)

# Register workflow components
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# Map edge connections and routing limits
workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "__end__": END
    }
)
workflow.add_edge("tools", "agent")

# Compile everything into a robust executor runtime
graph = workflow.compile()

# ==========================================
# 5. LOCAL EXECUTION TEST WRAPPER
# ==========================================
if __name__ == "__main__":
    print("🧠 Initializing Gemini Agentic SQL Analyst Engine...")
    
    test_query = "Who are our top 3 employees based on total sales volume, and what is their total volume?"
    
    print(f"\nUser Query: '{test_query}'\n")
    print("🛰️ Streaming Gemini Agent Reasoning Loop:")
    print("=" * 60)
    
    # TYPE FIX: Constructing an explicit typed state object containing HumanMessage classes
    initial_state: AgentState = {
        "messages": [HumanMessage(content=test_query)]
    }
    
    for event in graph.stream(initial_state, stream_mode="values"):
        if "messages" in event:
            last_msg = event["messages"][-1]
            if last_msg.content:
                print(f"\n[{type(last_msg).__name__}]:\n{last_msg.content}")
            elif hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                print(f"\n[Tool Calls Requested]: {last_msg.tool_calls}")