/**
 * CodeVI - Graph Visualization with Cytoscape.js
 */

const GRAPH_API_BASE = '/api/v1';

let cy = null;
let graphData = null;

// Expose to window for global access
window.cy = null;

/**
 * Initialize the graph visualization
 */
async function initGraph() {
    const container = document.getElementById('graph-container');
    if (!container) {
        console.error('Graph container not found');
        return;
    }

    // Check if Cytoscape is loaded
    if (typeof cytoscape === 'undefined') {
        container.innerHTML = '<div class="empty-state"><h3>Error: Cytoscape.js not loaded</h3><p>Please refresh the page or check your internet connection.</p></div>';
        console.error('Cytoscape.js library not loaded');
        return;
    }

    // Show loading state
    container.innerHTML = '<div class="loading">Loading graph...</div>';

    try {
        console.log(`Fetching graph from: ${GRAPH_API_BASE}/graph`);
        
        // Fetch graph data from API
        const response = await fetch(`${GRAPH_API_BASE}/graph`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMsg = errorData.error || errorData.detail || `HTTP ${response.status}: ${response.statusText}`;
            throw new Error(errorMsg);
        }

        graphData = await response.json();
        console.log('Graph data received:', { nodes: graphData.nodes?.length || 0, links: graphData.links?.length || 0 });
        
        if (!graphData.nodes || graphData.nodes.length === 0) {
            container.innerHTML = '<div class="empty-state"><h3>No graph data available</h3><p>Scan your codebase first to generate the graph. Go to the Ask page and click "Scan Codebase".</p></div>';
            return;
        }

        // Build elements
        const elements = buildCytoscapeElements(graphData);
        console.log('Building graph with', graphData.nodes.length + graphData.links.length, 'elements');
        
        if (elements.length === 0) {
            container.innerHTML = '<div class="empty-state"><h3>No graph elements</h3><p>Graph data received but no valid nodes or links found.</p></div>';
            return;
        }

        // Fallback layout: use cose if bilkent isn't available
        let layoutName = 'cose-bilkent';
        if (!cytoscape.layouts || !cytoscape.layouts['cose-bilkent']) {
            console.warn('⚠️ cose-bilkent not available, falling back to regular "cose" layout');
            layoutName = 'cose';
        }

        // Initialize Cytoscape
        cy = window.cy = cytoscape({
            container: container,
            elements: elements,
            style: getGraphStyle(),
            layout: { 
                name: layoutName, 
                animate: true, 
                padding: 30 
            },
            minZoom: 0.1,
            maxZoom: 4
        });

        // Add event handlers
        setupGraphEvents(cy);
        
        console.log('Graph initialized successfully');

    } catch (error) {
        console.error('Graph initialization error:', error);
        const errorMsg = error.message.includes('Failed to fetch') || error.message.includes('NetworkError')
            ? 'Cannot connect to backend. Is the server running on http://localhost:8000?'
            : error.message.includes('not indexed') || error.message.includes('Call /scan')
            ? 'Codebase not indexed. Please scan your codebase first from the Ask page.'
            : error.message;
        container.innerHTML = `<div class="empty-state"><h3>Error loading graph</h3><p>${escapeHtml(errorMsg)}</p></div>`;
    }
}

/**
 * Build Cytoscape elements from graph data
 */
function buildCytoscapeElements(data) {
    const elements = [];
    
    // Add nodes
    data.nodes.forEach(node => {
        elements.push({
            data: {
                id: node.id,
                label: node.label || node.id.split('/').pop(),
                type: node.type,
                color: node.color || '#6b7280',
                filePath: node.id
            }
        });
    });
    
    // Add edges
    data.links.forEach(link => {
        // Only add edge if both source and target nodes exist
        const sourceExists = data.nodes.some(n => n.id === link.source);
        const targetExists = data.nodes.some(n => n.id === link.target);
        
        if (sourceExists && targetExists) {
            elements.push({
                data: {
                    id: `${link.source}-${link.target}`,
                    source: link.source,
                    target: link.target,
                    type: link.type || 'import'
                }
            });
        }
    });
    
    return elements;
}

/**
 * Get Cytoscape style configuration
 */
