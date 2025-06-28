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

# Set page config
st.set_page_config(page_title="MP Biography Generator", layout="wide")

# Create necessary folders
os.makedirs('uploads', exist_ok=True)
os.makedirs('new_bios', exist_ok=True)
os.makedirs('example_bios', exist_ok=True)

def inject_custom_css():
    """Inject custom CSS for professional branding - FIXED BUTTON SELECTORS"""
    st.markdown("""
    <style>
    /* Import better font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global styling */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* TARGET FORM SUBMIT BUTTONS SPECIFICALLY */
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

    button[kind="primaryFormSubmit"]:active {
        transform: translateY(0px) !important;
        box-shadow: 0 2px 4px rgba(34, 67, 71, 0.2) !important;
    }

    /* TARGET REGULAR BUTTONS */
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

    div.stButton > button:first-child:hover {
        background: linear-gradient(90deg, #1a3437, #008b85) !important;
        border-color: #008b85 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(34, 67, 71, 0.3) !important;
    }

    /* ALTERNATIVE TARGETING BY DATA-TESTID */
    button[data-testid="stBaseButton-primaryFormSubmit"] {
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

    button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
        background: linear-gradient(90deg, #1a3437, #008b85) !important;
        border-color: #008b85 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(34, 67, 71, 0.3) !important;
    }

    /* Input field styling */
    .stTextInput > div > div > input {
        border: 2px solid #e6e9ef !important;
        border-radius: 8px !important;
        padding: 0.75rem !important;
        font-size: 1rem !important;
        transition: border-color 0.2s ease !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #00A199 !important;
        box-shadow: 0 0 0 3px rgba(0, 161, 153, 0.1) !important;
        outline: none !important;
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

    /* Login page styling */
    .login-container {
        max-width: 400px;
        margin: 2rem auto;
        padding: 2rem;
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        border: 1px solid #e6e9ef;
    }

    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }

    .login-logo {
        width: 60px;
        height: 60px;
        margin: 0 auto 1rem;
        background: linear-gradient(135deg, #224347, #00A199);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 600;
        font-size: 0.8rem;
        text-align: center;
        line-height: 1.1;
        border: 2px dashed rgba(255,255,255,0.3);
    }

    .login-title {
        color: #224347;
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    .login-subtitle {
        color: #6c757d;
        font-size: 0.95rem;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Remove default margins */
    .block-container {
        padding-top: 1rem;
    }

    </style>
    """, unsafe_allow_html=True)# Replace the test_hansard_api() function with this simplified version:
