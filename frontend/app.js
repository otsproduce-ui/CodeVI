/**
 * CodeVI Frontend - Ask Page
 * Calm command center interface
 */

const API_BASE = '/api/v1';
const STORAGE_KEY_RECENT = 'codevi_recent_queries';
const MAX_RECENT_QUERIES = 5;

// DOM elements
const searchForm = document.getElementById('search-form');
const queryInput = document.getElementById('query-input');
const searchBtn = document.getElementById('search-btn');
const scanForm = document.getElementById('scan-form');
const rootPathInput = document.getElementById('root-path-input');
const scanBtn = document.getElementById('scan-btn');
const statusBanner = document.getElementById('status-banner');
const statusContent = document.getElementById('status-content');
const promptChips = document.querySelectorAll('.prompt-chip');
const recentSection = document.getElementById('recent-section');
const recentList = document.getElementById('recent-list');

// Initialize
checkHealth();
loadRecentQueries();

// Search form handler
searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    
    if (!query) {
        showStatus('Please enter a search query', 'error');
        return;
    }
    
    // Save to recent queries
    saveRecentQuery(query);
    
    // Navigate to results page with query
    const params = new URLSearchParams({ q: query });
    window.location.href = `results.html?${params.toString()}`;
});

// Prompt chip handlers
promptChips.forEach(chip => {
    chip.addEventListener('click', () => {
        const query = chip.getAttribute('data-query');
        queryInput.value = query;
        queryInput.focus();
        
        // Trigger search after a brief moment for visual feedback
        setTimeout(() => {
            searchForm.dispatchEvent(new Event('submit'));
        }, 100);
    });
});

// Scan form handler
scanForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const rootPath = rootPathInput.value.trim() || '.';
    
    setButtonLoading(scanBtn, true);
    showStatus('Scanning codebase...', 'info');
    
    try {
        const response = await fetch(`${API_BASE}/scan`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ root_path: rootPath }),
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        showStatus(
            `Found ${data.files_indexed} files indexed`,
            'success'
        );
    } catch (error) {
        console.error('Scan error:', error);
        const errorMsg = error.message.includes('Failed to fetch') || error.message.includes('NetworkError')
            ? 'Cannot connect to backend. Is the server running on http://localhost:8000?'
            : `Error: ${error.message}`;
        showStatus(errorMsg, 'error');
    } finally {
        setButtonLoading(scanBtn, false);
        checkHealth();
    }
});

// Health check
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.indexed) {
            showStatus(
                `Ready — ${data.file_count} files indexed`,
                'success'
            );
        } else {
            // Don't show warning on initial load, only if user tries to search
        }
    } catch (error) {
        console.error('Health check failed:', error);
        const errorMsg = error.message.includes('Failed to fetch') || error.message.includes('NetworkError')
            ? 'Cannot connect to backend. Is the server running on http://localhost:8000?'
            : `Backend error: ${error.message}`;
        showStatus(errorMsg, 'error');
    }
}

// Recent queries management
function loadRecentQueries() {
    const recent = getRecentQueries();
    
    if (recent.length === 0) {
        recentSection.style.display = 'none';
        return;
    }
    
    recentSection.style.display = 'block';
    recentList.innerHTML = '';
    
    recent.forEach(query => {
        const item = document.createElement('button');
        item.className = 'recent-item';
        item.textContent = query;
        item.addEventListener('click', () => {
            queryInput.value = query;
            queryInput.focus();
            searchForm.dispatchEvent(new Event('submit'));
        });
        recentList.appendChild(item);
    });
}

function saveRecentQuery(query) {
    let recent = getRecentQueries();
    
    // Remove if already exists
    recent = recent.filter(q => q !== query);
    
    // Add to beginning
    recent.unshift(query);
    
    // Keep only max items
    recent = recent.slice(0, MAX_RECENT_QUERIES);
    
    // Save to localStorage
    try {
        localStorage.setItem(STORAGE_KEY_RECENT, JSON.stringify(recent));
    } catch (e) {
        // localStorage not available, ignore
    }
    
    loadRecentQueries();
}

function getRecentQueries() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY_RECENT);
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        return [];
    }
}

// Status banner
function showStatus(message, type = 'info') {
    statusBanner.style.display = 'block';
    statusContent.textContent = message;
    statusContent.className = `status-content ${type}`;
    
    // Auto-hide success messages after 4 seconds
    if (type === 'success') {
        setTimeout(() => {
            if (statusContent.textContent === message) {
                statusBanner.style.display = 'none';
            }
        }, 4000);
    }
}

// Button loading state
function setButtonLoading(button, loading) {
    const text = button.querySelector('.button-text');
    const loader = button.querySelector('.button-loader');
    
    if (loading) {
        if (text) text.style.display = 'none';
        if (loader) loader.style.display = 'inline-flex';
        button.disabled = true;
    } else {
        if (text) text.style.display = 'inline';
        if (loader) loader.style.display = 'none';
        button.disabled = false;
    }
}

// Focus input on load
queryInput.focus();
