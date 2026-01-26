def calculate_success_rate(participants, reussites):
    """Calculate success rate percentage"""
    if participants == 0:
        return 0
    return round((reussites / participants) * 100, 2)


def get_available_years(connection):
    """Get all available years from the database"""
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT years FROM schools ORDER BY years DESC")
    years = [row['years'] for row in cursor.fetchall()]
    cursor.close()
    
    return years


def get_filter_options(connection, year=None):
    """Get available provinces and options based on selected year"""
    cursor = connection.cursor(dictionary=True)
    
    # Build query based on year filter
    province_query = "SELECT DISTINCT province FROM schools"
    option_query = "SELECT DISTINCT school_option FROM schools"
    params = []
    
    if year:
        province_query += " WHERE years = %s"
        option_query += " WHERE years = %s"
        params = [year]
    
    province_query += " ORDER BY province"
    option_query += " ORDER BY school_option"
    
    # Get provinces
    cursor.execute(province_query, params)
    provinces = [row['province'] for row in cursor.fetchall()]
    
    # Get options
    cursor.execute(option_query, params)
    options = [row['school_option'] for row in cursor.fetchall()]
    
    cursor.close()
    
    return {
        'provinces': provinces,
        'options': options
    }


def get_school_rankings(connection, year=None, province=None, option=None, limit=50):
    """Get school rankings based purely on average student performance (school percentage)"""
    cursor = connection.cursor(dictionary=True)

    # 1. Determine the target year
    if year:
        target_year = year
    else:
        cursor.execute("SELECT MAX(years) AS latest_year FROM schools")
        target_year = cursor.fetchone()['latest_year']

    # 2. Build ranking query based on school percentage only
    query = """
        SELECT 
            s.school_name,
            s.school_option,
            s.province,
            s.years,
            s.participants AS total_participants,
            s.reussites AS total_reussites,
            SUM(st.pourcentage) AS total_points,
            COUNT(st.pourcentage) AS successful_students,
            ROUND(
                (SUM(st.pourcentage) / (COUNT(st.pourcentage) * 100)) * 100,
                2
            ) AS school_percentage
        FROM schools s
        JOIN students st 
            ON s.school_name = st.school_name
            AND s.school_option = st.school_option
            AND s.years = st.years
            AND s.province = st.province
        WHERE s.years = %s
            AND st.years = %s
    """

    params = [target_year, target_year]

    # Optional filters
    if province:
        query += " AND s.province = %s AND st.province = %s"
        params.extend([province, province])

    if option:
        query += " AND s.school_option = %s AND st.school_option = %s"
        params.extend([option, option])

    query += """
        GROUP BY s.school_name, s.school_option, s.province, s.years, 
                 s.participants, s.reussites
        ORDER BY school_percentage DESC, successful_students DESC
        LIMIT %s
    """

    params.append(limit)

    cursor.execute(query, params)
    schools = cursor.fetchall()

    # Add ranking number and use school_percentage as success_rate for display
    for i, school in enumerate(schools, 1):
        school['rank'] = i
        school['success_rate'] = school['school_percentage']

    cursor.close()

    return schools


def get_best_student(connection, year=None, province=None, option=None):
    """Get the best student overall"""
    cursor = connection.cursor(dictionary=True)
    
    query = """
        SELECT 
            student_name,
            school_name,
            school_option,
            province,
            pourcentage,
            years
        FROM students
        WHERE 1=1
    """
    params = []
    
    if year:
        query += " AND years = %s"
        params.append(year)
    
    if province:
        query += " AND province = %s"
        params.append(province)
    
    if option:
        query += " AND school_option = %s"
        params.append(option)
    
    query += " ORDER BY pourcentage DESC LIMIT 1"
    
    cursor.execute(query, params)
    student = cursor.fetchone()
    
    cursor.close()
    
    return student


