def calculate_success_rate(participants, reussites):
    """Calculate success rate percentage"""
    if participants == 0:
        return 0
    return round((reussites / participants) * 100, 2)


def get_available_years(connection):
    """Get all available years from the database"""
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT years FROM exetat_entry ORDER BY years DESC")
    years = [row['years'] for row in cursor.fetchall()]
    cursor.close()
    
    return years


def get_filter_options(connection, year=None):
    """Get available provinces and options based on selected year - combined query"""
    cursor = connection.cursor(dictionary=True)
    
    # Single query using UNION to get both provinces and options efficiently
    query = """
        SELECT 'province' AS category, p.province_name AS value
        FROM exetat_entry ee
        JOIN schools s ON ee.school_id = s.id
        JOIN provinces p ON s.province_id = p.id
        WHERE 1=1
    """
    params = []
    
    if year:
        query += " AND ee.years = %s"
        params.append(year)
    
    query += """
        GROUP BY p.province_name
        UNION ALL
        SELECT 'option' AS category, o.option_name AS value
        FROM exetat_entry ee
        JOIN options o ON ee.option_id = o.id
        WHERE 1=1
    """
    
    if year:
        query += " AND ee.years = %s"
        params.append(year)
    
    query += " GROUP BY o.option_name"
    
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
    """Get school rankings based on normalized exetat and exam result tables."""
    cursor = connection.cursor(dictionary=True)

    # 1. Determine the target year
    if year:
        target_year = year
    else:
        cursor.execute("SELECT MAX(years) AS latest_year FROM exetat_entry")
        target_year = cursor.fetchone()['latest_year']

    query = """
        SELECT
            s.school_name,
            o.option_name AS school_option,
            p.province_name AS province,
            ee.years,
            ee.participants AS total_participants,
            ee.reussites AS total_reussites,
            COALESCE(SUM(er.percentage), 0) AS total_points,
            COUNT(er.percentage) AS successful_students,
            ROUND(
                IF(COUNT(er.percentage) = 0, 0, SUM(er.percentage) / (COUNT(er.percentage) * 100) * 100),
                2
            ) AS school_percentage
        FROM exetat_entry ee
        JOIN schools s ON ee.school_id = s.id
        JOIN provinces p ON s.province_id = p.id
        JOIN options o ON ee.option_id = o.id
        LEFT JOIN exam_results er ON er.school_session_id = ee.id
        WHERE ee.years = %s
    """

    params = [target_year]

    if province:
        query += " AND p.province_name = %s"
        params.append(province)

    if option:
        query += " AND o.option_name = %s"
        params.append(option)

    query += """
        GROUP BY s.school_name, o.option_name, p.province_name, ee.years,
                 ee.participants, ee.reussites
        ORDER BY school_percentage DESC, successful_students DESC
        LIMIT %s
    """

    params.append(limit)

    cursor.execute(query, params)
    schools = cursor.fetchall()

    for i, school in enumerate(schools, 1):
        school['rank'] = i
        school['success_rate'] = school['school_percentage']

    cursor.close()

    return schools


def get_best_student(connection, year=None, province=None, option=None):
    """Get the best student overall from normalized tables."""
    cursor = connection.cursor(dictionary=True)
    
    query = """
        SELECT
            s.student_name AS student_name,
            sc.school_name,
            o.option_name AS school_option,
            p.province_name AS province,
            er.percentage AS pourcentage,
            ee.years
        FROM exam_results er
        JOIN students s ON er.student_id = s.id
        JOIN exetat_entry ee ON er.school_session_id = ee.id
        JOIN schools sc ON ee.school_id = sc.id
        JOIN provinces p ON sc.province_id = p.id
        JOIN options o ON ee.option_id = o.id
        WHERE 1=1
    """
    params = []
    
    if year:
        query += " AND ee.years = %s"
        params.append(year)
    
    if province:
        query += " AND p.province_name = %s"
        params.append(province)
    
    if option:
        query += " AND o.option_name = %s"
        params.append(option)
    
    query += " ORDER BY er.percentage DESC LIMIT 1"
    
    cursor.execute(query, params)
    student = cursor.fetchone()
    
    cursor.close()
    
    return student


