import streamlit as st
import psycopg2
from psycopg2 import sql
import pandas as pd
from pathlib import Path
from io import BytesIO
from PIL import Image
from datetime import datetime

# --- PostgreSQL Connection Configuration ---
# These are loaded from the Streamlit Secrets file (.streamlit/secrets.toml)
try:
    DB_HOST = st.secrets["POSTGRES_HOST"]
    DB_PORT = st.secrets["POSTGRES_PORT"]
    DB_NAME = st.secrets["POSTGRES_DB"]
    DB_USER = st.secrets["POSTGRES_USER"]
    DB_PASSWORD = st.secrets["POSTGRES_PASSWORD"]
except (AttributeError, KeyError):
    # Fallback for local testing outside of Streamlit environment if needed
    DB_HOST = ""
    DB_PORT = 5432
    DB_NAME = ""
    DB_USER = ""
    DB_PASSWORD = ""

@st.cache_resource
def get_postgres_connection(db_host, db_port, db_name, db_user, db_password):
    """
    Connects to the PostgreSQL database using psycopg2.
    @st.cache_resource ensures the connection is only created once 
    per application deployment, which is crucial for efficiency.
    """
    if not all([db_host, db_name, db_user, db_password]):
        st.error("PostgreSQL secrets not found. Please configure POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD.")
        return None
        
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            sslmode="require"
        )
        return conn
    except Exception as e:
        st.error(f"Failed to connect to PostgreSQL: {e}")
        return None

def connect_db():
    """Returns the cached PostgreSQL database connection object."""
    return get_postgres_connection(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)

# --- Database Functions ---

def add_restaurant(title, cuisines, area, google_map_link, added_by, picture_bytes, price_per_person):
    """Inserts a new restaurant record and reliably retrieves the new ID."""
    
    conn = connect_db() 
    if not conn:
        print("Error: Database connection failed.")
        return None
        
    cur = conn.cursor()
    restaurant_id = None
    
    try:
        # 1. Execute the INSERT statement with RETURNING to get the ID
        cur.execute('''
            INSERT INTO restaurants (title, cuisines, area, google_map_link, added_by, restaurant_picture, price_per_person) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (title, cuisines, area, google_map_link, added_by, picture_bytes, price_per_person))
        
        # 2. Get the ID directly from the RETURNING clause
        restaurant_id = cur.fetchone()[0]
        
        # 3. Commit the transaction
        conn.commit()
        
        if restaurant_id and restaurant_id > 0:
            print(f"Successfully retrieved new restaurant ID: {restaurant_id}")
            return restaurant_id
        else:
            raise Exception(f"Failed to retrieve last inserted restaurant ID. Got ID: {restaurant_id}")

    except Exception as e:
        print(f"Error adding restaurant: {e}")
        conn.rollback()
        return None
    finally:
        cur.close()

def add_review(restaurant_id, reviewer_name, rating, comment):
    """Adds a review for a restaurant."""
    conn = connect_db()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO reviews (restaurant_id, reviewer_name, rating, comment) 
            VALUES (%s, %s, %s, %s)
        ''', (restaurant_id, reviewer_name, rating, comment))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error adding review: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()

def get_restaurant_id_by_title(title):
    """Gets restaurant ID by title."""
    conn = connect_db()
    if not conn: return None
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM restaurants WHERE title = %s", (title,))
        result = cur.fetchone()
        return result[0] if result else None
    finally:
        cur.close()

def get_reviews_for_restaurant(restaurant_id):
    """Fetches all reviews for a restaurant, ordered by date descending."""
    conn = connect_db()
    if not conn: return pd.DataFrame()
    query = """
        SELECT id, reviewer_name, rating, comment, review_date 
        FROM reviews 
        WHERE restaurant_id = %s 
        ORDER BY review_date DESC
    """
    try:
        df = pd.read_sql(query, conn, params=(restaurant_id,))
        return df
    except Exception as e:
        st.error(f"Error fetching reviews: {e}")
        return pd.DataFrame()

def get_average_rating(restaurant_id):
    """Gets the average rating for a restaurant."""
    conn = connect_db()
    if not conn: return 0
    cur = conn.cursor()
    try:
        cur.execute("SELECT AVG(rating) FROM reviews WHERE restaurant_id = %s", (restaurant_id,))
        result = cur.fetchone()
        return round(result[0], 1) if result[0] else 0
    finally:
        cur.close()

