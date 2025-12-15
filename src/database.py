import sqlite3

DATABASE_NAME = "food_tracker.db"

def setup_database():
    """Creates the SQLite database and the restaurants table."""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    
    # Create the users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default users
    default_users = ['Mahantesh', 'Shweta', 'Manjusha', 'Anish', 'Raj']
    for user in default_users:
        c.execute('INSERT OR IGNORE INTO users (name) VALUES (?)', (user,))
    
    # Create the restaurants table
    c.execute('''
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            cuisines TEXT,
            area TEXT,
            google_map_link TEXT,
            added_by TEXT,
            restaurant_picture BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create the reviews table
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
    
    conn.commit()
    conn.close()
    print(f"Database '{DATABASE_NAME}' and tables ready.")

if __name__ == "__main__":
    setup_database()