function getGraphStyle() {
    return [
        {
            selector: 'node',
            style: {
                'label': 'data(label)',
                'width': 30,
                'height': 30,
                'shape': 'ellipse',
                'background-color': 'data(color)',
                'border-width': 2,
                'border-color': '#1F6FEB',
                'text-valign': 'center',
                'text-halign': 'center',
                'text-outline-width': 2,
                'text-outline-color': '#0D1117',
                'text-outline-opacity': 0.8,
                'font-size': '10px',
                'font-weight': '500',
                'color': '#E6EDF3',
                'overlay-padding': '4px'
            }
        },
        {
            selector: 'node:selected',
            style: {
                'border-width': 4,
                'border-color': '#1F6FEB',
                'width': 40,
                'height': 40,
                'font-size': '12px'
            }
        },
        {
            selector: 'edge',
            style: {
                'width': 2,
                'line-color': '#7D8590',
                'target-arrow-color': '#7D8590',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'opacity': 0.6
            }
        },
        {
            selector: 'edge:selected',
            style: {
                'width': 3,
                'line-color': '#1F6FEB',
                'target-arrow-color': '#1F6FEB',
                'opacity': 1
            }
        },
        {
            selector: '.highlighted',
            style: {
                'background-color': '#1F6FEB',
                'border-color': '#3884F0',
                'border-width': 3,
                'opacity': 1
            }
        },
        {
            selector: '.neighbor',
            style: {
                'opacity': 0.8
            }
        },
        {
            selector: '.hidden',
            style: {
                'opacity': 0.1
            }
        }
    ];
}

/**
 * Setup graph event handlers
 */
function setupGraphEvents(cy) {
    // Click to focus on node
    cy.on('tap', 'node', function(evt) {
        const node = evt.target;
        const nodeId = node.id();
        
        // Reset all nodes
        cy.nodes().removeClass('highlighted neighbor hidden');
        cy.edges().removeClass('highlighted hidden');
        
        // Highlight clicked node
        node.addClass('highlighted');
        
        // Highlight neighbors
        const neighbors = node.neighborhood();
        neighbors.nodes().addClass('neighbor');
        neighbors.edges().addClass('highlighted');
        
        // Dim non-neighbors
        const allNodes = cy.nodes();
        const nonNeighbors = allNodes.difference(node).difference(neighbors.nodes());
        nonNeighbors.addClass('hidden');
        
        // Dim edges not connected to highlighted nodes
        const allEdges = cy.edges();
        const nonHighlightedEdges = allEdges.difference(neighbors.edges());
        nonHighlightedEdges.addClass('hidden');
        
        // Center on clicked node
        cy.center(node);
        cy.zoom({
            level: 1.5,
            position: node.position()
        });
        
        // Display file content in results view
        displayFileInResults(nodeId);
    });
    
    // Reset on background click
    cy.on('tap', function(evt) {
        if (evt.target === cy) {
            cy.nodes().removeClass('highlighted neighbor hidden');
            cy.edges().removeClass('highlighted hidden');
            cy.fit();
        }
    });
    
    // Hover effects
    cy.on('mouseover', 'node', function(evt) {
        const node = evt.target;
        if (!node.hasClass('highlighted')) {
            node.style('border-width', 3);
        }
    });
    
    cy.on('mouseout', 'node', function(evt) {
        const node = evt.target;
        if (!node.hasClass('highlighted')) {
            node.style('border-width', 2);
        }
    });
}

/**
 * Display file content in results view when node is clicked
 */
async function displayFileInResults(filePath) {
    const resultsContainer = document.getElementById('results-container');
    if (!resultsContainer) {
        return;
    }
    
    // Show loading
    resultsContainer.innerHTML = '<div class="loading">Loading file...</div>';
    
    try {
        // Search for the file to get its content
        const response = await fetch(`${GRAPH_API_BASE}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: filePath.split('/').pop(), // Use filename as query
                max_results: 1
            }),
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.results && data.results.length > 0) {
                const result = data.results[0];
                resultsContainer.innerHTML = `
                    <div class="result-item">
                        <div class="result-header">
                            <div>
                                <div class="result-file">${escapeHtml(result.file_path)}</div>
                                <div class="result-line">Line ${result.line_number}</div>
                            </div>
                        </div>
                        <div class="result-snippet">${formatSnippet(result.content)}</div>
                    </div>
                `;
            } else {
                resultsContainer.innerHTML = `
                    <div class="empty-state">
                        <h3>File: ${escapeHtml(filePath)}</h3>
                        <p>No content preview available.</p>
                    </div>
                `;
            }
        } else {
            resultsContainer.innerHTML = `
                <div class="empty-state">
                    <h3>File: ${escapeHtml(filePath)}</h3>
                    <p>Could not load file content.</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading file:', error);
        resultsContainer.innerHTML = `
            <div class="empty-state">
                <h3>Error</h3>
                <p>${escapeHtml(error.message)}</p>
            </div>
        `;
    }
}

/**
 * Format code snippet for display
 */
function formatSnippet(content) {
    const lines = content.split('\n');
    return lines.map(line => {
        if (line.startsWith('>')) {
            return `<div class="highlight-line">${escapeHtml(line)}</div>`;
        }
        return escapeHtml(line);
    }).join('\n');
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize graph when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGraph);
} else {
    initGraph();
}

