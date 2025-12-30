# Debug Guide - Trace Graph Issues

## Common Issues and Solutions

### 1. "No graph data available"
**Cause:** Codebase not scanned/indexed

**Solution:**
1. Go to Ask page (`index.html`)
2. Enter your codebase path
3. Click "Scan Codebase"
4. Wait for "Found X files indexed" message
5. Then try Trace Graph again

### 2. "Cytoscape.js not loaded"
**Cause:** CDN scripts failed to load

**Solution:**
- Check internet connection
- Open browser console (F12) and check for script loading errors
- Try refreshing the page
- Verify these scripts load:
  - `https://cdn.jsdelivr.net/npm/cytoscape@3.26.0/dist/cytoscape.min.js`
  - `https://cdn.jsdelivr.net/npm/cytoscape-cose-bilkent@4.1.0/cytoscape-cose-bilkent.min.js`

### 3. "Cannot connect to backend"
**Cause:** Backend server not running

**Solution:**
1. Start backend: `cd backend && python main.py`
2. Verify: Open `http://localhost:8000/health` in browser
3. Should return: `{"ok":true,"status":"healthy",...}`

### 4. Empty graph (no nodes visible)
**Cause:** No relationships found in codebase

**Solution:**
- Make sure your codebase has import statements (Python `import` or JS `import/require`)
- Check browser console for graph data: `console.log` shows node/link counts
- Try scanning a different codebase with more dependencies

## Debug Steps

1. **Check API_BASE in all files:**
   ```bash
   # Should be: http://localhost:8000/api/v1
   grep -r "API_BASE" frontend/
   ```

2. **Test Graph API directly:**
   ```bash
   curl http://localhost:8000/api/v1/graph
   # Should return: {"nodes": [...], "links": [...]}
   ```

3. **Check browser console:**
   - Open DevTools (F12)
   - Look for:
     - "Fetching graph from: ..."
     - "Graph data received: ..."
     - "Building graph with X elements"
     - Any error messages

4. **Verify Cytoscape:**
   - In browser console, type: `typeof cytoscape`
   - Should return: `"function"`

## API Endpoints

- `GET /api/v1/graph` - Get graph data (requires indexed codebase)
- `GET /api/graph` - Legacy endpoint (also works)
- `POST /api/v1/scan` - Scan codebase first!

