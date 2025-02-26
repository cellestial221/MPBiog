import streamlit as st
import os
from docx import Document
import io
import asyncio
import json
from datetime import datetime
from mp_functions import (
    read_example_bios,
    get_mp_id,
    get_mp_data,
    get_wiki_data,
    get_wiki_url,
    generate_biography,
    save_biography,
    get_verified_positions
)

# Set page config
st.set_page_config(page_title="MP Biography Generator", layout="wide")

# Create necessary folders
os.makedirs('uploads', exist_ok=True)
os.makedirs('new_bios', exist_ok=True)
os.makedirs('example_bios', exist_ok=True)

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

            # Buttons for managing comments
            col1, col2, col3 = st.columns(3)
            with col1:
                st.button("Add Another Comment", on_click=add_comment_form)
            with col2:
                st.button("Cancel", on_click=cancel_comments, type="secondary")
            with col3:
                st.button("Done Adding Comments", on_click=toggle_comments, type="primary")

    return comments if st.session_state.show_comments else []

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

        # Relevant comments section - full width
        comments = relevant_comments_section()

        if st.button("Generate Biography") and mp_name:
            # Validate inputs
            if not mp_name.strip():
                st.error("Please enter an MP name")
                return

            try:
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Show progress
                status_text.text('Reading example biographies...')
                progress_bar.progress(10)
                examples = read_example_bios()

                # Use text input
                input_content = user_input_text if user_input_text else ""
                has_user_input = bool(user_input_text.strip())

                status_text.text('Fetching MP data...')
                progress_bar.progress(30)
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

                mp_data = get_mp_data(mp_id) if mp_id else None
                has_api_data = mp_data is not None and any(data for data in mp_data.values() if data)

                status_text.text('Fetching Wikipedia data...')
                progress_bar.progress(60)
                wiki_data = get_wiki_data(mp_name)
                has_wiki_data = wiki_data is not None
                wiki_url = get_wiki_url(mp_name) if has_wiki_data else None

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

                # Generate biography
                status_text.text('Generating biography...')
                progress_bar.progress(80)
                biography = generate_biography(mp_name, input_content, examples, verified_positions, comments)

                # Save biography
                status_text.text('Saving biography...')
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

        The biography will be generated using all available sources.
        """)

if __name__ == "__main__":
    main()
