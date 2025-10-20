import os
import pdfplumber
import json
import re
import time
import gc
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter 


def list_pdf_in_folder(pdf_folder: str):
    """ this will take  my path and list all the pdf that it can find
    """

    try:
        directory = Path(pdf_folder).resolve()  # Replace with your target directory
            # Verify directory exists and is a directory
        if not directory.exists():
            raise FileNotFoundError(f"Directory does not exist: {directory}")
        if not directory.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory}")

        pdf_files = list(directory.rglob("*.pdf"))
        if pdf_files:
            print(f"Found {len(pdf_files)} PDF files in {directory}")
        else:
            print(f"No PDF files found in {directory}")
            
        return pdf_files

        print("pdf files in the directory: ", pdf_files )
    except FileNotFoundError:
        print("Directory does not exist.")
    except NotADirectoryError:
        print("That path is not a directory.")

def split_pdf_for_processing(input_pdf_path: str, temp_folder: str, pages_per_chunk: int = 200):
    """Split large PDF into smaller temporary parts (returns list of paths)."""
    os.makedirs(temp_folder, exist_ok=True)
    reader = PdfReader(input_pdf_path)
    total_pages = len(reader.pages)
    chunk_paths = []

    for start in range(0, total_pages, pages_per_chunk):
        end = min(start + pages_per_chunk, total_pages)
        writer = PdfWriter()

        for i in range(start, end):
            writer.add_page(reader.pages[i])

        chunk_path = os.path.join(temp_folder, f"chunk_{start+1}_to_{end}.pdf")
        with open(chunk_path, "wb") as f:
            writer.write(f)

        chunk_paths.append(chunk_path)

    del reader, writer
    gc.collect()
    return chunk_paths


