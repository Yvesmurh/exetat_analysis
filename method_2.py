import os
import pdfplumber
import csv

def main():
    pdf_path = "pdf_files/Palmares_2021_SUD-KIVU-3.pdf"
    
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
    export_school_data_to_csv(all_school_data, "csv_files/all_school_data_4.csv")
    export_student_data_to_csv(all_student_data, "csv_files/all_student_data_4.csv")
    
    print("\nData processing completed!")
    print(f"Total schools found: {len(all_school_data['schools'])}")
    print(f"Total students found: {sum(len(school['students']) for school in all_student_data['students_by_school'])}")
    print(f"School data saved to: all_school_data_3.csv")
    print(f"Student data saved to: all_student_data_3.csv")

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

def extract_text(pdf_path: str , page_num : int) -> str:
    """
    extract text from the header ,that will be use after and then extract text from the page by devising the page in tree
    part for more comprehension
    """
    with pdfplumber.open(pdf_path, laparams={"detect_vertical": True} ) as pdf:
        page = pdf.pages[page_num - 1]
        width = page.width
        height = page.height

        header_bbox = (0, 0,width, height* 0.10) #this mean thu ende tu anziye mwazo ku x, y iko 0 kisha thu ende thu ku top 10% ya height ya page
        header_text = page.within_bbox(header_bbox).extract_text(layout = True)
        header = height * 0.08
        footer_start = height* 0.92

        body_top = header 
        body_bottom = footer_start
        #which mean tuna anziya mwazo ya page ti ku bottom kisha tuna tosha amo header


        part_width = width / 3



        body_part1_bbox = (0, body_top, part_width * 1.1, body_bottom)
        body_part2_bbox = (part_width * 1.05 , body_top, 1.94* part_width, body_bottom)
        body_part3_bbox = (1.90* part_width , body_top, width, body_bottom)

        body_part1 = page.within_bbox(body_part1_bbox).extract_text(layout=True)
        body_part2 = page.within_bbox(body_part2_bbox).extract_text(layout=True)
        body_part3 = page.within_bbox(body_part3_bbox).extract_text(layout=True)

        all_text = body_part1 + body_part2 + body_part3 


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
        # Extract option - handle multiple format variations
        option_keywords = ["OPTION:", "OPTION :", "Option:", "Option :"]
        option_part = ""
        
        for keyword in option_keywords:
            if keyword in header_text:
                option_part = header_text.split(keyword)[1]
                
                # Remove everything after "- CODE" or "CODE" (with various spacing)
                delimiters = ["- CODE:", "- CODE :", "- Code:", "- Code :", "-CODE:", "-CODE :", "-Code:", "-Code :", "CODE:", "CODE :", "Code:", "Code :"]
                for delimiter in delimiters:
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
                    "school_province": page_province
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