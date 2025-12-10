import sqlite3

DATABASE_NAME = "food_tracker.db"

def setup_database():
    """Creates the SQLite database and the restaurants table."""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    
    # Create the table with all necessary columns including new fields
    c.execute('''
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            cuisines TEXT,
            area TEXT,
            google_map_link TEXT,
            comments TEXT,
            added_by TEXT,
            restaurant_picture BLOB
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database '{DATABASE_NAME}' and table 'restaurants' ready.")

if __name__ == "__main__":
    setup_database()