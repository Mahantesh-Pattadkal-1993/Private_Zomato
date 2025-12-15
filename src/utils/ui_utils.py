import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
from io import BytesIO
from PIL import Image
from datetime import datetime

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

def display_star_rating(rating):
    """Display star rating."""
    full_stars = int(rating)
    half_star = 1 if rating - full_stars >= 0.5 else 0
    empty_stars = 5 - full_stars - half_star
    
    stars = "⭐" * full_stars + "✨" * half_star + "☆" * empty_stars
    return f"{stars} ({rating:.1f})"
