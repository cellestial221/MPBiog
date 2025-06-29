import streamlit as st
import os
from docx import Document
import io
import asyncio
import json
import time
from datetime import datetime, timedelta
import bcrypt
import requests
from difflib import SequenceMatcher
from functools import lru_cache
import anthropic
import base64
from PIL import Image
from mp_functions import (
    read_example_bios,
    get_mp_id,
    get_mp_data,
    get_wiki_data_verified,    # ← Changed
    get_wiki_url_verified,
    generate_biography,
    save_biography,
    get_verified_positions,
    search_perplexity
)

favicon = Image.open("favicon2.png")

# Set page config
st.set_page_config(page_title="MP Biography Generator", page_icon=favicon, layout="wide")

# Create necessary folders
os.makedirs('uploads', exist_ok=True)
os.makedirs('new_bios', exist_ok=True)
os.makedirs('example_bios', exist_ok=True)


def get_logo_base64(image_path):
    """Convert logo image to base64 string"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return None

def inject_custom_css():
    """Inject custom CSS for professional branding - CLEANED UP VERSION"""
    st.markdown("""
    <style>
    /* Import better font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global styling */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Simple biography length button styling */
    button[key^="select_length"] {
        border: 2px solid #e6e9ef !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        background: white !important;
        min-height: 120px !important;
        color: #333 !important;
        transition: all 0.3s ease !important;
    }

    button[key^="select_length"]:hover {
        border-color: #00A199 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(0, 161, 153, 0.15) !important;
    }

    button[key^="select_length"][kind="primary"] {
        border-color: #00A199 !important;
        background: linear-gradient(135deg, rgba(0, 161, 153, 0.05) 0%, rgba(34, 67, 71, 0.05) 100%) !important;
        box-shadow: 0 0 0 3px rgba(0, 161, 153, 0.1) !important;
        color: #00A199 !important;
    }
    /* Progress indicator - ULTRA COMPACT VERSION */
    .progress-section {
        background: linear-gradient(135deg, #224347 0%, #00A199 100%);
        color: white;
        padding: 0.75rem 1rem;  /* Very compact padding */
        border-radius: 6px;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 4px rgba(34, 67, 71, 0.2);
    }

    .progress-title {
        font-weight: 600;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;  /* Smaller title */
    }

    .progress-steps {
        display: flex;
        justify-content: space-between;
        margin-bottom: 0.5rem;
        gap: 0.25rem;
    }

    .progress-step {
        flex: 1;
        text-align: center;
        font-size: 0.7rem;  /* Smaller text */
        max-width: 25%;
        line-height: 1.2;  /* Tighter line height */
    }

    .step-circle {
        width: 20px;  /* Even smaller circles */
        height: 20px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.2);
        color: rgba(255, 255, 255, 0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 0.2rem;  /* Minimal margin */
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.3);  /* Thinner border */
        font-size: 0.7rem;
    }

    .step-circle.active {
        background: white !important;
        color: #224347 !important;
        border-color: white !important;
    }

    .step-circle.completed {
        background: rgba(255, 255, 255, 0.9) !important;
        color: #224347 !important;
        border-color: rgba(255, 255, 255, 0.9) !important;
    }

    .progress-bar {
        height: 3px;  /* Very thin progress bar */
        background: rgba(255, 255, 255, 0.2);
        border-radius: 1.5px;
        overflow: hidden;
    }

    .progress-fill {
        height: 100%;
        background: white;
        border-radius: 1.5px;
        transition: width 0.3s ease;
    }

    /* Custom header styling */
    .custom-header {
        background: linear-gradient(90deg, #224347 0%, #00A199 100%);
        color: white;
        padding: 1.5rem 2rem;
        margin: -1rem -1rem 2rem -1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .header-left {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .company-logo {
        width: 50px;
        height: 50px;
        border: 2px dashed rgba(255, 255, 255, 0.5);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.7rem;
        text-align: center;
        line-height: 1.1;
        background: rgba(255, 255, 255, 0.1);
        color: white;
        font-weight: 600;
    }

    /* Section styling - REMOVE GREY BACKGROUND */
    .section-container {
        background: transparent;  /* Changed from #fafafa */
        border: none;  /* Changed from 1px solid #e6e9ef */
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .app-title {
        font-size: 1.4rem;
        font-weight: 600;
        color: white;
    }

    .header-right {
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.9);
    }

    .header-right a {
        color: rgba(255, 255, 255, 0.8);
        text-decoration: none;
        margin-left: 1rem;
    }

    .header-right a:hover {
        color: white;
    }

    /* Section styling */
    .section-container {
        background: #fafafa;
        border: 1px solid #e6e9ef;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .section-header {
        color: #224347;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #00A199;
    }

    /* MP Selection styling */
    .mp-selected {
        background: linear-gradient(135deg, #224347 0%, #00A199 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }

    .mp-name {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }

    .mp-details {
        opacity: 0.9;
        font-size: 0.95rem;
    }

    /* Button styling */
    button[kind="primaryFormSubmit"] {
        background: linear-gradient(90deg, #224347, #00A199) !important;
        color: white !important;
        border: 1px solid #00A199 !important;
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        min-height: 2.5rem !important;
        box-shadow: 0 2px 4px rgba(34, 67, 71, 0.2) !important;
    }

    button[kind="primaryFormSubmit"]:hover {
        background: linear-gradient(90deg, #1a3437, #008b85) !important;
        border-color: #008b85 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(34, 67, 71, 0.3) !important;
    }

    div.stButton > button:first-child {
        background: linear-gradient(90deg, #224347, #00A199) !important;
        color: white !important;
        border: 1px solid #00A199 !important;
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        margin-bottom: 0.5rem !important;
        box-shadow: 0 2px 4px rgba(34, 67, 71, 0.2) !important;
    }

    .step-circle.disabled {
        background: rgba(255, 255, 255, 0.1) !important;
        color: rgba(255, 255, 255, 0.3) !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        cursor: not-allowed !important;
    }

    div.stButton > button:first-child:hover {
        background: linear-gradient(90deg, #1a3437, #008b85) !important;
        border-color: #008b85 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(34, 67, 71, 0.3) !important;
    }

    /* Input field styling - CONSOLIDATED */
    .stTextInput > div > div > input {
        border: 2px solid #e6e9ef !important;
        border-radius: 8px !important;
        padding: 0.75rem !important;
        font-size: 1rem !important;
        transition: border-color 0.2s ease !important;
        background: white !important;
        color: #333333 !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #00A199 !important;
        box-shadow: 0 0 0 3px rgba(0, 161, 153, 0.1) !important;
        outline: none !important;
    }

    /* Remove conflicting borders */
    div[data-testid="stTextInputRootElement"] {
        border: none !important;
        background: transparent !important;
    }

    div[data-baseweb="base-input"] {
        border: none !important;
        background: transparent !important;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .block-container {
        padding-top: 1rem;
    }

    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .progress-steps {
            flex-direction: column;
            gap: 1rem;
        }

        .custom-header {
            padding: 1rem;
            flex-direction: column;
            gap: 1rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)#

def force_css_reload():
    """Force CSS to reload properly"""
    # Force CSS injection with a unique key
    st.markdown(f"""
    <style id="custom-css-{hash('unique')}">
    /* Force reload by adding unique identifier */
    </style>
    """, unsafe_allow_html=True)

    # Call your CSS injection
    inject_custom_css()


def debug_empty_containers():
    """Debug function to identify empty containers"""
    st.write("**DEBUG: Looking for empty containers...**")

    # Check if you have any empty containers
    st.markdown("""
    <div style="border: 2px solid red; padding: 10px; margin: 10px;">
        DEBUG: This should show as a red border box
    </div>
    """, unsafe_allow_html=True)


def debug_css():
    """Debug function to test CSS"""
    st.markdown("""
    <div style="background: red; color: white; padding: 1rem;">
        TEST: If you see this with red background, basic CSS works
    </div>

    <div class="progress-section">
        <div class="progress-title">TEST: If you see this styled, progress CSS works</div>
    </div>
    """, unsafe_allow_html=True)

def create_mp_selection_section():
    """Clean MP selection without grey boxes"""

    selected_mp = st.session_state.get('selected_mp')

    if selected_mp:
        # Clean, styled display without containers
        st.success(f"**{selected_mp['name']}** ({selected_mp['party']}) - {selected_mp['constituency']}")

        if st.button("🔄 Change MP Selection", key="change_mp_clean"):
            st.session_state.selected_mp = None
            st.session_state.mp_search_query = ''
            st.session_state.show_suggestions = False
            st.session_state.validation_result = None
            st.rerun()
    else:
        # Show MP search interface
        mp_name_input_with_validation()

def styled_login_page():
    """Complete replacement for the login section with restructured layout"""
    inject_custom_css()

    # Get logo as base64
    logo_base64 = get_logo_base64("logo.png")  # Replace with your logo filename

    # Create logo HTML - either image or fallback
    if logo_base64:
        logo_html = f'<img src="data:image/png;base64,{logo_base64}" style="width: 50px; height: 56px; border-radius: 0px;" alt="Logo">'
    else:
        logo_html = '<div class="login-logo">YOUR<br>LOGO</div>'

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Combined header section (logo + title) - clean HTML
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="width: 70px; height: 70px; margin: 0 auto 1.5rem; display: flex; align-items: center; justify-content: center; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border: 1px solid #e6e9ef;">
                {logo_html}
            </div>
            <div style="color: #224347; font-size: 1.5rem; font-weight: 600; margin: 0 0 0.5rem 0; font-family: 'Inter', sans-serif; text-align: center; width: 100%; padding: 0;">MP Biography Generator</div>
            <p style="color: #6c757d; font-size: 0.95rem; margin: 0; text-align: center; width: 100%; padding: 0;">Please log in to continue</p>
        </div>
        """, unsafe_allow_html=True)

        # Simple login form without custom container
        with st.form("login_form"):
            st.markdown("### Login")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_button = st.form_submit_button("Login", type="primary", use_container_width=True)

            if login_button:
                if check_password(username, password):
                    st.session_state.authenticated = True
                    st.session_state.name = st.secrets["credentials"]["usernames"][username]["name"]
                    st.session_state.username = username
                    st.session_state.email = st.secrets["credentials"]["usernames"][username]["email"]
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")


def generate_biography_flow(selected_mp, user_input, comments):
    """Handle the complete biography generation flow with progress - FIXED KEYS"""

    # Reset generation flag with different name
    st.session_state.generation_cancelled = False

    # Create progress container
    progress_container = st.container()

    with progress_container:
        # Cancel button with unique key
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("❌ Cancel", type="secondary", key="cancel_bio_generation"):
                st.session_state.generation_cancelled = True
                st.warning("Generation cancelled.")
                return

        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        details_expander = st.expander("📋 Generation Details", expanded=False)

        try:
            mp_name = selected_mp['name']
            mp_id = selected_mp['id']

            # Step 1: Read example biographies (10%)
            status_text.text('📚 Reading example biographies...')
            progress_bar.progress(10)

            if st.session_state.generation_cancelled:
                return

            with details_expander:
                st.write("✅ Loading example biography templates")

            examples = read_example_bios()

            # Step 2: Get verified parliamentary positions (25%)
            status_text.text('🏛️ Fetching verified parliamentary positions...')
            progress_bar.progress(25)

            if st.session_state.generation_cancelled:
                return

            verified_positions = None
            try:
                verified_positions = get_verified_positions(mp_id)
                with details_expander:
                    if verified_positions:
                        st.write("✅ Retrieved parliamentary API data")
                        if verified_positions.get('current_committees'):
                            st.write(f"  - Found {len(verified_positions['current_committees'])} current committee memberships")
                        if verified_positions.get('current_roles'):
                            st.write(f"  - Found {len(verified_positions['current_roles'])} current government/opposition roles")
                    else:
                        st.write("⚠️ No parliamentary API data available")
            except Exception as e:
                with details_expander:
                    st.write(f"⚠️ Parliament API error: {str(e)}")

            # Step 3: Get Wikipedia data (45%)
            status_text.text('📖 Fetching Wikipedia information...')
            progress_bar.progress(45)

            if st.session_state.generation_cancelled:
                return

            wiki_data = None
            wiki_url = None
            try:
                wiki_data = get_wiki_data_verified(selected_mp['name'], selected_mp['constituency'])
                if wiki_data:
                    wiki_url = get_wiki_url_verified(selected_mp['name'], selected_mp['constituency'])
                    with details_expander:
                        st.write(f"✅ Wikipedia data retrieved ({len(wiki_data)} characters)")
                else:
                    with details_expander:
                        st.write("⚠️ No verified Wikipedia page found")
            except Exception as e:
                with details_expander:
                    st.write(f"⚠️ Wikipedia error: {str(e)}")

            # Step 4: Prepare input content (60%)
            status_text.text('📝 Preparing biography content...')
            progress_bar.progress(60)

            if st.session_state.generation_cancelled:
                return

            # Combine all input sources
            input_content = user_input if user_input else ""

            if not input_content and wiki_data:
                input_content = wiki_data

            if not input_content:
                st.error("❌ No information found for this MP. Please add additional information and try again.")
                return

            with details_expander:
                st.write(f"✅ Content prepared: {len(input_content)} characters")
                if comments:
                    st.write(f"✅ Including {len(comments)} additional comments")

            # Step 5: Generate biography with Claude (80%)
            status_text.text('🤖 Generating biography with Claude AI...')
            progress_bar.progress(80)

            if st.session_state.generation_cancelled:
                return

            # Get length setting
            length_setting = st.session_state.get('length_setting', 'medium')

            with details_expander:
                st.write(f"✅ Generating {length_setting} biography...")

            biography = generate_biography(
                mp_name,
                input_content,
                examples,
                verified_positions,
                comments,
                length_setting
            )

            # Step 6: Save biography (95%)
            status_text.text('💾 Saving biography...')
            progress_bar.progress(95)

            if st.session_state.generation_cancelled:
                return

            saved_path = save_biography(
                mp_name,
                biography,
                comments,
                has_pdf=False,
                has_api_data=bool(verified_positions),
                has_wiki_data=bool(wiki_data),
                wiki_url=wiki_url
            )

            # Step 7: Complete (100%)
            progress_bar.progress(100)
            status_text.text('✅ Biography generation complete!')

            # Mark as generated for progress indicator
            st.session_state.biography_generated = True

            # Prepare file for download
            with open(saved_path, 'rb') as file:
                bio_bytes = file.read()

            # Success message and download
            st.success(f'🎉 {length_setting.title()} biography generated successfully!')

            # Download button
            st.download_button(
                label=f"📥 Download {length_setting.title()} Biography",
                data=bio_bytes,
                file_name=f"{mp_name}_{length_setting}_biography.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
                use_container_width=True
            )

            # Show generation summary
            with st.expander("📊 Generation Summary", expanded=True):
                st.write("**Data Sources Used:**")
                if user_input:
                    st.write("✅ User-provided information")
                if verified_positions:
                    st.write("✅ Parliament API data")
                if wiki_data:
                    st.write("✅ Wikipedia information")
                if comments:
                    st.write(f"✅ {len(comments)} additional comments")

                st.write(f"**Biography Length:** {length_setting.title()}")
                st.write(f"**Generated:** {datetime.now().strftime('%d %B %Y at %H:%M')}")

        except Exception as e:
            st.error(f"❌ Generation failed: {str(e)}")
            with details_expander:
                st.write(f"❌ Error details: {str(e)}")
            # Reset generation flag
            st.session_state.biography_generated = False

def create_enhanced_sidebar():
    """Enhanced sidebar with parliamentary positions and status"""
    with st.sidebar:
        # Account section
        st.header("👤 Account")
        st.write(f"Welcome, **{st.session_state.get('name', 'User')}**")
        if st.button('🚪 Logout', key="logout_enhanced"):
            st.session_state.authenticated = False
            st.rerun()

        st.divider()

        # Selected MP Info & Verified Positions
        selected_mp = st.session_state.get('selected_mp')
        if selected_mp:
            st.header("🏛️ Selected MP")
            st.write(f"**{selected_mp['name']}**")
            st.write(f"{selected_mp['party']} • {selected_mp['constituency']}")

            # Get and display verified positions
            with st.spinner("Loading parliamentary data..."):
                try:
                    verified_positions = get_verified_positions(selected_mp['id'])
                    if verified_positions:
                        st.subheader("Current Positions")

                        # Current committees
                        if verified_positions.get('current_committees'):
                            st.write("**Committee Memberships:**")
                            for committee in verified_positions['current_committees'][:3]:  # Show max 3
                                st.write(f"• {committee['name']}")
                            if len(verified_positions['current_committees']) > 3:
                                st.write(f"• ... and {len(verified_positions['current_committees']) - 3} more")

                        # Current roles
                        if verified_positions.get('current_roles'):
                            st.write("**Government/Opposition Roles:**")
                            for role in verified_positions['current_roles']:
                                st.write(f"• {role['name']}")

                        if not verified_positions.get('current_committees') and not verified_positions.get('current_roles'):
                            st.info("No current official positions")

                    else:
                        st.info("No parliamentary data available")
                except Exception as e:
                    st.warning("Could not load parliamentary data")

            st.divider()

        # Biography Status
        st.header("📊 Biography Status")

        # Data sources
        st.write("**Available Data Sources:**")
        sources = []

        # User input
        if st.session_state.get('additional_info', '').strip():
            sources.append("✅ User information")
        else:
            sources.append("○ User information")

        # Hansard comments
        hansard_count = len(st.session_state.get('hansard_comments_added', []))
        if hansard_count > 0:
            sources.append(f"✅ {hansard_count} Hansard records")
        else:
            sources.append("○ Hansard records")

        # Manual comments
        manual_count = len(st.session_state.get('manual_comments_added', []))
        if manual_count > 0:
            sources.append(f"✅ {manual_count} manual comments")
        else:
            sources.append("○ Manual comments")

        # Parliament API
        if selected_mp:
            sources.append("✅ Parliament API")
        else:
            sources.append("○ Parliament API")

        # Wikipedia
        sources.append("✅ Wikipedia (auto)")

        for source in sources:
            st.write(source)

        st.divider()

        # API Status
        st.header("🔗 API Status")

        # Anthropic
        st.write("✅ **Claude AI:** Ready")

        # Hansard API
        try:
            hansard_test = requests.get("https://hansard-api.parliament.uk/overview/firstyear.json", timeout=2)
            if hansard_test.status_code == 200:
                st.write("✅ **Hansard API:** Available")
            else:
                st.write("⚠️ **Hansard API:** Limited")
        except:
            st.write("❌ **Hansard API:** Unavailable")

        # Parliament API
        if selected_mp:
            st.write("✅ **Parliament API:** Connected")
        else:
            st.write("○ **Parliament API:** Waiting for MP")

        st.divider()

        # Quick Actions
        st.header("⚡ Quick Actions")

        if st.button("🗑️ Clear All Data", key="clear_all_data"):
            # Clear all user data
            keys_to_clear = [
                'selected_mp', 'mp_search_query', 'show_suggestions',
                'validation_result', 'hansard_comments_added',
                'manual_comments_added', 'additional_info', 'biography_generated'
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]

            # Clear cache
            cached_search_mps.cache_clear()
            st.success("All data cleared!")
            st.rerun()

        if st.button("🔄 Clear Cache", key="clear_cache_enhanced"):
            cached_search_mps.cache_clear()
            st.success("Cache cleared!")

def create_manual_comments_section():
    """Manual comments section - separate interface"""
    st.subheader("💬 Add Manual Comments")

    # Back button
    if st.button("← Back to Actions", key="back_from_manual_comments"):
        st.session_state.show_manual_comments = False
        st.rerun()

    st.write("Add comments or statements from sources other than parliamentary records.")

    # Initialize session state
    if 'manual_comments_added' not in st.session_state:
        st.session_state.manual_comments_added = []
    if 'manual_comment_count' not in st.session_state:
        st.session_state.manual_comment_count = 1

    # Show existing comments
    existing_comments = st.session_state.get('manual_comments_added', [])
    if existing_comments:
        st.write(f"**📋 Added Comments ({len(existing_comments)}):**")

        for i, comment in enumerate(existing_comments):
            with st.container():
                col1, col2 = st.columns([4, 1])

                with col1:
                    st.write(f"**{i+1}. {comment['type']}** ({comment['date']})")
                    if comment.get('url'):
                        st.markdown(f"🔗 [Source]({comment['url']})")

                    preview = comment['text'][:150] + "..." if len(comment['text']) > 150 else comment['text']
                    st.write(preview)

                with col2:
                    if st.button("🗑️", key=f"remove_manual_{i}", help="Remove this comment"):
                        st.session_state.manual_comments_added.pop(i)
                        st.rerun()

                st.divider()

    # Add new comment form
    st.write("**➕ Add New Comment:**")

    with st.form("manual_comment_form"):
        comment_type = st.selectbox(
            "Source Type",
            options=[
                "Social Media Post",
                "Written Question",
                "Interview/Speech",
                "Press Release",
                "Newsletter/Blog",
                "Other"
            ]
        )

        comment_url = st.text_input(
            "Source URL (Optional)",
            placeholder="https://..."
        )

        comment_date = st.date_input(
            "Date of Comment",
            value=datetime.now().date()
        )

        comment_text = st.text_area(
            "Comment Text",
            height=120,
            placeholder="Enter the comment or statement here..."
        )

        submit_comment = st.form_submit_button("➕ Add Comment", type="primary", use_container_width=True)

        if submit_comment and comment_text:
            new_comment = {
                "type": comment_type,
                "url": comment_url,
                "date": comment_date.strftime("%Y-%m-%d"),
                "text": comment_text
            }

            st.session_state.manual_comments_added.append(new_comment)
            st.success("✅ Comment added!")
            st.rerun()

    # Actions
    if existing_comments:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear All", key="clear_all_manual"):
                st.session_state.manual_comments_added = []
                st.success("All manual comments cleared!")
                st.rerun()
        with col2:
            if st.button("✅ Done", key="done_manual_comments", type="primary"):
                st.session_state.show_manual_comments = False
                st.rerun()


def test_hansard_api_simple():
    """Simplified test function to debug Hansard API issues - no expanders"""
    st.subheader("🧪 Hansard API Debug")

    # Test 1: Basic API connectivity
    st.write("**Test 1: Basic API Connectivity**")
    if st.button("Test Basic API", key="test_basic"):
        try:
            test_url = "https://hansard-api.parliament.uk/overview/firstyear.json"
            response = requests.get(test_url, timeout=5)
            st.write(f"Status: {response.status_code}")
            st.write(f"Response: {response.text}")
            if response.status_code == 200:
                st.success("✅ Hansard API is accessible")
            else:
                st.error("❌ Hansard API not responding correctly")
        except Exception as e:
            st.error(f"❌ API Error: {str(e)}")

    st.divider()

    # Test 2: Search for contributions
    st.write("**Test 2: Search Contributions**")
    test_mp_id = st.text_input("Enter MP ID to test (e.g., 1423):", value="1423", key="test_mp_id")
    if st.button("Test Search", key="test_search") and test_mp_id:
        try:
            url = "https://hansard-api.parliament.uk/search/contributions/Spoken.json"
            params = {
                'queryParameters.memberId': test_mp_id,
                'queryParameters.take': 5,
                'queryParameters.orderBy': 'SittingDateDesc'
            }

            response = requests.get(url, params=params, timeout=10)
            st.write(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                st.success(f"✅ Found {len(data.get('Results', []))} contributions")

                if data.get('Results'):
                    first_result = data['Results'][0]
                    st.write("**First result sample:**")
                    st.json({
                        'ContributionExtId': first_result.get('ContributionExtId'),
                        'MemberName': first_result.get('MemberName'),
                        'DebateSection': first_result.get('DebateSection'),
                        'SittingDate': first_result.get('SittingDate'),
                        'ContributionText': first_result.get('ContributionText', '')[:200] + "..."
                    })

                    # Store the first contribution ID for testing
                    if 'test_contribution_id' not in st.session_state:
                        st.session_state.test_contribution_id = first_result.get('ContributionExtId', '')
                    st.info(f"💡 Stored contribution ID for redirect test: {st.session_state.test_contribution_id}")
            else:
                st.error(f"❌ Search failed: {response.status_code}")
                st.code(response.text)
        except Exception as e:
            st.error(f"❌ Search Error: {str(e)}")

    st.divider()

    # Test 3: Test redirect API
    st.write("**Test 3: Test Redirect API**")
    test_ext_id = st.text_input(
        "Enter Contribution External ID to test:",
        value=st.session_state.get('test_contribution_id', ''),
        key="test_ext_id"
    )
    if st.button("Test Redirect", key="test_redirect") and test_ext_id:
        try:
            url = "https://hansard-api.parliament.uk/search/parlisearchredirect.json"
            params = {'externalId': test_ext_id}

            response = requests.get(url, params=params, timeout=5)
            st.write(f"Status: {response.status_code}")
            st.write(f"Response: {response.text}")

            if response.status_code == 200:
                hansard_url = response.text.strip().strip('"')
                if hansard_url and hansard_url.startswith('http'):
                    st.success(f"✅ Got URL: {hansard_url}")
                    st.markdown(f"[Test this link]({hansard_url})")
                else:
                    st.warning(f"⚠️ Unexpected response format: {hansard_url}")
            else:
                st.error(f"❌ Redirect failed: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Redirect Error: {str(e)}")

    st.divider()

    # Test 4: Test fallback URL creation
    st.write("**Test 4: Test Fallback URL Creation**")
    if st.button("Test Fallback URLs", key="test_fallback"):
        if test_ext_id:
            from urllib.parse import quote

            # Test different URL patterns
            test_urls = [
                f"https://hansard.parliament.uk/Commons/{test_ext_id}",
                f"https://hansard.parliament.uk/debates/{test_ext_id}",
                f"https://hansard.parliament.uk/search/contributions?searchTerm={test_ext_id}",
                f"https://hansard.parliament.uk/search/Contributions?searchTerm={quote(test_ext_id)}"
            ]

            st.write("Testing these URL patterns:")
            for i, test_url in enumerate(test_urls):
                st.write(f"{i+1}. {test_url}")
                st.markdown(f"   [Test this link]({test_url})")
        else:
            st.warning("Please enter a contribution ID first")


def get_hansard_url(contribution_ext_id):
    """Get the web URL for a Hansard contribution using the redirect endpoint"""
    try:
        if not contribution_ext_id:
            return None

        url = "https://hansard-api.parliament.uk/search/parlisearchredirect.json"
        params = {'externalId': contribution_ext_id}

        response = requests.get(url, params=params, timeout=5)

        if response.status_code == 200:
            # The API returns the URL path as a string
            hansard_path = response.text.strip().strip('"')

            # Check if it's a relative URL (starts with /)
            if hansard_path and hansard_path.startswith('/'):
                # Convert relative URL to absolute URL
                hansard_url = f"https://hansard.parliament.uk{hansard_path}"
                return hansard_url

            # Check if it's already an absolute URL
            elif hansard_path and hansard_path.startswith('http'):
                return hansard_path

            # If we get something else, try to construct it
            elif hansard_path:
                # Some responses might not have the leading slash
                hansard_url = f"https://hansard.parliament.uk/{hansard_path.lstrip('/')}"
                return hansard_url

    except Exception as e:
        print(f"Error getting Hansard URL for {contribution_ext_id}: {str(e)}")

    return None
# NEW FUNCTIONS FOR HANSARD SEARCH
#
#
def create_configuration_section():
    """Clean configuration section"""
    st.subheader("Biography Configuration")

    # Length selection
    length_options = ["Brief", "Standard", "Comprehensive"]
    selected_length = st.selectbox("Biography Length:", length_options, index=1)
    st.session_state.length_setting = selected_length.lower()

    # Show description
    descriptions = {
        "Brief": "📝 Essential information only (2-3 short paragraphs)",
        "Standard": "📄 Comprehensive biography (default)",
        "Comprehensive": "📚 Extended detail with additional sections"
    }
    st.info(descriptions[selected_length])

    # Additional info
    st.text_area("Additional Information (Optional):", key="additional_info", height=100,
                placeholder="Add specific information about the MP's recent work, policy positions, etc.")

def create_hansard_search_section():
    """Hansard search interface integrated into main app"""
    st.subheader("🔍 Search Parliamentary Records")

    selected_mp = st.session_state.get('selected_mp')
    if not selected_mp:
        st.error("No MP selected")
        return

    # Back button
    if st.button("← Back to Actions", key="back_from_hansard"):
        st.session_state.show_hansard_search = False
        st.rerun()

    st.write(f"Search for **{selected_mp['name']}'s** parliamentary contributions on specific topics.")

    # Initialize session state for Hansard search
    if 'hansard_results' not in st.session_state:
        st.session_state.hansard_results = []
    if 'selected_hansard_items' not in st.session_state:
        st.session_state.selected_hansard_items = []
    if 'hansard_search_performed' not in st.session_state:
        st.session_state.hansard_search_performed = False
    if 'hansard_comments_added' not in st.session_state:
        st.session_state.hansard_comments_added = []

    # Search form
    with st.form("hansard_search_form_main"):
        issue_query = st.text_input(
            "What topic would you like to search for?",
            placeholder="e.g., climate change, healthcare, education funding, housing policy...",
            help="Describe the topic or issue you want to find the MP's statements about"
        )

        # Date range selection
        col1, col2 = st.columns(2)
        with col1:
            date_range = st.selectbox(
                "Time period",
                ["Last 6 months", "Last year", "Last 2 years", "All available"],
                index=1
            )
        with col2:
            max_results = st.slider("Maximum results", 5, 30, 15)

        search_button = st.form_submit_button("🔍 Search Hansard Records", type="primary", use_container_width=True)

    if search_button and issue_query:
        with st.spinner("Generating search terms and searching Hansard..."):
            # Generate search terms using Claude
            search_terms = generate_search_terms(issue_query, selected_mp['name'])

            if search_terms:
                st.success(f"Generated search terms: {', '.join(search_terms)}")

                # Calculate date range
                start_date = None
                end_date = datetime.now().strftime('%Y-%m-%d')

                if date_range == "Last 6 months":
                    start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
                elif date_range == "Last year":
                    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                elif date_range == "Last 2 years":
                    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

                # Search Hansard
                results = search_hansard_contributions(selected_mp['id'], search_terms, start_date, end_date, max_results)

                st.session_state.hansard_results = results
                st.session_state.hansard_search_performed = True

                if results:
                    st.success(f"Found {len(results)} relevant contributions!")
                else:
                    st.warning("No contributions found for this topic. Try different search terms or expand the date range.")

    # Display results if available
    if st.session_state.hansard_search_performed and st.session_state.hansard_results:
        st.subheader(f"📋 Search Results ({len(st.session_state.hansard_results)} found)")

        # Selection controls
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Select All", key="select_all_hansard_main"):
                st.session_state.selected_hansard_items = [item['id'] for item in st.session_state.hansard_results]
                st.rerun()
        with col2:
            if st.button("❌ Clear Selection", key="clear_all_hansard_main"):
                st.session_state.selected_hansard_items = []
                st.rerun()
        with col3:
            selected_count = len(st.session_state.selected_hansard_items)
            st.write(f"**Selected: {selected_count}**")

        # Display results
        for i, result in enumerate(st.session_state.hansard_results):
            with st.container():
                # Checkbox for selection
                is_selected = result['id'] in st.session_state.selected_hansard_items

                selected = st.checkbox(
                    f"Select this contribution",
                    value=is_selected,
                    key=f"hansard_select_main_{i}"
                )

                if selected and result['id'] not in st.session_state.selected_hansard_items:
                    st.session_state.selected_hansard_items.append(result['id'])
                elif not selected and result['id'] in st.session_state.selected_hansard_items:
                    st.session_state.selected_hansard_items.remove(result['id'])

                # Result display
                result_date = format_hansard_date(result['date'])
                st.markdown(f"**{result_date}** - {result['debate_title']}")
                st.caption(f"Found by search term: '{result['search_term']}'")

                # Show contribution text
                text_to_show = result['full_text'] if result['full_text'] else result['text']
                if len(text_to_show) > 400:
                    text_to_show = text_to_show[:400] + "..."

                st.write(text_to_show)

                # Add link if available
                if result.get('url'):
                    st.markdown(f"🔗 [View in Hansard]({result['url']})")

                st.divider()

        # Add selected items to comments
        if st.session_state.selected_hansard_items:
            if st.button(f"➕ Add {len(st.session_state.selected_hansard_items)} Selected Items",
                        type="primary", key="add_hansard_to_comments", use_container_width=True):
                # Convert selected results to comment format
                new_comments = []
                for result in st.session_state.hansard_results:
                    if result['id'] in st.session_state.selected_hansard_items:
                        hansard_comment = {
                            "type": "Parliamentary Remarks",
                            "url": result.get('url', ''),
                            "date": result['date'][:10] if result['date'] else datetime.now().strftime("%Y-%m-%d"),
                            "text": f"In {result['debate_title']} on {format_hansard_date(result['date'])}, {selected_mp['name']} said: \"{result['full_text'] if result['full_text'] else result['text']}\""
                        }
                        new_comments.append(hansard_comment)

                # Add to session state
                if 'hansard_comments_added' not in st.session_state:
                    st.session_state.hansard_comments_added = []
                st.session_state.hansard_comments_added.extend(new_comments)

                st.success(f"✅ Added {len(new_comments)} parliamentary contributions!")

                # Clear selections and hide search
                st.session_state.selected_hansard_items = []
                st.session_state.show_hansard_search = False
                st.rerun()

def create_hansard_management_section():
    """Manage added Hansard comments"""
    st.subheader("📋 Manage Hansard Comments")

    # Back button
    if st.button("← Back to Actions", key="back_from_hansard_mgmt"):
        st.session_state.show_hansard_management = False
        st.rerun()

    hansard_comments = st.session_state.get('hansard_comments_added', [])

    if not hansard_comments:
        st.info("No Hansard comments added yet.")
        return

    st.write(f"You have **{len(hansard_comments)}** parliamentary contributions added:")

    # Display each comment with option to remove
    for i, comment in enumerate(hansard_comments):
        with st.container():
            col1, col2 = st.columns([4, 1])

            with col1:
                st.write(f"**{i+1}. {comment['type']}** ({comment['date']})")
                if comment.get('url'):
                    st.markdown(f"🔗 [View in Hansard]({comment['url']})")

                # Show preview of text
                preview_text = comment['text'][:200] + "..." if len(comment['text']) > 200 else comment['text']
                st.write(preview_text)

            with col2:
                if st.button("🗑️", key=f"remove_hansard_{i}", help="Remove this comment"):
                    st.session_state.hansard_comments_added.pop(i)
                    st.rerun()

            st.divider()

    # Clear all button
    if st.button("🗑️ Clear All Hansard Comments", key="clear_all_hansard_comments", type="secondary"):
        st.session_state.hansard_comments_added = []
        st.success("All Hansard comments cleared!")
        st.rerun()


def create_actions_section():
    """Actions section with Hansard search and generation"""
    selected_mp = st.session_state.get('selected_mp')

    if not selected_mp:
        st.warning("Please select an MP first")
        return

    # Step 1: Hansard Search (Optional)
    st.write("**Step 1: Search Parliamentary Records (Optional)**")
    st.write("Find the MP's statements on specific topics from Hansard database.")

    if st.button("🔍 Search Hansard Records", type="secondary", key="start_hansard_search", use_container_width=True):
        st.session_state.show_hansard_search = True
        st.rerun()

    # Show Hansard count if any added
    hansard_count = len(st.session_state.get('hansard_comments_added', []))
    if hansard_count > 0:
        st.success(f"✅ {hansard_count} parliamentary contributions added")

        # Option to view/manage Hansard comments
        if st.button("📋 View Hansard Comments", key="view_hansard", use_container_width=True):
            st.session_state.show_hansard_management = True
            st.rerun()

    st.divider()

    # Step 2: Manual Comments (Optional)
    st.write("**Step 2: Add Manual Comments (Optional)**")
    st.write("Add comments from other sources like social media, interviews, etc.")

    if st.button("💬 Add Manual Comments", type="secondary", key="start_manual_comments", use_container_width=True):
        st.session_state.show_manual_comments = True
        st.rerun()

    # Show manual comment count
    manual_count = len(st.session_state.get('manual_comments_added', []))
    if manual_count > 0:
        st.success(f"✅ {manual_count} manual comments added")

    st.divider()

    # Step 3: Generate Biography
    st.write("**Step 3: Generate Biography**")

    # Show data summary
    data_summary = []
    user_input = st.session_state.get('additional_info', '').strip()

    if user_input:
        data_summary.append("User-provided information")
    if hansard_count > 0:
        data_summary.append(f"{hansard_count} Hansard contributions")
    if manual_count > 0:
        data_summary.append(f"{manual_count} manual comments")

    if data_summary:
        st.info(f"📊 Ready to generate with: {', '.join(data_summary)}")
    else:
        st.info("📊 Will use Parliament API and Wikipedia data")

    # Generation button
    if st.button("🚀 Generate Biography", type="primary", key="generate_biography_main", use_container_width=True):
        # Collect all comments
        all_comments = st.session_state.get('hansard_comments_added', []).copy()
        all_comments.extend(st.session_state.get('manual_comments_added', []))

        # Start generation flow
        generate_biography_flow(selected_mp, user_input, all_comments)


def generate_search_terms(issue_description, mp_name):
    """Use Claude Haiku to generate search terms for Hansard API"""
    try:
        client = anthropic.Client(api_key=os.getenv('ANTHROPIC_API_KEY'))

        prompt = f"""Given that a user wants to find parliamentary contributions by {mp_name} MP related to "{issue_description}", generate 3-5 specific search terms that would be effective for searching parliamentary records.

The search terms should be:
- Specific enough to find relevant content
- Varied to catch different ways the topic might be discussed
- Suitable for parliamentary/political context
- Be specific and related
- Be 1-2 words only

Format your response as a simple list of search terms, one per line, without numbers or bullets.

Example for "climate change":
climate change
net zero
carbon emissions
renewable energy

Now generate search terms for: {issue_description}"""

        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=200,
            temperature=0.7,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse the response to extract search terms
        search_terms = []
        for line in response.content[0].text.strip().split('\n'):
            term = line.strip()
            if term and not term.startswith('#') and not term.startswith('-'):
                search_terms.append(term)

        return search_terms[:5]  # Limit to 5 terms

    except Exception as e:
        st.error(f"Error generating search terms: {str(e)}")
        # Fallback to basic search term
        return [issue_description]



def create_custom_header():
    """Custom branded header to replace st.title"""
    user_name = st.session_state.get('name', 'User')

    st.markdown(f"""
    <div class="custom-header">
        <div class="header-left">
            <div class="company-logo">YOUR<br>LOGO</div>
            <div class="app-title">MP Biography Generator</div>
        </div>
        <div class="header-right">
            Welcome, {user_name} |
            <a href="javascript:void(0)" onclick="if(confirm('Are you sure you want to logout?')) {{
                window.location.reload();
            }}">Logout</a>
        </div>
    </div>
    """, unsafe_allow_html=True)


def create_hansard_search_inline():
    """Compact Hansard search with longer excerpts and pagination"""
    selected_mp = st.session_state.get('selected_mp')

    if st.button("← Close Search", key="close_hansard_search"):
        st.session_state.hansard_tab_mode = None
        st.rerun()

    # Initialize session state
    if 'hansard_results' not in st.session_state:
        st.session_state.hansard_results = []
    if 'selected_hansard_items' not in st.session_state:
        st.session_state.selected_hansard_items = []
    if 'hansard_search_page' not in st.session_state:
        st.session_state.hansard_search_page = 1

    # Search form with pagination info
    st.info("💡 **Note:** Hansard API limits results. We'll search with multiple terms to get comprehensive results.")

    with st.form("hansard_search_inline"):
        col1, col2 = st.columns([2, 1])
        with col1:
            issue_query = st.text_input("Topic to search for:", placeholder="e.g., climate change, healthcare...")
        with col2:
            date_range = st.selectbox("Period", ["Last 6 months", "Last year", "Last 2 years", "All available"])

        # Advanced options
        with st.expander("🔧 Advanced Options"):
            max_results_per_term = st.slider("Results per search term", 5, 20, 10, help="More terms = more total results")

        search_button = st.form_submit_button("🔍 Search", type="primary", use_container_width=True)

    if search_button and issue_query:
        with st.spinner("Generating search terms and searching Hansard..."):
            # Generate multiple search terms for better coverage
            search_terms = generate_search_terms(issue_query, selected_mp['name'])
            st.success(f"🔍 Searching with terms: {', '.join(search_terms)}")

            # Calculate date range
            start_date = None
            if date_range == "Last 6 months":
                start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
            elif date_range == "Last year":
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            elif date_range == "Last 2 years":
                start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

            # Search with higher limits and multiple terms
            results = search_hansard_contributions(
                selected_mp['id'],
                search_terms,
                start_date,
                datetime.now().strftime('%Y-%m-%d'),
                max_results_per_term * len(search_terms)  # Multiply by number of terms
            )
            st.session_state.hansard_results = results

            if results:
                st.success(f"✅ Found {len(results)} contributions across {len(search_terms)} search terms!")
                if len(results) >= max_results_per_term * len(search_terms):
                    st.warning("⚠️ Results may be limited by API. Try more specific search terms for better targeting.")
            else:
                st.warning("No contributions found. Try different terms or expand the date range.")

    # Show results with longer excerpts
    if st.session_state.hansard_results:
        st.write(f"**📋 Found {len(st.session_state.hansard_results)} Results:**")

        # Pagination for results
        results_per_page = 5
        total_pages = (len(st.session_state.hansard_results) - 1) // results_per_page + 1
        current_page = st.session_state.get('hansard_display_page', 1)

        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if current_page > 1:
                    if st.button("← Prev", key="prev_hansard_page"):
                        st.session_state.hansard_display_page = current_page - 1
                        st.rerun()
            with col2:
                st.write(f"Page {current_page} of {total_pages}")
            with col3:
                if current_page < total_pages:
                    if st.button("Next →", key="next_hansard_page"):
                        st.session_state.hansard_display_page = current_page + 1
                        st.rerun()

        # Show results for current page
        start_idx = (current_page - 1) * results_per_page
        end_idx = start_idx + results_per_page
        page_results = st.session_state.hansard_results[start_idx:end_idx]

        for i, result in enumerate(page_results):
            actual_idx = start_idx + i

            # Checkbox for selection
            selected = st.checkbox(
                f"Select this contribution",
                value=result['id'] in st.session_state.selected_hansard_items,
                key=f"hansard_inline_{actual_idx}"
            )

            if selected and result['id'] not in st.session_state.selected_hansard_items:
                st.session_state.selected_hansard_items.append(result['id'])
            elif not selected and result['id'] in st.session_state.selected_hansard_items:
                st.session_state.selected_hansard_items.remove(result['id'])

            # Show result with longer excerpt
            st.markdown(f"**{format_hansard_date(result['date'])}** - {result['debate_title']}")
            st.caption(f"Found by search term: '{result['search_term']}'")

            # Show longer excerpt - up to 600 characters
            text_to_show = result['full_text'] if result['full_text'] else result['text']
            if len(text_to_show) > 600:
                text_to_show = text_to_show[:600] + "..."

            st.write(text_to_show)

            # Add link if available
            if result.get('url'):
                st.markdown(f"🔗 [View full speech in Hansard]({result['url']})")

            st.divider()

        # Selection summary and add button
        selected_count = len(st.session_state.selected_hansard_items)
        if selected_count > 0:
            st.info(f"📌 {selected_count} contributions selected across all pages")

            if st.button(f"➕ Add {selected_count} Selected Contributions", type="primary", use_container_width=True):
                # Add selected items to comments
                new_comments = []
                for result in st.session_state.hansard_results:
                    if result['id'] in st.session_state.selected_hansard_items:
                        # Use longer text for the biography
                        full_text = result['full_text'] if result['full_text'] else result['text']
                        hansard_comment = {
                            "type": "Parliamentary Remarks",
                            "url": result.get('url', ''),
                            "date": result['date'][:10],
                            "text": f"In {result['debate_title']} on {format_hansard_date(result['date'])}, {selected_mp['name']} said: \"{full_text}\""
                        }
                        new_comments.append(hansard_comment)

                if 'hansard_comments_added' not in st.session_state:
                    st.session_state.hansard_comments_added = []
                st.session_state.hansard_comments_added.extend(new_comments)

                st.session_state.selected_hansard_items = []
                st.session_state.hansard_tab_mode = None
                st.session_state.hansard_display_page = 1
                st.success(f"✅ Added {len(new_comments)} parliamentary contributions!")
                st.rerun()


def create_hansard_management_inline():
    """Compact Hansard management for tab interface"""
    if st.button("← Close Management", key="close_hansard_mgmt"):
        st.session_state.hansard_tab_mode = None
        st.rerun()

    hansard_comments = st.session_state.get('hansard_comments_added', [])

    for i, comment in enumerate(hansard_comments):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{comment['type']}** ({comment['date']})")
            st.write(comment['text'][:100] + "...")
        with col2:
            if st.button("🗑️", key=f"remove_hansard_inline_{i}"):
                st.session_state.hansard_comments_added.pop(i)
                st.rerun()

def create_progress_indicator_navigation():
    """Interactive progress indicator with step navigation"""

    current_step = st.session_state.get('wizard_step', 1)

    # Determine which steps are accessible
    max_accessible_step = 1

    if st.session_state.get('selected_mp'):
        max_accessible_step = 2
    if st.session_state.get('selected_mp') and st.session_state.get('length_setting'):
        max_accessible_step = 3
    if st.session_state.get('biography_generated'):
        max_accessible_step = 4

    st.markdown(f"""
    <div class="progress-section">
        <div class="progress-title">Biography Creation Wizard</div>
        <div class="progress-steps">
            <div class="progress-step">
                <div class="step-circle {'completed' if current_step > 1 else 'active'}"
                     onclick="setStep(1)" style="cursor: pointer;">1</div>
                <div>Select MP</div>
            </div>
            <div class="progress-step">
                <div class="step-circle {'completed' if current_step > 2 else ('active' if current_step == 2 else ('disabled' if max_accessible_step < 2 else ''))}"
                     onclick="setStep(2)" style="cursor: {'pointer' if max_accessible_step >= 2 else 'not-allowed'};">2</div>
                <div>Configure</div>
            </div>
            <div class="progress-step">
                <div class="step-circle {'completed' if current_step > 3 else ('active' if current_step == 3 else ('disabled' if max_accessible_step < 3 else ''))}"
                     onclick="setStep(3)" style="cursor: {'pointer' if max_accessible_step >= 3 else 'not-allowed'};">3</div>
                <div>Add Information</div>
            </div>
            <div class="progress-step">
                <div class="step-circle {'completed' if current_step >= 4 else ('active' if current_step == 4 else ('disabled' if max_accessible_step < 4 else ''))}"
                     onclick="setStep(4)" style="cursor: {'pointer' if max_accessible_step >= 4 else 'not-allowed'};">4</div>
                <div>Generate & Download</div>
            </div>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {current_step * 25}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def wizard_step_1_select_mp():
    """Step 1: Select MP - FIXED to handle multiple matches properly"""
    st.header("Step 1: Select Member of Parliament")

    # Check if we already have a selected MP
    if st.session_state.get('selected_mp'):
        selected_mp = st.session_state.selected_mp
        st.success(f"✅ Selected: **{selected_mp['name']}** ({selected_mp['party']}) - {selected_mp['constituency']}")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("🔄 Change MP", key="change_mp_step1", use_container_width=True):
                # Clear selection and show search again
                for key in ['selected_mp', 'mp_search_query', 'show_suggestions', 'validation_result', 'mp_search_results']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

        with col3:
            if st.button("Next →", type="primary", key="step1_next", use_container_width=True):
                st.session_state.wizard_step = 2
                st.rerun()
        return

    # Check if we have search results to display
    if st.session_state.get('mp_search_results'):
        suggestions = st.session_state.mp_search_results
        search_query = st.session_state.get('mp_search_query', '')

        if len(suggestions) == 1:
            st.info(f"Found MP matching '{search_query}'. Please confirm:")
        else:
            st.info(f"Found {len(suggestions)} MPs matching '{search_query}'. Please select one:")

        # Display suggestions in a clean grid
        for i in range(0, len(suggestions), 2):
            cols = st.columns(2)

            for j, col in enumerate(cols):
                if i + j < len(suggestions):
                    suggestion = suggestions[i + j]

                    with col:
                        # Show MP info clearly
                        if st.button(
                            f"**{suggestion['name']}**",
                            key=f"suggestion_{i+j}",
                            use_container_width=True,
                            help=f"Select {suggestion['name']}"
                        ):
                            st.session_state.selected_mp = suggestion
                            st.session_state.mp_search_results = None  # Clear results
                            st.success(f"✅ Selected: {suggestion['name']}")
                            st.rerun()

                        # Show party and constituency below button
                        st.caption(f"{suggestion['party']} • {suggestion['constituency']}")

        # Option to search again
        st.divider()
        if st.button("🔍 Search Again", key="search_again", use_container_width=True):
            for key in ['mp_search_results', 'mp_search_query']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        return

    # MP search interface with submit button
    with st.form("mp_search_form"):
        search_query = st.text_input(
            "Search for MP name:",
            value=st.session_state.get('mp_search_query', ''),
            placeholder="e.g., Keir Starmer, Rishi Sunak, Angela Rayner...",
            help="Enter the MP's name (titles like 'Sir' are optional). Only current MPs in the House of Commons will be shown."
        )

        submit_search = st.form_submit_button("🔍 Search MPs", type="primary", use_container_width=True)

    # Process search when submitted
    if submit_search and search_query:
        st.session_state.mp_search_query = search_query

        with st.spinner('Searching MPs...'):
            validation_result = validate_mp_name(search_query)

        if validation_result['is_valid']:
            # Direct match found - auto-select only if very confident
            st.session_state.selected_mp = validation_result['exact_match']
            st.success(f"✅ Found exact match: {validation_result['exact_match']['name']}")
            st.rerun()

        elif validation_result['suggestions']:
            # Multiple matches - store for selection
            st.session_state.mp_search_results = validation_result['suggestions']
            st.rerun()
        else:
            # No matches found
            st.error(validation_result['message'])
            st.session_state.mp_search_results = None

    # Show search tips if no search performed yet
    if not submit_search and not st.session_state.get('mp_search_results'):
        with st.expander("💡 Search Tips"):
            st.write("""
            - Enter the MP's full name (e.g., "Keir Starmer")
            - You can search by surname only (e.g., "Starmer")
            - Handles titles automatically (Sir, Dame, etc.)
            - Shows suggestions if multiple matches found
            - **Only current MPs in the House of Commons are available**
            - Lords and peers are automatically excluded
            """)

def create_hansard_search_section_wizard():
    """Hansard search for wizard - fixed navigation"""
    st.subheader("🔍 Search Parliamentary Records")

    selected_mp = st.session_state.get('selected_mp')

    # Wizard-specific back button
    if st.button("← Back to Step 3", key="back_from_hansard_wizard"):
        st.session_state.show_hansard_search = False
        st.rerun()

    st.write(f"Search for **{selected_mp['name']}'s** parliamentary contributions on specific topics.")

    # Initialize session state for Hansard search
    if 'hansard_results' not in st.session_state:
        st.session_state.hansard_results = []
    if 'selected_hansard_items' not in st.session_state:
        st.session_state.selected_hansard_items = []
    if 'hansard_search_performed' not in st.session_state:
        st.session_state.hansard_search_performed = False
    if 'hansard_comments_added' not in st.session_state:
        st.session_state.hansard_comments_added = []

    # Search form
    with st.form("hansard_search_form_wizard"):
        issue_query = st.text_input(
            "What topic would you like to search for?",
            placeholder="e.g., climate change, healthcare, education funding, housing policy...",
        )

        col1, col2 = st.columns(2)
        with col1:
            date_range = st.selectbox(
                "Time period",
                ["Last 6 months", "Last year", "Last 2 years", "All available"],
                index=1
            )
        with col2:
            max_results = st.slider("Maximum results", 5, 30, 15)

        search_button = st.form_submit_button("🔍 Search Hansard Records", type="primary", use_container_width=True)

    if search_button and issue_query:
        with st.spinner("Generating search terms and searching Hansard..."):
            search_terms = generate_search_terms(issue_query, selected_mp['name'])

            if search_terms:
                st.success(f"Generated search terms: {', '.join(search_terms)}")

                # Calculate date range
                start_date = None
                end_date = datetime.now().strftime('%Y-%m-%d')

                if date_range == "Last 6 months":
                    start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
                elif date_range == "Last year":
                    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                elif date_range == "Last 2 years":
                    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

                results = search_hansard_contributions(selected_mp['id'], search_terms, start_date, end_date, max_results)
                st.session_state.hansard_results = results
                st.session_state.hansard_search_performed = True

                if results:
                    st.success(f"Found {len(results)} relevant contributions!")
                else:
                    st.warning("No contributions found for this topic. Try different search terms or expand the date range.")

    # Display results (same as before but with wizard navigation)
    if st.session_state.hansard_search_performed and st.session_state.hansard_results:
        st.subheader(f"📋 Search Results ({len(st.session_state.hansard_results)} found)")

        # Selection controls
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Select All", key="select_all_hansard_wizard"):
                st.session_state.selected_hansard_items = [item['id'] for item in st.session_state.hansard_results]
                st.rerun()
        with col2:
            if st.button("❌ Clear Selection", key="clear_all_hansard_wizard"):
                st.session_state.selected_hansard_items = []
                st.rerun()
        with col3:
            selected_count = len(st.session_state.selected_hansard_items)
            st.write(f"**Selected: {selected_count}**")

        # Display results (keeping existing display logic)
        for i, result in enumerate(st.session_state.hansard_results):
            with st.container():
                is_selected = result['id'] in st.session_state.selected_hansard_items

                selected = st.checkbox(
                    f"Select this contribution",
                    value=is_selected,
                    key=f"hansard_select_wizard_{i}"
                )

                if selected and result['id'] not in st.session_state.selected_hansard_items:
                    st.session_state.selected_hansard_items.append(result['id'])
                elif not selected and result['id'] in st.session_state.selected_hansard_items:
                    st.session_state.selected_hansard_items.remove(result['id'])

                result_date = format_hansard_date(result['date'])
                st.markdown(f"**{result_date}** - {result['debate_title']}")
                st.caption(f"Found by search term: '{result['search_term']}'")

                text_to_show = result['full_text'] if result['full_text'] else result['text']
                if len(text_to_show) > 400:
                    text_to_show = text_to_show[:400] + "..."
                st.write(text_to_show)

                if result.get('url'):
                    st.markdown(f"🔗 [View in Hansard]({result['url']})")

                st.divider()

        # Add selected items - wizard navigation
        if st.session_state.selected_hansard_items:
            if st.button(f"➕ Add {len(st.session_state.selected_hansard_items)} Selected Items",
                        type="primary", key="add_hansard_wizard", use_container_width=True):
                new_comments = []
                for result in st.session_state.hansard_results:
                    if result['id'] in st.session_state.selected_hansard_items:
                        hansard_comment = {
                            "type": "Parliamentary Remarks",
                            "url": result.get('url', ''),
                            "date": result['date'][:10] if result['date'] else datetime.now().strftime("%Y-%m-%d"),
                            "text": f"In {result['debate_title']} on {format_hansard_date(result['date'])}, {selected_mp['name']} said: \"{result['full_text'] if result['full_text'] else result['text']}\""
                        }
                        new_comments.append(hansard_comment)

                if 'hansard_comments_added' not in st.session_state:
                    st.session_state.hansard_comments_added = []
                st.session_state.hansard_comments_added.extend(new_comments)

                st.success(f"✅ Added {len(new_comments)} parliamentary contributions!")

                # Return to step 3
                st.session_state.selected_hansard_items = []
                st.session_state.show_hansard_search = False
                st.rerun()

def create_manual_comments_section_wizard():
    """Manual comments for wizard - fixed navigation"""
    st.subheader("💬 Add Manual Comments")

    # Wizard-specific back button
    if st.button("← Back to Step 3", key="back_from_manual_wizard"):
        st.session_state.show_manual_comments = False
        st.rerun()

    st.write("Add comments or statements from sources other than parliamentary records.")

    # Initialize session state
    if 'manual_comments_added' not in st.session_state:
        st.session_state.manual_comments_added = []

    # Show existing comments
    existing_comments = st.session_state.get('manual_comments_added', [])
    if existing_comments:
        st.write(f"**📋 Added Comments ({len(existing_comments)}):**")

        for i, comment in enumerate(existing_comments):
            with st.container():
                col1, col2 = st.columns([4, 1])

                with col1:
                    st.write(f"**{i+1}. {comment['type']}** ({comment['date']})")
                    if comment.get('url'):
                        st.markdown(f"🔗 [Source]({comment['url']})")

                    preview = comment['text'][:150] + "..." if len(comment['text']) > 150 else comment['text']
                    st.write(preview)

                with col2:
                    if st.button("🗑️", key=f"remove_manual_wizard_{i}", help="Remove this comment"):
                        st.session_state.manual_comments_added.pop(i)
                        st.rerun()

                st.divider()

    # Add new comment form
    st.write("**➕ Add New Comment:**")

    with st.form("manual_comment_form_wizard"):
        comment_type = st.selectbox(
            "Source Type",
            options=[
                "Social Media Post",
                "Written Question",
                "Interview/Speech",
                "Press Release",
                "Newsletter/Blog",
                "Other"
            ]
        )

        comment_url = st.text_input("Source URL (Optional)", placeholder="https://...")
        comment_date = st.date_input("Date of Comment", value=datetime.now().date())
        comment_text = st.text_area("Comment Text", height=120, placeholder="Enter the comment or statement here...")

        submit_comment = st.form_submit_button("➕ Add Comment", type="primary", use_container_width=True)

        if submit_comment and comment_text:
            new_comment = {
                "type": comment_type,
                "url": comment_url,
                "date": comment_date.strftime("%Y-%m-%d"),
                "text": comment_text
            }

            st.session_state.manual_comments_added.append(new_comment)
            st.success("✅ Comment added!")
            st.rerun()

    # Actions
    if existing_comments:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear All", key="clear_all_manual_wizard"):
                st.session_state.manual_comments_added = []
                st.success("All manual comments cleared!")
                st.rerun()
        with col2:
            if st.button("✅ Done", key="done_manual_wizard", type="primary"):
                st.session_state.show_manual_comments = False
                st.rerun()


def wizard_step_2_configure():
    """Step 2: Configure biography settings - CLEAN clickable cards only"""
    st.header("Step 2: Configure Biography")

    selected_mp = st.session_state.get('selected_mp')
    st.info(f"Creating biography for: **{selected_mp['name']}**")

    # Biography length selection
    st.subheader("Biography Length")

    length_options = [
        {
            "key": "brief",
            "title": "Brief Biography",
            "description": "Essential information only (2-3 short paragraphs, ~100-150 words)",
            "icon": "📝"
        },
        {
            "key": "medium",
            "title": "Standard Biography",
            "description": "Comprehensive coverage following example format (default length)",
            "icon": "📄"
        },
        {
            "key": "comprehensive",
            "title": "Comprehensive Biography",
            "description": "Extended detail with additional sections (~50-75% longer)",
            "icon": "📚"
        }
    ]

    current_length = st.session_state.get('length_setting', 'medium')

    # Create three columns for the selection cards
    cols = st.columns(3)

    for i, option in enumerate(length_options):
        with cols[i]:
            is_selected = current_length == option["key"]

            # Create button with card-like content
            button_label = f"{option['icon']} **{option['title']}**\n\n{option['description']}"

            if st.button(
                button_label,
                key=f"select_length_{option['key']}",
                use_container_width=True,
                type="primary" if is_selected else "secondary"
            ):
                st.session_state.length_setting = option["key"]
                st.rerun()

    # Show current selection
    current_option = next((opt for opt in length_options if opt["key"] == current_length), length_options[1])
    st.success(f"✅ Selected: **{current_option['title']}** - {current_option['description']}")

    st.divider()

    # Additional information section (unchanged)
    st.subheader("Additional Information (Optional)")

    current_additional_info = st.session_state.get('additional_info', '')

    additional_info = st.text_area(
        "Enter any specific information about the MP you'd like to include:",
        value=current_additional_info,
        height=120,
        placeholder="Add information about recent work, policy positions, constituency issues, etc.",
        key="additional_info_input"
    )

    # Save to session state whenever it changes
    if additional_info != current_additional_info:
        st.session_state.additional_info = additional_info

    # Navigation buttons
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        if st.button("← Back", key="step2_back", use_container_width=True):
            st.session_state.wizard_step = 1
            st.rerun()

    with col3:
        if st.button("Next →", type="primary", key="step2_next", use_container_width=True):
            st.session_state.additional_info = additional_info
            st.session_state.wizard_step = 3
            st.rerun()

def wizard_step_3_add_information():
    """Step 3: Add additional information - with tabs for better navigation"""
    st.header("Step 3: Add Additional Information")

    selected_mp = st.session_state.get('selected_mp')

    st.write("Enhance your biography with parliamentary records or comments from other sources (optional).")

    # Show current counts
    hansard_count = len(st.session_state.get('hansard_comments_added', []))
    manual_count = len(st.session_state.get('manual_comments_added', []))

    if hansard_count > 0 or manual_count > 0:
        status_parts = []
        if hansard_count > 0:
            status_parts.append(f"{hansard_count} Hansard records")
        if manual_count > 0:
            status_parts.append(f"{manual_count} manual comments")

        st.success(f"✅ Added: {', '.join(status_parts)}")

    # Tabbed interface for better navigation
    tab1, tab2 = st.tabs(["🏛️ Parliamentary Records", "💬 Other Sources"])

    with tab1:
        st.write("Search Hansard for the MP's statements on specific topics.")

        if hansard_count > 0:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔍 Search More Records", key="search_more_hansard", use_container_width=True):
                    st.session_state.hansard_tab_mode = "search"
                    st.rerun()
            with col2:
                if st.button("📋 Manage Added Records", key="manage_hansard_tab", use_container_width=True):
                    st.session_state.hansard_tab_mode = "manage"
                    st.rerun()
        else:
            if st.button("🔍 Search Hansard Records", key="start_hansard_tab", use_container_width=True):
                st.session_state.hansard_tab_mode = "search"
                st.rerun()

        # Show Hansard interface if activated
        if st.session_state.get('hansard_tab_mode') == "search":
            st.divider()
            create_hansard_search_inline()
        elif st.session_state.get('hansard_tab_mode') == "manage":
            st.divider()
            create_hansard_management_inline()

    with tab2:
        st.write("Add comments from social media, interviews, press releases, etc.")

        if manual_count > 0:
            st.write(f"**📋 {manual_count} Comments Added**")

            # Show existing comments
            for i, comment in enumerate(st.session_state.get('manual_comments_added', [])):
                with st.container():
                    col1, col2 = st.columns([4, 1])

                    with col1:
                        st.write(f"**{comment['type']}** ({comment['date']})")
                        preview = comment['text'][:100] + "..." if len(comment['text']) > 100 else comment['text']
                        st.write(preview)

                    with col2:
                        if st.button("🗑️", key=f"remove_manual_tab_{i}", help="Remove"):
                            st.session_state.manual_comments_added.pop(i)
                            st.rerun()

                    st.divider()

        # Add new comment form
        st.write("**➕ Add New Comment:**")

        with st.form("manual_comment_tab_form"):
            comment_type = st.selectbox(
                "Source Type",
                options=["Social Media Post", "Written Question", "Interview/Speech", "Press Release", "Newsletter/Blog", "Other"]
            )

            col1, col2 = st.columns(2)
            with col1:
                comment_url = st.text_input("Source URL (Optional)", placeholder="https://...")
            with col2:
                comment_date = st.date_input("Date", value=datetime.now().date())

            comment_text = st.text_area("Comment Text", height=100, placeholder="Enter the comment or statement here...")

            if st.form_submit_button("➕ Add Comment", type="primary", use_container_width=True):
                if comment_text:
                    new_comment = {
                        "type": comment_type,
                        "url": comment_url,
                        "date": comment_date.strftime("%Y-%m-%d"),
                        "text": comment_text
                    }

                    if 'manual_comments_added' not in st.session_state:
                        st.session_state.manual_comments_added = []
                    st.session_state.manual_comments_added.append(new_comment)
                    st.rerun()

    st.divider()

    # Navigation buttons
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        if st.button("← Back", key="step3_back", use_container_width=True):
            # Clear any tab modes when leaving step
            st.session_state.hansard_tab_mode = None
            st.session_state.wizard_step = 2
            st.rerun()

    with col3:
        if st.button("Generate Biography →", type="primary", key="step3_next", use_container_width=True):
            st.session_state.hansard_tab_mode = None
            st.session_state.wizard_step = 4
            st.rerun()


def wizard_step_4_generate():
    """Step 4: Generate and download - fixed additional info detection"""
    st.header("Step 4: Generate & Download Biography")

    selected_mp = st.session_state.get('selected_mp')
    length_setting = st.session_state.get('length_setting', 'medium')

    st.subheader("📋 Biography Summary")

    # Check for additional info properly
    additional_info = st.session_state.get('additional_info', '').strip()

    data_sources = []
    if additional_info:  # Fixed check
        data_sources.append("Your additional information")

    hansard_count = len(st.session_state.get('hansard_comments_added', []))
    if hansard_count > 0:
        data_sources.append(f"{hansard_count} Hansard parliamentary records")

    manual_count = len(st.session_state.get('manual_comments_added', []))
    if manual_count > 0:
        data_sources.append(f"{manual_count} manual comments")

    data_sources.extend(["Parliament API data", "Wikipedia information"])

    # Compact display
    st.write(f"**{length_setting.title()} biography for {selected_mp['name']} including:**")
    for source in data_sources:
        st.write(f"• {source}")

    # Generate button
    if not st.session_state.get('biography_generated'):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Generate Biography", type="primary", key="final_generate", use_container_width=True):
                user_input = st.session_state.get('additional_info', '')
                all_comments = st.session_state.get('hansard_comments_added', []).copy()
                all_comments.extend(st.session_state.get('manual_comments_added', []))

                generate_biography_flow(selected_mp, user_input, all_comments)

    # Navigation
    st.divider()
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        if st.button("← Back", key="step4_back", use_container_width=True):
            st.session_state.wizard_step = 3
            st.rerun()

    if st.session_state.get('biography_generated'):
        with col3:
            if st.button("🔄 Create Another", key="step4_restart", use_container_width=True):
                keys_to_clear = [
                    'wizard_step', 'selected_mp', 'mp_search_query', 'show_suggestions',
                    'validation_result', 'hansard_comments_added', 'manual_comments_added',
                    'additional_info', 'biography_generated', 'length_setting'
                ]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]

                st.session_state.wizard_step = 1
                st.rerun()

def search_hansard_contributions(mp_id, search_terms, start_date=None, end_date=None, max_results=20):
    """Search Hansard API for MP contributions using generated search terms"""
    all_results = []

    # Set default date range (last 2 years if not specified)
    if not start_date:
        start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    base_url = "https://hansard-api.parliament.uk"

    for search_term in search_terms:
        try:
            # Search for spoken contributions
            url = f"{base_url}/search/contributions/Spoken.json"

            params = {
                'queryParameters.searchTerm': search_term,
                'queryParameters.memberId': mp_id,
                'queryParameters.startDate': start_date,
                'queryParameters.endDate': end_date,
                'queryParameters.take': max_results // len(search_terms),  # Distribute results across search terms
                'queryParameters.orderBy': 'SittingDateDesc'  # Most recent first
            }

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if 'Results' in data and data['Results']:
                    for result in data['Results']:
                        contribution_ext_id = result.get('ContributionExtId', '')

                        # Get the Hansard URL for this contribution
                        hansard_url = get_hansard_url(contribution_ext_id)

                        # Create a standardized result object
                        contribution = {
                            'id': contribution_ext_id,
                            'date': result.get('SittingDate', ''),
                            'debate_title': result.get('DebateSection', 'Unknown Debate'),
                            'text': result.get('ContributionText', ''),
                            'full_text': result.get('ContributionTextFull', ''),
                            'member_name': result.get('MemberName', ''),
                            'hansard_section': result.get('HansardSection', ''),
                            'search_term': search_term,
                            'timecode': result.get('Timecode', ''),
                            'house': result.get('House', 'Commons'),
                            'url': hansard_url  # Add the URL
                        }

                        # Only add if we have meaningful content
                        if contribution['text'] and len(contribution['text'].strip()) > 50:
                            all_results.append(contribution)

        except Exception as e:
            st.warning(f"Error searching for '{search_term}': {str(e)}")
            continue

    # Remove duplicates and sort by date
    seen_ids = set()
    unique_results = []
    for result in all_results:
        if result['id'] not in seen_ids:
            seen_ids.add(result['id'])
            unique_results.append(result)

    # Sort by date (most recent first)
    unique_results.sort(key=lambda x: x['date'], reverse=True)

    return unique_results[:max_results]


def format_hansard_date(date_string):
    """Format date string for display"""
    try:
        if date_string:
            date_obj = datetime.strptime(date_string[:10], '%Y-%m-%d')
            return date_obj.strftime('%d %B %Y')
    except:
        pass
    return date_string

def hansard_search_interface(mp_name, mp_id):
    """Create the Hansard search interface"""
    st.subheader("🔍 Search Parliamentary Records")
    st.write("Search for the MP's parliamentary contributions on specific topics using the Hansard database.")

    # Initialize session state for Hansard search
    if 'hansard_results' not in st.session_state:
        st.session_state.hansard_results = []
    if 'selected_hansard_items' not in st.session_state:
        st.session_state.selected_hansard_items = []
    if 'hansard_search_performed' not in st.session_state:
        st.session_state.hansard_search_performed = False
    if 'hansard_comments_added' not in st.session_state:
        st.session_state.hansard_comments_added = []
    if 'show_hansard_success' not in st.session_state:
        st.session_state.show_hansard_success = False

    # Search form
    with st.form("hansard_search_form"):
        issue_query = st.text_input(
            "What topic would you like to search for?",
            placeholder="e.g., climate change, healthcare, education funding, housing policy...",
            help="Describe the topic or issue you want to find the MP's statements about"
        )

        # Date range selection
        date_range = st.selectbox(
            "Time period",
            ["Last 6 months", "Last year", "Last 2 years", "All available"],
            index=1
        )

        # Advanced options in expander
        with st.expander("Advanced Search Options"):
            custom_start_date = st.date_input(
                "Custom start date (optional)",
                value=None,
                help="Leave blank to use the time period above"
            )
            custom_end_date = st.date_input(
                "Custom end date (optional)",
                value=None,
                help="Leave blank to use today's date"
            )

            max_results = st.slider("Maximum results", 5, 50, 20)

        search_button = st.form_submit_button("🔍 Search Hansard Records", type="primary")

    if search_button and issue_query:
        with st.spinner("Generating search terms and searching Hansard..."):
            # Generate search terms using Claude
            st.info("🤖 Generating search terms with AI...")
            search_terms = generate_search_terms(issue_query, mp_name)

            if search_terms:
                st.success(f"Generated search terms: {', '.join(search_terms)}")

                # Calculate date range
                start_date = None
                end_date = None

                if custom_start_date:
                    start_date = custom_start_date.strftime('%Y-%m-%d')
                if custom_end_date:
                    end_date = custom_end_date.strftime('%Y-%m-%d')

                if not start_date:
                    if date_range == "Last 6 months":
                        start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
                    elif date_range == "Last year":
                        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
                    elif date_range == "Last 2 years":
                        start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
                    # For "All available", leave start_date as None

                if not end_date:
                    end_date = datetime.now().strftime('%Y-%m-%d')

                # Search Hansard
                st.info("🔍 Searching Hansard database...")
                results = search_hansard_contributions(mp_id, search_terms, start_date, end_date, max_results)

                st.session_state.hansard_results = results
                st.session_state.hansard_search_performed = True

                if results:
                    st.success(f"Found {len(results)} relevant contributions!")
                else:
                    st.warning("No contributions found for this topic. Try different search terms or expand the date range.")

    # Display results if available
    if st.session_state.hansard_search_performed and st.session_state.hansard_results:
        st.subheader(f"📋 Search Results ({len(st.session_state.hansard_results)} found)")

        # Selection controls - use a simple row layout instead of columns
        if st.button("✅ Select All", key="select_all_hansard"):
            st.session_state.selected_hansard_items = [item['id'] for item in st.session_state.hansard_results]
            st.rerun()

        if st.button("❌ Clear Selection", key="clear_all_hansard"):
            st.session_state.selected_hansard_items = []
            st.rerun()

        selected_count = len(st.session_state.selected_hansard_items)
        st.write(f"**Selected: {selected_count} items**")

        # Display results
        for i, result in enumerate(st.session_state.hansard_results):
            with st.container():
                # Create checkbox for selection
                is_selected = result['id'] in st.session_state.selected_hansard_items

                # Use a single column layout to avoid nesting issues
                selected = st.checkbox(
                    f"Select this contribution",
                    value=is_selected,
                    key=f"hansard_select_{i}"
                )

                if selected and result['id'] not in st.session_state.selected_hansard_items:
                    st.session_state.selected_hansard_items.append(result['id'])
                elif not selected and result['id'] in st.session_state.selected_hansard_items:
                    st.session_state.selected_hansard_items.remove(result['id'])

                # Result display
                result_date = format_hansard_date(result['date'])

                # Header with date and debate
                st.markdown(f"**{result_date}** - {result['debate_title']}")

                # Show search term that found this result
                st.caption(f"Found by search term: '{result['search_term']}'")

                # Show contribution text
                text_to_show = result['full_text'] if result['full_text'] else result['text']
                if len(text_to_show) > 500:
                    text_to_show = text_to_show[:500] + "..."

                st.write(text_to_show)

                # Add link to full Hansard entry if available - avoid nested columns
                if result.get('url'):
                    st.markdown(f"🔗 [View in Hansard]({result['url']})")
                else:
                    st.caption("Link unavailable")

                # Additional metadata
                if result['hansard_section']:
                    st.caption(f"Section: {result['hansard_section']}")

                st.divider()

        # Add selected items to comments
        if st.session_state.selected_hansard_items:
            if st.button(f"➕ Add {len(st.session_state.selected_hansard_items)} Selected Items to Comments", type="primary"):
                # Convert selected results to comment format
                new_comments = []
                for result in st.session_state.hansard_results:
                    if result['id'] in st.session_state.selected_hansard_items:
                        hansard_comment = {
                            "type": "Parliamentary Remarks",
                            "url": result.get('url', ''),  # Include the Hansard URL
                            "date": result['date'][:10] if result['date'] else datetime.now().strftime("%Y-%m-%d"),
                            "text": f"In {result['debate_title']} on {format_hansard_date(result['date'])}, {mp_name} said: \"{result['full_text'] if result['full_text'] else result['text']}\""
                        }
                        new_comments.append(hansard_comment)

                # Add to session state
                st.session_state.hansard_comments_added.extend(new_comments)

                # Show success message
                st.success(f"✅ Successfully added {len(new_comments)} parliamentary contributions to your comments!")
                st.session_state.show_hansard_success = True

                # Clear selections after adding
                st.session_state.selected_hansard_items = []
                st.rerun()

    # Show success message if items were just added
    if st.session_state.show_hansard_success:
        st.info(f"💡 {len(st.session_state.hansard_comments_added)} Hansard items have been added to your comments. You can view them in the Manual Entry tab.")
        if st.button("✅ Got it!", key="dismiss_hansard_success"):
            st.session_state.show_hansard_success = False
            st.rerun()

    return []
# Cache for API responses to improve performance
@lru_cache(maxsize=500)
def cached_search_mps(query, limit=20):
    """Cached version of MP search - FIXED to only return Commons MPs"""
    if not query or len(query.strip()) < 2:
        return []

    try:
        search_url = f"https://members-api.parliament.uk/api/Members/Search"
        params = {
            'Name': query.strip(),
            'IsCurrentMember': True,
            'take': limit * 2  # Get more results to account for filtering
        }

        response = requests.get(search_url, params=params, timeout=3)
        if response.status_code == 200:
            data = response.json()

            mps = []
            if data.get('items'):
                for item in data['items']:
                    member = item.get('value', {})

                    # Check if this is a Commons MP (house_id == 1)
                    latest_membership = member.get('latestHouseMembership', {})
                    house_id = latest_membership.get('house')

                    # ONLY include Commons MPs (house_id == 1)
                    if house_id != 1:
                        continue

                    mp_info = {
                        'id': member.get('id'),
                        'name': member.get('nameDisplayAs', ''),
                        'party': member.get('latestParty', {}).get('name', '') if member.get('latestParty') else '',
                        'constituency': latest_membership.get('membershipFrom', ''),
                        'house': 'Commons'  # We know it's Commons since we filtered
                    }

                    if mp_info['name'] and mp_info['id'] and mp_info['constituency']:
                        mps.append(mp_info)

                        # Stop when we have enough Commons MPs
                        if len(mps) >= limit:
                            break

            return tuple(mps)  # Return tuple for caching

    except Exception as e:
        st.error(f"Error searching for MPs: {str(e)}")
        return []

def search_mps(query, limit=20):
    """Wrapper for cached search that returns list"""
    return list(cached_search_mps(query, limit))

def normalize_name(name):
    """Normalize names for better matching"""
    # Remove titles and honorifics
    name = name.lower().strip()

    # Remove common titles
    titles = ['sir', 'dame', 'lord', 'baroness', 'rt hon', 'the rt hon', 'dr', 'prof']
    for title in titles:
        if name.startswith(title + ' '):
            name = name[len(title) + 1:]

    # Remove extra whitespace
    return ' '.join(name.split())

def calculate_similarity(query, mp_name):
    """Calculate similarity between query and MP name with normalization"""
    query_norm = normalize_name(query)
    mp_name_norm = normalize_name(mp_name)

    # Check for exact match after normalization
    if query_norm == mp_name_norm:
        return 1.0

    # Check if query is contained in MP name (for partial matches)
    if query_norm in mp_name_norm:
        return 0.95

    # Use sequence matcher for fuzzy matching
    return SequenceMatcher(None, query_norm, mp_name_norm).ratio()

def validate_mp_name(query):
    """Enhanced validation - FIXED to always show multiple options when there are several matches"""
    if not query or len(query.strip()) < 2:
        return {
            'is_valid': False,
            'exact_match': None,
            'suggestions': [],
            'message': 'Please enter at least 2 characters'
        }

    # Add debouncing
    if 'last_search_time' not in st.session_state:
        st.session_state.last_search_time = 0

    current_time = time.time()
    if current_time - st.session_state.last_search_time < 1.0:
        return {
            'is_valid': False,
            'exact_match': None,
            'suggestions': [],
            'message': 'Searching...'
        }

    st.session_state.last_search_time = current_time

    mps = search_mps(query)

    if not mps:
        return {
            'is_valid': False,
            'exact_match': None,
            'suggestions': [],
            'message': f'No MPs found matching "{query}". Please check the spelling and try again.'
        }

    # Calculate similarities for all MPs
    mp_similarities = []
    for mp in mps:
        similarity = calculate_similarity(query, mp['name'])
        mp_similarities.append((mp, similarity))

    # Sort by similarity
    mp_similarities.sort(key=lambda x: x[1], reverse=True)

    # Get high-quality matches (similarity >= 0.8)
    high_quality_matches = [match for match in mp_similarities if match[1] >= 0.8]

    # CHANGED: Only auto-select if there's exactly ONE very high quality match (>= 0.95)
    # and no other good matches
    best_match = mp_similarities[0]
    best_similarity = best_match[1]

    very_high_matches = [match for match in mp_similarities if match[1] >= 0.95]

    # Only auto-select if:
    # 1. We have exactly one very high quality match (>= 0.95)
    # 2. AND the second best match (if any) is significantly worse (< 0.85)
    if (len(very_high_matches) == 1 and
        best_similarity >= 0.95 and
        (len(mp_similarities) == 1 or mp_similarities[1][1] < 0.85)):

        return {
            'is_valid': True,
            'exact_match': best_match[0],
            'suggestions': [],
            'message': f'✅ Found MP: {best_match[0]["name"]}'
        }

    # Otherwise, show suggestions for any match with similarity >= 0.6
    good_matches = [match[0] for match in mp_similarities if match[1] >= 0.6]

    if good_matches:
        if len(good_matches) == 1:
            message = f'Found MP matching "{query}". Please confirm:'
        else:
            message = f'Found {len(good_matches)} MPs matching "{query}". Please select one:'

        return {
            'is_valid': False,
            'exact_match': None,
            'suggestions': good_matches[:10],  # Limit to 10 suggestions
            'message': message
        }

    # No good matches
    return {
        'is_valid': False,
        'exact_match': None,
        'suggestions': [match[0] for match in mp_similarities[:5]],  # Show top 5 as fallback
        'message': f'No exact matches found for "{query}". Did you mean one of these?'
    }

def mp_name_input_with_validation():
    """Enhanced MP name input with improved performance and UX"""

    if 'selected_mp' not in st.session_state:
        st.session_state.selected_mp = None
    if 'mp_search_query' not in st.session_state:
        st.session_state.mp_search_query = ''
    if 'show_suggestions' not in st.session_state:
        st.session_state.show_suggestions = False
    if 'validation_result' not in st.session_state:
        st.session_state.validation_result = None

    st.subheader("Select MP")

    # If we already have a selected MP, just show it without validation
    if st.session_state.selected_mp:
        mp = st.session_state.selected_mp

        # Add clear button option
        clear_col, info_col1, info_col2, info_col3 = st.columns([1, 2, 2, 2])
        with clear_col:
            if st.button("❌", help="Clear selection and search again", key="clear_mp_selection"):
                st.session_state.selected_mp = None
                st.session_state.mp_search_query = ''
                st.session_state.show_suggestions = False
                st.session_state.validation_result = None
                st.rerun()

        with info_col1:
            st.markdown(f"**Name:**<br><small>{mp['name']}</small>", unsafe_allow_html=True)
        with info_col2:
            st.markdown(f"**Party:**<br><small>{mp['party']}</small>", unsafe_allow_html=True)
        with info_col3:
            st.markdown(f"**Constituency:**<br><small>{mp['constituency']}</small>", unsafe_allow_html=True)

        return st.session_state.selected_mp

    # Only show search interface if no MP is selected
    search_query = st.text_input(
        "Search for MP name:",
        value=st.session_state.mp_search_query,
        placeholder="e.g., Keir Starmer, Rishi Sunak, Angela Rayner...",
        help="Enter the MP's name (titles like 'Sir' are optional)",
        key="mp_search_input"
    )

    # Only process if query has changed
    if search_query != st.session_state.mp_search_query:
        st.session_state.mp_search_query = search_query
        st.session_state.selected_mp = None
        st.session_state.show_suggestions = False
        st.session_state.validation_result = None

    # Validate with improved logic
    if search_query and len(search_query.strip()) >= 2:
        # Show loading spinner for better UX
        with st.spinner('Searching MPs...'):
            validation_result = validate_mp_name(search_query)

        st.session_state.validation_result = validation_result

        if validation_result['message'] == 'Searching...':
            st.info("⏳ Searching...")
            return None

        if validation_result['is_valid']:
            st.success(validation_result['message'])
            st.session_state.selected_mp = validation_result['exact_match']
            st.session_state.show_suggestions = False
            # Will display on next rerun

        elif validation_result['suggestions']:
            if len(validation_result['suggestions']) == 1:
                st.info(validation_result['message'])
            else:
                st.warning(validation_result['message'])

            st.session_state.show_suggestions = True

            suggestions = validation_result['suggestions']

            for i in range(0, len(suggestions), 2):
                cols = st.columns(2)

                for j, col in enumerate(cols):
                    if i + j < len(suggestions):
                        suggestion = suggestions[i + j]

                        with col:
                            button_text = f"{suggestion['name']}"
                            subtext = f"{suggestion['party']} • {suggestion['constituency']}"

                            if st.button(
                                button_text,
                                key=f"suggestion_{i+j}",
                                help=f"{subtext}\n\nClick to select this MP",
                                use_container_width=True
                            ):
                                st.session_state.selected_mp = suggestion
                                st.session_state.mp_search_query = suggestion['name']
                                st.session_state.show_suggestions = False
                                st.rerun()

                            st.markdown(f"<small>{subtext}</small>", unsafe_allow_html=True)

        else:
            st.error(validation_result['message'])
            st.session_state.selected_mp = None
            st.session_state.show_suggestions = False

    elif search_query and len(search_query.strip()) > 0:
        st.info("Please enter at least 2 characters to search")
        st.session_state.selected_mp = None

    return st.session_state.selected_mp

def check_password(username, password):
    """Check if username and password are correct"""
    try:
        if username in st.secrets["credentials"]["usernames"]:
            stored_password = st.secrets["credentials"]["usernames"][username]["password"]
            result = bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8'))
            return result
        else:
            return False
    except Exception as e:
        st.error(f"Password check failed: {str(e)}")
        return False

def setup_api_keys():
    """Setup API keys from secrets"""
    try:
        os.environ['ANTHROPIC_API_KEY'] = st.secrets["api_keys"]["anthropic"]
        # Removed perplexity_key return
    except Exception as e:
        st.error(f"API key setup failed: {str(e)}")
        st.info("Please ensure your API keys are configured in secrets.toml")
        st.stop()

if 'cancel_generation' not in st.session_state:
    st.session_state.cancel_generation = False

def display_verified_positions(verified_data):
    """Display verified Parliamentary positions in the sidebar"""
    st.sidebar.title("Verified Parliament Data")

    if not verified_data:
        st.sidebar.warning("No verified data available from Parliament API")
        return

    st.sidebar.subheader("Current Committee Memberships")
    if verified_data['current_committees']:
        for committee in verified_data['current_committees']:
            st.sidebar.markdown(f"• **{committee['name']}**  \n"
                              f"  Since: {committee['start_date']}")
    else:
        st.sidebar.info("No current committee memberships")

    st.sidebar.subheader("Current Government/Opposition Roles")
    if verified_data['current_roles']:
        for role in verified_data['current_roles']:
            st.sidebar.markdown(f"• **{role['name']}**  \n"
                              f"  Since: {role['start_date']}")
    else:
        st.sidebar.info("No current government/opposition roles")

    with st.sidebar.expander("View Historical Positions"):
        st.subheader("Past Committee Memberships")
        if verified_data['historical_committees']:
            for committee in verified_data['historical_committees']:
                st.markdown(f"• **{committee['name']}**  \n"
                          f"  {committee['start_date']} - {committee['end_date']}")
        else:
            st.info("No past committee memberships")

        st.subheader("Past Government/Opposition Roles")
        if verified_data['historical_roles']:
            for role in verified_data['historical_roles']:
                st.markdown(f"• **{role['name']}**  \n"
                          f"  {role['start_date']} - {role['end_date']}")
        else:
            st.info("No past government/opposition roles")

    if verified_data.get('api_response'):
        with st.sidebar.expander("Debug: Raw API Data"):
            st.json(verified_data['api_response'])


# Add this debug function to streamlit_app.py to test comment matching
# You can call this in your app to see how the matching works

def debug_comment_matching(comments, biography_text):
    """Debug function to test comment URL matching"""
    st.subheader("🐛 Debug: Comment URL Matching")

    if not comments:
        st.info("No comments to debug")
        return

    # Show comments with URLs
    st.write("**Comments with URLs:**")
    for i, comment in enumerate(comments):
        if comment.get('url'):
            st.write(f"**Comment {i+1}:**")
            st.write(f"- URL: {comment['url']}")
            st.write(f"- Text snippet (first 50 chars): `{comment['text'][:50].strip()}`")
            st.write(f"- Full text: {comment['text']}")
            st.divider()

    # Show relevant comments section from biography
    st.write("**Biography Relevant Comments Section:**")
    lines = biography_text.split('\n')
    in_comments = False
    for line in lines:
        if line.strip() == 'Relevant Comments':
            in_comments = True
        if in_comments:
            if line.strip().startswith('•'):
                st.write(f"Bullet point: `{line.strip()}`")

                # Test matching
                for comment in comments:
                    if comment.get('url'):
                        snippet = comment['text'][:50].strip()
                        if snippet in line:
                            st.success(f"✅ MATCH FOUND! This bullet point matches comment with URL: {comment['url']}")
                        else:
                            st.warning(f"❌ No match for: {snippet}")

# Usage in your main app (add this temporarily for debugging):
# if st.button("🐛 Debug Comment Matching"):
#     debug_comment_matching(comments, biography)

def relevant_comments_section(mp_name=None, mp_id=None):
    """Create and handle the relevant comments section UI with Hansard search"""
    comments = []

    if 'show_comments' not in st.session_state:
        st.session_state.show_comments = False
    if 'comment_count' not in st.session_state:
        st.session_state.comment_count = 1
    if 'hansard_comments_added' not in st.session_state:
        st.session_state.hansard_comments_added = []

    def toggle_comments():
        st.session_state.show_comments = not st.session_state.show_comments
        if not st.session_state.show_comments:
            st.session_state.comment_count = 1

    def add_comment_form():
        st.session_state.comment_count += 1

    def cancel_comments():
        st.session_state.show_comments = False
        st.session_state.comment_count = 1
        # Clear hansard comments when canceling
        st.session_state.hansard_comments_added = []

    if not st.session_state.show_comments:
        # Show count of added hansard comments if any
        hansard_count = len(st.session_state.hansard_comments_added)
        button_text = "Add Relevant Comments"
        if hansard_count > 0:
            button_text += f" ({hansard_count} from Hansard)"
        st.button(button_text, on_click=toggle_comments, key="add_comments")
    else:
        with st.container():
            st.subheader("Relevant Comments")
            st.write("Add comments or remarks made by the MP from various sources. These will appear as bullet points at the end of the biography.")

            # Add tabs for manual entry vs Hansard search
            tab1, tab2 = st.tabs(["✍️ Manual Entry", "🔍 Search Hansard"])

            with tab1:
                # Show hansard comments that have been added
                if st.session_state.hansard_comments_added:
                    st.success(f"✅ {len(st.session_state.hansard_comments_added)} comments added from Hansard search")

                    with st.expander(f"📋 View {len(st.session_state.hansard_comments_added)} Hansard Comments", expanded=False):
                        for i, comment in enumerate(st.session_state.hansard_comments_added):
                            st.write(f"**{i+1}. {comment['type']}** ({comment['date']})")
                            if comment.get('url'):
                                st.write("🔗 Has Hansard link")
                            st.write(comment['text'][:200] + "..." if len(comment['text']) > 200 else comment['text'])
                            st.divider()

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🗑️ Clear Hansard Comments", key="clear_hansard"):
                            st.session_state.hansard_comments_added = []
                            st.success("Hansard comments cleared!")
                            st.rerun()
                    with col2:
                        st.info(f"These will be included in the biography")

                st.write("Manually enter additional comments from any source:")

                # Manual comment forms
                for i in range(st.session_state.comment_count):
                    with st.expander(f"Manual Comment {i+1}", expanded=(i == st.session_state.comment_count-1)):
                        comment_type = st.selectbox(
                            "Source Type",
                            options=[
                                "Social Media Post",
                                "Written Question",
                                "Parliamentary Remarks",
                                "Ministerial/Government Remarks"
                            ],
                            key=f"type_{i}"
                        )

                        comment_url = st.text_input("Source URL (Optional)", key=f"url_{i}")

                        comment_date = st.date_input(
                            "Date of Comment",
                            value=datetime.now().date(),
                            key=f"date_{i}"
                        )

                        comment_text = st.text_area(
                            "Comment Text",
                            height=150,
                            key=f"text_{i}"
                        )

                        if comment_text:
                            comments.append({
                                "type": comment_type,
                                "url": comment_url,
                                "date": comment_date.strftime("%Y-%m-%d"),
                                "text": comment_text
                            })

                col1, col2 = st.columns(2)
                with col1:
                    st.button("Add Another Manual Comment", on_click=add_comment_form)
                with col2:
                    st.button("Cancel All Comments", on_click=cancel_comments, type="secondary")

            with tab2:
                if mp_name and mp_id:
                    # Hansard search interface
                    hansard_search_interface(mp_name, mp_id)
                else:
                    st.info("Select an MP first to search parliamentary records.")

    # Combine manual comments with hansard comments
    all_comments = comments + st.session_state.hansard_comments_added

    return all_comments if st.session_state.show_comments else st.session_state.hansard_comments_added



def main_app():
    """Wizard-style step-by-step flow"""
    force_css_reload()
    create_custom_header()
    create_progress_indicator_navigation()

    # Get current step from session state
    current_step = st.session_state.get('wizard_step', 1)

    # Route to appropriate step
    if current_step == 1:
        wizard_step_1_select_mp()
    elif current_step == 2:
        wizard_step_2_configure()
    elif current_step == 3:
        wizard_step_3_add_information()
    elif current_step == 4:
        wizard_step_4_generate()

    # Enhanced sidebar (existing function)
    create_enhanced_sidebar()

def main():
    """Main entry point with wizard initialization"""

    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'wizard_step' not in st.session_state:  # ADD THIS
        st.session_state.wizard_step = 1
    if 'generation_cancelled' not in st.session_state:
        st.session_state.generation_cancelled = False
    if 'biography_generated' not in st.session_state:
        st.session_state.biography_generated = False
    if 'mp_search_results' not in st.session_state:  # ADD THIS
        st.session_state.mp_search_results = None


    if not st.session_state.authenticated:
        styled_login_page()
        return

    # User is authenticated - setup API keys
    setup_api_keys()

    # Run main app (which handles ALL content including sidebar)
    main_app()


if __name__ == "__main__":
    main()