def fetch_all_restaurants():
    """Fetches all restaurant records with average ratings."""
    conn = connect_db()
    if not conn: return pd.DataFrame()
    query = """
        SELECT r.id, r.title, r.cuisines, r.area, r.google_map_link, 
               r.added_by, r.restaurant_picture, r.price_per_person,
               COALESCE(AVG(rev.rating), 0) as avg_rating,
               COUNT(rev.id) as review_count
        FROM restaurants r
        LEFT JOIN reviews rev ON r.id = rev.restaurant_id
        GROUP BY r.id
        ORDER BY r.id DESC
    """
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        print("Connection is healthy")
        cur.close()
    except Exception as e:
        print(f"Connection failed: {e}")
        return pd.DataFrame()

    try:
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Error fetching restaurants: {e}")
        return pd.DataFrame()

def search_restaurants(area, cuisine):
    """Searches the database based on the selected area and cuisine."""
    conn = connect_db()
    if not conn: return pd.DataFrame()
    
    conditions = []
    params = []
    
    if area:
        conditions.append("r.area ILIKE %s")
        params.append(f"%{area}%")
        
    if cuisine:
        conditions.append("r.cuisines ILIKE %s")
        params.append(f"%{cuisine}%")
        
    where_clause = " AND ".join(conditions)
    
    base_query = """
        SELECT r.id, r.title, r.cuisines, r.area, r.google_map_link, 
               r.added_by, r.restaurant_picture, r.price_per_person,
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
    
    try:
        df = pd.read_sql(query, conn, params=params)
        return df
    except Exception as e:
        st.error(f"Error searching restaurants: {e}")
        return pd.DataFrame()

def delete_restaurant(restaurant_id):
    """Deletes a restaurant record from the database."""
    conn = connect_db()
    if not conn: return False
    cur = conn.cursor()
    try:
        # Reviews will be deleted automatically due to CASCADE
        cur.execute('DELETE FROM restaurants WHERE id = %s', (restaurant_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error deleting restaurant: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()

def update_restaurant(restaurant_id, title, cuisines, area, map_link, price_per_person, picture_bytes=None):
    conn = connect_db()
    if not conn:
        st.error("Database connection failed.")
        return False

    # Ensure price_per_person is never None
    price_per_person = price_per_person or 0

    cur = conn.cursor()
    try:
        if picture_bytes:
            query = """
                UPDATE restaurants
                SET title=%s, cuisines=%s, area=%s, google_map_link=%s, price_per_person=%s, restaurant_picture=%s
                WHERE id=%s
            """
            cur.execute(query, (title, cuisines, area, map_link, price_per_person, picture_bytes, restaurant_id))
        else:
            query = """
                UPDATE restaurants
                SET title=%s, cuisines=%s, area=%s, google_map_link=%s, price_per_person=%s
                WHERE id=%s
            """
            cur.execute(query, (title, cuisines, area, map_link, price_per_person, restaurant_id))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error updating restaurant: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()

def update_review(review_id, rating, comment):
    conn = connect_db()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("UPDATE reviews SET rating=%s, comment=%s WHERE id=%s", (rating, comment, review_id))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error updating review: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()

##------------------------------------------------
# User Functions
#-------------------------------------------------

def get_all_users():
    """Fetches all users from the database."""
    conn = connect_db()
    if not conn: return []
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM users ORDER BY name")
        users = [row[0] for row in cur.fetchall()]
        return users
    finally:
        cur.close()

def add_user(name):
    """Adds a new user to the database."""
    conn = connect_db()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO users (name) VALUES (%s)', (name,))
        conn.commit()
        return True
    except psycopg2.IntegrityError:
        st.error(f"User '{name}' already exists!")
        conn.rollback()
        return False
    except Exception as e:
        st.error(f"Error adding user: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()

def delete_user(name):
    """Deletes a user from the database."""
    conn = connect_db()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM users WHERE name = %s', (name,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error deleting user: {e}")
        conn.rollback()
        return False
    finally:
        cur.close()

def get_user_count():
    """Gets the total number of users."""
    conn = connect_db()
    if not conn: return 0
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM users")
        result = cur.fetchone()
        return result[0] if result else 0
    finally:
        cur.close()