from flask import Flask, render_template, request, jsonify
from src.db.db import get_connection
from src.app.queries import (
    get_available_years,
    get_filter_options,
    get_school_rankings,
    get_best_student,
    get_best_per_option,
    get_statistics,
    get_school_detail
)


app = Flask(__name__)


@app.route('/')
def index():
    """Main dashboard page"""
    connection = get_connection()
    if not connection:
        return "Database connection error", 500
    
    try:
        years = get_available_years(connection)
        return render_template('dashboard.html', years=years)
    finally:
        connection.close()


@app.route('/api/filter-options')
def filter_options():
    """API endpoint to get available provinces and options based on selected year"""
    year = request.args.get('year', type=int)
    
    connection = get_connection()
    if not connection:
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        result = get_filter_options(connection, year)
        return jsonify(result)
    finally:
        connection.close()


@app.route('/api/rankings')
def rankings():
    """API endpoint to get school rankings over a 5-year window anchored on the selected year"""
    year = request.args.get('year', type=int)
    province = request.args.get('province')
    option = request.args.get('option')
    limit = request.args.get('limit', 50, type=int)

    connection = get_connection()
    if not connection:
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        schools = get_school_rankings(connection, year, province, option, limit)
        return jsonify(schools)
    finally:
        connection.close()


@app.route('/api/best-student')
def best_student():
    """Get the best student overall"""
    year = request.args.get('year', type=int)
    province = request.args.get('province')
    option = request.args.get('option')
    
    connection = get_connection()
    if not connection:
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        student = get_best_student(connection, year, province, option)
        return jsonify(student if student else {})
    finally:
        connection.close()


@app.route('/api/best-per-option')
def best_per_option():
    """Get the best student for each option"""
    year = request.args.get('year', type=int)
    province = request.args.get('province')
    
    connection = get_connection()
    if not connection:
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        best_students = get_best_per_option(connection, year, province)
        return jsonify(best_students)
    finally:
        connection.close()


@app.route('/api/statistics')
def statistics():
    """Get overall statistics"""
    year = request.args.get('year', type=int)
    province = request.args.get('province')
    option = request.args.get('option')
    
    connection = get_connection()
    if not connection:
        return jsonify({'error': 'Database connection error'}), 500
    
    try:
        stats = get_statistics(connection, year, province, option)
        return jsonify(stats)
    finally:
        connection.close()


@app.route('/school/<school_name>')
def school_detail(school_name):
    """Detailed view for a specific school"""
    connection = get_connection()
    if not connection:
        return "Database connection error", 500
    
    try:
        school_data = get_school_detail(connection, school_name)
        
        if not school_data:
            return "School not found", 404
        
        return render_template('school_detail.html', school_data=school_data)
    finally:
        connection.close()


if __name__ == '__main__':
    app.run(debug=True)