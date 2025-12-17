import libsql
from libsql import connect

# --- Turso Connection Details ---
# 1. REPLACE with your actual Turso Database URL
DB_URL = "libsql://privatezomato-mahantesh-pattadkal-1993.aws-ap-south-1.turso.io"

# 2. REPLACE with the Auth Token you generated
AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NjU4NjY4NDgsImlkIjoiODQzYjBlMzItN2FhMS00NzcwLTkwODctODRlOWNlZmExYTM5IiwicmlkIjoiZWNiZjI3MmUtNGJhYS00YzVkLWIwYTYtMGY2ZDk5YjNhOTk1In0.9CSsYH9LwxjnuDlZNRLlcfPB3mqaHAInxhL0EsKoJ7QzCgwZONd4x8O6sUr-mjBKqUlUCnzmNzB5ZsFIEUfzAg" 

def setup_database_on_turso():
    """Connects to the Turso database, tests the connection, and creates tables."""
    conn = None # Initialize conn outside try block

    # --- Connection Test and Setup ---
    try:
        # Connect to the remote Turso database using libsql
        conn = connect(
            # Using ":memory:" or a local file is standard when connecting to a remote sync URL
            database="turso_local_cache.db",  
            sync_url=DB_URL,
            auth_token=AUTH_TOKEN
        )
        print("✅ Connection to Turso Cloud successful!")

        c = conn.cursor()

        # --- Create the users table ---
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("Table 'users' created/checked.")

        # Insert default users
        default_users = ['Mahantesh', 'Shweta', 'Manjusha', 'Anish', 'Raj']
        for user in default_users:
            # Use INSERT OR IGNORE to prevent errors if the user already exists
            c.execute('INSERT OR IGNORE INTO users (name) VALUES (?)', (user,))
        print(f"{len(default_users)} default users inserted or ignored.")
        
        # --- Create the restaurants table ---
        c.execute('''
            CREATE TABLE IF NOT EXISTS restaurants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                cuisines TEXT,
                area TEXT,
                google_map_link TEXT,
                added_by TEXT,
                price_per_person REAL,  -- <--- New Numerical Field Added
                restaurant_picture BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("Table 'restaurants' created/checked.")
        
        # --- Create the reviews table ---
        c.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER NOT NULL,
                reviewer_name TEXT NOT NULL,
                rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                comment TEXT,
                review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (restaurant_id) REFERENCES restaurants (id) ON DELETE CASCADE
            )
        ''')
        print("Table 'reviews' created/checked.")

        # --- Finalize Changes ---
        conn.commit()
        print("--- All tables and default data committed successfully to Turso Cloud! ---")
        
    except Exception as e:
        print(f"❌ An error occurred while connecting or executing queries:")
        print(f"Error Details: {e}")
        print("Please double-check your DB_URL and AUTH_TOKEN.")

    finally:
        # Close the connection
        if conn:
            conn.close()
            print("Connection closed.")

if __name__ == "__main__":
    setup_database_on_turso()