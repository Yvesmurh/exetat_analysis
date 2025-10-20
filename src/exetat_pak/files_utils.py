import os
import json
from pathlib import Path

def create_directory(directory_name : str):

    output_directory = Path(directory_name).mkdir(exist_ok=True)

    return output_directory

    

    