import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";
import { getFileContent } from "@/lib/api";

interface GraphNode {
  id: string;
  label: string;
  type: "frontend" | "backend" | "component" | "api" | "file" | string;
  code?: string;
  file_path?: string;
  context?: string;
  metadata?: Record<string, any>;
}

interface GraphLink {
  source: string;
  target: string;
  type?: string;
  label?: string;
}

interface GraphVisualizationProps {
  className?: string;
  nodes?: GraphNode[];
  edges?: GraphLink[];
}

// Helper function to determine node type from file path and context
function getNodeType(
  filePath: string | undefined, 
  label: string, 
  context?: string,
  nodeType?: string
): "frontend" | "backend" | "component" | "api" | "file" {
  // Use context from backend if available
  if (context === "frontend") return "frontend";
  if (context === "backend") return "backend";
  
  // Use node type from backend
  if (nodeType === "route" || nodeType === "endpoint") return "api";
  if (nodeType === "function" || nodeType === "class") {
    // Check if it's a component based on file path
    if (filePath && (filePath.includes('component') || filePath.includes('hook'))) {
      return "component";
    }
  }
  
  // Fallback to file path analysis
  if (!filePath) return "file";
  const path = filePath.toLowerCase();
  if (path.includes('.tsx') || path.includes('.jsx') || path.includes('.html') || path.includes('.js')) return "frontend";
  if (path.includes('.py') || path.includes('routes') || path.includes('api')) return "backend";
  if (path.includes('component') || path.includes('hook')) return "component";
  if (path.includes('api') || path.includes('endpoint')) return "api";
  return "file";
}

const nodeColors = {
  frontend: { 
    border: "border-indigo-500/50", 
    bg: "bg-indigo-500/10",
    glow: "shadow-indigo-500/20",
    dot: "bg-indigo-500",
    line: "#6366f1"
  },
  backend: { 
    border: "border-emerald-500/50", 
    bg: "bg-emerald-500/10",
    glow: "shadow-emerald-500/20",
    dot: "bg-emerald-500",
    line: "#10b981"
  },
  component: { 
    border: "border-violet-500/50", 
    bg: "bg-violet-500/10",
    glow: "shadow-violet-500/20",
    dot: "bg-violet-500",
    line: "#8b5cf6"
  },
  api: { 
    border: "border-amber-500/50", 
    bg: "bg-amber-500/10",
    glow: "shadow-amber-500/20",
    dot: "bg-amber-500",
    line: "#f59e0b"
  },
};

