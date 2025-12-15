import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from io import BytesIO
from PIL import Image
from datetime import datetime

DATABASE_NAME = "food_tracker.db"

# --- Database Functions ---

def connect_db():
    """Connects to the SQLite database."""
    return sqlite3.connect(DATABASE_NAME)

def add_restaurant(title, cuisines, area, google_map_link, added_by, picture_bytes):
    """Inserts a new restaurant record into the database."""
    conn = connect_db()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO restaurants (title, cuisines, area, google_map_link, added_by, restaurant_picture) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, cuisines, area, google_map_link, added_by, picture_bytes))
        conn.commit()
        restaurant_id = c.lastrowid
        return restaurant_id
    except Exception as e:
        st.error(f"Error adding restaurant: {e}")
        return None
    finally:
        conn.close()

def add_review(restaurant_id, reviewer_name, rating, comment):
    """Adds a review for a restaurant."""
    conn = connect_db()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO reviews (restaurant_id, reviewer_name, rating, comment) 
            VALUES (?, ?, ?, ?)
        ''', (restaurant_id, reviewer_name, rating, comment))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error adding review: {e}")
        return False
    finally:
        conn.close()

def get_restaurant_id_by_title(title):
    """Gets restaurant ID by title."""
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT id FROM restaurants WHERE title = ?", (title,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_reviews_for_restaurant(restaurant_id):
    """Fetches all reviews for a restaurant, ordered by date descending."""
    conn = connect_db()
    query = """
        SELECT reviewer_name, rating, comment, review_date 
        FROM reviews 
        WHERE restaurant_id = ? 
        ORDER BY review_date DESC
    """
    df = pd.read_sql(query, conn, params=(restaurant_id,))
    conn.close()
    return df

def get_average_rating(restaurant_id):
    """Gets the average rating for a restaurant."""
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT AVG(rating) FROM reviews WHERE restaurant_id = ?", (restaurant_id,))
    result = c.fetchone()
    conn.close()
    return round(result[0], 1) if result[0] else 0

def fetch_all_restaurants():
    """Fetches all restaurant records with average ratings."""
    conn = connect_db()
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
    conn.close()
    return df

def search_restaurants(area, cuisine):
    """Searches the database based on the selected area and cuisine."""
    conn = connect_db()
    
    # Build the WHERE clause dynamically
    conditions = []
    params = []
    
    if area:
        conditions.append("r.area LIKE ?")
        params.append(f"%{area}%")
        
    if cuisine:
        conditions.append("r.cuisines LIKE ?")
        params.append(f"%{cuisine}%")
        
    where_clause = " AND ".join(conditions)
    
    if where_clause:
        query = f"""
            SELECT r.id, r.title, r.cuisines, r.area, r.google_map_link, 
                   r.added_by, r.restaurant_picture,
                   COALESCE(AVG(rev.rating), 0) as avg_rating,
                   COUNT(rev.id) as review_count
            FROM restaurants r
            LEFT JOIN reviews rev ON r.id = rev.restaurant_id
            WHERE {where_clause}
            GROUP BY r.id
            ORDER BY r.id DESC
        """
    else:
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
        
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def delete_restaurant(restaurant_id):
    """Deletes a restaurant record from the database."""
    conn = connect_db()
    c = conn.cursor()
    try:
        # Reviews will be deleted automatically due to CASCADE
        c.execute('DELETE FROM restaurants WHERE id = ?', (restaurant_id,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error deleting restaurant: {e}")
        return False
    finally:
        conn.close()


##------------------------------------------------
# User Functions
#-------------------------------------------------

# ... existing code ...

def get_all_users():
    """Fetches all users from the database."""
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT name FROM users ORDER BY name")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def add_user(name):
    """Adds a new user to the database."""
    conn = connect_db()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (name) VALUES (?)', (name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        st.error(f"User '{name}' already exists!")
        return False
    except Exception as e:
        st.error(f"Error adding user: {e}")
        return False
    finally:
        conn.close()

def delete_user(name):
    """Deletes a user from the database."""
    conn = connect_db()
    c = conn.cursor()
    try:
        c.execute('DELETE FROM users WHERE name = ?', (name,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error deleting user: {e}")
        return False
    finally:
        conn.close()

def get_user_count():
    """Gets the total number of users."""
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0