// Toggle sidebar on mobile
function toggleSidebar() {
    const sidebar = document.querySelector('.side-panel');
    const body = document.body;
    
    sidebar.classList.toggle('active');
    body.classList.toggle('sidebar-open');
}

// Toggle city dropdown
function toggleCityDropdown(event) {
    if (event) {
        event.stopPropagation();
    }
    
    const dropdown = document.getElementById('cityDropdown');
    const arrow = document.querySelector('.city-arrow');
    
    dropdown.classList.toggle('active');
    arrow.classList.toggle('active');
    
    // Add click outside listener to close dropdown
    if (dropdown.classList.contains('active')) {
        setTimeout(() => {
            document.addEventListener('click', closeCityDropdownOnClickOutside);
        }, 10);
    }
}

// Close dropdown when clicking outside
function closeCityDropdownOnClickOutside(event) {
    const dropdown = document.getElementById('cityDropdown');
    const container = document.querySelector('.city-dropdown-container');
    const arrow = document.querySelector('.city-arrow');
    
    if (!container.contains(event.target) && !dropdown.contains(event.target)) {
        dropdown.classList.remove('active');
        arrow.classList.remove('active');
        document.removeEventListener('click', closeCityDropdownOnClickOutside);
    }
}

// City selection handler
function selectCity(city, event) {
    if (event) {
        event.stopPropagation();
    }
    
    if (city) {
        // Check if we're on the optimization strategy page
        if (window.location.pathname.includes('optimization-strategy')) {
            // Get the current news_item from the URL or input field
            let newsItem = '';
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('news_item')) {
                newsItem = urlParams.get('news_item');
            } else {
                const newsItemInput = document.querySelector('input[name="news_item"]');
                if (newsItemInput) {
                    newsItem = newsItemInput.value;
                }
            }
            
            // Redirect to the optimization strategy page with the selected city and news item
            window.location.href = `/optimization-strategy/?city=${encodeURIComponent(city)}&news_item=${encodeURIComponent(newsItem)}`;
        } else {
            // Default behavior - redirect to impact assessment
            window.location.href = `/impact-assessment-new/?city=${encodeURIComponent(city)}`;
        }
    }
}

// Initialize left panel functionality
document.addEventListener('DOMContentLoaded', function() {
    // Set hidden city input value for forms
    const hiddenCityInput = document.querySelector('input[name="city"]');
    const selectedCity = document.querySelector('.city-name').textContent.trim();
    
    if (hiddenCityInput && selectedCity) {
        hiddenCityInput.value = selectedCity;
    }
    
    // Make sure dropdown is hidden initially
    const dropdown = document.getElementById('cityDropdown');
    if (dropdown) {
        dropdown.classList.remove('active');
    }
    
    // Initialize collapsible sections
    const categoryNames = document.querySelectorAll('.category-name');
    categoryNames.forEach(function(categoryName) {
        // Make all sections collapsed by default
        categoryName.classList.add('collapsed');
        const subcategoryList = categoryName.nextElementSibling;
        if (subcategoryList && subcategoryList.classList.contains('subcategory-list')) {
            subcategoryList.classList.add('collapsed');
        }
        
        categoryName.addEventListener('click', function() {
            // Toggle the collapsed class on the category name
            this.classList.toggle('collapsed');
            
            // Find the next sibling which is the subcategory list
            const subcategoryList = this.nextElementSibling;
            if (subcategoryList && subcategoryList.classList.contains('subcategory-list')) {
                subcategoryList.classList.toggle('collapsed');
            }
        });
    });
    
    // Format percentage values if needed
    const percentageElements = document.querySelectorAll('.subcategory-percentage');
    percentageElements.forEach(function(element) {
        const text = element.textContent.trim();
        // If the percentage is a decimal value (e.g., 0.45), convert to percentage
        if (text && !text.includes('%') && !isNaN(parseFloat(text))) {
            const value = parseFloat(text);
            if (value <= 1) {
                element.textContent = (value * 100).toFixed(0) + '%';
            }
        }
    });
});
