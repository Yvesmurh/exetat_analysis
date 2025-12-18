# DRC National Exam Results Dashboard

## Overview
This project is a data-driven dashboard designed to analyze and visualize national state examination (Exetat) results in the Democratic Republic of Congo (DRC). The system ranks secondary schools based on exam performance and presents insights in a clear and accessible format to support informed decision-making by showing the statistic of the national state exam .

The project aims to transform existing examination data (pdf file) into actionable information (dashboard) for parents, educators, and education stakeholders.

## Problem Statement
In the DRC, the Ministry of Education publishes the Palmarès de l’Exetat, which presents school performance based on the National State Examination. However, these results are disseminated in static, text-heavy, and tabular formats (pdf format), which are difficult for stakeholders—particularly parents, school administrators, and policymakers—to interpret or analyze effectively. The lack of interactivity and absence of integrated visual analytics limits users’s ability to compare schools, identify performance trends, or assess relative educational quality

## Features
- School ranking based on national exam performance
- Analysis of success rates and participation
- Filtering by year and location
- Clear visual presentation of results through a dashboard

## Technologies Used
- Python
- SQL / MySQL
- Flask
- HTML / CSS

## System Architecture
The project follows a modular architecture:
- A relational database stores and organizes examination data
- SQL queries perform aggregation and ranking
- A Flask backend processes data and exposes it to the frontend
- A web interface displays results through a user-friendly dashboard

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/your-repository-name.git
2. Configure the database connection in the application settings.

3. Run the application:
    python -m src.app.app

## Usage 
After launching the application, users can access the dashboard via a web browser to:
    View ranked lists of schools
    Analyze performance trends by year
    Explore key indicators related to examination success

