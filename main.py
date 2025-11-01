import os
from src.exetat_pak.pdf_parser import list_pdf_in_folder, process_single_pdf
from src.exetat_pak.files_utils import create_directory


def main():
    """ Process multiple PDF files and save data to JSON format """

    base_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_folder = os.path.join(base_dir, "pdf_files", "2019")
    output_folder = os.path.join(base_dir, "json_files", "2019")
    
    output_path = create_directory(directory_name = output_folder )
    
    pdf_files = list_pdf_in_folder(pdf_folder)
    
    print(f"Found {len(pdf_files)} PDF files to process\n")
    
    # Process each PDF file
    for pdf_index, pdf_filename in enumerate(pdf_files, 1):
        print(f"\n{'='*60}")
        print(f"Processing PDF {pdf_index}/{len(pdf_files)}: {pdf_filename}")
        print(f"{'='*60}")
        
        pdf_path = str(pdf_filename)
        
        # Create output filenames based on PDF name (remove .pdf extension)
        base_name = pdf_filename.stem  
        school_json = os.path.join(output_folder, f"{base_name}_schools_data.json")
        student_json = os.path.join(output_folder, f"{base_name}_students_data.json")
        
        # Process this PDF
        try:
            process_single_pdf(pdf_path, school_json, student_json, pdf_folder)
        except Exception as e:
            print(f"ERROR: Failed to process {pdf_filename}: {e}")
            continue
    
    print(f"\n{'='*60}")
    print("ALL FILES PROCESSED!")
    print(f"{'='*60}")
 

if __name__ == "__main__":
    main()
