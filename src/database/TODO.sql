SELECT student_code, COUNT(DISTINCT student_code) as name_variants  FROM students  GROUP BY student_code  HAVING name_variants > 1;

--to check something while looking for my bug 
select * from students join exam_results on students.id = exam_results.student_id join exetat_entry on exam_results.school_session_id = exetat_entry.id where student_name = "MBO MOKIOMBA";

--kasongo wa kasongo 
 select count(student_name) as total_student_2022 from students 
 join exam_results on exam_results.student_id = students.id 
 join exetat_entry on exetat_entry.id = exam_results.school_session_id 
 join schools on schools.id = exetat_entry.school_id 
 join provinces on schools.province_id = provinces.id 
 where years = 2022;

 select student_name, years, exam_results.percentage, participants, reussites, sexe, province_name, school_name, schools.id from students 
 join exam_results on exam_results.student_id = students.id 
 join exetat_entry on exetat_entry.id = exam_results.school_session_id 
 join schools on schools.id = exetat_entry.school_id 
 join provinces on schools.province_id = provinces.id 
 where schools.id = '466536'
 ORDER BY student_name asc ;
 
delete s, er, ee, sc, op, ep from students s
join exam_results er on s.id = er.student_id 
join exetat_entry ee on ee.id = er.school_session_id 
join schools sc on ee.school_id = sc.id 
join options op on ee.option_id = op.id
join educational_province ep on sc.province_id = ep.id
where years = 2009;

delete ep, ee, sc from educational_province ep 
join schools sc on sc.province_id = ep.id
join exetat_entry ee on ee.schoold_id = sc.id 
where years = 2009;
 
Explain analyze select student_name, school_name , years, exam_results.percentage, province_name, option_name from students  join exam_results on students.id = exam_results.student_id  join exetat_entry on exetat_entry.id = exam_results.school_session_id  join schools on exetat_entry.school_id = schools.id  join options on exetat_entry.option_id = options.id join provinces on schools.province_id = provinces.id where option_id = 1022 order by years desc;
 

 SELECT * 
FROM students 
WHERE SUBSTRING_INDEX(student_name, ' ', -1) = 'MURHABAZI';   

SELECT 
    TABLE_NAME,
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS COLUMNS,
    NON_UNIQUE,
    INDEX_TYPE
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'exetat'
GROUP BY TABLE_NAME, INDEX_NAME, NON_UNIQUE, INDEX_TYPE
ORDER BY TABLE_NAME, INDEX_NAME;   

--student name starting with digit , 
SELECT * FROM students WHERE student_name REGEXP '^[0-9]+';  

--adding a new column to my exetat_entry to check something 

ALTER TABLE exetat_entry ADD COLUMN total_students INT NOT NULL DEFAULT 0;
UPDATE exetat_entry ee
JOIN (
    SELECT school_session_id, COUNT(*) AS cnt
    FROM exam_results
    GROUP BY school_session_id
) counts ON counts.school_session_id = ee.id
SET ee.total_students = counts.cnt;
-- code i'm using to check my database problem just changing the name 
 select student_name, school_name , years, exam_results.percentage, province_name, option_name from students  join exam_results on students.id = exam_results.student_id  join exetat_entry on exetat_entry.id = exam_results.school_session_id  join schools on exetat_entry.school_id = schools.id  join options on exetat_entry.option_id = options.id join provinces on schools.province_id = provinces.id  where student_name = 'KABANGE NUMBI PATIENT';
 
--kind of hard to understand here 
mysql> UPDATE exetat_entry ee
    -> JOIN (
    ->     SELECT school_session_id, COUNT(*) AS cnt
    ->     FROM exam_results
    ->     GROUP BY school_session_id
    -> ) counts ON counts.school_session_id = ee.id
    -> SET ee.total_students = counts.cnt;
Query OK, 481369 rows affected (46.55 sec)
Rows matched: 481369  Changed: 481369  Warnings: 0

mysql> select count(id) from exetat_entry;
+-----------+
| count(id) |
+-----------+
|    551035 |
+-----------+
1 row in set (0.27 sec)

-- still trying to get it 
mysql> select count(id) from exetat_entry where reussites = 0;
+-----------+
| count(id) |
+-----------+
|     66977 |
+-----------+
-- still on it
select * from exetat_entry where reussites != total_students;
-- again 
select * from exetat_entry where reussites != total_students and reussites >= 100;

--still on it 
select school_name , years, province_name, option_name from schools 
join exetat_entry on exetat_entry.school_id = schools.id 
join options on exetat_entry.option_id = options.id
join provinces on schools.province_id = provinces.id
where school_id= 406117 and option_id = 19;

