# Interactive Dashboard for School Performance Analysis (EXETAT-DRC)
## Overview
This project addresses a critical gap in the education system of the Democratic Republic of Congo (DRC). Currently, the Ministry of Education (MEPST) publishes annual National State Examination (Exetat) results in static, text-heavy tabular formats (PDFs). These formats are difficult for parents, administrators, and policymakers to interpret effectively.

This research study presents the design and implementation of an Interactive Dashboard that transforms raw, static Exetat data into dynamic, user-friendly visualizations. The tool empowers families to make evidence-based school choices and enables policymakers to monitor educational performance trends with precision.

## Key Features
1. Summary Metrics (KPIs): Instant visibility into Total Schools, Total Participants, and Success Rates using dynamic filters.

2. Success Rate Indicators: Real-time calculations and comparisons for both Student and School performance.

3. Dynamic School Rankings: A ranking system that evaluates schools based on the longitudinal average of student performance scores.

4. Student Highlights: Features "Best Student of the Year" and "Best Student per Option" to recognize and celebrate individual excellence.

5. Multi-Dimensional Filters: Capability to slice and dice data by Year, Province, and Option.

6. Visual Hierarchy: A professional UI/UX design using color-coded indicators (blue/purple) to enhance data readability.

## Methodology
The development followed a structured, data-driven methodology:

1. Web Scraping: Automated collection of official Palmarès reports from ministry sources.

2. PDF Parsing & Extraction: Conversion of unstructured PDF data into machine-readable formats.

3. Database Modeling: Design of a normalized relational database (3NF) to store and manage complex school and student datasets.

4. Dashboard Design: Development of a responsive, interactive web interface using Python-based frameworks.

## Technologies Used
    Backend: Python, Flask
    Database: SQL / MySQL
    Frontend: HTML5, CSS, JavaScript
    Data Processing: PDF Parsing and Web Scraping libraries

## System Architecture

The project utilizes a modular architecture:
    Data Layer: A relational database organizes years of examination data.
    Logic Layer: SQL queries handle complex aggregations, rankings, and filtering logic.
    Processing Layer: A Flask backend processes data requests and manages API routes.
    Presentation Layer: A modern web interface displays data through an intuitive dashboard.
## Installation
1. Prerequisites
    Python 3.12+
    MySQL Server
    uv

## Setup
1. Clone the repository:
    git clone https://github.com/your-username/your-repository-name.git
    cd your-repository-name
2. Install dependencies: 
Using uv:
    uv sync
   
4. Database Configuration: in that process we did a step by step method to collect data and insert them inside a database. and by that i mean
    . Web scraping: Since the Palmarès (national exam rankings) are published on the official website of the Ministry of Education (MINEDUC-NC), I implemented a scraping routine to download all relevant PDF documents.
    I created a Python file named downloader.py, which performs the following operations:
        Extract card links from the main Palmarès page
        Convert relative URLs to absolute URLs
        Categorize links (PDF vs. HTML)
        Generate clean filenames for downloaded PDFs
        Identify all PDF file locations
        Download and save all Palmarès PDFs locally
    . PDF parsing :The aims of this step was to extract structured data from the downloaded Palmarès PDFs and convert it into JSON. To achieve this, I developed a script named pdf_parser, which performs the following tasks:
        List PDF files in the designated directory
        Extract header, body, and footer text from each PDF page
        Identify and extract school-level data, including:
            School name
            School code
            Number of participants
            Number of successful candidates
            Academic option
            Province
            Year
        Identify and extract student-level data, including:
            Student name
            Gender
            Percentage
            Option
            Year
            School
        Export extracted data into two structured JSON files:
            school_data.json
            student_data.json
    . and then i created a database using Mysql and since we have json's file we can use any kind of database we want and insert those data inside the database 
and from there we perform the database confirguration and connect it to the project using mysql.connector 

5. Run the application:
    python -m src.app.app

## Usage
    Once the application is running, access the dashboard via your web browser (typically localhost:5000) to:

    Consult Rankings: View and sort schools based on historical performance.

    Trend Analysis: Analyze how specific provinces or options have performed over time.

    Search Excellence: Identify top-performing students across various academic options.

## Project Structure

├── main.py                 
├── pyproject.toml          
├── README.md               
├── run.sh                  
├── src
│   ├── app                 
│   │   ├── backend         
│   │   ├── queries.py      
│   │   ├── static          
│   │   └── templates       
│   ├── db                  
│   ├── downloader.py       
│   └── exetat_pak          
└── uv.lock                 

## Future Enhancements
    AI agent : developping a chatbot that for quick searching and user friendly conversation 

    Longitudinal Trends: Integration of multi-year performance trend visualizations.

    Sector Comparison: Comparative analysis between province , 

    Geospatial Mapping: Integration of interactive maps for school location analysis.

    Parental Portal: Custom views tailored specifically for parent-school matching.

## Author
Yves Murhabazi

Institution: ISBAT University, Faculty of Information and Communication Technology

Location: Kampala, Uganda
