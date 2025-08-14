import streamlit as st
import os

def load_css(file_path: str):
    """Load CSS file and inject into Streamlit"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            css = f.read()
        st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        # Silently skip missing files
        pass
    except Exception as e:
        st.error(f"Error loading CSS: {e}")

def load_theme():
    """Load the complete theme with all enhancements"""
    styles_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'styles')
    
    # Load main theme
    load_css(os.path.join(styles_dir, 'theme.css'))
    
    # Load accessibility enhancements
    load_css(os.path.join(styles_dir, 'accessibility.css'))
    
    # Load modern UX patterns
    load_css(os.path.join(styles_dir, 'modern-patterns.css'))
    
    # Skip link removed as requested