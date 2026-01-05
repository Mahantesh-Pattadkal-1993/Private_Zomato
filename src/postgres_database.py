import psycopg2
from psycopg2 import sql

# --- PostgreSQL Connection Details ---
# REPLACE with your actual PostgreSQL connection details
DB_HOST = "private-zomato-mpattadkal-e565.l.aivencloud.com"
DB_PORT = 23459
DB_NAME = "defaultdb"
DB_USER = "avnadmin"
DB_PASSWORD = "AVNS_dQHnEa5bvIc_ReNoy5a"

def setup_database_on_postgres():
    """Connects to the PostgreSQL database, tests the connection, and creates tables."""
    conn = None
    cur = None

    # --- Connection Test and Setup ---
    try:
        # Connect to the remote PostgreSQL database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            sslmode="require"
        )
        print("✅ Connection to PostgreSQL successful!")

        cur = conn.cursor()

        # --- Create the users table ---
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("Table 'users' created/checked.")

        # Insert default users
        default_users = ['Mahantesh', 'Shweta', 'Manjusha', 'Anish', 'Raj']
        for user in default_users:
            # Use ON CONFLICT to prevent errors if the user already exists
            cur.execute('''
                INSERT INTO users (name) VALUES (%s)
                ON CONFLICT (name) DO NOTHING
            ''', (user,))
        print(f"{len(default_users)} default users inserted or ignored.")
        
        # --- Create the restaurants table ---
        cur.execute('''
            CREATE TABLE IF NOT EXISTS restaurants (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                cuisines TEXT,
                area TEXT,
                google_map_link TEXT,
                added_by TEXT,
                price_per_person REAL,
                restaurant_picture BYTEA,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("Table 'restaurants' created/checked.")
        
        # --- Create the reviews table ---
        cur.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id SERIAL PRIMARY KEY,
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
        print("--- All tables and default data committed successfully to PostgreSQL! ---")
        
    except Exception as e:
        print(f"❌ An error occurred while connecting or executing queries:")
        print(f"Error Details: {e}")
        print("Please double-check your connection details.")
        if conn:
            conn.rollback()

    finally:
        # Close the cursor and connection
        if cur:
            cur.close()
        if conn:
            conn.close()
            print("Connection closed.")

if __name__ == "__main__":
    setup_database_on_postgres()