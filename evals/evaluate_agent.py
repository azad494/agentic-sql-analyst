import os
import asyncio
import json
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.agent.analyst import graph, AgentState
from src.tools.db_tools import get_db_connection

# Initialize an independent LLM instance exclusively dedicated to test generation
generator_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)

# ==========================================
# 1. DYNAMIC TEST DATA GENERATION ENGINE
# ==========================================
def generate_dynamic_golden_dataset(num_cases=3) -> list:
    print("🔄 Sampling active database catalog to synthesize test matrices...")
    conn = get_db_connection()
    dataset = []
    
    try:
        # Step A: Dynamically discover what tables exist inside the target layer
        tables_res = conn.execute("SHOW TABLES").fetchall()
        tables = [row[0] for row in tables_res]
        
        if not tables:
            raise Exception("Database tables are missing or not initialized properly.")
            
        # Step B: Generate a dynamic scenario focusing on Employee performance metrics
        if "employees" in tables and "order_details" in tables:
            # Randomly sample an actual employee out of the database dynamically
            sample_res = conn.execute("SELECT LastName FROM employees ORDER BY random() LIMIT 1").fetchone()
            
            # TYPE FIX: Explicit type assertion to guarantee to Pylance that the object is not None
            assert sample_res is not None, "Failed to sample an employee record from the database."
            emp_name = sample_res[0]
            
            # Pre-calculate the absolute truth value directly via trusted live backend queries
            query_truth = f"""
                SELECT ROUND(SUM(d.UnitPrice * d.Quantity * (1.0 - d.Discount)), 2)
                FROM order_details d
                JOIN orders o ON d.OrderID = o.OrderID
                JOIN employees e ON o.EmployeeID = e.EmployeeID
                WHERE e.LastName = '{emp_name}'
            """
            truth_res = conn.execute(query_truth).fetchone()
            
            # TYPE FIX: Explicit type assertion to prevent subscripting error
            assert truth_res is not None, f"Failed to compute factual truth metrics for {emp_name}."
            truth_val = truth_res[0]
            
            # Synthesize natural language variants using the isolated test generator model
            prompt = f"Generate a short, direct business question asking for total sales revenue for employee '{emp_name}'."
            gen_msg = generator_llm.invoke([HumanMessage(content=prompt)])
            synthetic_query = str(gen_msg.content).strip().strip('"')
            
            dataset.append({
                "id": "DY-001",
                "category": "Automated Joins",
                "user_query": synthetic_query,
                "expected_table": "order_details",
                "target_metrics": [emp_name, str(truth_val)]
            })

        # Step C: Generate a dynamic scenario verifying structural math counting
        if "orders" in tables:
            count_res = conn.execute("SELECT COUNT(*) FROM orders").fetchone()
            
            # TYPE FIX: Explicit type assertion to keep code type-safe
            assert count_res is not None, "Failed to fetch order rows metric."
            total_orders = count_res[0]
            
            prompt = "Generate a direct user request asking to count how many orders total exist in our database."
            gen_msg = generator_llm.invoke([HumanMessage(content=prompt)])
            synthetic_query = str(gen_msg.content).strip().strip('"')
            
            dataset.append({
                "id": "DY-002",
                "category": "Automated Counting",
                "user_query": synthetic_query,
                "expected_table": "orders",
                "target_metrics": [str(total_orders)]
            })

        # Step D: General structural test fallback case
        dataset.append({
            "id": "DY-003",
            "category": "Metadata Layer Discovery",
            "user_query": "Show me all the database tables currently tracked.",
            "expected_table": "SHOW TABLES",
            "target_metrics": [tables[0]]
        })
        
    except Exception as e:
        print(f"⚠️ Synthesis generation warning, falling back to basic metrics: {str(e)}")
        # Safeguard fallback set
        return [
            {
                "id": "FB-001",
                "category": "Static Fallback",
                "user_query": "List all database tables active.",
                "expected_table": "SHOW TABLES",
                "target_metrics": ["orders"]
            }
        ]
    finally:
        conn.close()
        
    print(f"✨ Successfully generated {len(dataset)} dynamic test scenarios!")
    return dataset

