/**
 * CodeVI API Client
 * Centralized API configuration and helper functions
 */

const API_BASE = '/api/v1';

export interface SearchResult {
  id: string;
  file_path: string;
  code?: string;
  content?: string;
  start_line?: number;
  line_number?: number;
  score?: number;
  relevance?: number;
  snippet?: string;
  type?: string;
  name?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: "frontend" | "backend" | "component" | "api" | "file";
  file_path?: string;
  metadata?: Record<string, any>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type?: string;
  label?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

/**
 * Perform a search query
 */
export async function search(query: string, maxResults: number = 20): Promise<SearchResult[]> {
  const response = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      max_results: maxResults,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();
  return data.results || data;
}

/**
 * Get graph data for a query
 */
export async function getFlowGraph(query: string): Promise<GraphData> {
  const response = await fetch(`${API_BASE}/flow_graph?query=${encodeURIComponent(query)}`);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Get general graph data
 */
export async function getGraph(): Promise<GraphData> {
  const response = await fetch(`${API_BASE}/graph`);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Scan/index the codebase
 */
export async function scanCodebase(rootPath: string): Promise<{ count: number; message: string }> {
  const response = await fetch(`${API_BASE}/scan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      root_path: rootPath,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Get file content
 */
export async function getFileContent(filePath: string): Promise<string> {
  const response = await fetch(`${API_BASE}/file?path=${encodeURIComponent(filePath)}`);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();
  return data.content || data.code || '';
}

