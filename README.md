 Interactive Dashboard for School Performance Analysis (EXETAT-DRC)
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

3. Database Configuration: Update the database connection settings in src/db/ or your configuration file.

4. Run the application:
    python -m src.app.app

## Usage
    Once the application is running, access the dashboard via your web browser (typically localhost:5000) to:

    Consult Rankings: View and sort schools based on historical performance.

    Trend Analysis: Analyze how specific provinces or options have performed over time.

    Search Excellence: Identify top-performing students across various academic options.

## Project Structure

├── main.py                 # Entry point
├── pyproject.toml          # Project dependencies and metadata
├── README.md               # Documentation
├── run.sh                  # Execution script
├── src
│   ├── app                 # Web application logic
│   │   ├── backend         # API and data processing
│   │   ├── queries.py      # SQL aggregation logic
│   │   ├── static          # CSS and JS files
│   │   └── templates       # HTML files
│   ├── db                  # Database scripts (Migration & Insertion)
│   ├── downloader.py       # Scraper for official reports
│   └── exetat_pak          # Core PDF parsing engine
└── uv.lock                 # Dependency lockfile

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
