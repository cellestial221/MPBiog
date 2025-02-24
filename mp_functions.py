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

# Create verified positions text
    verified_positions_text = "\nVERIFIED PARLIAMENTARY INFORMATION:\n"
    
    if verified_positions:
        has_any_positions = False
        has_any_content = False
        
        # Add synopsis if available
        if verified_positions.get('synopsis'):
            has_any_content = True
            verified_positions_text += f"\nOFFICIAL SYNOPSIS:\n{verified_positions['synopsis']}\n"
        
        # Add committee memberships
        if verified_positions['current_committees']:
            has_any_positions = True
            verified_positions_text += "\nCurrent Committee Memberships:\n"
            for committee in verified_positions['current_committees']:
                verified_positions_text += f"- {committee['name']} (Since {committee['start_date']})\n"
        
        # Add roles
        if verified_positions['current_roles']:
            has_any_positions = True
            verified_positions_text += "\nCurrent Government/Opposition Roles:\n"
            for role in verified_positions['current_roles']:
                verified_positions_text += f"- {role['name']} (Since {role['start_date']})\n"
                
        if not has_any_positions:
            verified_positions_text += "\nNo current committee memberships or government/opposition roles found. Do not include any such positions in the biography.\n"
                
        # Add recent contributions if available
        if verified_positions.get('recent_contributions'):
            has_any_content = True
            contrib = verified_positions['recent_contributions']
            verified_positions_text += "\nRecent Parliamentary Activity:\n"
            if contrib['recent_debates']:
                for debate in contrib['recent_debates']:
                    debate_date = datetime.strptime(debate['date'][:10], '%Y-%m-%d').strftime('%d %B %Y')
                    verified_positions_text += f"- {debate['contributions']} contributions in '{debate['title']}' on {debate_date}\n"
            else:
                verified_positions_text += "No recent contributions found in Parliament.\n"
                
        if not has_any_content and not has_any_positions:
            verified_positions_text += "\nNo verified parliamentary information available. Do not include unverified committee memberships, roles, or parliamentary activities in the biography.\n"
            
    else:
        verified_positions_text += "\nNo verified position data available. Do not include any committee memberships, government/opposition roles, or parliamentary activities in the biography.\n"
        
    prompt = f"""Using these examples as a guide for style ONLY, generate a new biography for {mp_name}.

    CRITICAL REQUIREMENTS:
    1. ONLY include specific, verifiable facts about this MP - no generic statements about MP duties
    2. For career history, try to include named positions, companies, and years - no vague industry descriptions
    3. Focus on concrete facts: dates, organizations, position titles, qualifications, specific achievements
    4. DO NOT include any of these generic phrases or concepts:
       - "advocating for constituents' interests"
       - "matters that matter to constituents"    
    
    IMPORTANT: Use ONLY the following verified positions when mentioning committee memberships and roles. 
    DO NOT list them explicitly, but incorporate them naturally into the narrative:
    {verified_positions_text}
    
    DO NOT include any committee memberships or roles that are not listed above, even if you find them in other sources.
    The biography should follow the exact same structure and sections as the examples, including:

    1. The MP's name and role as a title
    2. Their party and constituency in parentheses on a seperate line
    3. A brief introduction paragraph with their current position and VERIFIED roles
    4. A "Politics" section with a clear heading, this should be the chunkiest section
    5. A "Background" section with a clear heading, focusing less on their politics and more on their life/career outside of politics

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
    8. Keep sentences fairly concise, factual, and clear
    9. Use British English spelling AT ALL TIMES
    10. Do not include the detailed list of donations
    11. Include current significant roles and committee memberships in the top section
    12. Be VERY VERY careful in being accurate with dates, using today's current date ({current_date}) as reference to determine both past AND current roles
    13. Be sure to be VERY careful in being accurate with Committee names, memberships, and government roles if applicable
    14. If recent parliamentary contributions are provided, include a SHORT 1-2 sentence summary at the end of the Politics section
    15. Use the official synopsis where provided, incorporating its verified information naturally into the narrative
    16. Do NOT include Date of Birth"""

    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",  # CHANGE 2: Updated model to Claude 3.7 Sonnet
            max_tokens=1000,
            temperature=0.7,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Ensure we return a string
        biography = str(response.content[0].text)
        return biography

    except Exception as e:
        print(f"Error in biography generation: {str(e)}")
        raise
