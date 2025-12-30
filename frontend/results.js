/**
 * CodeVI Frontend - Results Page
 */

const API_BASE = '/api/v1';

// Get query from URL
const urlParams = new URLSearchParams(window.location.search);
const query = urlParams.get('q') || '';

// DOM elements
const queryDisplay = document.getElementById('query-display');
const resultsContainer = document.getElementById('results-container');
const loading = document.getElementById('loading');

// Display query
queryDisplay.textContent = query || 'No query provided';

// Perform search
if (query) {
    performSearch(query);
} else {
    showError('No search query provided');
}

async function performSearch(query) {
    loading.style.display = 'block';
    resultsContainer.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                max_results: 20
            }),
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        displayResults(data.results, data.total_matches);
    } catch (error) {
        console.error('Search error:', error);
        const errorMsg = error.message.includes('Failed to fetch') || error.message.includes('NetworkError')
            ? 'Cannot connect to backend. Is the server running on http://localhost:8000?'
            : `Error: ${error.message}`;
        showError(errorMsg);
    } finally {
        loading.style.display = 'none';
    }
}

function displayResults(results, totalMatches) {
    if (results.length === 0) {
        resultsContainer.innerHTML = `
            <div class="empty-state">
                <h3>No results found</h3>
                <p>Try rephrasing your query or scanning your codebase first.</p>
            </div>
        `;
        return;
    }
    
    resultsContainer.innerHTML = results.map(result => {
        // Format snippet with syntax highlighting for the highlighted line
        const snippetLines = result.content.split('\n');
        const formattedSnippet = snippetLines.map(line => {
            if (line.startsWith('>')) {
                return `<div class="highlight-line">${escapeHtml(line)}</div>`;
            }
            return escapeHtml(line);
        }).join('\n');
        
        return `
            <div class="result-item">
                <div class="result-header">
                    <div>
                        <div class="result-file">${escapeHtml(result.file_path)}</div>
                        <div class="result-line">Line ${result.line_number}</div>
                    </div>
                    <div class="result-actions">
                        <div class="result-score">Score: ${result.score.toFixed(2)}</div>
                        <button class="related-btn" onclick="loadRelatedFiles('${escapeHtml(result.file_path)}')">Show Related Files</button>
                    </div>
                </div>
                <div class="result-snippet">${formattedSnippet}</div>
            </div>
        `;
    }).join('');
}

function showError(message) {
    resultsContainer.innerHTML = `
        <div class="empty-state">
            <h3>Error</h3>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Expose loadRelatedFiles to window (will be available from relations_view.js)
// This allows the button onclick to work

