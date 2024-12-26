from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.shared import OxmlElement
from docx.oxml.ns import qn  # Changed from ns to qn
from datetime import datetime
import docx.opc.constants
import anthropic
import os
import PyPDF2
import re
import requests
import io
import wikipediaapi




def create_hyperlink(paragraph, text, url):
    """Create a hyperlink in a paragraph"""
    # Create relationship
    part = paragraph.part
    r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)

    # Create hyperlink element
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)

    # Create new run
    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')

    # Set font
    rFont = OxmlElement('w:rFonts')
    rFont.set(qn('w:ascii'), 'Hanken Grotesk')
    rFont.set(qn('w:hAnsi'), 'Hanken Grotesk')
    rPr.append(rFont)

    # Add bold
    b = OxmlElement('w:b')
    rPr.append(b)

    # Set font size
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), '16')  # 16 half-points = 8 points
    rPr.append(sz)

    # Set color
    color = OxmlElement('w:color')
    color.set(qn('w:val'), '808080')  # Grey
    rPr.append(color)

    new_run.append(rPr)

    # Add text
    t = OxmlElement('w:t')
    t.text = text
    new_run.append(t)

    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)

def clean_text(text):
    """Clean up the text format"""
    # Handle list or string input
    if isinstance(text, list):
        text = '\n'.join(str(item) for item in text)

    # Convert to string if it isn't already
    text = str(text)

    # Remove TextBlock wrapper
    if 'TextBlock(text=' in text:
        text = text.split('TextBlock(text=\'')[1].split('\', type=\'text\')')[0]

    # Replace escaped characters
    text = text.replace('\\n', '\n')
    text = text.replace('\\\'', "'")

    # Replace straight quotes with curly quotes
    text = text.replace('"', '"').replace('"', '"')

    # Remove empty lines while preserving intentional spacing
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        if line.strip():
            cleaned_lines.append(line.strip())
        else:
            cleaned_lines.append('')  # Preserve empty lines for spacing

    return '\n'.join(cleaned_lines)

def get_mp_id(mp_name):
    """Search for MP and return their ID"""
    try:
        # Make API request to search for MP
        search_url = f"https://members-api.parliament.uk/api/Members/Search?Name={mp_name}"
        response = requests.get(search_url)
        if response.status_code == 200:
            data = response.json()
            if data['items'] and len(data['items']) > 0:
                return data['items'][0]['value']['id']
    except Exception as e:
        print(f"Error searching for MP: {str(e)}")
    return None

async def get_verified_positions(mp_id):
    """Get verified committee memberships and roles from Parliament API"""
    try:
        verified_data = {
            'current_committees': [],
            'historical_committees': [],
            'current_roles': [],
            'historical_roles': [],
            'api_response': None
        }

        bio_url = f"https://members-api.parliament.uk/api/Members/{mp_id}/Biography"
        bio_response = requests.get(bio_url)
        
        if bio_response.status_code == 200:
            bio_data = bio_response.json()['value']
            verified_data['api_response'] = bio_data
            
            # Process committee memberships - they're under 'committeeMemberships' directly
            if bio_data.get('committeeMemberships'):
                for committee in bio_data['committeeMemberships']:
                    committee_info = {
                        'name': committee.get('name'),
                        'start_date': committee.get('startDate', '')[:10] if committee.get('startDate') else None,
                        'end_date': committee.get('endDate', '')[:10] if committee.get('endDate') else 'present'
                    }
                    
                    # Check if current or historical based on endDate
                    if not committee.get('endDate'):
                        verified_data['current_committees'].append(committee_info)
                    else:
                        verified_data['historical_committees'].append(committee_info)

            # Process government posts
            if bio_data.get('governmentPosts'):
                for post in bio_data['governmentPosts']:
                    post_info = {
                        'name': post.get('name'),
                        'start_date': post.get('startDate', '')[:10] if post.get('startDate') else None,
                        'end_date': post.get('endDate', '')[:10] if post.get('endDate') else 'present'
                    }
                    
                    if not post.get('endDate'):
                        verified_data['current_roles'].append(post_info)
                    else:
                        verified_data['historical_roles'].append(post_info)

            # Process opposition posts
            if bio_data.get('oppositionPosts'):
                for post in bio_data['oppositionPosts']:
                    post_info = {
                        'name': post.get('name'),
                        'start_date': post.get('startDate', '')[:10] if post.get('startDate') else None,
                        'end_date': post.get('endDate', '')[:10] if post.get('endDate') else 'present'
                    }
                    
                    if not post.get('endDate'):
                        verified_data['current_roles'].append(post_info)
                    else:
                        verified_data['historical_roles'].append(post_info)

        return verified_data

    except Exception as e:
        print(f"Error fetching verified positions: {str(e)}")
        return verified_data
    
        