export function GraphVisualization({ className, nodes, edges }: GraphVisualizationProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [expandedNode, setExpandedNode] = useState<string | null>(null);
  const [nodePositions, setNodePositions] = useState<{ [key: string]: { x: number; y: number } }>({});
  const [nodeCodes, setNodeCodes] = useState<{ [key: string]: string }>({});
  const [loadingCodes, setLoadingCodes] = useState<Set<string>>(new Set());

  // Use provided nodes/edges or fallback to empty arrays
  const graphNodes: GraphNode[] = nodes || [];
  const graphLinks: GraphLink[] = edges || [];

  // Load code content for nodes when needed
  const loadNodeCode = async (node: GraphNode) => {
    if (nodeCodes[node.id] || loadingCodes.has(node.id)) return;
    if (!node.file_path) return;

    setLoadingCodes(prev => new Set(prev).add(node.id));
    try {
      const code = await getFileContent(node.file_path);
      setNodeCodes(prev => ({ ...prev, [node.id]: code }));
    } catch (err) {
      console.error(`Failed to load code for ${node.file_path}:`, err);
      setNodeCodes(prev => ({ ...prev, [node.id]: node.code || "Code not available" }));
    } finally {
      setLoadingCodes(prev => {
        const next = new Set(prev);
        next.delete(node.id);
        return next;
      });
    }
  };

  useEffect(() => {
    const updatePositions = () => {
      const container = containerRef.current;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const radius = Math.min(centerX, centerY) * 0.55;

      const positions: { [key: string]: { x: number; y: number } } = {};
      graphNodes.forEach((node, i) => {
        const angle = (i / graphNodes.length) * Math.PI * 2 - Math.PI / 2;
        positions[node.id] = {
          x: centerX + Math.cos(angle) * radius,
          y: centerY + Math.sin(angle) * radius,
        };
      });
      setNodePositions(positions);
    };

    updatePositions();
    window.addEventListener("resize", updatePositions);
    return () => window.removeEventListener("resize", updatePositions);
  }, [graphNodes]);

  // Load code for visible nodes
  useEffect(() => {
    graphNodes.forEach(node => {
      if (node.file_path && !nodeCodes[node.id] && !node.code) {
        loadNodeCode(node);
      }
    });
  }, [graphNodes]);

  const handleNodeClick = (nodeId: string) => {
    setExpandedNode(expandedNode === nodeId ? null : nodeId);
  };

  const getCodePreview = (code: string, expanded: boolean) => {
    const lines = code.split('\n');
    if (expanded) return code;
    return lines.slice(0, 3).join('\n') + (lines.length > 3 ? '\n...' : '');
  };

  return (
    <div ref={containerRef} className={cn("relative w-full h-full min-h-[500px] overflow-hidden", className)}>
      {/* SVG for connection lines */}
      <svg 
        ref={svgRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ zIndex: 0 }}
      >
        <defs>
          {graphLinks.map((link, i) => {
            const sourceNode = graphNodes.find(n => n.id === link.source);
            const targetNode = graphNodes.find(n => n.id === link.target);
            if (!sourceNode || !targetNode) return null;
            const sourceContext = sourceNode.context || (sourceNode.metadata?.context as string);
            const targetContext = targetNode.context || (targetNode.metadata?.context as string);
            const sourceType = getNodeType(sourceNode.file_path, sourceNode.label, sourceContext, sourceNode.type);
            const targetType = getNodeType(targetNode.file_path, targetNode.label, targetContext, targetNode.type);
            return (
              <linearGradient 
                key={`gradient-${i}`} 
                id={`link-gradient-${i}`}
                x1="0%" y1="0%" x2="100%" y2="0%"
              >
                <stop offset="0%" stopColor={nodeColors[sourceType].line} stopOpacity="0.4" />
                <stop offset="100%" stopColor={nodeColors[targetType].line} stopOpacity="0.4" />
              </linearGradient>
            );
          })}
        </defs>
        
        {graphLinks.map((link, i) => {
          const sourcePos = nodePositions[link.source];
          const targetPos = nodePositions[link.target];
          if (!sourcePos || !targetPos) return null;

          return (
            <line
              key={i}
              x1={sourcePos.x}
              y1={sourcePos.y}
              x2={targetPos.x}
              y2={targetPos.y}
              stroke={`url(#link-gradient-${i})`}
              strokeWidth="2"
              className="transition-all duration-300"
            />
          );
        })}
      </svg>

      {/* Nodes as code cards */}
      {graphNodes.map((node) => {
        const pos = nodePositions[node.id];
        if (!pos) return null;

        const isExpanded = expandedNode === node.id;
        // Use context from backend if available (can be in node.context or node.metadata.context)
        const context = node.context || (node.metadata?.context as string);
        const nodeType = getNodeType(node.file_path, node.label, context, node.type);
        const colors = nodeColors[nodeType];
        
        // Get code content - prefer loaded code, then node.code, then placeholder
        const codeContent = nodeCodes[node.id] || node.code || (node.file_path ? "Loading code..." : "No code available");
        const isLoading = loadingCodes.has(node.id) && !nodeCodes[node.id];

        return (
          <div
            key={node.id}
            onClick={() => handleNodeClick(node.id)}
            className={cn(
              "absolute cursor-pointer transition-all duration-500 ease-out",
              "rounded-xl border backdrop-blur-md",
              colors.border,
              colors.bg,
              isExpanded 
                ? "z-20 shadow-2xl" 
                : "z-10 hover:z-15 hover:scale-105 shadow-lg",
              colors.glow,
              "bg-card/95"
            )}
            style={{
              left: isExpanded ? '50%' : pos.x,
              top: isExpanded ? '50%' : pos.y,
              transform: isExpanded 
                ? 'translate(-50%, -50%)' 
                : 'translate(-50%, -50%)',
              width: isExpanded ? 'min(400px, 90vw)' : '160px',
              maxHeight: isExpanded ? '320px' : '120px',
            }}
          >
            {/* Header */}
            <div className={cn(
              "flex items-center gap-2 px-3 py-2.5 border-b border-border/40",
              "bg-background/80 rounded-t-xl backdrop-blur-sm"
            )}>
              <div className={cn("w-2.5 h-2.5 rounded-full", colors.dot)} />
              <span className="text-xs font-semibold text-foreground truncate flex-1">
                {node.label || node.file_path || node.id}
              </span>
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted/30">
                {nodeType}
              </span>
              {isExpanded && (
                <button 
                  onClick={(e) => { e.stopPropagation(); setExpandedNode(null); }}
                  className="p-0.5 hover:bg-muted/50 rounded transition-colors"
                >
                  <X className="w-3.5 h-3.5 text-muted-foreground" />
                </button>
              )}
            </div>

            {/* Code content */}
            <div className={cn(
              "p-3 font-mono text-[11px] leading-relaxed overflow-hidden relative",
              isExpanded && "overflow-y-auto max-h-[240px]"
            )}>
              {isLoading ? (
                <div className="flex items-center justify-center py-4">
                  <div className="text-xs text-muted-foreground">Loading code...</div>
                </div>
              ) : (
                <pre className="text-foreground/90 whitespace-pre-wrap font-medium">
                  <code className="text-foreground/90">{getCodePreview(codeContent, isExpanded)}</code>
                </pre>
              )}
            </div>
            
            {/* Load code on expand if not already loaded */}
            {isExpanded && node.file_path && !nodeCodes[node.id] && !node.code && !loadingCodes.has(node.id) && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/50 rounded-xl">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    loadNodeCode(node);
                  }}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm hover:bg-primary/90"
                >
                  Load Code
                </button>
              </div>
            )}

            {/* Expand hint - floating above the card */}
            {!isExpanded && (
              <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 z-30 pointer-events-none">
                <div className="px-3 py-1.5 rounded-lg bg-background/95 border border-border/50 backdrop-blur-sm shadow-lg">
                  <span className="text-[10px] font-medium text-muted-foreground whitespace-nowrap">
                    click to expand
                  </span>
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* Backdrop when expanded */}
      {expandedNode && (
        <div 
          className="absolute inset-0 bg-background/60 backdrop-blur-sm z-15 transition-opacity duration-300"
          onClick={() => setExpandedNode(null)}
        />
      )}
    </div>
  );
}