def process_single_pdf(pdf_path: str, school_json_path: str, student_json_path: str,
                       pdf_folder: str, pages_per_chunk: int = 20, large_pdf_threshold: int = 600):
    """
    Process a PDF file. If large (>600 pages), split into smaller chunks (350 pages each).
    Each chunk is processed individually, merged into one JSON, and memory is freed after each chunk.
    """

    # Initialize containers
    all_school_data = {"schools": []}
    all_student_data = {"students_by_school": []}

    last_option = ""
    last_province = ""
    failed_pages = []
    successful_pages = []
    start_time = time.time()

    try:
        # Step 1: Check total pages before loading fully
        with pdfplumber.open(pdf_path) as pdf_check:
            total_pages = len(pdf_check.pages)
        print(f"\n📘 File: {os.path.basename(pdf_path)} — {total_pages} pages detected")

        # Step 2: Handle large files by splitting
        if total_pages > large_pdf_threshold:
            temp_folder = os.path.join(pdf_folder, "_temp_chunks")
            chunk_paths = split_pdf_for_processing(pdf_path, temp_folder, pages_per_chunk=200)
            print(f"🔹 Split into {len(chunk_paths)} chunks (200 pages each)\n")

            total_chunks = len(chunk_paths)

            for idx, chunk_path in enumerate(chunk_paths, start=1):
                print(f"▶️ Processing chunk {idx}/{total_chunks}: {os.path.basename(chunk_path)}")

                # Process each chunk as a normal smaller PDF
                result = process_single_pdf(
                    pdf_path=chunk_path,
                    school_json_path=school_json_path,
                    student_json_path=student_json_path,
                    pdf_folder=pdf_folder,
                    pages_per_chunk=pages_per_chunk,
                    large_pdf_threshold=large_pdf_threshold  # ensures recursion won’t re-split small chunks
                )

                # Merge chunk results
                if result and "schools" in result and "students_by_school" in result:
                    all_school_data["schools"].extend(result["schools"])
                    all_student_data["students_by_school"].extend(result["students_by_school"])

                print(f"✅ Finished chunk {idx}/{total_chunks} "
                      f"— Total so far: {len(all_school_data['schools'])} schools, "
                      f"{sum(len(s['students']) for s in all_student_data['students_by_school'])} students.\n")

                # Free memory explicitly
                gc.collect()

            # Cleanup temporary chunk files
            for path in chunk_paths:
                os.remove(path)
            os.rmdir(temp_folder)

            # Final save
            export_data_json(all_school_data, school_json_path)
            export_data_json(all_student_data, student_json_path)
            print("\n🎉 All chunks processed successfully (merged into single JSON).")

            return {
                "schools": all_school_data["schools"],
                "students_by_school": all_student_data["students_by_school"]
            }

        # Step 3: Process normal-sized PDFs directly
        with pdfplumber.open(pdf_path, laparams={"detect_vertical": True}) as pdf:
            total_pages = len(pdf.pages)
            print(f"Processing {total_pages} pages...")

            for chunk_start in range(0, total_pages, pages_per_chunk):
                chunk_end = min(chunk_start + pages_per_chunk, total_pages)
                for page_num in range(chunk_start, chunk_end):
                    try:
                        progress = ((page_num + 1) / total_pages) * 100
                        print(f"  [{progress:5.1f}%] Page {page_num + 1}/{total_pages}", end="\r")

                        # Process page
                        page = pdf.pages[page_num]
                        header_footer = extract_header(page, pdf_folder, header_adjustement=0.05)
                        body_text = extract_body(page, pdf_folder, header_adjustement=0.05)
                        extracted_result = {
                            "header": header_footer["header"],
                            "footer": header_footer["footer"],
                            "body": body_text
                        }
                        filename = os.path.basename(pdf_path)
                        page_school_data = school_data(extracted_result, filename)
                        page_student_data = student_data(extracted_result, filename)

                        # Keep last known option/province to fill missing fields
                        if page_school_data["school_option"]:
                            last_option = page_school_data["school_option"]
                        if page_school_data["school_province"]:
                            last_province = page_school_data["school_province"]

                        for school in page_school_data["schools"]:
                            school.setdefault("school_option", last_option)
                            school.setdefault("school_province", last_province)
                            all_school_data["schools"].append(school)

                        all_student_data["students_by_school"].extend(page_student_data["students_by_school"])
                        successful_pages.append(page_num + 1)

                    except Exception as e:
                        failed_pages.append((page_num + 1, str(e)[:100]))

                gc.collect()

    except Exception as e:
        print(f"\n❌ Failed to open or process PDF: {e}")
        return None

    # Step 4: Save results
    export_data_json(all_school_data, school_json_path)
    export_data_json(all_student_data, student_json_path)

    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(int(elapsed_time), 60)

    print(f"\n✅ Completed {os.path.basename(pdf_path)} in {minutes}m {seconds}s")
    print(f"   Pages: {len(successful_pages)}/{total_pages}")
    print(f"   Schools: {len(all_school_data['schools'])} | Students: {sum(len(s['students']) for s in all_student_data['students_by_school'])}")

    return {
        "schools": all_school_data["schools"],
        "students_by_school": all_student_data["students_by_school"]
    }

def export_data_json(data: dict, filename: str):
    """
    Export school data to a JSON file
    """
    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, ensure_ascii=False, indent=4)


def extract_header(page, path : str, header_adjustement : float) -> dict:
    """
    Extract text from the header and footer sections.
    
    """
    width = page.width
    height = page.height

    if path.endswith("style_2"):
        header_adjustement = 0.09

    footer_adjustement = 1.0 - header_adjustement
    
    # Define header and footer bounding box 
    header_bbox = (0, 0,width, height* header_adjustement) #this mean thu ende tu anziye mwazo ku x, y iko 0 kisha thu ende thu ku top 10% ya height ya page
    footer_bbox = (0, height * footer_adjustement, width, height)
    
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