def get_mp_portrait(mp_id):
    """Get MP's thumbnail image"""
    if not mp_id:
        return None

    try:
        thumbnail_url = f"https://members-api.parliament.uk/api/Members/{mp_id}/Thumbnail"
        response = requests.get(thumbnail_url)
        if response.status_code == 200:
            return io.BytesIO(response.content)
    except Exception as e:
        print(f"Error getting MP thumbnail: {str(e)}")
    return None

def get_mp_data(mp_id):
    """Get comprehensive MP data from various API endpoints"""
    data = {
        'biography': None,
        'experience': None,
        'interests': None,
        'focus': None,
        'committees': None,
        'contact': None
    }

    if not mp_id:
        return data

    try:
        # Get biography
        bio_url = f"https://members-api.parliament.uk/api/Members/{mp_id}/Biography"
        bio_response = requests.get(bio_url)
        if bio_response.status_code == 200:
            data['biography'] = bio_response.json()['value']

        # Get experience
        exp_url = f"https://members-api.parliament.uk/api/Members/{mp_id}/Experience"
        exp_response = requests.get(exp_url)
        if exp_response.status_code == 200:
            data['experience'] = exp_response.json()['value']

        # Get registered interests
        interests_url = f"https://members-api.parliament.uk/api/Members/{mp_id}/RegisteredInterests"
        interests_response = requests.get(interests_url)
        if interests_response.status_code == 200:
            data['interests'] = interests_response.json()['value']

        # Get focus areas
        focus_url = f"https://members-api.parliament.uk/api/Members/{mp_id}/Focus"
        focus_response = requests.get(focus_url)
        if focus_response.status_code == 200:
            data['focus'] = focus_response.json()['value']

        # Get committee memberships from biography if available
        if data['biography']:
            data['committees'] = data['biography'].get('committeeMemberships', [])

        # Get contact information
        contact_url = f"https://members-api.parliament.uk/api/Members/{mp_id}/Contact"
        contact_response = requests.get(contact_url)
        if contact_response.status_code == 200:
            data['contact'] = contact_response.json()['value']

    except Exception as e:
        print(f"Error fetching MP data: {str(e)}")

    return data

def format_mp_data(mp_data):
    """Format MP data into structured text"""
    formatted_text = ""

    try:
        # Add biography information
        if mp_data['biography']:
            if mp_data['biography'].get('governmentPosts'):
                formatted_text += "\nGovernment Posts:\n"
                for post in mp_data['biography']['governmentPosts']:
                    formatted_text += f"- {post.get('name', '')}"
                    if post.get('startDate'):
                        formatted_text += f" ({post['startDate'][:10]} to {post.get('endDate', 'present')[:10]})\n"

            if mp_data['biography'].get('committeesMemberships'):
                formatted_text += "\nCommittee Memberships:\n"
                for committee in mp_data['biography']['committeeMemberships']:
                    formatted_text += f"- {committee.get('name', '')}"
                    if committee.get('startDate'):
                        formatted_text += f" ({committee['startDate'][:10]} to {committee.get('endDate', 'present')[:10]})\n"

        # Add focus areas
        if mp_data['focus']:
            formatted_text += "\nAreas of Focus:\n"
            for focus in mp_data['focus']:
                if focus.get('category'):
                    formatted_text += f"- {focus['category']}: "
                    formatted_text += ", ".join(focus.get('focus', [])) + "\n"

        # Add experience
        if mp_data['experience']:
            formatted_text += "\nProfessional Background:\n"
            for exp in mp_data['experience']:
                if exp.get('title'):
                    formatted_text += f"- {exp['title']}"
                    if exp.get('organisation'):
                        formatted_text += f", {exp['organisation']}"
                    formatted_text += "\n"

    except Exception as e:
        print(f"Error formatting MP data: {str(e)}")

    return formatted_text

