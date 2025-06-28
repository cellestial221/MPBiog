import streamlit as st
import os
from docx import Document
import io
import asyncio
import json
import time
from datetime import datetime
import bcrypt
import requests
from difflib import SequenceMatcher
from functools import lru_cache
from mp_functions import (
    read_example_bios,
    get_mp_id,
    get_mp_data,
    get_wiki_data,
    get_wiki_url,
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

def relevant_comments_section():
    """Create and handle the relevant comments section UI"""
    comments = []

    if 'show_comments' not in st.session_state:
        st.session_state.show_comments = False
    if 'comment_count' not in st.session_state:
        st.session_state.comment_count = 1

    def toggle_comments():
        st.session_state.show_comments = not st.session_state.show_comments
        if not st.session_state.show_comments:
            st.session_state.comment_count = 1

    def add_comment_form():
        st.session_state.comment_count += 1

    def cancel_comments():
        st.session_state.show_comments = False
        st.session_state.comment_count = 1

    if not st.session_state.show_comments:
        st.button("Add Relevant Comments", on_click=toggle_comments, key="add_comments")
    else:
        with st.container():
            st.subheader("Relevant Comments")
            st.write("Add comments or remarks made by the MP from various sources. These will appear as bullet points at the end of the biography.")

            for i in range(st.session_state.comment_count):
                with st.expander(f"Comment {i+1}", expanded=(i == st.session_state.comment_count-1)):
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
                st.button("Add Another Comment", on_click=add_comment_form)
            with col2:
                st.button("Cancel Comments", on_click=cancel_comments, type="secondary")

    return comments if st.session_state.show_comments else []

def cancel_generation():
    """Set the cancel flag to true"""
    st.session_state.cancel_generation = True
    st.warning("Cancellation requested. The process will stop at the next checkpoint.")

def main_app(perplexity_api_key):
    """Main application logic with enhanced MP validation"""
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

            # Relevant comments section
            comments = relevant_comments_section()

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

                                    wiki_data = get_wiki_data(mp_name)
                                    has_wiki_data = wiki_data is not None
                                    wiki_url = get_wiki_url(mp_name) if has_wiki_data else None

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

                                    saved_path = save_biography(mp_name, biography,
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
            - Perplexity AI web search (optional)

            **New: Enhanced MP Validation & Biography Length Control**
            - Only verified MPs can be selected
            - Real-time search with suggestions
            - Protection against invalid entries
            - Shows party and constituency information
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
                Try searching for:
                - **"Keir Starmer"** → Direct match
                - **"Starmer"** → Shows suggestion
                - **"Alec Shelbrooke"** → Finds "Sir Alec Shelbrooke"
                - **"Angela Rayner"** → Direct match
                - **"Boris"** → Shows multiple suggestions
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

                **Length Control:**
                - Adaptive token limits based on length
                - Tailored prompts for each length setting
                - Optimised for different use cases
                """)

            # Removed search interface preview as requested

def main():
    """Main entry point with custom authentication"""

    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("MP Biography Generator")
        st.subheader("Please log in to continue")

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login")

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

        # Add cache controls for debugging
        st.header("Cache Controls")
        if st.button("🗑️ Clear MP Search Cache", help="Clear cached search results for better performance"):
            cached_search_mps.cache_clear()
            st.success("Cache cleared!")

    # Run main app
    main_app(perplexity_api_key)

if __name__ == "__main__":
    main()
