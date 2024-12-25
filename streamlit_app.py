import streamlit as st
import os
from docx import Document
import io
from mp_functions import (
    read_example_bios,
    read_pdf,
    get_mp_id,
    get_mp_data,
    get_wiki_data,
    get_wiki_url,
    generate_biography,
    save_biography
)

# Set page config
st.set_page_config(page_title="MP Biography Generator", layout="wide")

# Create necessary folders
os.makedirs('uploads', exist_ok=True)
os.makedirs('new_bios', exist_ok=True)
os.makedirs('example_bios', exist_ok=True)

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
        uploaded_file = st.file_uploader("Upload PDF file (Optional)", type=['pdf'], help="PDF is optional. You can generate a biography using only API and Wikipedia data.")

        if st.button("Generate Biography") and mp_name:
            # Validate inputs
            if not mp_name.strip():
                st.error("Please enter an MP name")
                return

            try:
                pdf_path = None
                # Optional PDF processing
                if uploaded_file:
                    # Save uploaded file
                    pdf_path = os.path.join('uploads', uploaded_file.name)
                    with open(pdf_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())

                progress_bar = st.progress(0)
                status_text = st.empty()

                # Show progress
                status_text.text('Reading example biographies...')
                progress_bar.progress(10)
                examples = read_example_bios()

                # Optional PDF content
                input_content = ""
                has_pdf = False
                if pdf_path and os.path.exists(pdf_path):
                    status_text.text('Reading PDF file...')
                    progress_bar.progress(30)
                    input_content = read_pdf(pdf_path)
                    has_pdf = input_content is not None

                status_text.text('Fetching MP data...')
                progress_bar.progress(50)
                mp_id = get_mp_id(mp_name)
                mp_data = get_mp_data(mp_id) if mp_id else None
                has_api_data = mp_data is not None and any(data for data in mp_data.values() if data)

                status_text.text('Fetching Wikipedia data...')
                progress_bar.progress(70)
                wiki_data = get_wiki_data(mp_name)
                has_wiki_data = wiki_data is not None
                wiki_url = get_wiki_url(mp_name) if has_wiki_data else None

                # Combine all available information
                if not input_content and has_api_data:
                    # If no PDF, use formatted MP data as input content
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
                progress_bar.progress(90)
                biography = generate_biography(mp_name, input_content, examples)

                # Save biography
                status_text.text('Saving biography...')
                saved_path = save_biography(mp_name, biography,
                                        has_pdf=has_pdf,
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
            finally:
                # Clean up uploaded file if it exists
                if pdf_path and os.path.exists(pdf_path):
                    os.remove(pdf_path)

    with col2:
        st.header("Information")
        st.write("""
        This tool generates MP biographies using:
        - Optional user submitted PDF
        - Parliament's API data
        - Wikipedia information

        The biography will be generated using available sources.
        PDF upload is completely optional.
        """)

if __name__ == "__main__":
    main()
