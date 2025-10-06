import os
import pdfplumber
import json

def main ():
    """ this one match with the style_2 of pdf very well so far"""
    
    pdf_folder = "pdf_files/style_2/text"
    output_folder = "json_files"
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all PDF files in the folder
    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_folder}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process\n")
    
    # Process each PDF file
    for pdf_index, pdf_filename in enumerate(pdf_files, 1):
        print(f"\n{'='*60}")
        print(f"Processing PDF {pdf_index}/{len(pdf_files)}: {pdf_filename}")
        print(f"{'='*60}")
        
        pdf_path = os.path.join(pdf_folder, pdf_filename)
        
        # Create output filenames based on PDF name (remove .pdf extension)
        base_name = os.path.splitext(pdf_filename)[0]
        school_json = os.path.join(output_folder, f"{base_name}_schools_data.json")
        student_json = os.path.join(output_folder, f"{base_name}_students_data.json")
        
        # Process this PDF
        try:
            process_single_pdf(pdf_path, school_json, student_json)
        except Exception as e:
            print(f"ERROR: Failed to process {pdf_filename}: {e}")
            continue
    
    print(f"\n{'='*60}")
    print("ALL FILES PROCESSED!")
    print(f"{'='*60}")


def process_single_pdf(pdf_path: str, school_json_path: str, student_json_path: str):
    """Process a single PDF file and export to JSON"""
    
    # Initialize combined data structures
    all_school_data = {
        "schools": []
    }
    all_student_data = {
        "students_by_school": []
    }
    
    # Track the last valid option and province found
    last_option = ""
    last_province = ""
    
    # Open PDF once and process all pages
    with pdfplumber.open(pdf_path, laparams={"detect_vertical": True}) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total pages: {total_pages}")
        
        # Process each page
        for page_num in range(total_pages):
            print(f"  Processing page {page_num + 1}/{total_pages}", end='\r')
            
            try:
                page = pdf.pages[page_num]
                
                # Extract header/footer and body separately
                header_footer = extract_header(page)
                body_text = extract_body(page)
                
                # Combine extracted sections
                extracted_result = {
                    "header": header_footer["header"],
                    "footer": header_footer["footer"],
                    "body": body_text
                }
                
                # Get school and student data for this page
                page_school_data = school_data(extracted_result)
                page_student_data = student_data(extracted_result)
                
                # Update last known option and province if found
                if page_school_data["school_option"]:
                    last_option = page_school_data["school_option"]
                if page_school_data["school_province"]:
                    last_province = page_school_data["school_province"]
                
                # Add schools from this page with current option/province
                for school in page_school_data["schools"]:
                    # If school doesn't have option/province, use the last known ones
                    if not school.get("school_option"):
                        school["school_option"] = last_option
                    if not school.get("school_province"):
                        school["school_province"] = last_province
                    all_school_data["schools"].append(school)
                
                # Add students from this page
                all_student_data["students_by_school"].extend(page_student_data["students_by_school"])
                
            except Exception as e:
                print(f"\n  Error on page {page_num + 1}: {e}")
                continue
    
    print()  
    
    # Export to JSON files
    export_school_json(all_school_data, school_json_path)
    export_student_json(all_student_data, student_json_path)
    
    print(f"Results:")
    print(f"  - Schools: {len(all_school_data['schools'])}")
    print(f"  - Students: {sum(len(s['students']) for s in all_student_data['students_by_school'])}")
    print(f"  - Saved to: {os.path.basename(school_json_path)} & {os.path.basename(student_json_path)}")


def export_school_json(data: dict, filename: str):
    """
    Export school data to a JSON file
    """
    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, ensure_ascii=False, indent=4)


def export_student_json(data: dict, filename: str):
    """
    Export student data to JSON file
    """
    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, ensure_ascii=False, indent=4)


def extract_header(page) -> dict:
    """
    Extract text from the header and footer sections.
    
    """
    width = page.width
    height = page.height
    
    # Define header and footer bounding box 
    header_bbox = (0, 0,width, height* 0.10) #this mean thu ende tu anziye mwazo ku x, y iko 0 kisha thu ende thu ku top 10% ya height ya page
    footer_bbox = (0, height * 0.90, width, height)
    
    # Extract header text with layout preserved
    header = page.within_bbox(header_bbox).extract_text(layout=True)
    footer = page.within_bbox(footer_bbox).extract_text(layout=True)
    
    # Clean and return header text
    header_text = (header or "").replace('\x00', '')
    footer_text = (footer or "").replace('\x00', '')
    
    return {
        "header": header_text,
        "footer": footer_text
    }


