import streamlit as st
import libsql
import pandas as pd
from pathlib import Path
from io import BytesIO
from PIL import Image
from datetime import datetime
import sqlite3 # Keep sqlite3 imported just for the IntegrityError handling (though libsql should be used)

# --- Turso Connection Configuration ---
# These are loaded from the Streamlit Secrets file (.streamlit/secrets.toml)
try:
    DB_URL = st.secrets["TURSO_DATABASE_URL"]
    AUTH_TOKEN = st.secrets["TURSO_AUTH_TOKEN"]
except AttributeError:
    # Fallback for local testing outside of Streamlit environment if needed
    DB_URL = "" 
    AUTH_TOKEN = ""

@st.cache_resource
def get_turso_connection(db_url, auth_token):
    """
    Connects to the Turso database using libsql.
    @st.cache_resource ensures the connection is only created once 
    per application deployment, which is crucial for efficiency.
    """
    if not db_url or not auth_token:
        st.error("Turso secrets not found. Please configure TURSO_DATABASE_URL and TURSO_AUTH_TOKEN.")
        return None
        
    try:
        # We use a simple local file for the embedded replica/cache 
        # to avoid the OS error 123 seen previously.
        conn = libsql.connect(
            database="turso_local_cache.db",  
            sync_url=db_url,
            auth_token=auth_token
        )
        # Optional: Sync on startup to ensure fresh data
        # conn.sync() 
        return conn
    except Exception as e:
        st.error(f"Failed to connect to Turso: {e}")
        return None

def connect_db():
    """Returns the cached Turso database connection object."""
    return get_turso_connection(DB_URL, AUTH_TOKEN)

# --- Database Functions ---

def add_restaurant(title, cuisines, area, google_map_link, added_by, picture_bytes):
    """Inserts a new restaurant record and reliably retrieves the new ID."""
    
    conn = connect_db() 
    if not conn:
        print("Error: Database connection failed.")
        return None
        
    c = conn.cursor()
    restaurant_id = None
    
    try:
        # 1. Execute the INSERT statement
        c.execute('''
            INSERT INTO restaurants (title, cuisines, area, google_map_link, added_by, restaurant_picture) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, cuisines, area, google_map_link, added_by, picture_bytes))
        
        # 2. **CRITICAL FIX: Get the ID directly from the cursor**
        # The libsql driver should populate this after the execute() call.
        restaurant_id = c.lastrowid
        
        # 3. Commit the transaction to the remote Turso DB
        conn.commit()
        
        # 4. Explicitly synchronize the local replica to ensure the commit is fully registered
        conn.sync() 
        
        if restaurant_id and restaurant_id > 0:
            print(f"Successfully retrieved new restaurant ID: {restaurant_id}")
            
            return restaurant_id
        else:
            # If we still get 0 or None, raise a specific error
            raise Exception(f"Failed to retrieve last inserted restaurant ID. Got ID: {restaurant_id}")

    except Exception as e:
        print(f"Error adding restaurant: {e}")
        return None
    finally:
        pass

def add_review(restaurant_id, reviewer_name, rating, comment):
    """Adds a review for a restaurant."""
    conn = connect_db()
    if not conn: return False
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO reviews (restaurant_id, reviewer_name, rating, comment) 
            VALUES (?, ?, ?, ?)
        ''', (restaurant_id, reviewer_name, rating, comment))
        conn.commit()

        # Explicitly sync after commit is often crucial for remote operations
        conn.sync()

        # Invalidate cache for functions relying on reviews/ratings
        # fetch_all_restaurants.clear()
        # get_reviews_for_restaurant.clear()
        # get_average_rating.clear()
        return True
    except Exception as e:
        st.error(f"Error adding review: {e}")
        return False
    finally:
        pass

def get_restaurant_id_by_title(title):
    """Gets restaurant ID by title."""
    conn = connect_db()
    if not conn: return None
    c = conn.cursor()
    c.execute("SELECT id FROM restaurants WHERE title = ?", (title,))
    result = c.fetchone()
    # No commit needed for SELECT
    return result[0] if result else None

# @st.cache_data(ttl=600) # Cache the reviews for 10 minutes
def get_reviews_for_restaurant(restaurant_id):
    """Fetches all reviews for a restaurant, ordered by date descending."""
    conn = connect_db()
    if not conn: return pd.DataFrame()
    query = """
        SELECT reviewer_name, rating, comment, review_date 
        FROM reviews 
        WHERE restaurant_id = ? 
        ORDER BY review_date DESC
    """
    # pandas read_sql works seamlessly with the libsql connection object
    df = pd.read_sql(query, conn, params=(restaurant_id,))
    return df

