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
    """Get available provinces and options based on selected year - combined query"""
    cursor = connection.cursor(dictionary=True)
    
    # Single query using UNION to get both provinces and options efficiently
    query = """
        SELECT 'province' AS category, province AS value
        FROM schools
        WHERE 1=1
    """
    params = []
    
    if year:
        query += " AND years = %s"
        params.append(year)
    
    query += """
        GROUP BY province
        UNION ALL
        SELECT 'option' AS category, school_option AS value
        FROM schools
        WHERE 1=1
    """
    
    if year:
        query += " AND years = %s"
        params.append(year)
    
    query += " GROUP BY school_option"
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    
    # Parse results into provinces and options
    provinces = []
    options = []
    for row in results:
        if row['category'] == 'province':
            provinces.append(row['value'])
        else:
            options.append(row['value'])
    
    cursor.close()
    
    return {
        'provinces': sorted(provinces),
        'options': sorted(options)
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

    # 2. Build ranking query optimized for index usage
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
        INNER JOIN students st 
            ON s.school_name = st.school_name
            AND s.school_option = st.school_option
            AND s.years = st.years
            AND s.province = st.province
        WHERE s.years = %s
    """

    params = [target_year]

    # Optional filters - indexes will be used for these
    if province:
        query += " AND s.province = %s"
        params.append(province)

    if option:
        query += " AND s.school_option = %s"
        params.append(option)

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
    """Get the best student for each option using window function (single query)"""
    cursor = connection.cursor(dictionary=True)
    
    # Use ROW_NUMBER() to get best student per option in ONE query (eliminates N+1 problem)
    query = """
        SELECT 
            student_name,
            school_name,
            school_option,
            province,
            pourcentage,
            years
        FROM (
            SELECT 
                student_name,
                school_name,
                school_option,
                province,
                pourcentage,
                years,
                ROW_NUMBER() OVER (PARTITION BY school_option ORDER BY pourcentage DESC) AS rn
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
    
    query += """
        ) AS ranked
        WHERE rn = 1
        ORDER BY pourcentage DESC
    """
    
    cursor.execute(query, params)
    best_students = cursor.fetchall()
    
    cursor.close()
    
    return best_students


def get_statistics(connection, year=None, province=None, option=None):
    """Get overall statistics combined in a single query for better performance"""
    cursor = connection.cursor(dictionary=True)
    
    # Combine school stats and student performance in ONE query using LEFT JOIN
    query = """
        SELECT 
            school_stats.total_schools,
            school_stats.total_participants,
            school_stats.total_reussites,
            school_stats.avg_pass_rate,
            COALESCE(student_perf.avg_school_performance, school_stats.avg_pass_rate) AS avg_success_rate
        FROM (
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
        query += " AND years = %s"
        params.append(year)
    
    if province:
        query += " AND province = %s"
        params.append(province)
    
    if option:
        query += " AND school_option = %s"
        params.append(option)
    
    query += """
        ) school_stats
        LEFT JOIN (
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
    
    if year:
        query += " AND s.years = %s AND st.years = %s"
        params.extend([year, year])
    
    if province:
        query += " AND s.province = %s AND st.province = %s"
        params.extend([province, province])
    
    if option:
        query += " AND s.school_option = %s AND st.school_option = %s"
        params.extend([option, option])
    
    query += """
                GROUP BY s.school_name, s.school_option, s.province, s.years
            ) AS school_performances
        ) student_perf ON 1=1
    """
    
    cursor.execute(query, params)
    stats = cursor.fetchone()
    
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