def get_best_per_option(connection, year=None, province=None):
    """Get the best student for each option using window function (single query)."""
    cursor = connection.cursor(dictionary=True)
    
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
                s.student_name AS student_name,
                sc.school_name,
                o.option_name AS school_option,
                p.province_name AS province,
                er.percentage AS pourcentage,
                ee.years,
                ROW_NUMBER() OVER (PARTITION BY o.option_name ORDER BY er.percentage DESC) AS rn
            FROM exam_results er
            JOIN students s ON er.student_id = s.id
            JOIN exetat_entry ee ON er.school_session_id = ee.id
            JOIN schools sc ON ee.school_id = sc.id
            JOIN provinces p ON sc.province_id = p.id
            JOIN options o ON ee.option_id = o.id
            WHERE 1=1
    """
    params = []
    
    if year:
        query += " AND ee.years = %s"
        params.append(year)
    
    if province:
        query += " AND p.province_name = %s"
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
    """Get overall statistics combined in a single query for better performance."""
    cursor = connection.cursor(dictionary=True)
    
    query = """
        SELECT
            school_stats.total_schools,
            school_stats.total_participants,
            school_stats.total_reussites,
            school_stats.avg_pass_rate,
            COALESCE(student_perf.avg_school_performance, school_stats.avg_pass_rate) AS avg_success_rate
        FROM (
            SELECT
                COUNT(DISTINCT ee.school_id) AS total_schools,
                SUM(ee.participants) AS total_participants,
                SUM(ee.reussites) AS total_reussites,
                ROUND(AVG(CASE WHEN ee.participants = 0 THEN 0 ELSE ee.reussites / ee.participants * 100 END), 2) AS avg_pass_rate
            FROM exetat_entry ee
            JOIN schools s ON ee.school_id = s.id
            JOIN provinces p ON s.province_id = p.id
            JOIN options o ON ee.option_id = o.id
            WHERE 1=1
    """
    params = []
    
    if year:
        query += " AND ee.years = %s"
        params.append(year)
    
    if province:
        query += " AND p.province_name = %s"
        params.append(province)
    
    if option:
        query += " AND o.option_name = %s"
        params.append(option)
    
    query += """
        ) school_stats
        LEFT JOIN (
            SELECT
                ROUND(AVG(entry_perf), 2) AS avg_school_performance
            FROM (
                SELECT
                    ee.id,
                    ROUND(
                        IF(COUNT(er.percentage) = 0, 0, SUM(er.percentage) / (COUNT(er.percentage) * 100) * 100),
                        2
                    ) AS entry_perf
                FROM exetat_entry ee
                JOIN schools s ON ee.school_id = s.id
                JOIN provinces p ON s.province_id = p.id
                JOIN options o ON ee.option_id = o.id
                LEFT JOIN exam_results er ON er.school_session_id = ee.id
                WHERE 1=1
    """
    
    if year:
        query += " AND ee.years = %s"
        params.append(year)
    
    if province:
        query += " AND p.province_name = %s"
        params.append(province)
    
    if option:
        query += " AND o.option_name = %s"
        params.append(option)
    
    query += """
                GROUP BY ee.id
            ) AS school_performances
        ) student_perf ON 1=1
    """
    
    cursor.execute(query, params)
    stats = cursor.fetchone()
    
    cursor.close()
    
    return stats


def get_school_detail(connection, school_name):
    """Get detailed data for a specific school across years, aggregated by year."""
    cursor = connection.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT
            s.school_name,
            s.school_code,
            o.option_name AS school_option,
            p.province_name AS province,
            ee.years,
            ee.participants AS participants,
            ee.reussites AS reussites,
            ROUND(
                CASE WHEN ee.participants = 0 THEN 0 ELSE ee.reussites / ee.participants * 100 END,
                2
            ) AS pass_rate,
            CASE WHEN COUNT(er.percentage) = 0 THEN NULL
                ELSE ROUND(SUM(er.percentage) / (COUNT(er.percentage) * 100) * 100, 2)
            END AS school_percentage,
            COUNT(er.percentage) AS successful_students
        FROM schools s
        JOIN exetat_entry ee ON ee.school_id = s.id
        JOIN provinces p ON s.province_id = p.id
        JOIN options o ON ee.option_id = o.id
        LEFT JOIN exam_results er ON er.school_session_id = ee.id
        WHERE s.school_name = %s
        GROUP BY s.school_name, s.school_code, o.option_name, p.province_name, ee.years,
                 ee.participants, ee.reussites
        ORDER BY ee.years DESC
    """, (school_name,))
    
    school_data = cursor.fetchall()
    
    cursor.close()
    
    return school_data