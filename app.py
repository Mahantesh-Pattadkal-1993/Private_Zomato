import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from io import BytesIO
from PIL import Image

DATABASE_NAME = "food_tracker.db"

# --- Database Functions ---

def connect_db():
    """Connects to the SQLite database."""
    return sqlite3.connect(DATABASE_NAME)

def add_restaurant(title, cuisines, area, google_map_link, comments, added_by, picture_bytes):
    """Inserts a new restaurant record into the database."""
    conn = connect_db()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO restaurants (title, cuisines, area, google_map_link, comments, added_by, restaurant_picture) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (title, cuisines, area, google_map_link, comments, added_by, picture_bytes))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error adding restaurant: {e}")
        return False
    finally:
        conn.close()

def fetch_all_restaurants():
    """Fetches all restaurant records."""
    conn = connect_db()
    query = "SELECT title, cuisines, area, google_map_link, comments, added_by, restaurant_picture FROM restaurants"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def search_restaurants(area, cuisine):
    """Searches the database based on the selected area and cuisine."""
    conn = connect_db()
    
    # Build the WHERE clause dynamically
    conditions = []
    params = []
    
    # Use LIKE for partial/case-insensitive matching
    if area:
        conditions.append("area LIKE ?")
        params.append(f"%{area}%")
        
    if cuisine:
        conditions.append("cuisines LIKE ?")
        params.append(f"%{cuisine}%")
        
    where_clause = " AND ".join(conditions)
    
    if where_clause:
        query = f"SELECT title, cuisines, area, google_map_link, comments, added_by, restaurant_picture FROM restaurants WHERE {where_clause}"
    else:
        query = "SELECT title, cuisines, area, google_map_link, comments, added_by, restaurant_picture FROM restaurants"
        
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def delete_restaurant(title):
    """Deletes a restaurant record from the database."""
    conn = connect_db()
    c = conn.cursor()
    try:
        c.execute('''
            DELETE FROM restaurants WHERE title = ?
        ''', (title,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error deleting restaurant: {e}")
        return False
    finally:
        conn.close()

def image_to_bytes(image_file):
    """Convert uploaded image to bytes."""
    if image_file is not None:
        return image_file.read()
    return None

def bytes_to_image(image_bytes):
    """Convert bytes to PIL Image."""
    if image_bytes:
        return Image.open(BytesIO(image_bytes))
    return None

# --- Streamlit UI ---

st.set_page_config(
    page_title="My Food Tracker App",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #FF6B6B;
        border-color: #FF6B6B;
    }
    .restaurant-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stSelectbox, .stMultiSelect, .stTextInput, .stTextArea {
        border-radius: 10px;
    }
    div[data-testid="stSidebarNav"] {
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state for page navigation
if 'current_page' not in st.session_state:
    st.session_state.current_page = "🏠 Home"

# Sidebar Navigation
with st.sidebar:
    # Display logo in sidebar
    image_path = Path("title_image.jpg")
    if image_path.exists():
        st.image("title_image.jpg", use_container_width=True)
    
    st.title("🍽️ MARS Restaurant")
    st.markdown("---")
    
    # Get the index of current page for radio button
    pages = ["🏠 Home", "➕ Add Restaurant", "🔍 Search & View", "📊 Manage Data"]
    current_index = pages.index(st.session_state.current_page)
    
    selected_page = st.radio(
        "Navigate",
        pages,
        index=current_index,
        label_visibility="collapsed"
    )
    
    # Update session state when sidebar selection changes
    if selected_page != st.session_state.current_page:
        st.session_state.current_page = selected_page
        st.rerun()
    
    st.markdown("---")
    
    # Stats in sidebar
    df_all = fetch_all_restaurants()
    st.metric("Total Restaurants", len(df_all))
    if not df_all.empty:
        st.metric("Total Areas", df_all['area'].nunique())
        st.metric("Total Cuisines", len(df_all['cuisines'].str.split(', ').explode().unique()))

# Use the current page from session state
page = st.session_state.current_page

# --- Home Page ---
if page == "🏠 Home":
    st.title("🍽️ MARS Food App")
    st.markdown("### Discover and save your favorite dining spots!")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Add Restaurant\n\nSave new favorite places with photos and reviews", use_container_width=True, key="home_add"):
            st.session_state.current_page = "➕ Add Restaurant"
            st.rerun()
    
    with col2:
        if st.button("🔍 Search & View\n\nFind restaurants by area or cuisine type", use_container_width=True, key="home_search"):
            st.session_state.current_page = "🔍 Search & View"
            st.rerun()
    
    with col3:
        if st.button("📊 Manage Data\n\nView and manage all your saved restaurants", use_container_width=True, key="home_manage"):
            st.session_state.current_page = "📊 Manage Data"
            st.rerun()
    
    st.markdown("---")
    
    # Recent additions
    if not df_all.empty:
        st.subheader("📍 Recently Added Restaurants")
        recent = df_all.tail(3)
        
        cols = st.columns(3)
        for idx, (i, row) in enumerate(recent.iterrows()):
            with cols[idx]:
                with st.container():
                    if row['restaurant_picture']:
                        img = bytes_to_image(row['restaurant_picture'])
                        st.image(img, use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/300x200?text=No+Image", use_container_width=True)
                    
                    st.markdown(f"**{row['title']}**")
                    st.caption(f"📍 {row['area']} | 🍴 {row['cuisines']}")
    else:
        st.info("No restaurants added yet. Start by adding your first favorite place!")

# --- Add Restaurant Page ---
elif page == "➕ Add Restaurant":
    st.title("➕ Add a New Favorite Place")
    st.markdown("Fill in the details below to save a new restaurant")
    
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("🏪 Restaurant Name *", placeholder="Enter restaurant name")
            
            cuisines = st.multiselect(
                "🍜 Cuisines *", 
                options=['Indian', 'Italian', 'Chinese', 'Japanese', 'Mexican', 'Continental', 'South Indian', 'Thai', 'Korean', 'Other'],
            )
            
            area = st.text_input("📍 Area / Locality *", placeholder="e.g., Whitefield, Koramangala")
        
        with col2:
            google_map_link = st.text_input("🗺️ Google Map Link *", placeholder="Paste Google Maps link here")
            
            added_by = st.selectbox(
                "👤 Added By *", 
                options=['Mahantesh', 'Shweta', 'Manjusha', 'Anish', 'Raj'],
            )
            
            restaurant_picture = st.file_uploader("📸 Upload Restaurant Picture", type=['jpg', 'jpeg', 'png'])
        
        comments = st.text_area("💭 Comments / Review", placeholder="Share your experience...", height=100)
        
        st.markdown("---")
        submitted = st.form_submit_button("💾 Save Restaurant", use_container_width=True)
        
        if submitted:
            if title and area and google_map_link and cuisines:
                cuisine_str = ", ".join(cuisines)
                picture_bytes = image_to_bytes(restaurant_picture) if restaurant_picture else None
                
                if add_restaurant(title, cuisine_str, area, google_map_link, comments, added_by, picture_bytes):
                    st.success(f"✅ Successfully added **{title}** to your tracker!")
                    st.balloons()
            else:
                st.error("⚠️ Please fill out all required fields (marked with *)")

# --- Search & View Page ---
elif page == "🔍 Search & View":
    st.title("🔍 Find Your Next Meal")
    
    # Search filters
    with st.container():
        col1, col2, col3 = st.columns([2, 2, 1])
        
        df_all = fetch_all_restaurants()
        all_areas = ['All Areas'] + sorted(df_all['area'].unique().tolist())
        all_cuisines_raw = ['All Cuisines'] + sorted(df_all['cuisines'].str.split(', ').explode().str.strip().unique().tolist())
        
        with col1:
            selected_area = st.selectbox("📍 Filter by Area", options=all_areas)
        
        with col2:
            selected_cuisine = st.selectbox("🍜 Filter by Cuisine", options=all_cuisines_raw)
        
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            search_clicked = st.button("🔍 Search", use_container_width=True)
    
    st.markdown("---")
    
    # Auto-search on page load or when button clicked
    if search_clicked or True:
        area_filter = None if selected_area == 'All Areas' else selected_area
        cuisine_filter = None if selected_cuisine == 'All Cuisines' else selected_cuisine
        
        df_results = search_restaurants(area_filter, cuisine_filter)
        
        if df_results.empty:
            st.info("🔍 No restaurants found matching your criteria. Try different filters!")
        else:
            st.success(f"✨ Found **{len(df_results)}** restaurant(s)!")
            
            # Display results in a grid
            for idx, row in df_results.iterrows():
                with st.container():
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        if row['restaurant_picture']:
                            img = bytes_to_image(row['restaurant_picture'])
                            st.image(img, use_container_width=True)
                        else:
                            st.image("https://via.placeholder.com/400x300?text=No+Image", use_container_width=True)
                    
                    with col2:
                        st.markdown(f"### 🍽️ {row['title']}")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.markdown(f"**🍜 Cuisines:** {row['cuisines']}")
                            st.markdown(f"**📍 Area:** {row['area']}")
                        with col_b:
                            if row['added_by']:
                                st.markdown(f"**👤 Added by:** {row['added_by']}")
                        
                        if row['comments']:
                            st.markdown(f"**💭 Review:**")
                            st.info(row['comments'])
                        
                        st.markdown(f"[🗺️ View on Google Maps]({row['google_map_link']})")
                    
                    st.markdown("---")

# --- Manage Data Page ---
elif page == "📊 Manage Data":
    st.title("📊 Manage Your Restaurants")
    
    df_raw = fetch_all_restaurants()
    
    if df_raw.empty:
        st.info("📭 No restaurants in the database yet. Add your first one!")
    else:
        st.success(f"📚 You have **{len(df_raw)}** restaurant(s) saved")
        st.markdown("---")
        
        # Display each restaurant with delete option
        for idx, row in df_raw.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([1, 3, 1])
                
                with col1:
                    if row['restaurant_picture']:
                        img = bytes_to_image(row['restaurant_picture'])
                        st.image(img, use_container_width=True)
                    else:
                        st.image("https://via.placeholder.com/300x200?text=No+Image", use_container_width=True)
                
                with col2:
                    st.markdown(f"### {row['title']}")
                    st.markdown(f"**🍜 Cuisines:** {row['cuisines']}")
                    st.markdown(f"**📍 Area:** {row['area']}")
                    
                    if row['comments']:
                        with st.expander("💭 View Comments"):
                            st.write(row['comments'])
                    
                    if row['added_by']:
                        st.caption(f"👤 Added by: {row['added_by']}")
                    
                    st.markdown(f"[🗺️ View Map]({row['google_map_link']})")
                
                with col3:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    if st.button("🗑️ Delete", key=f"delete_{idx}", help=f"Delete {row['title']}", type="secondary"):
                        if delete_restaurant(row['title']):
                            st.success(f"✅ Deleted **{row['title']}**!")
                            st.rerun()
                
                st.markdown("---")