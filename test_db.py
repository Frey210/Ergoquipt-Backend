import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        database="ergoquipt",
        user="ergoquipt",
        password="password"
    )
    print("✅ Database connection successful!")
    conn.close()
except Exception as e:
    print(f"❌ Database connection failed: {e}")