import os
import pdfplumber
import csv

def main():
    pdf_path = "pdf/Palmares_2021_SUD-KIVU-3.pdf"
    
    # Initialize combined data structures
    all_school_data = {
        "school_option": "",
        "school_province": "",
        "schools": []
    }
    all_student_data = {
        "students_by_school": []
    }
    
    # Get total number of pages in PDF
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
    
    print(f"Processing {total_pages} pages...")
    
    # Process each page
    for page_num in range(1, total_pages + 1):  # Pages are 1-indexed
        print(f"Processing page {page_num}/{total_pages}")
        
        try:
            # Extract data from current page
            extracted_result = extract_text(pdf_path, page_num)
            
            # Get school and student data for this page
            page_school_data = school_data(extracted_result)
            page_student_data = student_data(extracted_result)
            
            # Combine school data
            if page_school_data["school_option"] and not all_school_data["school_option"]:
                all_school_data["school_option"] = page_school_data["school_option"]
            if page_school_data["school_province"] and not all_school_data["school_province"]:
                all_school_data["school_province"] = page_school_data["school_province"]
            
            # Add schools from this page
            all_school_data["schools"].extend(page_school_data["schools"])
            
            # Add students from this page
            all_student_data["students_by_school"].extend(page_student_data["students_by_school"])
            
        except Exception as e:
            print(f"Error processing page {page_num}: {e}")
            continue
    
    # Export combined data to CSV files
    export_school_data_to_csv(all_school_data, "all_school_data.csv")
    export_student_data_to_csv(all_student_data, "all_student_data.csv")
    
    print("\nData processing completed!")
    print(f"Total schools found: {len(all_school_data['schools'])}")
    print(f"Total students found: {sum(len(school['students']) for school in all_student_data['students_by_school'])}")
    print(f"School data saved to: all_school_data.csv")
    print(f"Student data saved to: all_student_data.csv")

def export_school_data_to_csv(data: dict, filename: str):
    """
    Export school data to CSV file
    """
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header row - now includes individual Option and Province for each school
        writer.writerow(['Option', 'Province', 'School_Name', 'School_Code', 'Participants', 'Reussites'])
        
        # Write school data rows - each school has its own option/province
        for school in data.get("schools", []):
            writer.writerow([
                school.get("school_option", ""),    # Individual option for this school
                school.get("school_province", ""),  # Individual province for this school
                school.get("school_name", ""),
                school.get("school_code", ""),
                school.get("school_participants", ""),
                school.get("school_reussites", "")
            ])

def export_student_data_to_csv(data: dict, filename: str):
    """
    Export student data to CSV file
    """
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header row - now includes student_code
        writer.writerow(['Student_Code', 'School_Name', 'Place', 'Student_Name', 'Gender', 'Score'])
        
        # Write student data rows
        for school_data in data.get("students_by_school", []):
            school_name = school_data.get("school_name", "")
            
            for student in school_data.get("students", []):
                writer.writerow([
                    student.get("student_code", ""),  # New student_code field
                    school_name,
                    student.get("place", ""),
                    student.get("name", ""),
                    student.get("sexe", ""),
                    student.get("point", "")
                ])

# Your existing functions remain the same
def extract_text(pdf_path: str, page_num: int) -> dict:
    """
    extract text from the header, that will be use after and then extract text from the page by devising the page in tree
    part for more comprehension
    """
    with pdfplumber.open(pdf_path, laparams={"detect_vertical": True}) as pdf:
        page = pdf.pages[page_num - 1]
        width = page.width
        height = page.height

        header_bbox = (0, 0, width, height * 0.05)
        header_text = page.within_bbox(header_bbox).extract_text(layout=True)
        header = height * 0.05
        footer_start = height * 0.95

        body_top = header 
        body_bottom = footer_start

        part_width = width / 3.0
        body_part1_bbox = (0, body_top, part_width * 1.1, body_bottom)
        body_part2_bbox = (part_width * 1.1, body_top, 2 * part_width, body_bottom)
        body_part3_bbox = (1.93 * part_width, body_top, width, body_bottom)

        part1_text = page.within_bbox(body_part1_bbox).extract_text(layout=True) or ""
        part2_text = page.within_bbox(body_part2_bbox).extract_text(layout=True) or ""
        part3_text = page.within_bbox(body_part3_bbox).extract_text(layout=True) or ""

        all_text = part1_text + part2_text + part3_text

        clean_header = (header_text or "").replace('\x00', '')
        clean_body = (all_text or "").replace('\x00', '')
        
    return {
        "header": clean_header, 
        "body": clean_body
    }