def extract_body(page, path : str , header_adjustement: float ) -> str:
    """
    Extract text from the body section by dividing it into three vertical parts.
    This helps maintain proper text extraction from multi-column PDF layouts.
    
    """
    width = page.width
    height = page.height


    if path.endswith("style_2"):
        header_adjustement = 0.09

    footer_adjustement = 1- header_adjustement
    
    # Define body boundaries (between header and footer)
    header = height * header_adjustement
    footer_start = height* footer_adjustement

    body_top = header 
    body_bottom = footer_start
    #which mean tuna anziya mwazo ya page ti ku bottom kisha tuna tosha amo header

    part_width = width / 3

    # Define bounding boxes for three vertical sections with slight overlap
    body_part1_bbox = (0, body_top, part_width * 1.1, body_bottom)
    body_part2_bbox = (part_width * 1.1, body_top, 2 * part_width, body_bottom)
    body_part3_bbox = (1.93 * part_width, body_top, width, body_bottom)

    if path.endswith("style_2"):
        body_part1_bbox = (0, body_top, part_width * 1.08, body_bottom)
        body_part2_bbox = (part_width * 1.05 , body_top, 1.94* part_width, body_bottom)
        body_part3_bbox = (1.90* part_width , body_top, width, body_bottom)
    elif path.endswith("pdf_2008"):
        body_part1_bbox = (0, body_top, part_width * 1.15, body_bottom)
        body_part2_bbox = (part_width * 1.15, body_top, 2.03 * part_width, body_bottom)
        body_part3_bbox = (2.05 * part_width, body_top, width, body_bottom)
        
    body_part1 = page.within_bbox(body_part1_bbox).extract_text(layout=True)
    body_part2 = page.within_bbox(body_part2_bbox).extract_text(layout=True)
    body_part3 = page.within_bbox(body_part3_bbox).extract_text(layout=True)

    # Combine all parts
    body = body_part1 + body_part2 + body_part3
    
    # Clean and return combined body text
    body_text = (body or "").replace('\x00', '')
    
    return body_text
    
