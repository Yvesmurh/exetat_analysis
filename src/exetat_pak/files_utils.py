import gc
import os
import json
import time 
from pathlib import Path
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
from pdf_helper import extract_header, extract_body
from pdf_parser import school_data, student_data

def create_directory(directory_name: str):
    output_directory = Path(directory_name)
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory

# file utilities

def list_pdf_in_folder(pdf_folder: str):
    """Return all PDF paths found recursively under *pdf_folder*."""
    directory = Path(pdf_folder).resolve()
    if not directory.exists():
        raise FileNotFoundError(f"Directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {directory}")

    pdf_files = list(directory.rglob("*.pdf"))
    count = len(pdf_files)
    print(f"Found {count} PDF file(s) in {directory}" if count else f"No PDF files found in {directory}")
    return pdf_files


def export_data_json(data: dict, filename: str) -> None:
    """Serialize *data* to a UTF-8 JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def split_pdf_for_processing(input_pdf_path: str, temp_folder: str, pages_per_chunk: int = 200):
    """Split a large PDF into smaller temporary chunk files."""
    os.makedirs(temp_folder, exist_ok=True)
    reader = PdfReader(input_pdf_path)
    total_pages = len(reader.pages)
    chunk_paths = []

    for start in range(0, total_pages, pages_per_chunk):
        end = min(start + pages_per_chunk, total_pages)
        writer = PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])

        chunk_path = os.path.join(temp_folder, f"chunk_{start + 1}_to_{end}.pdf")
        with open(chunk_path, "wb") as f:
            writer.write(f)
        chunk_paths.append(chunk_path)

    del reader, writer
    gc.collect()
    return chunk_paths


def process_large_pdf(
    pdf_path: str,
    school_json_path: str,
    student_json_path: str,
    pdf_folder: str,
    pages_per_chunk: int,
    large_pdf_threshold: int,
) -> dict | None:
    """Process a large PDF by splitting into chunks and merging results."""
    all_school_data = {"schools": []}
    all_student_data = {"students_by_school": []}

    try:
        temp_folder = os.path.join(pdf_folder, "_temp_chunks")
        chunk_paths = split_pdf_for_processing(pdf_path, temp_folder, pages_per_chunk=200)
        total_chunks = len(chunk_paths)
        print(f"🔹 Split into {total_chunks} chunks (200 pages each)\n")

        for idx, chunk_path in enumerate(chunk_paths, start=1):
            print(f"▶️  Chunk {idx}/{total_chunks}: {os.path.basename(chunk_path)}")
            result = process_single_pdf(
                pdf_path=chunk_path,
                school_json_path=school_json_path,
                student_json_path=student_json_path,
                pdf_folder=pdf_folder,
                pages_per_chunk=pages_per_chunk,
                large_pdf_threshold=large_pdf_threshold,
            )
            if result:
                all_school_data["schools"].extend(result.get("schools", []))
                all_student_data["students_by_school"].extend(result.get("students_by_school", []))

            n_students = sum(len(s["students"]) for s in all_student_data["students_by_school"])
            print(f"✅ Chunk {idx}/{total_chunks} — "
                  f"{len(all_school_data['schools'])} schools, {n_students} students so far\n")
            gc.collect()

        # Cleanup
        for path in chunk_paths:
            os.remove(path)
        os.rmdir(temp_folder)

        export_data_json(all_school_data, school_json_path)
        export_data_json(all_student_data, student_json_path)
        print("🎉 All chunks merged and saved.")
        return {
            "schools": all_school_data["schools"],
            "students_by_school": all_student_data["students_by_school"],
        }
    except Exception as e:
        print(f"❌ Failed to process large PDF: {e}")
        return None


def process_normal_pdf(
    pdf_path: str,
    school_json_path: str,
    student_json_path: str,
    pdf_folder: str,
    pages_per_chunk: int,
) -> dict | None:
    """Process a normal-sized PDF page by page."""
    all_school_data = {"schools": []}
    all_student_data = {"students_by_school": []}
    last_option = ""
    last_province = ""
    failed_pages = []
    successful_pages = []

    try:
        with pdfplumber.open(pdf_path, laparams={"detect_vertical": True}) as pdf:
            total_pages = len(pdf.pages)
            print(f"Processing {total_pages} pages...")

            for chunk_start in range(0, total_pages, pages_per_chunk):
                chunk_end = min(chunk_start + pages_per_chunk, total_pages)

                for page_num in range(chunk_start, chunk_end):
                    try:
                        pct = (page_num + 1) / total_pages * 100
                        print(f"  [{pct:5.1f}%] Page {page_num + 1}/{total_pages}", end="\r")

                        page = pdf.pages[page_num]
                        filename = os.path.basename(pdf_path)
                        header_footer = extract_header(page, pdf_folder, header_adjustement=0.05)
                        body_text = extract_body(page, pdf_folder, header_adjustement=0.05)

                        sections = {
                            "header": header_footer["header"],
                            "footer": header_footer["footer"],
                            "body": body_text,
                        }

                        page_school = school_data(sections, filename)
                        page_student = student_data(sections, filename)

                        # Propagate last-known option/province to pages with blank headers
                        if page_school["school_option"]:
                            last_option = page_school["school_option"]
                        if page_school["school_province"]:
                            last_province = page_school["school_province"]

                        for school in page_school["schools"]:
                            school.setdefault("school_option", last_option)
                            school.setdefault("school_province", last_province)
                            all_school_data["schools"].append(school)

                        all_student_data["students_by_school"].extend(
                            page_student["students_by_school"]
                        )
                        successful_pages.append(page_num + 1)

                    except Exception as e:
                        failed_pages.append((page_num + 1, str(e)[:100]))

                gc.collect()

        export_data_json(all_school_data, school_json_path)
        export_data_json(all_student_data, student_json_path)

        n_students = sum(len(s["students"]) for s in all_student_data["students_by_school"])
        print(f"\n   Pages: {len(successful_pages)}/{total_pages}"
              + (f" ({len(failed_pages)} failed)" if failed_pages else ""))
        print(f"   Schools: {len(all_school_data['schools'])} | Students: {n_students}")

        return {
            "schools": all_school_data["schools"],
            "students_by_school": all_student_data["students_by_school"],
        }
    except Exception as e:
        print(f"❌ Failed to process normal PDF: {e}")
        return None

# Main processing pipeline

def process_single_pdf(
    pdf_path: str,
    school_json_path: str,
    student_json_path: str,
    pdf_folder: str,
    pages_per_chunk: int = 20,
    large_pdf_threshold: int = 400,
) -> dict | None:
    """
    Process one PDF file.

    Files larger than *large_pdf_threshold* pages are first split into
    200-page chunks, each processed recursively, then merged into a single
    JSON output. Normal-sized files are processed page-by-page in memory
    chunks of *pages_per_chunk* pages.
    """
    start_time = time.time()

    try:
        with pdfplumber.open(pdf_path) as pdf_check:
            total_pages = len(pdf_check.pages)
        print(f"\n📘 {os.path.basename(pdf_path)} — {total_pages} pages")

        if total_pages > large_pdf_threshold:
            result = process_large_pdf(
                pdf_path, school_json_path, student_json_path, pdf_folder,
                pages_per_chunk, large_pdf_threshold
            )
        else:
            result = process_normal_pdf(
                pdf_path, school_json_path, student_json_path, pdf_folder,
                pages_per_chunk
            )

        if result:
            elapsed = time.time() - start_time
            mins, secs = divmod(int(elapsed), 60)
            print(f"✅ {os.path.basename(pdf_path)} — {mins}m {secs}s")

        return result

    except Exception as e:
        print(f"\n❌ Failed to process PDF: {e}")
        return None
    

    