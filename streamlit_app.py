import streamlit as st
import os
from docx import Document
import io
import asyncio
import json
import time
from datetime import datetime
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

# Initialize session state for cancel mechanism
if 'cancel_generation' not in st.session_state:
    st.session_state.cancel_generation = False

def display_verified_positions(verified_data):
    """Display verified Parliamentary positions in the sidebar"""
    st.sidebar.title("Verified Parliament Data")

    if not verified_data:
        st.sidebar.warning("No verified data available from Parliament API")
        return

    # Current Committees
    st.sidebar.subheader("Current Committee Memberships")
    if verified_data['current_committees']:
        for committee in verified_data['current_committees']:
            st.sidebar.markdown(f"• **{committee['name']}**  \n"
                              f"  Since: {committee['start_date']}")
    else:
        st.sidebar.info("No current committee memberships")

    # Current Roles
    st.sidebar.subheader("Current Government/Opposition Roles")
    if verified_data['current_roles']:
        for role in verified_data['current_roles']:
            st.sidebar.markdown(f"• **{role['name']}**  \n"
                              f"  Since: {role['start_date']}")
    else:
        st.sidebar.info("No current government/opposition roles")

    # Historical Data (Collapsible)
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

    # Debug Data (Collapsible)
    if verified_data.get('api_response'):
        with st.sidebar.expander("Debug: Raw API Data"):
            st.json(verified_data['api_response'])

def relevant_comments_section():
    """Create and handle the relevant comments section UI"""
    comments = []

    # Initialize session state variables
    if 'show_comments' not in st.session_state:
        st.session_state.show_comments = False
    if 'comment_count' not in st.session_state:
        st.session_state.comment_count = 1

    # Functions to handle state changes
    def toggle_comments():
        st.session_state.show_comments = not st.session_state.show_comments
        # Reset comment count when toggling off
        if not st.session_state.show_comments:
            st.session_state.comment_count = 1

    def add_comment_form():
        st.session_state.comment_count += 1

    def cancel_comments():
        st.session_state.show_comments = False
        st.session_state.comment_count = 1

    # Button to toggle comments visibility
    if not st.session_state.show_comments:
        st.button("Add Relevant Comments", on_click=toggle_comments, key="add_comments")
    else:
        # Full width container for comments
        with st.container():
            st.subheader("Relevant Comments")
            st.write("Add comments or remarks made by the MP from various sources. These will appear as bullet points at the end of the biography.")

            # Create forms for each comment
            for i in range(st.session_state.comment_count):
                with st.expander(f"Comment {i+1}", expanded=(i == st.session_state.comment_count-1)):
                    # Use full width for all elements
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
                        height=150,  # Increased height
                        key=f"text_{i}"
                    )

                    # Only add to comments list if text is filled
                    if comment_text:
                        comments.append({
                            "type": comment_type,
                            "url": comment_url,
                            "date": comment_date.strftime("%Y-%m-%d"),
                            "text": comment_text
                        })

            # Buttons for managing comments - simplified to just two options
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

