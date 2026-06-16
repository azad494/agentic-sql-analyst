import os
import duckdb
from langchain_core.tools import tool

# Connect directly to the local database file established in Phase 1
DB_PATH = os.path.abspath(os.path.join("data", "northwind.db"))

def get_db_connection():
    """Returns a read-only cursor to the local analytical database."""
    return duckdb.connect(DB_PATH, read_only=True)

@tool
def list_tables() -> str:
    """
    Lists all available table names inside the Northwind relational database catalog.
    Use this tool first when you need to see what data structures are accessible.
    """
    try:
        conn = get_db_connection()
        results = conn.execute("SHOW TABLES;").fetchall()
        tables = [row[0] for row in results]
        conn.close()
        return f"Available Tables in Database: {', '.join(tables)}"
    except Exception as e:
        return f"Error listing database tables: {str(e)}"

@tool
def get_table_schema(table_name: str) -> str:
    """
    Retrieves the column layout, precise field names, and data types for a given table.
    Always query a table's schema before writing or generating SQL queries to avoid column name errors.
    
    Args:
        table_name (str): The exact name of the table to inspect (e.g., 'orders', 'customers').
    """
    try:
        conn = get_db_connection()
        # Verify if the requested table exists safely
        tables = [row[0] for row in conn.execute("SHOW TABLES;").fetchall()]
        if table_name not in tables:
            conn.close()
            return f"Error: Table '{table_name}' does not exist in this database. Valid tables are: {', '.join(tables)}"
            
        results = conn.execute(f"DESCRIBE {table_name};").fetchall()
        conn.close()
        
        # Format the schema catalog layout for crisp LLM ingestion
        schema_lines = [f"Table Schema for '{table_name}':"]
        for row in results:
            col_name, col_type = row[0], row[1]
            schema_lines.append(f" - {col_name} ({col_type})")
            
        return "\n".join(schema_lines)
    except Exception as e:
        return f"Error describing table '{table_name}': {str(e)}"

@tool
def execute_sql(query: str) -> str:
    """
    Executes a read-only DuckDB SQL query against the Northwind database and returns the result matrix.
    Ensure your query matches the schema layouts returned by get_table_schema.
    
    Args:
        query (str): A valid read-only standard SQL statement.
    """
    try:
        conn = get_db_connection()
        # Enforce analytical execution limits to prevent token-overflow crashes
        cursor = conn.execute(query)
        
        # Extract headers and dataset rows
        headers = [desc[0] for desc in cursor.description]
        rows = cursor.fetchmany(100) # Safeguard threshold up to 100 analytical rows
        conn.close()
        
        if not rows:
            return "Query executed completely, but returned 0 data rows."
            
        # Format rows cleanly into a readable table block
        formatted_output = [ " | ".join(headers), "-" * (len(" | ".join(headers))) ]
        for row in rows:
            formatted_output.append(" | ".join(str(val) for val in row))
            
        if len(rows) == 100:
            formatted_output.append("\n⚠️ Warning: Output truncated to the top 100 rows.")
            
        return "\n".join(formatted_output)
    except Exception as e:
        return f"SQL Execution Error: {str(e)}"
    