def school_data(sections: dict) -> dict:
    """
    Extract school data from the extracted text sections
    Returns organized school information including header data and school_details datat...
    """
    result = {
        "school_option": "",
        "school_province": "",
        "schools": []
    }
    
    # Extract header information
    header_text = sections.get("header", "")
    page_option = ""
    page_province = ""
    
    if header_text:
        # Extract option 
        if "Option :" in header_text:
            option_part = header_text.split("Option :")[1].split("-Code:")[0].strip()
            result["school_option"] = option_part
            page_option = option_part
        
        # Extract province 
        if "Province:" in header_text:
            province_part = header_text.split("Province:")[1].split("-Code:")[0].strip()
            result["school_province"] = province_part
            page_province = province_part
    
    # Process the combined body text to extract school data
    body_text = sections.get("body", "")
    if not body_text or not body_text.strip():
        return result
        
    lines = [line.strip() for line in body_text.split('\n') if line.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this line start with Reussite: or Reussite: 
        if line.startswith("Réussites:") or line.startswith("Réussite:"):
            # Go back 3 lines to get the school name
            if i >= 3:
                school_name_line = lines[i - 3]
                code_line = lines[i - 2]
                participants_line = lines[i - 1]
                reussites_line = lines[i]
                
                # Clean school code - remove "Code:" prefix
                code_clean = code_line.strip()
                if code_clean.startswith("Code:"):
                    code_clean = code_clean.replace("Code:", "").strip()
                
                # Clean participants - remove "Participants:" and "Dont:XF" part
                participants_clean = participants_line.strip()
                if participants_clean.startswith("Participants:"):
                    participants_clean = participants_clean.replace("Participants:", "").strip()
                if "Dont:" in participants_clean:
                    participants_clean = participants_clean.split("Dont:")[0].strip()
                
                # Clean reussites - remove "Réussites:"/"Réussite:" and "Dont:XF" part  
                reussites_clean = reussites_line.strip()
                if reussites_clean.startswith("Réussites:"):
                    reussites_clean = reussites_clean.replace("Réussites:", "").strip()
                elif reussites_clean.startswith("Réussite:"):
                    reussites_clean = reussites_clean.replace("Réussite:", "").strip()
                if "Dont:" in reussites_clean:
                    reussites_clean = reussites_clean.split("Dont:")[0].strip()
                
                school_info = {
                    "school_name": school_name_line.strip(),
                    "school_code": code_clean,
                    "school_participants": participants_clean,
                    "school_reussites": reussites_clean,
                    "school_option": page_option,      # Add option for this specific school
                    "school_province": page_province   # Add province for this specific school
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
    
    # Process the combined body text to extract student data
    body_text = sections.get("body", "")
    if not body_text or not body_text.strip():
        return result
        
    lines = [line.strip() for line in body_text.split('\n') if line.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this line contains results (this indicates end of a school's basic info)
        if line.startswith("Réussites:") or line.startswith("Réussite:"):
            # After finding a results line, look for students
            if i >= 3:
                school_name = lines[i - 3].strip()  # Get school name
                school_code_line = lines[i - 2].strip()  # Get school code line
                
                # Extract clean school code
                school_code = school_code_line
                if school_code.startswith("Code:"):
                    school_code = school_code.replace("Code:", "").strip()
                
                # Initialize school's student data
                school_students = {
                    "school_name": school_name,
                    "school_code": school_code,
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
    Parse a single student line like: "1 ACHIZAMARANGI  M50"
    Returns: {"student_code": "67001/201/01/6/1", "place": "1", "name": "ACHIZAMARANGI", "sexe": "M", "point": "50"}
    """
    try:
        # Split the line into parts
        parts = line.split()
        
        if len(parts) < 3:  # Need at least rank, name, and gender+score
            return None
            
        rank = parts[0]  # First part is the ranking number
        
        # Create student_code by combining school_code and rank
        student_code = f"{school_code}/{rank}"
        
        # Last part should contain gender and score (e.g., "M50", "F53")
        gender_score = parts[-1]
        
        # Extract gender (first character) and score (remaining characters)
        if len(gender_score) >= 2:
            gender = gender_score[0]  # M or F
            score = gender_score[1:]  # Everything after gender
        else:
            gender = ""
            score = gender_score
        
        # Everything between rank and gender_score is the name
        name_parts = parts[1:-1]  # All parts except first (rank) and last (gender+score)
        name = " ".join(name_parts)
        
        return {
            "student_code": student_code,  # New field: school_code + rank
            "place": rank,
            "name": name,
            "sexe": gender,
            "point": score
        }
        
    except (IndexError, ValueError):
        return None  # Return None if parsing fails

if __name__ == "__main__":
    main()