def read_pdf(file_path):
    """Read and extract text from PDF"""
    try:
        with open(file_path, 'rb') as file:
            # Create PDF reader object
            pdf_reader = PyPDF2.PdfReader(file)

            # Extract text from all pages
            sections = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                # Clean up the text
                text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
                sections.append(text)

            # Join all sections with proper spacing
            final_text = ' '.join(sections)

            # Extract key information
            summary_match = re.search(r'Summary(.*?)Current role', final_text, re.DOTALL)
            if summary_match:
                summary = summary_match.group(1).strip()
            else:
                summary = ""

            # Clean up and structure the text
            structured_text = "Summary:\n" + summary + "\n\n"

            # Add additional sections if found
            for section in ["Current role", "Previous roles", "World view and political affiliations"]:
                section_match = re.search(f"{section}(.*?)(Current|World view|Background|Election|\Z)", final_text, re.DOTALL)
                if section_match:
                    structured_text += f"{section}:\n{section_match.group(1).strip()}\n\n"

            # Remove any registration dates, donor details, etc.
            structured_text = re.sub(r'\(Registered.*?\)', '', structured_text)
            structured_text = re.sub(r'Address of donor:.*?\n', '', structured_text)

            return structured_text.strip()

    except Exception as e:
        print(f"Error reading PDF: {str(e)}")
        return None

def read_example_bios():
    examples = []
    try:
        for file in os.listdir('example_bios'):
            if file.endswith('.docx'):
                print(f"Processing: {file}")
                doc = Document(os.path.join('example_bios', file))

                # Get all text content
                full_text = ' '.join(str(paragraph.text) for paragraph in doc.paragraphs)

                # Clean the text
                cleaned_text = clean_text(full_text)
                if cleaned_text:
                    examples.append(cleaned_text)
                print(f"Successfully processed {file}")
    except Exception as e:
        print(f"Error processing DOCX: {str(e)}")
        raise

    return '\n\n---\n\n'.join(examples)

def read_input_file(file_path):
    """Read and return the contents of the input file"""
    with open(file_path, 'r') as file:
        return file.read()

def get_wiki_data(mp_name):
    """Get MP data from Wikipedia"""
    try:
        # Initialize Wikipedia API
        wiki = wikipediaapi.Wikipedia(
            user_agent='MP_Biography_Generator (yourname@example.com)',
            language='en'
        )

        # Try different variations of the name
        possible_titles = [
            mp_name,
            f"{mp_name} (politician)",
            f"{mp_name} MP"
        ]

        page = None
        for title in possible_titles:
            page = wiki.page(title)
            if page.exists():
                break

        if page and page.exists():
            return page.summary
        return None

    except Exception as e:
        print(f"Error fetching Wikipedia data: {str(e)}")
        return None

def get_wiki_url(mp_name):
    """Get Wikipedia URL for MP"""
    try:
        wiki = wikipediaapi.Wikipedia(
            user_agent='MP_Biography_Generator (yourname@example.com)',
            language='en'
        )

        possible_titles = [
            mp_name,
            f"{mp_name} (politician)",
            f"{mp_name} MP"
        ]

        for title in possible_titles:
            page = wiki.page(title)
            if page.exists():
                return page.fullurl
        return None

    except Exception as e:
        print(f"Error getting Wikipedia URL: {str(e)}")
        return None


