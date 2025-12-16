import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from io import BytesIO
from PIL import Image
from datetime import datetime

from src.utils.turso_db_utils import (
    add_restaurant,     
    add_review,
    get_reviews_for_restaurant,
    fetch_all_restaurants,
    search_restaurants,
    delete_restaurant,
    get_all_users,
    add_user,
    delete_user,
    get_user_count
)

from src.utils.ui_utils import (
    image_to_bytes,
    bytes_to_image,
    display_star_rating
)


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
    .review-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        color: #262730;
    }
    .review-box strong {
        color: #262730;
        font-size: 16px;
    }
    .review-box p {
        color: #262730;
        margin-top: 10px;
        margin-bottom: 0;
    }
    .review-box small {
        color: #6c757d;
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
    pages = ["🏠 Home", "➕ Add Restaurant", "🔍 Search & View", "📊 Manage Data", "👥 Manage Users"]
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
        st.metric("Total Reviews", int(df_all['review_count'].sum()))
    st.metric("Total Users", get_user_count())

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
        recent = df_all.head(3)
        
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
                    if row['avg_rating'] > 0:
                        st.caption(display_star_rating(row['avg_rating']))
    else:
        st.info("No restaurants added yet. Start by adding your first favorite place!")

# --- Add Restaurant Page ---
elif page == "➕ Add Restaurant":
    st.title("➕ Add a New Favorite Place")
    st.markdown("Fill in the details below to save a new restaurant")
    
    # Get users dynamically
    users = get_all_users()
    
    if not users:
        st.warning("⚠️ No users found! Please add users in the 'Manage Users' section first.")
    else:
        with st.form("add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("🏪 Restaurant Name *", placeholder="Enter restaurant name")
                
                cuisines = st.multiselect(
                    "🍜 Cuisines *", 
                    options=['Indian','Arabic' ,'Italian', 'Chinese', 'Japanese', 'Mexican', 'Continental', 'South Indian', 'Thai', 'Korean', 'Other'],
                )
                
                area = st.text_input("📍 Area / Locality *", placeholder="e.g., Whitefield, Koramangala")
            
            with col2:
                google_map_link = st.text_input("🗺️ Google Map Link *", placeholder="Paste Google Maps link here")
                
                added_by = st.selectbox(
                    "👤 Added By *", 
                    options=users,
                )
                
                restaurant_picture = st.file_uploader("📸 Upload Restaurant Picture", type=['jpg', 'jpeg', 'png'])
            
            st.markdown("### 📝 Add Your First Review")
            
            col3, col4 = st.columns(2)
            with col3:
                rating = st.slider("⭐ Rating", 1, 5, 3)
            with col4:
                st.write("")  # Spacing
            
            comments = st.text_area("💭 Your Review", placeholder="Share your experience...", height=100)
            
            st.markdown("---")
            submitted = st.form_submit_button("💾 Save Restaurant", use_container_width=True)
            
            if submitted:
                if title and area and google_map_link and cuisines:
                    cuisine_str = ", ".join(cuisines)
                    picture_bytes = image_to_bytes(restaurant_picture) if restaurant_picture else None
                    
                    restaurant_id = add_restaurant(title, cuisine_str, area, google_map_link, added_by, picture_bytes)
                    
                    if restaurant_id:
                        # Add the first review
                        if comments:
                            add_review(restaurant_id, added_by, rating, comments)
                        
                        st.success(f"✅ Successfully added **{title}** to your tracker!")
                        st.balloons()
                else:
                    st.error("⚠️ Please fill out all required fields (marked with *)")

# --- Search & View Page ---
elif page == "🔍 Search & View":
    st.title("🔍 Find Your Next Meal")
    
    # Get users dynamically
    users = get_all_users()
    
    # Search filters
    with st.container():
        col1, col2, col3 = st.columns([2, 2, 1])
        
        df_all = fetch_all_restaurants()
        all_areas = ['All Areas'] + sorted(df_all['area'].unique().tolist()) if not df_all.empty else ['All Areas']
        all_cuisines_raw = ['All Cuisines'] + sorted(df_all['cuisines'].str.split(', ').explode().str.strip().unique().tolist()) if not df_all.empty else ['All Cuisines']
        
        with col1:
            selected_area = st.selectbox("📍 Filter by Area", options=all_areas)
        
        with col2:
            selected_cuisine = st.selectbox("🍜 Filter by Cuisine", options=all_cuisines_raw)
        
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            search_clicked = st.button("🔍 Search", use_container_width=True)
    
    st.markdown("---")
    
    # Auto-search on page load or when button clicked
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
                    
                    # Display average rating
                    if row['avg_rating'] > 0:
                        st.markdown(display_star_rating(row['avg_rating']) + f" ({int(row['review_count'])} reviews)")
                    else:
                        st.markdown("⭐ No reviews yet")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"**🍜 Cuisines:** {row['cuisines']}")
                        st.markdown(f"**📍 Area:** {row['area']}")
                    with col_b:
                        if row['added_by']:
                            st.markdown(f"**👤 Added by:** {row['added_by']}")
                    
                    # Action buttons
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        st.markdown(f"[🗺️ View on Google Maps]({row['google_map_link']})")
                    with btn_col2:
                        if st.button("✏️ Add Review", key=f"review_btn_{row['id']}", type="secondary"):
                            st.session_state[f'show_review_form_{row["id"]}'] = True
                    
                    # Show review form if button clicked
                    if st.session_state.get(f'show_review_form_{row["id"]}', False):
                        if not users:
                            st.warning("⚠️ No users available. Please add users in 'Manage Users' section.")
                        else:
                            with st.form(key=f"review_form_{row['id']}"):
                                st.markdown("#### Add Your Review")
                                
                                review_col1, review_col2 = st.columns(2)
                                with review_col1:
                                    reviewer_name = st.selectbox(
                                        "Your Name",
                                        options=users,
                                        key=f"reviewer_{row['id']}"
                                    )
                                with review_col2:
                                    rating = st.slider("Rating", 1, 5, 3, key=f"rating_{row['id']}")
                                
                                comment = st.text_area("Your Review", placeholder="Share your experience...", key=f"comment_{row['id']}")
                                
                                submit_review = st.form_submit_button("Submit Review")
                                
                                if submit_review:
                                    if add_review(row['id'], reviewer_name, rating, comment):
                                        st.success("✅ Review added successfully!")
                                        st.session_state[f'show_review_form_{row["id"]}'] = False
                                        st.rerun()
                    
                    # Display existing reviews
                    reviews_df = get_reviews_for_restaurant(row['id'])
                    
                    if not reviews_df.empty:
                        with st.expander(f"📝 View All Reviews ({len(reviews_df)})"):
                            for _, review in reviews_df.iterrows():
                                review_date = pd.to_datetime(review['review_date']).strftime('%d %B %Y')
                                st.markdown(f"""
                                <div class="review-box">
                                    <strong>{review['reviewer_name']}</strong> {display_star_rating(review['rating'])}<br>
                                    <small style="color: gray;">📅 {review_date}</small><br>
                                    <p style="margin-top: 10px;">{review['comment']}</p>
                                </div>
                                """, unsafe_allow_html=True)
                
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
                    
                    # Display average rating
                    if row['avg_rating'] > 0:
                        st.markdown(display_star_rating(row['avg_rating']) + f" ({int(row['review_count'])} reviews)")
                    
                    st.markdown(f"**🍜 Cuisines:** {row['cuisines']}")
                    st.markdown(f"**📍 Area:** {row['area']}")
                    
                    # Display reviews
                    reviews_df = get_reviews_for_restaurant(row['id'])
                    if not reviews_df.empty:
                        with st.expander(f"💭 View Reviews ({len(reviews_df)})"):
                            for _, review in reviews_df.iterrows():
                                review_date = pd.to_datetime(review['review_date']).strftime('%d %B %Y')
                                st.markdown(f"""
                                <div class="review-box">
                                    <strong>{review['reviewer_name']}</strong> {display_star_rating(review['rating'])}<br>
                                    <small style="color: gray;">📅 {review_date}</small><br>
                                    <p style="margin-top: 10px;">{review['comment']}</p>
                                </div>
                                """, unsafe_allow_html=True)
                    
                    if row['added_by']:
                        st.caption(f"👤 Added by: {row['added_by']}")
                    
                    st.markdown(f"[🗺️ View Map]({row['google_map_link']})")
                
                with col3:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    if st.button("🗑️ Delete", key=f"delete_{row['id']}", help=f"Delete {row['title']}", type="secondary"):
                        if delete_restaurant(row['id']):
                            st.success(f"✅ Deleted **{row['title']}**!")
                            st.rerun()
                
                st.markdown("---")

# --- Manage Users Page ---
elif page == "👥 Manage Users":
    st.title("👥 Manage Users")
    st.markdown("Add or remove users who can add restaurants and reviews")
    
    # Add new user section
    st.subheader("➕ Add New User")
    with st.form("add_user_form"):
        new_user_name = st.text_input("User Name", placeholder="Enter user name")
        submit_user = st.form_submit_button("Add User")
        
        if submit_user:
            if new_user_name and new_user_name.strip():
                if add_user(new_user_name.strip()):
                    st.success(f"✅ Successfully added user **{new_user_name}**!")
                    st.rerun()
            else:
                st.error("⚠️ Please enter a valid user name")
    
    st.markdown("---")
    
    # Display existing users
    st.subheader("📋 Current Users")
    users = get_all_users()
    
    if not users:
        st.info("No users found. Add your first user above!")
    else:
        st.success(f"Total Users: **{len(users)}**")
        
        # Display users in a grid
        cols_per_row = 3
        for i in range(0, len(users), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                if i + j < len(users):
                    user = users[i + j]
                    with col:
                        with st.container():
                            st.markdown(f"### 👤 {user}")
                            if st.button("🗑️ Remove", key=f"delete_user_{user}", type="secondary", use_container_width=True):
                                if delete_user(user):
                                    st.success(f"✅ Removed user **{user}**!")
                                    st.rerun()
                            st.markdown("---")