--funny line 
 73066 |     73066 |  2012 |        17 |           11 |         5 |             10 

 -- for the school which doesn't have same number of reussite as number of students;
 select * from exetat_entry where reussites != total_students ;

 --duplication data checking
 SELECT 
    student_name,
    school_name,
    years,
    percentage,
    province_name,
    option_name,
    COUNT(*) as duplicate_count
FROM (
    SELECT 
        st.student_name,
        s.school_name,
        ee.years,
        er.percentage,
        p.province_name,
        o.option_name
    FROM exam_results er
    JOIN students st ON st.id = er.student_id
    JOIN exetat_entry ee ON ee.id = er.school_session_id
    JOIN schools s ON s.id = ee.school_id
    JOIN provinces p ON p.id = s.province_id
    JOIN options o ON o.id = ee.option_id
    WHERE province_name = 'KINSHASA – EST' and years = 2009
) AS full_data
GROUP BY 
    student_name, school_name, years, 
    percentage, province_name, option_name
HAVING COUNT(*) > 1 
ORDER BY duplicate_count DESC;
 
 --there distinct years 
 SELECT DISTINCT years
FROM (
    SELECT 
        st.student_name,
        s.school_name,
        ee.years,
        er.percentage,
        p.province_name,
        o.option_name,
        COUNT(*) as duplicate_count
    FROM exam_results er
    JOIN students st ON st.id = er.student_id
    JOIN exetat_entry ee ON ee.id = er.school_session_id
    JOIN schools s ON s.id = ee.school_id
    JOIN provinces p ON p.id = s.province_id
    JOIN options o ON o.id = ee.option_id
    GROUP BY 
        st.student_name, s.school_name, ee.years, 
        er.percentage, p.province_name, o.option_name
    HAVING COUNT(*) > 1
) AS dupes
ORDER BY years;


--distinct years and province 
SELECT DISTINCT years, province_name
FROM (
    SELECT 
        st.student_name,
        s.school_name,
        ee.years,
        er.percentage,
        p.province_name,
        o.option_name,
        COUNT(*) as duplicate_count
    FROM exam_results er
    JOIN students st ON st.id = er.student_id
    JOIN exetat_entry ee ON ee.id = er.school_session_id
    JOIN schools s ON s.id = ee.school_id
    JOIN provinces p ON p.id = s.province_id
    JOIN options o ON o.id = ee.option_id
    GROUP BY 
        st.student_name, s.school_name, ee.years, 
        er.percentage, p.province_name, o.option_name
    HAVING COUNT(*) > 1
) AS dupes
ORDER BY years, province_name;

--dashboard new update and new statistic data ...
--total number of schools
Select Count(*) from schools 
join exetat_entry on schools.id = exetat_entry.school_id
where years = 2023; --that can depend of the user selection 

--total number of participants
Select SUM(participants) from exetat_entry where years = 2023;

--What is the total number of successful students?
Select SUM(reussites) FROM  exetat_entry where years = 2023;
--trying to check if total student are total reussite 
 select Count(*) as total_student from students
 join exam_results on exam_results.student_id = students.id 
 join exetat_entry on exetat_entry.id = exam_results.school_session_id
 where years = 2023 ;
--What is the national success rate?

Select (SUM(reussites)/SUM(participants))*100 as Success_rate 
from exetat_entry where years = 2023;


--solving province problem some how 
INSERT INTO pr_after_reform26 (name)
VALUES
('BAS-UELE'),
('EQUATEUR'),
('HAUT-KATANGA'),
('HAUT-LOMAMI'),
('HAUT-UELE'),
('HORS-FRONTIERE'),
('ITURI'),
('KASAI'),
('KASAI CENTRAL'),
('KASAI ORIENTAL'),
('KINSHASA'),
('KONGO CENTRAL'),
('KWANGO'),
('KWILU'),
('LUALABA'),
('LOMAMI'),
('MANIEMA'),
('MAI-NDOMBE'),
('MONGALA'),
('NORD-KIVU'),
('NORD-UBANGI'),
('SANKURU'),
('SUD-KIVU'),
('SUD-UBANGI'),
('TANGANYIKA'),
('TSHOPO'),
('TSHUAPA');


INSERT INTO pr_before_reform11 (name)
VALUES
('BANDUNDU'),
('BAS-CONGO'),
('EQUATEUR'),
('KASAI-OCCIDENTAL'),
('KASAI-ORIENTAL'),
('KATANGA'),
('KINSHASA'),
('MANIEMA'),
('NORD-KIVU'),
('SUD-KIVU'),
('HORS – FRONTIERE'),
('PROVINCE ORIENTALE');