def main():
    st.title("MP Biography Generator")

    # Add sidebar for API key
    with st.sidebar:
        st.header("Settings")
        api_key = st.text_input("Enter your Anthropic API key:", type="password")
        if api_key:
            os.environ['ANTHROPIC_API_KEY'] = api_key
        else:
            st.warning("Please enter your Anthropic API key to continue")
            return

    # Main interface
    col1, col2 = st.columns(2)

    with col1:
        # Input section
        st.header("Input")
        mp_name = st.text_input("Enter MP name:")

        # Text area for additional information
        user_input_text = st.text_area(
            "Enter additional information about the MP (Optional):",
            height=150,
            help="Add any additional information about the MP you'd like to include in the biography."
        )

        # Add Perplexity search option
        use_perplexity = st.checkbox("Search for MP's statements on specific issues using Perplexity AI",
                                  help="This will use Perplexity AI to search the web for statements made by the MP on specific issues. Note: This may increase biography generation time.")

        # Display additional fields if checkbox is selected
        issues = None
        perplexity_api_key = None
        if use_perplexity:
            issues = st.text_input("Issues to search for (e.g., 'climate change, farming, immigration'):",
                                help="Specify topics you want to find the MP's statements on")

            perplexity_api_key = st.text_input("Perplexity API Key:", type="password",
                                           help="Enter your Perplexity API key for web search")

        # Relevant comments section - full width
        comments = relevant_comments_section()

        generate_button = st.button("Generate Biography")

        if generate_button and mp_name:
            # Reset the cancel flag at the start of generation
            st.session_state.cancel_generation = False

            # Create a container for the cancel button and progress indicators
            progress_container = st.container()

            with progress_container:
                # Add cancel button prominently at the top
                st.button("Cancel Generation", on_click=cancel_generation, type="secondary")

                progress_bar = st.progress(0)
                status_text = st.empty()

                # Validate inputs
                if not mp_name.strip():
                    st.error("Please enter an MP name")
                    return

                try:
                    # Show progress
                    status_text.text('Reading example biographies...')
                    progress_bar.progress(10)

                    # Check for cancellation
                    if st.session_state.cancel_generation:
                        st.warning("Generation cancelled.")
                        return

                    examples = read_example_bios()

                    # Use text input
                    input_content = user_input_text if user_input_text else ""
                    has_user_input = bool(user_input_text.strip())

                    status_text.text('Fetching MP data...')
                    progress_bar.progress(25)

                    # Check for cancellation
                    if st.session_state.cancel_generation:
                        st.warning("Generation cancelled.")
                        return

                    mp_id = get_mp_id(mp_name)

                    # Get and display verified positions
                    verified_positions = None
                    if mp_id:
                        verified_positions = asyncio.run(get_verified_positions(mp_id))
                        with st.expander("API Diagnostics"):
                            st.write("MP ID:", mp_id)
                            st.write("API Response Status:", verified_positions.get('api_response') is not None)
                            if verified_positions.get('api_response'):
                                st.json(verified_positions['api_response'])
                            else:
                                st.error("No API response received")
                        display_verified_positions(verified_positions)

                    # Check for cancellation
                    if st.session_state.cancel_generation:
                        st.warning("Generation cancelled.")
                        return

                    mp_data = get_mp_data(mp_id) if mp_id else None
                    has_api_data = mp_data is not None and any(data for data in mp_data.values() if data)

                    status_text.text('Fetching Wikipedia data...')
                    progress_bar.progress(40)

                    # Check for cancellation
                    if st.session_state.cancel_generation:
                        st.warning("Generation cancelled.")
                        return

                    wiki_data = get_wiki_data(mp_name)
                    has_wiki_data = wiki_data is not None
                    wiki_url = get_wiki_url(mp_name) if has_wiki_data else None

                    # If Perplexity search is enabled, perform the search
                    if use_perplexity and issues and perplexity_api_key:
                        status_text.text('Searching for MP statements on specified issues...')
                        progress_bar.progress(60)

                        # Check for cancellation
                        if st.session_state.cancel_generation:
                            st.warning("Generation cancelled.")
                            return

                        try:
                            # Perform Perplexity search
                            perplexity_results = search_perplexity(mp_name, issues, perplexity_api_key)

                            # If there are results, create a comment to add to the list
                            if perplexity_results and "Error" not in perplexity_results:
                                # Create a new comment with today's date
                                perplexity_comment = {
                                    "type": "Perplexity AI Search Results",
                                    "url": "",
                                    "date": datetime.now().strftime("%Y-%m-%d"),
                                    "text": f"MP's positions on {issues}:\n\n{perplexity_results}"
                                }

                                # Add to comments if there are existing comments, otherwise create a new list
                                if comments:
                                    comments.append(perplexity_comment)
                                else:
                                    comments = [perplexity_comment]

                                # Display in debug section
                                with st.expander("Perplexity Search Results"):
                                    if perplexity_results:
                                        st.write(perplexity_results)
                                    else:
                                        st.write("No results found")
                        except Exception as e:
                            st.warning(f"Error performing Perplexity search: {str(e)}")
                            # Continue with biography generation even if search fails

                    with st.expander("Debug Information"):
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
                        # If no user input, use formatted MP data as input content
                        from mp_functions import format_mp_data
                        input_content = format_mp_data(mp_data)

                    # If still no content, use Wikipedia
                    if not input_content and has_wiki_data:
                        input_content = wiki_data

                    # Check if we have any content
                    if not input_content:
                        st.error("No information found for this MP. Please check the name and try again.")
                        return

                    # Check for cancellation
                    if st.session_state.cancel_generation:
                        st.warning("Generation cancelled.")
                        return

                    # Generate biography
                    status_text.text('Generating biography with Claude...')
                    progress_bar.progress(80)

                    # This step takes the longest, so check if cancelled
                    if st.session_state.cancel_generation:
                        st.warning("Generation cancelled.")
                        return

                    biography = generate_biography(mp_name, input_content, examples, verified_positions, comments)

                    # Save biography
                    status_text.text('Saving biography...')

                    # Check for cancellation before saving
                    if st.session_state.cancel_generation:
                        st.warning("Generation cancelled.")
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

                    st.success('Biography generated successfully!')
                    st.download_button(
                        label="Download Biography",
                        data=bio_bytes,
                        file_name=f"{mp_name}_biography.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

    with col2:
        st.header("Information")
        st.write("""
        This tool generates MP biographies using:
        - Your optional input text about the MP
        - Parliament's API data (verified positions shown in sidebar)
        - Wikipedia information
        - User-submitted relevant comments (optional)
        - Perplexity AI web search (optional)

        The biography will be generated using all available sources.
        """)

if __name__ == "__main__":
    main()