def generate_biography(mp_name, input_content, examples, verified_positions=None):
    # Validate and clean inputs
    if isinstance(input_content, list):
        input_content = ' '.join(str(x) for x in input_content)
    if isinstance(examples, list):
        examples = ' '.join(str(x) for x in examples)

    # Ensure both are strings
    input_content = str(input_content).strip()
    examples = str(examples).strip()

    # Provide a fallback if no content is found
    if not input_content:
        # Default to a generic biography structure
        input_content = f"Background information for {mp_name} could not be found. Further research is needed."

    # Get Wikipedia data as a fallback
    wiki_content = get_wiki_data(mp_name)

    client = anthropic.Client(api_key=os.getenv('ANTHROPIC_API_KEY'))

    # Combine input content with Wikipedia if available
    if wiki_content:
        input_content = f"{input_content}\n\nWikipedia information:\n{wiki_content}"
        # Create the prompt
    current_date = datetime.now().strftime('%Y-%m-%d')  # Get current date in YYYY-MM-DD format

    # Create verified positions text for prompt only
    verified_positions_text = "\nVERIFIED POSITIONS (For reference - do not list explicitly):\n"
    
    if verified_positions:
        has_any_positions = False
        
        if verified_positions['current_committees']:
            has_any_positions = True
            verified_positions_text += "\nCommittee Memberships:\n"
            for committee in verified_positions['current_committees']:
                verified_positions_text += f"- {committee['name']} (Since {committee['start_date']})\n"
                
        if verified_positions['current_roles']:
            has_any_positions = True
            verified_positions_text += "\nGovernment/Opposition Roles:\n"
            for role in verified_positions['current_roles']:
                verified_positions_text += f"- {role['name']} (Since {role['start_date']})\n"
                
        if not has_any_positions:
            verified_positions_text += "\nNo current committee memberships or government/opposition roles found. Do not include any such positions in the biography.\n"
    else:
        verified_positions_text += "\nNo verified position data available. Do not include any committee memberships or government/opposition roles in the biography.\n"
        
    prompt = f"""Using these examples as a guide for style ONLY, generate a new biography for {mp_name}.

    IMPORTANT: Use ONLY the following verified positions when mentioning committee memberships and roles. 
    DO NOT list them explicitly, but incorporate them naturally into the narrative:
    {verified_positions_text}
    
    DO NOT include any committee memberships or roles that are not listed above, even if you find them in other sources.
    The biography should follow the exact same structure and sections as the examples, including:

    1. The MP's name and role as a title
    2. Their party and constituency in parentheses on a seperate line
    3. A brief introduction paragraph
    4. A "Politics" section with a clear heading
    5. A "Background" section with a clear heading

    Example biography for style reference:
    {examples}

    Information to use for the new biography:
    {input_content}

    Important requirements:
    1. Match the exact formatting and style of the example, including the placement of newlines and section headers
    2. Use ONLY information from the provided input content and Wikipedia
    3. Rephrase and restructure the information - do not copy phrases directly
    4. Maintain the same professional tone and level of detail
    5. Use clear section headers with proper spacing before and after
    6. Focus on the most significant aspects of their career and current role, be specific and detailed
    7. Organise information chronologically within each section
    8. Keep sentences concise, factual, and clear - do not waffle
    9. Use British English spelling AT ALL TIMES
    10. Do not include the detailed list of donations or DOB
    11. Include current significant roles and committee memberships in the top section
    12. Be VERY VERY careful in being accurate with dates, using today's current date ({current_date}) as reference to determine both past AND current roles
    13. Be sure to be VERY careful in being accurate with Committee names, memberships, and government roles if applicable"""

    try:
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            temperature=0.7,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Ensure we return a string
        biography = str(response.content[0].text)  # Changed this line
        return biography

    except Exception as e:
        print(f"Error in biography generation: {str(e)}")
        raise

def apply_heading_style(paragraph):
    """Apply consistent styling to headings"""
    run = paragraph.runs[0]
    run.font.bold = True
    run.font.size = Pt(12)
    run.font.name = 'Calibri'
    paragraph.space_before = Pt(12)
    paragraph.space_after = Pt(6)

def apply_body_style(paragraph):
    """Apply consistent styling to body text"""
    for run in paragraph.runs:
        run.font.name = 'Calibri'
        run.font.size = Pt(11)
    paragraph.space_after = Pt(6)

