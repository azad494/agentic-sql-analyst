import os
import asyncio

# PYTHON 3.14 CORRECTION: Explicitly initialize and bind a running loop 
# to satisfy strict asyncio standards before Streamlit and LangGraph boot up.
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import streamlit as st
import plotly.express as px
import pandas as pd
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# Absolute path tracking adjustments to satisfy multi-directory runtime targets
from src.agent.analyst import graph, AgentState
from src.tools.db_tools import get_db_connection

# ==========================================
# 1. PAGE SETUP & CONFIGURATIONS
# ==========================================
st.set_page_config(
    page_title="Agentic SQL Analyst",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🧠 Agentic SQL Analyst")
st.caption("Powered by LangGraph, Gemini 2.5 Flash, and DuckDB Relational Engine")
st.markdown("---")

# Initialize persistent session chat history arrays
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ==========================================
# 2. SIDEBAR CATALOGUE DIRECTORY COMPONENT
# ==========================================
with st.sidebar:
    st.header("🗄️ Database Table Catalog")
    st.markdown("Inspect live schemas available inside the analytical engine:")
    
    try:
        conn = get_db_connection()
        tables_list = [row[0] for row in conn.execute("SHOW TABLES;").fetchall()]
        
        selected_table = st.selectbox("Select a table to inspect:", tables_list)
        
        if selected_table:
            st.markdown(f"**Schema layout for `{selected_table}`:**")
            schema_df = conn.execute(f"DESCRIBE {selected_table};").df()
            st.dataframe(
                schema_df[["column_name", "column_type"]],
                use_container_width=True,
                hide_index=True
            )
        conn.close()
    except Exception as e:
        st.error(f"Failed to load side catalog layout: {str(e)}")

# ==========================================
# 3. CORE FRONTEND WORKFLOW ROUTER
# ==========================================
user_query = st.chat_input("Ask your business data question (e.g., Show me our sales volume by employee)...")

if user_query:
    # Append user prompt immediately to view screen layout tracking
    st.session_state.chat_history.append(("user", user_query))
    
    # Render historical backlogs
    for role, text in st.session_state.chat_history[:-1]:
        with st.chat_message(role):
            st.markdown(text)
            
    with st.chat_message("user"):
        st.markdown(user_query)
        
    # Instantiate the agent container response frame block
    with st.chat_message("assistant"):
        thinking_container = st.status("🛰️ Agent Reasoning Stream Active...", expanded=True)
        final_answer_placeholder = st.empty()
        chart_placeholder = st.empty()
        
        # Configure initial payload execution dictionary parameters
        # FIX: Explicitly bound to the annotated AgentState type class
        initial_state: AgentState = {
            "messages": [HumanMessage(content=user_query)]
        }
        last_executed_sql = ""
        final_text_response = ""
        
        # Stream graph nodes live into the Streamlit terminal frame status block
        try:
            for event in graph.stream(initial_state, stream_mode="values"):
                if "messages" in event:
                    last_msg = event["messages"][-1]
                    
                    # If model requests tool executions, log them live
                    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                        for call in last_msg.tool_calls:
                            thinking_container.markdown(f"**🤖 Action Requested:** Invoke tool `{call['name']}`")
                            if call['name'] == 'execute_sql':
                                last_executed_sql = call['args'].get('query', '')
                                thinking_container.code(last_executed_sql, language="sql")
                                
                    # Capture tool output reports
                    elif isinstance(last_msg, ToolMessage):
                        thinking_container.markdown(f"*⚙️ Tool Output Completed (ID: `{last_msg.tool_call_id[:8]}`)...*")
                        
                    # Capture ultimate response summary calculations
                    elif isinstance(last_msg, AIMessage) and last_msg.content:
                        final_text_response = str(last_msg.content)
            
            # Collapse the thinking panel completely upon clean final completion loop
            thinking_container.update(label="✅ Reasoning Process Completed Successfully!", state="complete", expanded=False)
            
            # Print the complete natural response output smoothly
            final_answer_placeholder.markdown(final_text_response)
            st.session_state.chat_history.append(("assistant", final_text_response))
            
            # ==========================================
            # 4. AUTO-CHART VISUALIZATION ENGINE LAYER
            # ==========================================
            if last_executed_sql:
                try:
                    conn = get_db_connection()
                    data_df = conn.execute(last_executed_sql).df()
                    conn.close()
                    
                    if not data_df.empty and len(data_df.columns) >= 2:
                        # Extract numerical vs categoric parameters automatically
                        numeric_cols = data_df.select_dtypes(include=['number']).columns.tolist()
                        text_cols = data_df.select_dtypes(include=['object', 'category']).columns.tolist()
                        
                        if numeric_cols and text_cols:
                            chart_placeholder.markdown("### 📊 Dynamic Data Insight Chart")
                            fig = px.bar(
                                data_df,
                                x=text_cols[0],
                                y=numeric_cols[0],
                                title="Agent-Generated SQL Output View Metrics",
                                color=text_cols[0],
                                template="plotly_dark"
                            )
                            chart_placeholder.plotly_chart(fig, use_container_width=True)
                except Exception:
                    # Fail silently on chart plotting failures so it doesn't break the stable text answers
                    pass
                    
        except Exception as e:
            thinking_container.update(label="❌ Graph Process Exception Triggered", state="error", expanded=True)
            st.error(f"Critical execution block error encountered: {str(e)}")