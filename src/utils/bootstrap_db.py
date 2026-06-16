import os
import duckdb

DATA_DIR = os.path.abspath("data")
DB_PATH = os.path.join(DATA_DIR, "northwind.db")

def bootstrap_database():
    """
    Constructs a local, multi-column type-safe Northwind database by executing
    deterministic inline seeder commands. Bypasses external HTTP networks completely.
    """
    print("🚀 Initializing Production Local-First Seeder...")
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Auto-clean any broken previous generations safely
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("🧹 Cleared old database context.")
        except Exception:
            pass

    print("🔌 Booting analytical engine instance...")
    conn = duckdb.connect(DB_PATH)
    
    try:
        # 1. EMPLOYEES TABLE
        print("🧱 Compiling schema for table: 'employees'...")
        conn.execute("""
            CREATE TABLE employees (
                employeeID BIGINT PRIMARY KEY,
                lastName VARCHAR,
                firstName VARCHAR,
                title VARCHAR
            );
        """)
        conn.execute("""
            INSERT INTO employees VALUES 
            (1, 'Davolio', 'Nancy', 'Sales Representative'),
            (2, 'Fuller', 'Andrew', 'Vice President, Sales'),
            (3, 'Leverling', 'Janet', 'Sales Representative'),
            (4, 'Peacock', 'Margaret', 'Sales Representative');
        """)
        
        # 2. ORDERS TABLE
        print("🧱 Compiling schema for table: 'orders'...")
        conn.execute("""
            CREATE TABLE orders (
                orderID BIGINT PRIMARY KEY,
                customerID VARCHAR,
                employeeID BIGINT,
                orderDate VARCHAR
            );
        """)
        conn.execute("""
            INSERT INTO orders VALUES 
            (10248, 'VINET', 4, '1996-07-04'),
            (10249, 'TOMSP', 3, '1996-07-05'),
            (10250, 'HANAR', 4, '1996-07-08'),
            (10251, 'VICTE', 1, '1996-07-08'),
            (10252, 'SUPRD', 4, '1996-07-09'),
            (10253, 'HANAR', 3, '1996-07-10'),
            (10254, 'CHOPS', 1, '1996-07-11');
        """)
        
        # 3. ORDER_DETAILS TABLE
        print("🧱 Compiling schema for table: 'order_details'...")
        conn.execute("""
            CREATE TABLE order_details (
                orderID BIGINT,
                productID BIGINT,
                unitPrice DOUBLE,
                quantity BIGINT,
                discount DOUBLE
            );
        """)
        # Seed exact transactional values that mirror enterprise scale calculations
        conn.execute("""
            INSERT INTO order_details VALUES 
            (10248, 11, 14.00, 12, 0.0),
            (10248, 42, 9.80, 10, 0.0),
            (10249, 14, 18.60, 9, 0.0),
            (10250, 41, 7.70, 10, 0.0),
            (10250, 51, 42.40, 35, 0.15),
            (10251, 22, 16.80, 6, 0.05),
            (10251, 57, 15.60, 15, 0.05),
            (10252, 20, 64.80, 40, 0.05),
            (10252, 33, 2.00, 25, 0.05),
            (10253, 31, 12.50, 20, 0.0),
            (10253, 39, 15.00, 42, 0.0),
            (10254, 24, 3.60, 15, 0.15),
            (10254, 55, 19.20, 21, 0.15);
        """)
        
        # 4. AUXILIARY STRUCTURAL DATA STAGERS
        placeholder_tables = ["categories", "customers", "products", "shippers", "suppliers"]
        for table in placeholder_tables:
            print(f"🧱 Compiling skeleton for metadata table: '{table}'...")
            conn.execute(f"CREATE TABLE {table} (id BIGINT, name VARCHAR);")
            conn.execute(f"INSERT INTO {table} VALUES (1, 'Sample Entry');")

        print("⚡ Checking physical compilation inside catalog schema...")
        catalog = conn.execute("SHOW TABLES;").fetchall()
        print(f"✅ Database built successfully! Verified local tables: {[row[0] for row in catalog]}")
        
    except Exception as e:
        print(f"❌ Bootstrapper Failed to initialize: {str(e)}")
        conn.close()
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        raise e
    finally:
        if 'conn' in locals() and conn is not None:
            conn.close()

if __name__ == "__main__":
    bootstrap_database()