def get_average_rating(restaurant_id):
    """Gets the average rating for a restaurant."""
    conn = connect_db()
    if not conn: return 0
    c = conn.cursor()
    c.execute("SELECT AVG(rating) FROM reviews WHERE restaurant_id = ?", (restaurant_id,))
    result = c.fetchone()
    return round(result[0], 1) if result[0] else 0

def fetch_all_restaurants():
    """Fetches all restaurant records with average ratings."""
    conn = connect_db()
    if not conn: return pd.DataFrame()
    query = """
        SELECT r.id, r.title, r.cuisines, r.area, r.google_map_link, 
               r.added_by, r.restaurant_picture,
               COALESCE(AVG(rev.rating), 0) as avg_rating,
               COUNT(rev.id) as review_count
        FROM restaurants r
        LEFT JOIN reviews rev ON r.id = rev.restaurant_id
        GROUP BY r.id
        ORDER BY r.id DESC
    """
    df = pd.read_sql(query, conn)
    return df

def search_restaurants(area, cuisine):
    """Searches the database based on the selected area and cuisine."""
    conn = connect_db()
    if not conn: return pd.DataFrame()
    
    # ... (dynamic query building logic remains the same) ...
    conditions = []
    params = []
    
    if area:
        conditions.append("r.area LIKE ?")
        params.append(f"%{area}%")
        
    if cuisine:
        conditions.append("r.cuisines LIKE ?")
        params.append(f"%{cuisine}%")
        
    where_clause = " AND ".join(conditions)
    
    base_query = """
        SELECT r.id, r.title, r.cuisines, r.area, r.google_map_link, 
               r.added_by, r.restaurant_picture,
               COALESCE(AVG(rev.rating), 0) as avg_rating,
               COUNT(rev.id) as review_count
        FROM restaurants r
        LEFT JOIN reviews rev ON r.id = rev.restaurant_id
    """
    
    group_order_clause = """
        GROUP BY r.id
        ORDER BY r.id DESC
    """

    if where_clause:
        query = f"{base_query} WHERE {where_clause} {group_order_clause}"
    else:
        query = f"{base_query} {group_order_clause}"
        
    df = pd.read_sql(query, conn, params=params)
    return df

def delete_restaurant(restaurant_id):
    """Deletes a restaurant record from the database."""
    conn = connect_db()
    if not conn: return False
    c = conn.cursor()
    try:
        # Reviews will be deleted automatically due to CASCADE
        c.execute('DELETE FROM restaurants WHERE id = ?', (restaurant_id,))
        conn.commit()
        # Invalidate the cache for the main restaurant list
        #fetch_all_restaurants.clear()
        return True
    except Exception as e:
        st.error(f"Error deleting restaurant: {e}")
        return False
    finally:
        pass


##------------------------------------------------
# User Functions
#-------------------------------------------------

#@st.cache_data(ttl=3600) # Cache the user list
def get_all_users():
    """Fetches all users from the database."""
    conn = connect_db()
    if not conn: return []
    c = conn.cursor()
    c.execute("SELECT name FROM users ORDER BY name")
    users = [row[0] for row in c.fetchall()]
    return users

def add_user(name):
    """Adds a new user to the database."""
    conn = connect_db()
    if not conn: return False
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (name) VALUES (?)', (name,))
        conn.commit()
        # Clear the user list cache
        get_all_users.clear() 
        return True
    except libsql.IntegrityError: # Use libsql's error handling
        st.error(f"User '{name}' already exists!")
        return False
    except Exception as e:
        st.error(f"Error adding user: {e}")
        return False
    finally:
        pass

def delete_user(name):
    """Deletes a user from the database."""
    conn = connect_db()
    if not conn: return False
    c = conn.cursor()
    try:
        c.execute('DELETE FROM users WHERE name = ?', (name,))
        conn.commit()
        # Clear the user list cache
        get_all_users.clear()
        return True
    except Exception as e:
        st.error(f"Error deleting user: {e}")
        return False
    finally:
        pass

#@st.cache_data(ttl=3600)
def get_user_count():
    """Gets the total number of users."""
    conn = connect_db()
    if not conn: return 0
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    result = c.fetchone()
    return result[0] if result else 0

