import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";

interface GraphNode {
  id: string;
  label: string;
  type: "frontend" | "backend" | "component" | "api";
  code: string;
}

interface GraphLink {
  source: string;
  target: string;
}

interface GraphVisualizationProps {
  className?: string;
}

// Mock data with code snippets
const mockNodes: GraphNode[] = [
  { 
    id: "1", 
    label: "App.tsx", 
    type: "frontend",
    code: `import { AuthProvider } from './AuthProvider'
import { Dashboard } from './Dashboard'

export function App() {
  return (
    <AuthProvider>
      <Dashboard />
    </AuthProvider>
  )
}`
  },
  { 
    id: "2", 
    label: "AuthProvider", 
    type: "component",
    code: `export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  
  return (
    <AuthContext.Provider value={{ user }}>
      {children}
    </AuthContext.Provider>
  )
}`
  },
  { 
    id: "3", 
    label: "api/auth", 
    type: "api",
    code: `export async function login(email, password) {
  const response = await fetch('/api/auth', {
    method: 'POST',
    body: JSON.stringify({ email, password })
  })
  return response.json()
}`
  },
  { 
    id: "4", 
    label: "UserService", 
    type: "backend",
    code: `class UserService {
  async authenticate(credentials) {
    const user = await db.users.findOne({
      email: credentials.email
    })
    return this.verifyPassword(user, credentials)
  }
}`
  },
  { 
    id: "5", 
    label: "Dashboard", 
    type: "frontend",
    code: `export function Dashboard() {
  const { user } = useAuth()
  
  return (
    <div className="dashboard">
      <h1>Welcome, {user.name}</h1>
      <Stats />
    </div>
  )
}`
  },
  { 
    id: "6", 
    label: "useAuth", 
    type: "component",
    code: `export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}`
  },
];

const mockLinks: GraphLink[] = [
  { source: "1", target: "2" },
  { source: "2", target: "3" },
  { source: "3", target: "4" },
  { source: "1", target: "5" },
  { source: "5", target: "6" },
  { source: "6", target: "2" },
];

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

export function GraphVisualization({ className }: GraphVisualizationProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [expandedNode, setExpandedNode] = useState<string | null>(null);
  const [nodePositions, setNodePositions] = useState<{ [key: string]: { x: number; y: number } }>({});

  useEffect(() => {
    const updatePositions = () => {
      const container = containerRef.current;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const radius = Math.min(centerX, centerY) * 0.55;

      const positions: { [key: string]: { x: number; y: number } } = {};
      mockNodes.forEach((node, i) => {
        const angle = (i / mockNodes.length) * Math.PI * 2 - Math.PI / 2;
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
  }, []);

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
          {mockLinks.map((link, i) => {
            const sourceNode = mockNodes.find(n => n.id === link.source);
            const targetNode = mockNodes.find(n => n.id === link.target);
            if (!sourceNode || !targetNode) return null;
            return (
              <linearGradient 
                key={`gradient-${i}`} 
                id={`link-gradient-${i}`}
                x1="0%" y1="0%" x2="100%" y2="0%"
              >
                <stop offset="0%" stopColor={nodeColors[sourceNode.type].line} stopOpacity="0.4" />
                <stop offset="100%" stopColor={nodeColors[targetNode.type].line} stopOpacity="0.4" />
              </linearGradient>
            );
          })}
        </defs>
        
        {mockLinks.map((link, i) => {
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
      {mockNodes.map((node) => {
        const pos = nodePositions[node.id];
        if (!pos) return null;

        const isExpanded = expandedNode === node.id;
        const colors = nodeColors[node.type];

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
                {node.label}
              </span>
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted/30">
                {node.type}
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
              <pre className="text-foreground/90 whitespace-pre-wrap font-medium">
                <code className="text-foreground/90">{getCodePreview(node.code, isExpanded)}</code>
              </pre>
            </div>

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