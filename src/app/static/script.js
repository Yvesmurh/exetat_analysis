// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    updateDependentFilters();
    applyFilters();
});

// Update province and option dropdowns based on selected year
async function updateDependentFilters() {
    const year = document.getElementById('yearFilter').value;
    const provinceSelect = document.getElementById('provinceFilter');
    const optionSelect = document.getElementById('optionFilter');
    
    // Store current selections
    const currentProvince = provinceSelect.value;
    const currentOption = optionSelect.value;
    
    try {
        let url = '/api/filter-options';
        if (year) {
            url += `?year=${year}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        // Update provinces dropdown
        provinceSelect.innerHTML = '<option value="">All Provinces</option>';
        data.provinces.forEach(province => {
            const option = document.createElement('option');
            option.value = province;
            option.textContent = province;
            if (province === currentProvince) {
                option.selected = true;
            }
            provinceSelect.appendChild(option);
        });
        
        // Update options dropdown
        optionSelect.innerHTML = '<option value="">All Options</option>';
        data.options.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt;
            option.textContent = opt;
            if (opt === currentOption) {
                option.selected = true;
            }
            optionSelect.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error updating filter options:', error);
    }
}

// Apply current filters and reload all data
function applyFilters() {
    loadAllData();
}

// Reset all filters to default values
function resetFilters() {
    document.getElementById('yearFilter').selectedIndex = 1;
    document.getElementById('provinceFilter').value = '';
    document.getElementById('optionFilter').value = '';
    document.getElementById('limitFilter').value = '50';
    updateDependentFilters();
    loadAllData();
}

// Get current filter parameters as URL query string
function getFilterParams() {
    const year = document.getElementById('yearFilter').value;
    const province = document.getElementById('provinceFilter').value;
    const option = document.getElementById('optionFilter').value;
    const limit = document.getElementById('limitFilter').value;
    
    let params = new URLSearchParams();
    if (year) params.append('year', year);
    if (province) params.append('province', province);
    if (option) params.append('option', option);
    if (limit) params.append('limit', limit);
    
    return params.toString();
}

// Load all dashboard data
async function loadAllData() {
    await Promise.all([
        loadStatistics(),
        loadBestStudent(),
        loadBestPerOption(),
        loadRankings()
    ]);
}

// Load overall statistics
async function loadStatistics() {
    try {
        const params = getFilterParams();
        const response = await fetch(`/api/statistics?${params}`);
        const stats = await response.json();
        
        if (stats.error) {
            console.error('Statistics error:', stats.error);
            return;
        }
        
        document.getElementById('totalSchools').textContent = stats.total_schools || 0;
        document.getElementById('totalParticipants').textContent = (stats.total_participants || 0).toLocaleString();
        document.getElementById('totalSuccess').textContent = (stats.total_reussites || 0).toLocaleString();
        document.getElementById('schoolSuccessRate').textContent = (stats.avg_success_rate || 0) + '%';
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Load best student overall
async function loadBestStudent() {
    const loading = document.getElementById('bestStudentLoading');
    const content = document.getElementById('bestStudentContent');
    
    loading.style.display = 'block';
    content.style.display = 'none';
    
    try {
        const params = getFilterParams();
        const response = await fetch(`/api/best-student?${params}`);
        const student = await response.json();
        
        if (student.error) {
            loading.textContent = 'Error loading data';
            return;
        }
        
        if (student && student.student_name) {
            document.getElementById('bestStudentName').textContent = student.student_name;
            document.getElementById('bestStudentSchool').textContent = student.school_name;
            document.getElementById('bestStudentOption').textContent = student.school_option;
            document.getElementById('bestStudentProvince').textContent = student.province;
            document.getElementById('bestStudentScore').textContent = student.pourcentage + '%';
            document.getElementById('studentSuccessRate').textContent = student.pourcentage + '%';
            
            loading.style.display = 'none';
            content.style.display = 'block';
        } else {
            loading.textContent = 'No data available';
        }
    } catch (error) {
        console.error('Error loading best student:', error);
        loading.textContent = 'Error loading data';
    }
}

// Load best students per option
async function loadBestPerOption() {
    const loading = document.getElementById('bestPerOptionLoading');
    const content = document.getElementById('bestPerOptionContent');
    const list = document.getElementById('bestPerOptionList');
    
    loading.style.display = 'block';
    content.style.display = 'none';
    
    try {
        const params = getFilterParams();
        const response = await fetch(`/api/best-per-option?${params}`);
        const students = await response.json();
        
        if (students.error) {
            loading.textContent = 'Error loading data';
            return;
        }
        
        list.innerHTML = '';
        
        if (students && students.length > 0) {
            students.forEach(student => {
                const div = document.createElement('div');
                div.className = 'option-student';
                div.innerHTML = `
                    <div class="option-header">
                        <strong>${student.school_option}</strong>
                        <span class="score-badge">${student.pourcentage}%</span>
                    </div>
                    <p class="student-name">${student.student_name}</p>
                    <p class="school-info">${student.school_name} - ${student.province}</p>
                `;
                list.appendChild(div);
            });
            
            loading.style.display = 'none';
            content.style.display = 'block';
        } else {
            loading.textContent = 'No data available';
        }
    } catch (error) {
        console.error('Error loading best per option:', error);
        loading.textContent = 'Error loading data';
    }
}

// Load school rankings table
async function loadRankings() {
    const loading = document.getElementById('rankingsLoading');
    const container = document.getElementById('rankingsContainer');
    const tbody = document.getElementById('rankingsBody');
    
    loading.style.display = 'block';
    container.style.display = 'none';
    
    try {
        const params = getFilterParams();
        const response = await fetch(`/api/rankings?${params}`);
        const schools = await response.json();
        
        if (schools.error) {
            loading.textContent = 'Error loading data';
            return;
        }
        
        tbody.innerHTML = '';
        
        schools.forEach(school => {
            const row = document.createElement('tr');
            const rankClass = school.rank <= 3 ? 'top-rank' : '';
            
            row.innerHTML = `
                <td class="rank-cell ${rankClass}">
                    ${school.rank <= 3 ? getMedal(school.rank) : school.rank}
                </td>
                <td class="school-name">
                    <a href="/school/${encodeURIComponent(school.school_name)}" class="school-link">
                        ${school.school_name}
                    </a>
                </td>
                <td>${school.province}</td>
                <td>${school.school_option}</td>
                <td class="text-center">${school.total_participants || 0}</td>
                <td class="text-center">${school.total_reussites || 0}</td>
                <td>
                    <div class="progress-bar-small">
                        <div class="progress-fill" style="width: ${school.success_rate}%"></div>
                        <span class="progress-text">${school.success_rate}%</span>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        loading.style.display = 'none';
        container.style.display = 'block';
    } catch (error) {
        console.error('Error loading rankings:', error);
        loading.textContent = 'Error loading data';
    }
}

// Helper function to get medal emoji for top 3 ranks
function getMedal(rank) {
    const medals = { 1: '🥇', 2: '🥈', 3: '🥉' };
    return medals[rank] || rank;
}