def extract_body(page) -> str:
    """
    Extract text from the body section by dividing it into three vertical parts.
    This helps maintain proper text extraction from multi-column PDF layouts.
    
    """
    width = page.width
    height = page.height
    
    # Define body boundaries (between header and footer)
    header = height * 0.08
    footer_start = height* 0.92

    body_top = header 
    body_bottom = footer_start
    #which mean tuna anziya mwazo ya page ti ku bottom kisha tuna tosha amo header


    part_width = width / 3



    body_part1_bbox = (0, body_top, part_width * 1.08, body_bottom)
    body_part2_bbox = (part_width * 1.05 , body_top, 1.94* part_width, body_bottom)
    body_part3_bbox = (1.90* part_width , body_top, width, body_bottom)

    body_part1 = page.within_bbox(body_part1_bbox).extract_text(layout=True)
    body_part2 = page.within_bbox(body_part2_bbox).extract_text(layout=True)
    body_part3 = page.within_bbox(body_part3_bbox).extract_text(layout=True)

    
    # Combine all parts
    body = body_part1 + body_part2 + body_part3
    
    # Clean and return combined body text
    body_text = (body or "").replace('\x00', '')
    
    return body_text


def extract_year_from_footer(footer_text: str) -> str:
    """
    Extract the year from footer text by looking for 4 digits between 
    "EXAMEN D'ETAT" and "http".
    """
    if not footer_text:
        return ""
    
    # Normalize the text by removing spaces around "EXAMEN D'ETAT" for easier matching
    footer_normalized = footer_text.replace(" ", "")
    
    # Look for "EXAMEND'ETAT" (or variations) and "http"
    # Handle different apostrophe variations: ' ' ´
    start_marker = None
    if "EXAMEND'ETAT" in footer_normalized:
        start_marker = "EXAMEND'ETAT"
    elif "EXAMEND'ETAT" in footer_normalized:
        start_marker = "EXAMEND'ETAT"
    elif "EXAMEND'ETAT" in footer_normalized:
        start_marker = "EXAMEND'ETAT"
    elif "EXAMEND´ETAT" in footer_normalized:
        start_marker = "EXAMEND´ETAT"
    
    if not start_marker or "http" not in footer_normalized:
        return ""
    
    # Split by the markers
    after_examen = footer_normalized.split(start_marker)[1]
    before_http = after_examen.split("http")[0]
    
    # The text between should be something like: "-2021" or "2021" or "-2021-" etc.
    year_section = before_http.strip("-").strip()
    
    # Find 4 consecutive digits in the section
    i = 0
    while i <= len(year_section) - 4:
        potential_year = year_section[i:i+4]
        if potential_year.isdigit():
            return potential_year
        i += 1
    
    return ""