def get_best_per_option(connection, year=None, province=None):
    """Get the best student for each option"""
    cursor = connection.cursor(dictionary=True)
    
    # Get all options first
    options_query = "SELECT DISTINCT school_option FROM students WHERE 1=1"
    options_params = []
    
    if year:
        options_query += " AND years = %s"
        options_params.append(year)
    
    if province:
        options_query += " AND province = %s"
        options_params.append(province)
    
    cursor.execute(options_query, options_params)
    options = [row['school_option'] for row in cursor.fetchall()]
    
    best_students = []
    
    for opt in options:
        query = """
            SELECT 
                student_name,
                school_name,
                school_option,
                province,
                pourcentage,
                years
            FROM students
            WHERE school_option = %s
        """
        params = [opt]
        
        if year:
            query += " AND years = %s"
            params.append(year)
        
        if province:
            query += " AND province = %s"
            params.append(province)
        
        query += " ORDER BY pourcentage DESC LIMIT 1"
        
        cursor.execute(query, params)
        student = cursor.fetchone()
        
        if student:
            best_students.append(student)
    
    cursor.close()
    
    return best_students


def get_statistics(connection, year=None, province=None, option=None):
    """Get overall statistics including school performance metrics"""
    cursor = connection.cursor(dictionary=True)
    
    # Build query for basic statistics
    basic_query = """
        SELECT 
            COUNT(DISTINCT school_name) as total_schools,
            SUM(participants) as total_participants,
            SUM(reussites) as total_reussites,
            ROUND(AVG(reussites / participants * 100), 2) as avg_pass_rate
        FROM schools
        WHERE 1=1
    """
    params = []
    
    if year:
        basic_query += " AND years = %s"
        params.append(year)
    
    if province:
        basic_query += " AND province = %s"
        params.append(province)
    
    if option:
        basic_query += " AND school_option = %s"
        params.append(option)
    
    cursor.execute(basic_query, params)
    stats = cursor.fetchone()
    
    # Get average school performance based on student scores using subquery
    performance_query = """
        SELECT 
            ROUND(AVG(school_perf), 2) AS avg_school_performance
        FROM (
            SELECT 
                ROUND(
                    SUM(st.pourcentage) / (COUNT(st.pourcentage) * 100) * 100,
                    2
                ) AS school_perf
            FROM schools s
            JOIN students st 
                ON s.school_name = st.school_name
                AND s.school_option = st.school_option
                AND s.years = st.years
                AND s.province = st.province
            WHERE 1=1
    """
    perf_params = []
    
    if year:
        performance_query += " AND s.years = %s AND st.years = %s"
        perf_params.extend([year, year])
    
    if province:
        performance_query += " AND s.province = %s AND st.province = %s"
        perf_params.extend([province, province])
    
    if option:
        performance_query += " AND s.school_option = %s AND st.school_option = %s"
        perf_params.extend([option, option])
    
    performance_query += """
            GROUP BY s.school_name, s.school_option, s.province, s.years
        ) AS school_performances
    """
    
    cursor.execute(performance_query, perf_params)
    perf_result = cursor.fetchone()
    
    # Combine both statistics
    if perf_result and perf_result['avg_school_performance']:
        stats['avg_success_rate'] = perf_result['avg_school_performance']
    else:
        # Fallback to pass rate if no student data available
        stats['avg_success_rate'] = stats['avg_pass_rate']
    
    cursor.close()
    
    return stats


def get_school_detail(connection, school_name):
    """Get detailed data for a specific school across years, aggregated by year"""
    cursor = connection.cursor(dictionary=True)
    
    # Aggregate data by year in case there are multiple entries per year
    cursor.execute("""
        SELECT 
            s.school_name,
            s.school_code,
            s.school_option,
            s.province,
            s.years,
            SUM(s.participants) as participants,
            SUM(s.reussites) as reussites,
            ROUND((SUM(s.reussites) / SUM(s.participants) * 100), 2) as pass_rate,
            COALESCE(
                ROUND(
                    SUM(st.pourcentage) / (COUNT(st.pourcentage) * 100) * 100,
                    2
                ),
                NULL
            ) as school_percentage,
            COUNT(st.pourcentage) as successful_students
        FROM schools s
        LEFT JOIN students st 
            ON s.school_name = st.school_name
            AND s.school_option = st.school_option
            AND s.years = st.years
            AND s.province = st.province
        WHERE s.school_name = %s
        GROUP BY s.school_name, s.school_code, s.school_option, s.province, s.years
        ORDER BY s.years DESC
    """, (school_name,))
    
    school_data = cursor.fetchall()
    
    cursor.close()
    
    return school_data