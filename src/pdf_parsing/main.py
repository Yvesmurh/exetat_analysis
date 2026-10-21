from pathlib import Path
from files_utils import create_directory, list_pdf_in_folder, process_single_pdf



def main():
    """Process multiple PDF files and save data to JSON format."""

    base_dir = Path(__file__).resolve().parent
    pdf_folder = base_dir / "test_pdf" / "style_3" / "large_pdf"
    output_folder = base_dir / "json" / "style_3"

    create_directory(output_folder)

    pdf_files = list_pdf_in_folder(pdf_folder)

    print(f"Found {len(pdf_files)} PDF files to process\n")

    for pdf_index, pdf_filename in enumerate(pdf_files, 1):
        print(f"\n{'='*60}")
        print(f"Processing PDF {pdf_index}/{len(pdf_files)}: {pdf_filename.name}")
        print(f"{'='*60}")

        pdf_path = str(pdf_filename)
        base_name = pdf_filename.stem
        school_json = output_folder / f"{base_name}_schools_data.json"
        student_json = output_folder / f"{base_name}_students_data.json"

        try:
            process_single_pdf(pdf_path, str(school_json), str(student_json), str(pdf_folder))
        except Exception as e:
            print(f"ERROR: Failed to process {pdf_filename.name}: {e}")
            continue

    print(f"\n{'='*60}")
    print("ALL FILES PROCESSED!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