CREATE TABLE pr_before_reform11 (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE pr_after_reform26 (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);


+----+----------------+
| id | name           |
+----+----------------+
|  1 | BAS-UELE       |
|  2 | EQUATEUR       |
|  3 | HAUT-KATANGA   |
|  4 | HAUT-LOMAMI    |
|  5 | HAUT-UELE      |
|  6 | ITURI          |
|  7 | KASAI          |
|  8 | KASAI CENTRAL  |
|  9 | KASAI ORIENTAL |
| 10 | KINSHASA       |
| 11 | KONGO CENTRAL  |
| 12 | KWANGO         |
| 13 | KWILU          |
| 14 | LUALABA        |
| 15 | LOMAMI         |
| 16 | MANIEMA        |
| 17 | MAI-NDOMBE     |
| 18 | MONGALA        |
| 19 | NORD-KIVU      |
| 20 | NORD-UBANGI    |
| 21 | SANKURU        |
| 22 | SUD-KIVU       |
| 23 | SUD-UBANGI     |
| 24 | TANGANYIKA     |
| 25 | TSHOPO         |
| 26 | TSHUAPA        |
| 27 | HORS-FRONTIERE |
+----+----------------+

database schema.
            CREATE TABLE IF NOT EXISTS pr_before_reform11 (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE
            )

            CREATE TABLE IF NOT EXISTS pr_after_reform26 (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE
            )
            
            CREATE TABLE IF NOT EXISTS educational_province (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE, 
                FOREIGN KEY (province_before_id) REFERENCES pr_before_reform11(id),
                FOREIGN KEY (province_after_id) REFERENCES pr_after_reform26(id)
            )

            CREATE TABLE IF NOT EXISTS options (
                id INT AUTO_INCREMENT PRIMARY KEY,
                option_name VARCHAR(255) NOT NULL UNIQUE
            )

            CREATE TABLE IF NOT EXISTS schools (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_code VARCHAR(100) NOT NULL,
                school_name VARCHAR(255) NOT NULL,
                province_id INT NOT NULL,
                INDEX school_name (school_name),
                INDEX idx_province (province_id),
                FOREIGN KEY (province_id) REFERENCES educational_province(id)
            )

            CREATE TABLE IF NOT EXISTS exetat_entry (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                school_id INT NOT NULL,
                years INT NOT NULL,
                option_id INT NOT NULL,
                participants INT NOT NULL DEFAULT 0,
                reussites INT NOT NULL DEFAULT 0,
                UNIQUE KEY idx_school_year_option (school_id, years, option_id),
                INDEX idx_years (years),
                INDEX idx_years_option (years, option_id),
                INDEX idx_years_school (years, school_id),
                INDEX option_id (option_id),
                FOREIGN KEY (school_id) REFERENCES schools(id),
                FOREIGN KEY (option_id) REFERENCES options(id)
            )

            CREATE TABLE IF NOT EXISTS students (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                student_code VARCHAR(100) NOT NULL,
                student_name VARCHAR(255) NOT NULL,
                sexe VARCHAR(16),
                INDEX student_name (student_name)
            )

            CREATE TABLE IF NOT EXISTS exam_results (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                student_id BIGINT NOT NULL,
                school_session_id BIGINT NOT NULL,
                percentage DECIMAL(5,2) NOT NULL,
                UNIQUE KEY idx_student_session (student_id, school_session_id),
                INDEX idx_percentage_session (percentage, school_session_id),
                INDEX school_session_id (school_session_id),
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (school_session_id) REFERENCES exetat_entry(id)
            )

--very important but will try it after . 
select * from students where student_name regexp '^[0-9]';
SELECT
    e.years,
    SUM(CASE WHEN r.percentage >= 50 AND r.percentage < 60 THEN 1 ELSE 0 END) AS pct_50_59,
    SUM(CASE WHEN r.percentage >= 60 AND r.percentage < 70 THEN 1 ELSE 0 END) AS pct_60_69,
    SUM(CASE WHEN r.percentage >= 70 AND r.percentage < 80 THEN 1 ELSE 0 END) AS pct_70_79,
    SUM(CASE WHEN r.percentage >= 80 AND r.percentage < 90 THEN 1 ELSE 0 END) AS pct_80_89,
    SUM(CASE WHEN r.percentage >= 90 THEN 1 ELSE 0 END) AS pct_90_plus,
    COUNT(*) AS total_students
FROM exam_results r
JOIN exetat_entry e ON e.id = r.school_session_id
WHERE e.years = 2023
ORDER BY e.years;

something usefule --  npx --yes prettier --write assets/style.css