#
def styled_login_page():
    """Complete replacement for the login section"""
    inject_custom_css()

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div class="login-container">
            <div class="login-header">
                <div class="login-logo">YOUR<br>LOGO</div>
                <div class="login-title">MP Biography Generator</div>
                <div class="login-subtitle">Please log in to continue</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

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
    """Cached version of MP search to improve performance"""
    if not query or len(query.strip()) < 2:
        return []

    try:
        search_url = f"https://members-api.parliament.uk/api/Members/Search"
        params = {
            'Name': query.strip(),
            'IsCurrentMember': True,
            'take': limit
        }

        response = requests.get(search_url, params=params, timeout=3)  # Further reduced timeout for local testing
        if response.status_code == 200:
            data = response.json()

            mps = []
            if data.get('items'):
                for item in data['items']:
                    member = item.get('value', {})

                    mp_info = {
                        'id': member.get('id'),
                        'name': member.get('nameDisplayAs', ''),
                        'party': member.get('latestParty', {}).get('name', '') if member.get('latestParty') else '',
                        'constituency': '',
                        'house': 'Commons'
                    }

                    latest_membership = member.get('latestHouseMembership', {})
                    if latest_membership:
                        mp_info['constituency'] = latest_membership.get('membershipFrom', '')
                        house_id = latest_membership.get('house')
                        mp_info['house'] = 'Commons' if house_id == 1 else 'Lords' if house_id == 2 else 'Unknown'

                    if mp_info['name'] and mp_info['id']:
                        mps.append(mp_info)

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
    """Enhanced validation with better name matching logic"""
    if not query or len(query.strip()) < 2:
        return {
            'is_valid': False,
            'exact_match': None,
            'suggestions': [],
            'message': 'Please enter at least 2 characters'
        }

    # Add debouncing - only search after user stops typing with longer delay for performance
    if 'last_search_time' not in st.session_state:
        st.session_state.last_search_time = 0

    current_time = time.time()
    if current_time - st.session_state.last_search_time < 1.0:  # Increased to 1 second for better performance
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

    best_match = mp_similarities[0]
    best_similarity = best_match[1]

    # More generous matching - if similarity is very high, consider it a match
    if best_similarity >= 0.9:  # Lowered threshold for better UX
        return {
            'is_valid': True,
            'exact_match': best_match[0],
            'suggestions': [],
            'message': f'✅ Found MP: {best_match[0]["name"]}'
        }

    # If similarity is good but not perfect, show as suggestion
    if best_similarity >= 0.7:
        return {
            'is_valid': False,
            'exact_match': None,
            'suggestions': [match[0] for match in mp_similarities[:5]],
            'message': f'Did you mean "{best_match[0]["name"]}"?'
        }

    # Return all suggestions
    return {
        'is_valid': False,
        'exact_match': None,
        'suggestions': [match[0] for match in mp_similarities[:10]],
        'message': f'Multiple MPs found. Please select one:'
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
        perplexity_key = st.secrets["api_keys"].get("perplexity", "")
        return perplexity_key
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


def cancel_generation():
    """Set the cancel flag to true"""
    st.session_state.cancel_generation = True
    st.warning("Cancellation requested. The process will stop at the next checkpoint.")

def main_app(perplexity_api_key):
    """Main application logic with enhanced MP validation and Hansard search"""
    st.title("MP Biography Generator")

    col1, col2 = st.columns(2)

    with col1:
        st.header("Input")

        # Enhanced MP selection with validation
        selected_mp = mp_name_input_with_validation()

        # Only show the rest of the form if an MP is selected
        if selected_mp:
            st.divider()
            mp_display_col, clear_button_col = st.columns([4, 1])

            # Display selected MP prominently
            with mp_display_col:
                st.success(f"✅ **Selected MP:** {selected_mp['name']} ({selected_mp['party']}) - {selected_mp['constituency']}")

            with clear_button_col:
                if st.button("🔄 Change MP", help="Clear selection to choose a different MP", key="change_mp_main"):
                    st.session_state.selected_mp = None
                    st.session_state.mp_search_query = ''
                    st.session_state.show_suggestions = False
                    st.session_state.validation_result = None
                    st.rerun()

            # Biography length slider
            st.subheader("Biography Length")
            length_options = {
                "Brief": "brief",
                "Standard": "medium",
                "Comprehensive": "comprehensive"
            }

            length_display = st.select_slider(
                "Choose biography length:",
                options=list(length_options.keys()),
                value="Standard",
                help="Brief: 2-3 short paragraphs covering key points only. Standard: Full biography matching example length. Comprehensive: Extended detail with additional sections."
            )

            length_setting = length_options[length_display]

            # Show length description
            length_descriptions = {
                "brief": "📝 **Brief**: Essential information only (2-3 short paragraphs, ~100-150 words)",
                "medium": "📄 **Standard**: Comprehensive biography following example format (standard length)",
                "comprehensive": "📚 **Comprehensive**: Extended detail with additional sections (~50-75% longer than standard)"
            }

            st.info(length_descriptions[length_setting])

            # Text area for additional information
            user_input_text = st.text_area(
                "Enter additional information about the MP (Optional):",
                height=150,
                help="Add any additional information about the MP you'd like to include in the biography."
            )

            # Add Perplexity search option
            use_perplexity = False
            issues = None
            if perplexity_api_key:
                use_perplexity = st.checkbox("Search for MP's statements on specific issues using Perplexity AI",
                                          help="This will use Perplexity AI to search the web for statements made by the MP on specific issues.")

                if use_perplexity:
                    issues = st.text_input("Issues to search for (e.g., 'climate change, farming, immigration'):",
                                        help="Specify topics you want to find the MP's statements on")

            # Relevant comments section with Hansard search - pass MP info
            comments = relevant_comments_section(selected_mp['name'], selected_mp['id'])

            # Generate button
            generate_button = st.button("Generate Biography", type="primary")

            if generate_button:
                            # Set generation flag to prevent re-validation
                            st.session_state.generation_in_progress = True

                            # Reset the cancel flag at the start of generation
                            st.session_state.cancel_generation = False

                            progress_container = st.container()

                            with progress_container:
                                st.button("Cancel Generation", on_click=cancel_generation, type="secondary")

                                progress_bar = st.progress(0)
                                status_text = st.empty()

                                try:
                                    # Use the selected MP data - we already have the ID!
                                    mp_name = selected_mp['name']
                                    mp_id = selected_mp['id']

                                    status_text.text('Reading example biographies...')
                                    progress_bar.progress(10)

                                    if st.session_state.cancel_generation:
                                        st.warning("Generation cancelled.")
                                        st.session_state.generation_in_progress = False
                                        return

                                    examples = read_example_bios()
                                    input_content = user_input_text if user_input_text else ""
                                    has_user_input = bool(user_input_text.strip())

                                    status_text.text('Fetching verified positions...')
                                    progress_bar.progress(25)

                                    if st.session_state.cancel_generation:
                                        st.warning("Generation cancelled.")
                                        st.session_state.generation_in_progress = False
                                        return

                                    # Get verified positions using the known MP ID - much more efficient!
                                    verified_positions = None
                                    try:
                                        # Test if we can get basic MP data
                                        test_url = f"https://members-api.parliament.uk/api/Members/{mp_id}"
                                        test_response = requests.get(test_url, timeout=5)
                                        if test_response.status_code == 200:
                                            st.write(f"✅ MP ID {mp_id} is valid")
                                            verified_positions = get_verified_positions(mp_id)
                                        else:
                                            st.error(f"Invalid MP ID: {mp_id}")
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                                        verified_positions = None

                                    if verified_positions:
                                        with st.expander("API Diagnostics"):
                                            st.write("MP ID:", mp_id)
                                            st.write("MP Name:", mp_name)
                                            st.write("API Response Status:", verified_positions.get('api_response') is not None)
                                            if verified_positions.get('api_response'):
                                                st.json(verified_positions['api_response'])
                                            else:
                                                st.error("No API response received")
                                        display_verified_positions(verified_positions)

                                    if st.session_state.cancel_generation:
                                        st.warning("Generation cancelled.")
                                        st.session_state.generation_in_progress = False
                                        return

                                    status_text.text('Fetching additional MP data...')
                                    progress_bar.progress(35)

                                    # Get additional MP data using the ID
                                    mp_data = get_mp_data(mp_id)
                                    has_api_data = mp_data is not None and any(data for data in mp_data.values() if data)

                                    status_text.text('Fetching Wikipedia data...')
                                    progress_bar.progress(45)

                                    if st.session_state.cancel_generation:
                                        st.warning("Generation cancelled.")
                                        st.session_state.generation_in_progress = False
                                        return

                                    # NEW CODE
                                    wiki_data = get_wiki_data_verified(selected_mp['name'], selected_mp['constituency'])
                                    has_wiki_data = wiki_data is not None
                                    wiki_url = get_wiki_url_verified(selected_mp['name'], selected_mp['constituency']) if has_wiki_data else None

                                    # After getting wiki_data, add this:
                                    if has_wiki_data:
                                        st.sidebar.success(f"✅ Wikipedia: Verified for {selected_mp['constituency']}")
                                    else:
                                        st.sidebar.warning("⚠️ Wikipedia: No verified page found")

                                    # Perplexity search
                                    if use_perplexity and issues and perplexity_api_key:
                                        status_text.text('Searching for MP statements on specified issues...')
                                        progress_bar.progress(60)

                                        if st.session_state.cancel_generation:
                                            st.warning("Generation cancelled.")
                                            st.session_state.generation_in_progress = False
                                            return

                                        try:
                                            perplexity_results = search_perplexity(mp_name, issues, perplexity_api_key)

                                            if perplexity_results and "Error" not in perplexity_results:
                                                perplexity_comment = {
                                                    "type": "Perplexity AI Search Results",
                                                    "url": "",
                                                    "date": datetime.now().strftime("%Y-%m-%d"),
                                                    "text": f"MP's positions on {issues}:\n\n{perplexity_results}"
                                                }

                                                if comments:
                                                    comments.append(perplexity_comment)
                                                else:
                                                    comments = [perplexity_comment]

                                                with st.expander("Perplexity Search Results"):
                                                    if perplexity_results:
                                                        st.write(perplexity_results)
                                                    else:
                                                        st.write("No results found")
                                        except Exception as e:
                                            st.warning(f"Error performing Perplexity search: {str(e)}")

                                    with st.expander("Debug Information"):
                                        st.subheader("Selected MP Info")
                                        st.json(selected_mp)

                                        st.subheader("Biography Settings")
                                        st.write(f"Length: {length_display} ({length_setting})")

                                        st.subheader("Wikipedia Data")
                                        if wiki_data:
                                            st.text("Wikipedia content found")
                                            st.text(f"Length: {len(wiki_data)} characters")
                                            st.text(wiki_data[:500] + "...")
                                        else:
                                            st.text("No Wikipedia content found")

                                        if comments:
                                            st.subheader("User Comments")
                                            st.json(comments)

                                    # Combine all available information
                                    if not input_content and has_api_data:
                                        from mp_functions import format_mp_data
                                        input_content = format_mp_data(mp_data)

                                    if not input_content and has_wiki_data:
                                        input_content = wiki_data

                                    if not input_content:
                                        st.error("No information found for this MP. Please check the name and try again.")
                                        st.session_state.generation_in_progress = False
                                        return

                                    if st.session_state.cancel_generation:
                                        st.warning("Generation cancelled.")
                                        st.session_state.generation_in_progress = False
                                        return

                                    # Generate biography with length setting - THIS IS THE KEY CHANGE
                                    status_text.text(f'Generating {length_display.lower()} biography with Claude...')
                                    progress_bar.progress(80)

                                    if st.session_state.cancel_generation:
                                        st.warning("Generation cancelled.")
                                        st.session_state.generation_in_progress = False
                                        return

                                    biography = generate_biography(mp_name, input_content, examples, verified_positions, comments, length_setting)

                                    # Save biography
                                    status_text.text('Saving biography...')

                                    if st.session_state.cancel_generation:
                                        st.warning("Generation cancelled.")
                                        st.session_state.generation_in_progress = False
                                        return

                                    saved_path = save_biography(mp_name, biography, comments,
                                                            has_pdf=False,
                                                            has_api_data=has_api_data,
                                                            has_wiki_data=has_wiki_data,
                                                            wiki_url=wiki_url)

                                    progress_bar.progress(100)
                                    status_text.text('Complete!')

                                    # Prepare file for download
                                    with open(saved_path, 'rb') as file:
                                        bio_bytes = file.read()

                                    st.success(f'{length_display} biography generated successfully!')
                                    st.download_button(
                                        label=f"Download {length_display} Biography",
                                        data=bio_bytes,
                                        file_name=f"{mp_name}_{length_setting}_biography.docx",
                                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                                    )

                                    # Reset generation flag
                                    st.session_state.generation_in_progress = False

                                except Exception as e:
                                    st.error(f"An error occurred: {str(e)}")
                                    st.session_state.generation_in_progress = False

        else:
            # Show helpful information when no MP is selected
            st.info("👆 Please search for and select an MP above to continue")

            with st.expander("💡 Tips for searching"):
                st.write("""
                - Try entering the MP's full name (e.g., "Keir Starmer")
                - You can search by surname only (e.g., "Starmer")
                - The search will show current MPs only
                - If you're unsure of the exact spelling, start typing and suggestions will appear
                - Use the constituency name if you're not sure of the MP's name
                """)

            with st.expander("🔍 How the search works"):
                st.write("""
                - **Real-time validation**: As you type, we check against Parliament's official database
                - **Fuzzy matching**: Even with slight misspellings, we'll find close matches
                - **Current MPs only**: Only sitting MPs will appear in results
                - **Detailed info**: See party affiliation and constituency for each suggestion
                - **No invalid entries**: You can't generate a biography for someone who isn't an MP
                """)

    with col2:
            st.header("Information")
            st.write("""
            This tool generates MP biographies using:
            - Your optional input text about the MP
            - Parliament's API data (verified positions shown in sidebar)
            - Wikipedia information
            - User-submitted relevant comments (optional)
            - **NEW: Hansard parliamentary records search**
            - Perplexity AI web search (optional)

            **New: Enhanced MP Validation & Hansard Search**
            - Only verified MPs can be selected
            - Real-time search with suggestions
            - AI-powered search of parliamentary records
            - Smart topic-based Hansard search
            - Choose biography length: Brief, Standard, or Comprehensive
            """)

            # Use columns for feature highlights
            info_col1, info_col2 = st.columns(2)

            with info_col1:
                st.markdown("""
                **🔍 Smart Search**
                - Real-time MP lookup
                - Handles titles (Sir, Dame, etc.)
                - Fuzzy name matching
                - Shows party & constituency
                """)

            with info_col2:
                st.markdown("""
                **✅ Validation**
                - Current MPs only
                - Prevents invalid entries
                - Multiple match handling
                - Instant feedback
                """)

            # NEW: Hansard search information
            with st.expander("🏛️ NEW: Hansard Search Features"):
                st.markdown("""
                **🤖 AI-Powered Search:**
                - Enter any topic (e.g., "climate change", "healthcare")
                - Claude generates optimized search terms
                - Searches parliamentary contribution records
                - Smart date filtering options

                **📋 Result Management:**
                - Browse through MP's statements on your topic
                - See debate titles, dates, and full text
                - Select specific contributions to include
                - Automatically formatted for biography

                **🎯 Smart Matching:**
                - Finds relevant statements using multiple search strategies
                - Shows which search term found each result
                - Removes duplicates automatically
                - Orders by relevance and date

                **⏰ Flexible Time Ranges:**
                - Last 6 months, 1 year, 2 years, or all available
                - Custom date range selection
                - Configurable result limits
                """)

            # Biography length options
            with st.expander("📏 Biography Length Options"):
                st.markdown("""
                **📝 Brief Biography:**
                - 2-3 short paragraphs
                - Essential information only
                - Current role and key highlights
                - ~100-150 words

                **📄 Standard Biography:**
                - Comprehensive coverage
                - Follows example format
                - Full career and background
                - Standard length (default)

                **📚 Comprehensive Biography:**
                - Extended detail
                - Additional sections
                - More context and background
                - ~50-75% longer than standard
                """)

            # Example searches
            with st.expander("📝 Example Searches"):
                st.markdown("""
                **MP Search Examples:**
                - **"Keir Starmer"** → Direct match
                - **"Starmer"** → Shows suggestion
                - **"Alec Shelbrooke"** → Finds "Sir Alec Shelbrooke"
                - **"Angela Rayner"** → Direct match
                - **"Boris"** → Shows multiple suggestions

                **Hansard Topic Examples:**
                - **"climate change"** → Finds environmental policy statements
                - **"NHS funding"** → Locates healthcare discussions
                - **"education"** → Discovers school and university debates
                - **"housing crisis"** → Finds property and planning statements
                """)

            # Performance info
            with st.expander("⚡ Performance Features"):
                st.markdown("""
                **Speed Optimizations:**
                - Response caching (faster repeated searches)
                - Reduced API timeouts (3s max)
                - Debounced search (waits for typing to stop)
                - Efficient name normalization

                **Smart Matching:**
                - Ignores titles and honorifics
                - Handles partial name matches
                - Orders results by relevance

                **Hansard Integration:**
                - Parallel search term processing
                - Duplicate removal algorithms
                - Smart result ranking
                - Efficient API usage
                """)

def main():
    """Main entry point with custom authentication"""

    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if 'show_debug' not in st.session_state:
        st.session_state.show_debug = False

    if not st.session_state.authenticated:
        styled_login_page()  # ← Just this one line!
        return

    # User is authenticated - show main app
    perplexity_api_key = setup_api_keys()

    # Sidebar with user info and logout
    with st.sidebar:
        st.header("Account")
        st.write(f"Welcome, {st.session_state.get('name', 'User')}")
        st.write(f"Email: {st.session_state.get('email', 'N/A')}")

        if st.button('Logout'):
            st.session_state.authenticated = False
            for key in ['name', 'username', 'email']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        # API Status
        st.header("API Status")
        st.success("✅ Anthropic API: Configured")
        if perplexity_api_key and perplexity_api_key != "your_perplexity_api_key_here":
            st.success("✅ Perplexity API: Available")
        else:
            st.warning("⚠️ Perplexity API: Not configured")

        # Check Hansard API
        try:
            hansard_test = requests.get("https://hansard-api.parliament.uk/overview/firstyear.json", timeout=3)
            if hansard_test.status_code == 200:
                st.success("✅ Hansard API: Available")
            else:
                st.warning("⚠️ Hansard API: Limited access")
        except:
            st.error("❌ Hansard API: Unavailable")

        # Add cache controls for debugging
        st.header("Cache Controls")
        if st.button("🗑️ Clear MP Search Cache", help="Clear cached search results for better performance"):
            cached_search_mps.cache_clear()
            st.success("Cache cleared!")

        if st.button("🗑️ Clear Hansard Results", help="Clear current Hansard search results"):
            if 'hansard_results' in st.session_state:
                del st.session_state.hansard_results
            if 'selected_hansard_items' in st.session_state:
                del st.session_state.selected_hansard_items
            if 'hansard_search_performed' in st.session_state:
                del st.session_state.hansard_search_performed
            st.success("Hansard cache cleared!")

        st.header("Debug Tools")
        if st.button("🧪 Debug Hansard API"):
            st.session_state.show_debug = True

        if st.session_state.get('show_debug', False):
            if st.button("❌ Close Debug"):
                st.session_state.show_debug = False
                st.rerun()
            test_hansard_api_simple()

    # Run main app
    main_app(perplexity_api_key)

if __name__ == "__main__":
    main()
