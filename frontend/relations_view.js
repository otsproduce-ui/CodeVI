/**
 * CodeVI - Smart Related Files View
 */
const GRAPH_API_BASE = '/api/v1';

async function loadRelatedFiles(fileId) {
    const container = document.getElementById('relations-container');
    if (!container) {
        console.error('Relations container not found');
        return;
    }

    // Show relations view
    const relationsView = document.getElementById('relations-view');
    const resultsView = document.getElementById('results-view');
    if (relationsView && resultsView) {
        resultsView.classList.remove('active');
        relationsView.classList.add('active');
    }

    container.innerHTML = '<div class="loading">Loading related files...</div>';

    try {
        const res = await fetch(`${GRAPH_API_BASE}/graph`);
        
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        const data = await res.json();

        if (!data.nodes || !data.links) {
            container.innerHTML = '<div class="empty-state"><h3>No graph data available</h3><p>Scan your codebase first to generate the graph.</p></div>';
            return;
        }

        // מצא את כל הקשרים של הקובץ הזה
        const related = data.links
            .filter(link => link.source === fileId || link.target === fileId)
            .map(link => (link.source === fileId ? link.target : link.source));

        // הסר כפילויות
        const uniqueRelated = [...new Set(related)];

        if (uniqueRelated.length === 0) {
            container.innerHTML = `<div class="empty-state"><h3>No related files for <span class="highlight">${escapeHtml(fileId)}</span></h3><p>This file has no connections in the codebase.</p></div>`;
            return;
        }

        // צור רשימה של קבצים קשורים
        container.innerHTML = `
            <div class="relations-header">
                <h3>Files related to <span class="highlight">${escapeHtml(fileId)}</span></h3>
                <p class="relations-count">${uniqueRelated.length} file${uniqueRelated.length !== 1 ? 's' : ''} found</p>
            </div>
            <ul class="related-files">
                ${uniqueRelated.map(id => `
                    <li class="related-item" data-file="${escapeHtml(id)}">
                        <span class="file-name">${escapeHtml(id)}</span>
                        <button class="view-file-btn" onclick="showFileContent('${escapeHtml(id)}')">View</button>
                    </li>
                `).join('')}
            </ul>
        `;

        // הוספת אירועים לפתיחת קובץ
        document.querySelectorAll('.related-item').forEach(el => {
            el.addEventListener('click', (e) => {
                if (e.target.classList.contains('view-file-btn')) {
                    return; // הכפתור מטפל בזה
                }
                showFileContent(el.dataset.file);
            });
        });

    } catch (err) {
        console.error('Error loading related files:', err);
        container.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${escapeHtml(err.message)}</p></div>`;
    }
}

async function showFileContent(fileId) {
    const container = document.getElementById('relations-container');
    if (!container) {
        console.error('Relations container not found');
        return;
    }

    container.innerHTML = '<div class="loading">Loading file content...</div>';

    try {
        const res = await fetch(`${GRAPH_API_BASE}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                query: fileId.split('/').pop(), 
                max_results: 1 
            }),
        });

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        const data = await res.json();
        
        if (!data.results || !data.results[0]) {
            container.innerHTML = `<div class="empty-state"><h3>No content for <span class="highlight">${escapeHtml(fileId)}</span></h3><p>The file was found but no content is available.</p></div>`;
            return;
        }

        const result = data.results[0];
        const code = result.content;
        
        // Format snippet with syntax highlighting
        const snippetLines = code.split('\n');
        const formattedSnippet = snippetLines.map(line => {
            if (line.startsWith('>')) {
                return `<div class="highlight-line">${escapeHtml(line)}</div>`;
            }
            return escapeHtml(line);
        }).join('\n');

        container.innerHTML = `
            <div class="file-view">
                <div class="file-header">
                    <div>
                        <h3>${escapeHtml(fileId)}</h3>
                        <div class="file-meta">Line ${result.line_number} • Score: ${result.score.toFixed(2)}</div>
                    </div>
                    <button class="related-btn" onclick="loadRelatedFiles('${escapeHtml(fileId)}')">Show Related Files</button>
                </div>
                <pre class="code-block">${formattedSnippet}</pre>
            </div>
        `;
    } catch (err) {
        console.error('Error loading file:', err);
        container.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${escapeHtml(err.message)}</p></div>`;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showResultsView() {
    const relationsView = document.getElementById('relations-view');
    const resultsView = document.getElementById('results-view');
    if (relationsView && resultsView) {
        relationsView.classList.remove('active');
        resultsView.classList.add('active');
    }
}

// Expose functions to window for onclick handlers
window.loadRelatedFiles = loadRelatedFiles;
window.showFileContent = showFileContent;
window.showResultsView = showResultsView;