# ==========================================
# 2. RUN AUTONOMOUS EVALUATION LOOP
# ==========================================
async def evaluate_system_performance():
    print("🧠 Launching Autonomous Agent Dynamic Evaluation Platform...")
    print("====================================================================\n")
    
    # Generate our test variables automatically out of live data records
    dynamic_dataset = generate_dynamic_golden_dataset()
    
    total_tests = len(dynamic_dataset)
    passed_routing = 0
    passed_groundedness = 0
    
    for test in dynamic_dataset:
        print(f"\n📋 Running Test [{test['id']}] | Category: {test['category']}")
        print(f"💬 Generated Prompt: '{test['user_query']}'")
        
        initial_state: AgentState = {
            "messages": [HumanMessage(content=test["user_query"])]
        }
        
        last_executed_sql = ""
        final_answer = ""
        
        try:
            # Stream graph values smoothly to parse the internal node tracking trace
            for event in graph.stream(initial_state, stream_mode="values"):
                if "messages" in event:
                    last_msg = event["messages"][-1]
                    
                    # Intercept the exact tool calls parameters passed by the model
                    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                        for call in last_msg.tool_calls:
                            if call['name'] == 'execute_sql':
                                last_executed_sql = call['args'].get('query', '').lower()
                                
                    elif isinstance(last_msg, AIMessage) and last_msg.content:
                        if isinstance(last_msg.content, list):
                            text_parts = []
                            for block in last_msg.content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    text_parts.append(block.get("text", ""))
                            final_answer = "".join(text_parts)
                        else:
                            final_answer = str(last_msg.content)
            
            # --- EVALUATION CRITERIA 1: TRAJECTORY ROUTING PRECISION ---
            routing_success = False
            if test["expected_table"] == "SHOW TABLES":
                if "show" in last_executed_sql and "tables" in last_executed_sql:
                    routing_success = True
            elif test["expected_table"] in last_executed_sql:
                routing_success = True
                
            if routing_success:
                print("  🎯 Trajectory Routing: PASSED (Correct table target intercepted)")
                passed_routing += 1
            else:
                print(f"  ❌ Trajectory Routing: FAILED (Agent queried wrong tables or missed tool execution)")
                
            # --- EVALUATION CRITERIA 2: FACTUAL GROUNDEDNESS ACCURACY ---
            groundedness_success = True
            missing_anchors = []
            for metric in test["target_metrics"]:
                if metric.lower() not in final_answer.lower():
                    groundedness_success = False
                    missing_anchors.append(metric)
                    
            if groundedness_success:
                print("  🔒 Factual Groundedness: PASSED (Model summary matches live database realities)")
                passed_groundedness += 1
            else:
                print(f"  ❌ Factual Groundedness: FAILED (Hallucination detected! Missing metrics: {missing_anchors})")
                
            print(f"  📝 Agent Output Snippet: {final_answer[:80].strip()}...\n")
            
        except Exception as e:
            print(f"  💥 Critical Runtime Crash during test trace execution: {str(e)}\n")
            
    # ==========================================
    # 3. COMPILE SYSTEM METRICS SUMMARY REPORT
    # ==========================================
    routing_score = (passed_routing / total_tests) * 100
    groundedness_score = (passed_groundedness / total_tests) * 100
    
    print("====================================================================")
    print("📊 QUANTIFIABLE AUTOMATED AGENT PERFORMANCE METRICS REPORT")
    print("====================================================================")
    print(f"✅ Total Executed Automated Scenarios : {total_tests}")
    print(f"📈 Intent Routing Trajectory Precision  : {routing_score:.2f}%")
    print(f"🎯 Information Groundedness Accuracy    : {groundedness_score:.2f}%")
    print("====================================================================")
    
    if routing_score >= 90.0 and groundedness_score >= 90.0:
        print("🚀 VERIFICATION STATUS: STABLE FOR PRODUCTION SEEDING!")
    else:
        print("⚠️ VERIFICATION STATUS: QUALITY REGRESSION ENCOUNTERED. OPTIMIZE PROMPTS.")

if __name__ == "__main__":
    asyncio.run(evaluate_system_performance())