def find_year(text: str) -> str:
    """Helper function to find year in text using multiple patterns"""
    patterns = [
        r'[-\s](20\d{2})[-\s]',           # Year between dashes/spaces
        r'20\d{2}'                        # Any 4 digits starting with 20
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            # Return first group if it exists, otherwise full match
            return match.group(1) if len(match.groups()) > 0 else match.group(0)
    return ""

def extract_year(footer_text: str, filename: str = "") -> str:
    """
    Extract the year from footer text by looking for 4 digits between 
    "EXAMEN D'ETAT" and "https". or if not fund take the filename and check the year inside
    """

    # Check inputs
    if not footer_text and not filename:
        return ""

    # First try footer text
    if footer_text:
        year = find_year(footer_text)
        if year:
            return year

    # Then try filename if provided
    if filename:
        year = find_year(filename)
        if year:
            return year

    return ""


def normalize_reussite_value(value: str) -> str:
    """
    Normalize the reussite value to handle NEAN, ZERO, or empty values.
    Returns "0" for NEAN/ZERO, otherwise returns the original value.
    """
    if not value:
        return "0"
    
    # Convert to uppercase and strip whitespace for comparison
    normalized = value.strip().upper()
    
    # Check if it's NEAN, ZERO, or variations
    if normalized in ["Néant", "NÉANT", "ZERO", "ZÉRO","Zéro", ""]:
        return "0"
    
    return value.strip()

def extract_option(header_text: str) -> str: 
    """Extract the option of each school on a page with improved handling"""
    
    
    if header_text:
        # Try multiple keyword variations
        option_keywords = ["OPTION:", "OPTION :", "Option:", "Option :"]
        
        for keyword in option_keywords:
            if keyword in header_text:
                # Get everything after the keyword
                option_part = header_text.split(keyword, 1)[1]
                
                # Remove everything after PROVINCE (case insensitive, any spacing)
                province_keywords = ["PROVINCE:", "PROVINCE :", "Province:", "Province :", "province:", "province :"]
                for prov_delim in province_keywords:
                    if prov_delim in option_part:
                        option_part = option_part.split(prov_delim)[0]
                        break
                
                # Remove everything after CODE (handle various spacings)
                code_keywords = ["- CODE:", "- CODE :", "- Code:", "- Code :", "-CODE:", "-CODE :", "-Code:", "-Code :", "CODE:", "CODE :", "Code:", "Code :", "code:", "code :"]
                for code_delim in code_keywords:
                    if code_delim in option_part:
                        option_part = option_part.split(code_delim)[0]
                        break
                
                # Clean up whitespace - preserve the option value as is
                option_part = option_part.strip()
                
                if option_part:  # Only return if we found actual content
                    return option_part
    
    return ""


def extract_province(header_text: str) -> str:
    """Extract province from header text with improved logic"""
    
    if not header_text:
        return ""
    
    # First, try to find explicit PROVINCE keyword
    province_keywords = ["PROVINCE:", "PROVINCE :", "Province:", "Province :", "province:", "province :"]
    
    for keyword in province_keywords:
        if keyword in header_text:
            # Get everything after the keyword
            province_part = header_text.split(keyword, 1)[1]
            
            # Remove everything after CODE (handle various spacings)
            code_keywords = ["- CODE:", "- CODE :", "- Code:", "- Code :", "-CODE:", "-CODE :", "-Code:", "-Code :", "CODE:", "CODE :", "Code:", "Code :", "code:", "code :"]
            for code_delim in code_keywords:
                if code_delim in province_part:
                    province_part = province_part.split(code_delim)[0]
                    break
            
            # Clean and return
            province_part = province_part.strip()
            if province_part:
                return province_part
    
    # If no explicit PROVINCE keyword, try to extract from OPTION line
    # Format: "Option : 103 / CHIMIE-BIOLOGIE          HORS – FRONTIERE / Code : 01"
    option_keywords = ["OPTION:", "OPTION :", "Option:", "Option :"]
    
    for keyword in option_keywords:
        if keyword in header_text:
            # Get everything after OPTION keyword
            option_section = header_text.split(keyword, 1)[1]
            
            # Split by CODE to isolate the option section
            code_keywords = ["- CODE:", "- CODE :", "- Code:", "- Code :", "-CODE:", "-CODE :", "-Code:", "-Code :", "CODE:", "CODE :", "Code:", "Code :", "code:", "code :"]
            for code_delim in code_keywords:
                if code_delim in option_section:
                    option_section = option_section.split(code_delim)[0]
                    break
            
            # Now extract province from option section
            if "/" in option_section:
                parts = option_section.split("/")
                
                # If we have more than 2 parts separated by "/", the last part before CODE is province
                if len(parts) >= 2:
                    # Last part should be the province (after extra spaces)
                    potential_province = parts[-1].strip()
                    
                    # Clean up special characters and extra spaces
                    potential_province = " ".join(potential_province.split())
                    
                    if potential_province and potential_province.upper() != potential_province.lower():
                        # Make sure it's not empty and contains actual text
                        return potential_province
    
    return ""

def school_data(sections: dict, filename: str = "") -> dict:
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
    year = extract_year(footer_text, filename)

    header_text = sections.get("header", "")
    page_option = extract_option(header_text)
    page_province = extract_province(header_text)

    result["school_option"] = page_option
    result["school_province"] = page_province

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
                
                reussites_clean = normalize_reussite_value(reussites_clean)
                
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
    
def student_data(sections: dict, filename: str= "") -> dict: 
    """Extracted data from the extracted data function and then use it to range student data
    """
    result = {
        "students_by_school": []
    }
    # Extract year from footer
    footer_text = sections.get("footer", "")
    year = extract_year(footer_text, filename)
    
    # Extract option from header
    header_text = sections.get("header", "")
    page_option = extract_option(header_text)

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
    # TODO: Again, duplicate code create a function adn reuse it.
    try:
        # Split the line into parts - handle multiple spaces
        parts = [part for part in line.split() if part.strip()]
        
        if len(parts) < 3:  # Need at least rank, name, and gender+score
            return None
            
        rank = parts[0]  # First part is the ranking number
        
        # Create student_code by combining school_code and rank
        student_code = f"{school_code}/ {rank}"
        
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
        return None 