def school_data(sections: dict) -> dict:
    """
    Extract school data from the extracted text sections
    Returns organized school information including header data and school_details datas...
    """
    result = {
        "school_option": "",
        "school_province": "",
        "schools": []
    }
    
    # Extract year from footer
    footer_text = sections.get("footer", "")
    year = extract_year_from_footer(footer_text)

    # Extract header information
    header_text = sections.get("header", "")
    page_option = ""
    page_province = ""
    
    if header_text:
        # Extract option - handle multiple format variations
        option_keywords = ["OPTION:", "OPTION :", "Option:", "Option :"]
        option_part = ""
    
        for keyword in option_keywords:
            if keyword in header_text:
                option_part = header_text.split(keyword)[1]
            
                # First, remove everything after PROVINCE keyword (case insensitive)
                province_delimiters = ["PROVINCE:", "PROVINCE :", "Province:", "Province :"]
                for prov_delim in province_delimiters:
                    if prov_delim in option_part:
                        option_part = option_part.split(prov_delim)[0].strip()
                        break
            
                # Then remove everything after CODE if still present
                code_delimiters = ["- CODE:", "- CODE :", "- Code:", "- Code :", "-CODE:", "-CODE :", "-Code:", "-Code :", "CODE:", "CODE :", "Code:", "Code :"]
                for delimiter in code_delimiters:
                    if delimiter in option_part:
                        option_part = option_part.split(delimiter)[0].strip()
                        break
            
                result["school_option"] = option_part.strip()
                page_option = option_part.strip()
                break
        # Extract province - handle multiple format variations
        province_keywords = ["PROVINCE:", "PROVINCE :", "Province:", "Province :"]
        province_part = ""

        for keyword in province_keywords:
            if keyword in header_text:
                province_part = header_text.split(keyword)[1]
                
                # Remove everything after "- CODE" or "CODE" (with various spacing)
                delimiters = ["- CODE:", "- CODE :", "- Code:", "- Code :", "-CODE:", "-CODE :", "-Code:", "-Code :", "CODE:", "CODE :", "Code:", "Code :"]
                for delimiter in delimiters:
                    if delimiter in province_part:
                        province_part = province_part.split(delimiter)[0].strip()
                        break
                
                result["school_province"] = province_part.strip()
                page_province = province_part.strip()
                break
    
    # Process the combined body text to extract school data
    body_text = sections.get("body", "")
    if not body_text or not body_text.strip():
        return result
        
    lines = [line.strip() for line in body_text.split('\n') if line.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for both singular and plural forms of results
        if (line.startswith("Réussites:") or line.startswith("Réussite:") or 
            line.startswith("Réussites :") or line.startswith("Réussite :")):
            
            # Go back 3 lines to get the school name
            if i >= 3:
                school_name_line = lines[i - 3]
                code_line = lines[i - 2]
                participants_line = lines[i - 1]
                reussites_line = lines[i]
                
                # Clean school code - remove "Code:" or "Code :" prefix
                code_clean = code_line.strip()
                if code_clean.startswith("Code:") or code_clean.startswith("Code :"):
                    code_clean = code_clean.replace("Code:", "").replace("Code :", "").strip()
                
                # Clean participants - handle both "Participants:" and "Participant:"
                participants_clean = participants_line.strip()
                if participants_clean.startswith("Participants:") or participants_clean.startswith("Participants :"):
                    participants_clean = participants_clean.replace("Participants:", "").replace("Participants :", "").strip()
                elif participants_clean.startswith("Participant:") or participants_clean.startswith("Participant :"):
                    participants_clean = participants_clean.replace("Participant:", "").replace("Participant :", "").strip()
                
                # Remove "Dont: X F" part from participants
                if "Dont:" in participants_clean or "Dont :" in participants_clean:
                    participants_clean = participants_clean.split("Dont")[0].strip()
                
                # Clean reussites - handle both forms and spacing variations
                reussites_clean = reussites_line.strip()
                if reussites_clean.startswith("Réussites:") or reussites_clean.startswith("Réussites :"):
                    reussites_clean = reussites_clean.replace("Réussites:", "").replace("Réussites :", "").strip()
                elif reussites_clean.startswith("Réussite:") or reussites_clean.startswith("Réussite :"):
                    reussites_clean = reussites_clean.replace("Réussite:", "").replace("Réussite :", "").strip()
                
                # Remove "Dont: X F" part from reussites
                if "Dont:" in reussites_clean or "Dont :" in reussites_clean:
                    reussites_clean = reussites_clean.split("Dont")[0].strip()
                
                school_info = {
                    "school_name": school_name_line.strip(),
                    "school_code": code_clean,
                    "school_participants": participants_clean,
                    "school_reussites": reussites_clean,
                    "school_option": page_option,
                    "school_province": page_province,
                    "year": year
                }
                
                result["schools"].append(school_info)
        
        i += 1
    
    return result
    
def student_data(sections: dict) -> dict: 
    """Extracted data from the extracted data function and then use it to range student data
    """
    result = {
        "students_by_school": []
    }
    # Extract year from footer
    footer_text = sections.get("footer", "")
    year = extract_year_from_footer(footer_text)
    
    # Extract option from header
    header_text = sections.get("header", "")
    page_option = ""

    if header_text:
        # Extract option - handle multiple format variations
        option_keywords = ["OPTION:", "OPTION :", "Option:", "Option :"]
        option_part = ""
    
        for keyword in option_keywords:
            if keyword in header_text:
                option_part = header_text.split(keyword)[1]
            
                # First, remove everything after PROVINCE keyword (case insensitive)
                province_delimiters = ["PROVINCE:", "PROVINCE :", "Province:", "Province :"]
                for prov_delim in province_delimiters:
                    if prov_delim in option_part:
                        option_part = option_part.split(prov_delim)[0].strip()
                        break
            
                # Then remove everything after CODE if still present
                code_delimiters = ["- CODE:", "- CODE :", "- Code:", "- Code :", "-CODE:", "-CODE :", "-Code:", "-Code :", "CODE:", "CODE :", "Code:", "Code :"]
                for delimiter in code_delimiters:
                    if delimiter in option_part:
                        option_part = option_part.split(delimiter)[0].strip()
                        break
            
                result["school_option"] = option_part.strip()
                page_option = option_part.strip()
                break
    
    # Process the combined body text to extract student data
    body_text = sections.get("body", "")
    if not body_text or not body_text.strip():
        return result
        
    lines = [line.strip() for line in body_text.split('\n') if line.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for both singular and plural forms of results (with spacing variations)
        if (line.startswith("Réussites:") or line.startswith("Réussite:") or 
            line.startswith("Réussites :") or line.startswith("Réussite :")):
            
            # After finding a results line, look for students
            if i >= 3:
                school_name = lines[i - 3].strip()  # Get school name
                school_code_line = lines[i - 2].strip()  # Get school code line
                
                # Extract clean school code - handle spacing variations
                school_code = school_code_line
                if school_code.startswith("Code:") or school_code.startswith("Code :"):
                    school_code = school_code.replace("Code:", "").replace("Code :", "").strip()
                
                # Initialize school's student data
                school_students = {
                    "school_name": school_name,
                    "school_code": school_code,
                    "year":year,
                    "option":page_option,
                    "students": []
                }
                
                # Look for students after the results line
                j = i + 1  # Start from line after "Réussites:"
                while j < len(lines):
                    student_line = lines[j].strip()
                    
                    # Check if this line is a student entry (starts with a number)
                    if student_line and student_line[0].isdigit():
                        # Parse student information
                        student_info = parse_student_line(student_line, school_code)
                        if student_info:  # Only add if parsing was successful
                            school_students["students"].append(student_info)
                        j += 1
                    else:
                        # If we encounter a non-student line, we've reached the end of this school's students
                        break
                
                # Only add school if it has students
                if school_students["students"]:
                    result["students_by_school"].append(school_students)
        
        i += 1
    
    return result

def parse_student_line(line: str, school_code: str) -> dict:
    """
    Parse a single student line with multiple format variations:
    """
    try:
        # Split the line into parts - handle multiple spaces
        parts = [part for part in line.split() if part.strip()]
        
        if len(parts) < 3:  # Need at least rank, name, and gender+score
            return None
            
        rank = parts[0]  # First part is the ranking number
        
        # Create student_code by combining school_code and rank
        student_code = f"{school_code}/{rank}"
        
        # Look for gender and score pattern
        # The score part can be separate (Format 2) or combined (Format 1)
        gender = ""
        score = ""
        name_parts = []
        
        # Check if the last part is just a number (separate score)
        if parts[-1].isdigit():
            # Format 2: separate gender and score
            score = parts[-1]  # Last part is score
            if len(parts) >= 3:
                gender = parts[-2]  # Second to last is gender
                name_parts = parts[1:-2]  # Everything between rank and gender
        else:
            # Format 1: combined gender+score (like "M50", "F55")
            gender_score = parts[-1]
            
            # Extract gender (first character) and score (remaining characters)
            if len(gender_score) >= 2:
                gender = gender_score[0]  # M or F
                score = gender_score[1:]  # Everything after gender
            else:
                gender = gender_score if gender_score.isalpha() else ""
                score = gender_score if gender_score.isdigit() else ""
            
            # Everything between rank and gender_score is the name
            name_parts = parts[1:-1]  # All parts except first (rank) and last (gender+score)
        
        # Join name parts
        name = " ".join(name_parts)
        
        return {
            "name": name,
            "student_code": student_code,  
            "sexe": gender,
            "pourcentage": score
        }
        
    except (IndexError, ValueError):
        return None  # 

if __name__ == "__main__":
    main()