def save_biography(mp_name, content, has_pdf=False, has_api_data=False, has_wiki_data=False, wiki_url=None):
    doc = Document()

    # Define colors
    TEAL_COLOR = RGBColor(0, 161, 154)
    GREY_COLOR = RGBColor(128, 128, 128)

    # Add source information in header section
    section = doc.sections[0]
    header = section.header
    source_para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()

    # Get current date
    current_date = datetime.now().strftime('%d %B %Y')

    # Prepare source text parts
    source_text_start = f"AI generated MP biography on {current_date}. Sources: "
    sources = []
    if has_pdf:
        sources.append("user submitted PDF")
    if has_api_data:
        sources.append("Parliament's API data")

    # Add the start of the text
    run = source_para.add_run(source_text_start)
    run.font.name = 'Hanken Grotesk'
    run.font.size = Pt(8)
    run.font.bold = True
    run.font.color.rgb = GREY_COLOR

    if sources:
        run = source_para.add_run(" and ".join(sources))
        run.font.name = 'Hanken Grotesk'
        run.font.size = Pt(8)
        run.font.bold = True
        run.font.color.rgb = GREY_COLOR

        if has_wiki_data and wiki_url:
            run = source_para.add_run(" and ")
            run.font.name = 'Hanken Grotesk'
            run.font.size = Pt(8)
            run.font.bold = True
            run.font.color.rgb = GREY_COLOR

            # Add Wikipedia as hyperlink
            create_hyperlink(source_para, "Wikipedia", wiki_url)
    else:
        run = source_para.add_run("none")
        run.font.name = 'Hanken Grotesk'
        run.font.size = Pt(8)
        run.font.bold = True
        run.font.color.rgb = GREY_COLOR

    source_para.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT


    # Try to add MP's portrait
    mp_id = get_mp_id(mp_name)
    if mp_id:
        portrait = get_mp_portrait(mp_id)
        if portrait:
            doc.add_picture(portrait, width=Inches(2))  # Set width to 2 inches
            doc.add_paragraph()   # Add spacing after image

    # Clean and process the content
    content = clean_text(content)
    paragraphs = content.split('\n')

    # Process each paragraph
    for i in range(len(paragraphs)):
        para = paragraphs[i].strip()

        if para:
            p = doc.add_paragraph()

            # Title (first paragraph)
            if i == 0:
                run = p.add_run(para.strip())
                run.font.name = 'Hanken Grotesk'
                run.font.size = Pt(10)
                run.font.weight = 700  # Bold weight
                run.font.color.rgb = TEAL_COLOR

            # Party and constituency line
            elif para.strip().startswith('(Labour'):
                run = p.add_run(para.strip())
                run.font.name = 'Hanken Grotesk'
                run.font.size = Pt(10)
                run.font.weight = 400  # Regular weight
                run.font.color.rgb = RGBColor(0, 0, 0)  # Black

            # Section headers
            elif para.strip() in ['Politics', 'Background']:
                run = p.add_run(para.strip())
                run.font.name = 'Hanken Grotesk'
                run.font.size = Pt(10)
                run.font.weight = 400  # Regular weight
                run.font.color.rgb = TEAL_COLOR

            # Regular paragraphs
            else:
                run = p.add_run(para.strip())
                run.font.name = 'Hanken Grotesk'
                run.font.size = Pt(10)
                run.font.weight = 300  # Light weight
                run.font.color.rgb = RGBColor(0, 0, 0)  # Black

    filename = f'new_bios/{mp_name}_biography.docx'
    doc.save(filename)
    return filename



def main():
    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("Please set your ANTHROPIC_API_KEY first!")
        return

    # Get MP name
    mp_name = input("Enter MP name: ").strip()

    # Check if biography already exists
    if os.path.exists(f'new_bios/{mp_name}_biography.docx'):
        print(f"Biography already exists for {mp_name}")
        return

    # Get input file path
    input_path = input("Enter path to PDF file: ").strip()
    if not os.path.exists(input_path):
        print("File not found!")
        return

    try:
        # Read examples
        print("Reading example biographies...")
        examples = read_example_bios()

        # Read PDF input
        print("Reading PDF file...")
        input_content = read_pdf(input_path)
        has_pdf = input_content is not None

        
        # Get MP ID and API data
        mp_id = get_mp_id(mp_name)
        verified_positions = asyncio.run(get_verified_positions(mp_id)) if mp_id else None
        
        # Generate biography with verified positions
        biography = generate_biography(mp_name, input_content, examples, verified_positions)
        # Get Wikipedia data
        print("Fetching Wikipedia data...")
        wiki_data = get_wiki_data(mp_name)
        has_wiki_data = wiki_data is not None

        if input_content is None:
            print("Error reading PDF file")
            return

        # Generate biography
        print("Generating biography...")
        biography = generate_biography(mp_name, input_content, examples)

        # Get Wikipedia URL if data exists
        wiki_url = get_wiki_url(mp_name) if has_wiki_data else None

        # Save biography
        print("Saving biography...")
        saved_path = save_biography(mp_name, biography,
                                has_pdf=has_pdf,
                                has_api_data=has_api_data,
                                has_wiki_data=has_wiki_data,
                                wiki_url=wiki_url)
        print(f"Biography saved to {saved_path}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
