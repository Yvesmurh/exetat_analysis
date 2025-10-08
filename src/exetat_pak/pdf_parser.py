import os
import pdfplumber
import json
from pathlib import Path


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

