import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface GraphNode {
  id: string;
  label: string;
  type: "frontend" | "backend" | "component" | "api";
}

interface GraphLink {
  source: string;
  target: string;
}

interface GraphVisualizationProps {
  className?: string;
}

// Mock data for demonstration
const mockNodes: GraphNode[] = [
  { id: "1", label: "App.tsx", type: "frontend" },
  { id: "2", label: "AuthProvider", type: "component" },
  { id: "3", label: "api/auth", type: "api" },
  { id: "4", label: "UserService", type: "backend" },
  { id: "5", label: "Dashboard", type: "frontend" },
  { id: "6", label: "useAuth", type: "component" },
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
  frontend: "hsl(239, 84%, 67%)",
  backend: "hsl(142, 71%, 45%)",
  component: "hsl(280, 84%, 67%)",
  api: "hsl(45, 93%, 47%)",
};

export function GraphVisualization({ className }: GraphVisualizationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [animationFrame, setAnimationFrame] = useState(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resizeCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    };

    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);

    // Calculate node positions in a circle
    const centerX = canvas.width / (2 * window.devicePixelRatio);
    const centerY = canvas.height / (2 * window.devicePixelRatio);
    const radius = Math.min(centerX, centerY) * 0.6;

    const nodePositions = mockNodes.map((node, i) => {
      const angle = (i / mockNodes.length) * Math.PI * 2 - Math.PI / 2;
      return {
        ...node,
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
      };
    });

    let frame = 0;
    const animate = () => {
      frame++;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw links with animation
      ctx.lineWidth = 1.5;
      mockLinks.forEach((link) => {
        const source = nodePositions.find((n) => n.id === link.source);
        const target = nodePositions.find((n) => n.id === link.target);
        if (!source || !target) return;

        const gradient = ctx.createLinearGradient(
          source.x,
          source.y,
          target.x,
          target.y
        );
        gradient.addColorStop(0, `${nodeColors[source.type]}40`);
        gradient.addColorStop(1, `${nodeColors[target.type]}40`);

        ctx.strokeStyle = gradient;
        ctx.beginPath();
        ctx.moveTo(source.x, source.y);
        ctx.lineTo(target.x, target.y);
        ctx.stroke();

        // Animated dot along the line
        const progress = ((frame * 0.01) % 1);
        const dotX = source.x + (target.x - source.x) * progress;
        const dotY = source.y + (target.y - source.y) * progress;

        ctx.fillStyle = nodeColors[source.type];
        ctx.beginPath();
        ctx.arc(dotX, dotY, 3, 0, Math.PI * 2);
        ctx.fill();
      });

      // Draw nodes
      nodePositions.forEach((node) => {
        const isHovered = hoveredNode === node.id;
        const nodeRadius = isHovered ? 28 : 24;
        const pulseRadius = nodeRadius + Math.sin(frame * 0.05) * 3;

        // Glow effect
        const gradient = ctx.createRadialGradient(
          node.x,
          node.y,
          0,
          node.x,
          node.y,
          pulseRadius * 2
        );
        gradient.addColorStop(0, `${nodeColors[node.type]}30`);
        gradient.addColorStop(1, "transparent");
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(node.x, node.y, pulseRadius * 2, 0, Math.PI * 2);
        ctx.fill();

        // Node circle
        ctx.fillStyle = nodeColors[node.type];
        ctx.beginPath();
        ctx.arc(node.x, node.y, nodeRadius, 0, Math.PI * 2);
        ctx.fill();

        // Inner circle
        ctx.fillStyle = "hsl(225, 14%, 7%)";
        ctx.beginPath();
        ctx.arc(node.x, node.y, nodeRadius - 3, 0, Math.PI * 2);
        ctx.fill();

        // Label
        ctx.fillStyle = "#ffffff";
        ctx.font = "12px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(node.label, node.x, node.y + nodeRadius + 20);
      });

      requestAnimationFrame(animate);
    };

    const animationId = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener("resize", resizeCanvas);
      cancelAnimationFrame(animationId);
    };
  }, [hoveredNode]);

  return (
    <div className={cn("relative w-full h-full min-h-[400px]", className)}>
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ background: "transparent" }}
      />
      
      {/* Legend */}
      <div className="absolute bottom-4 left-4 flex flex-wrap gap-4 text-xs">
        {Object.entries(nodeColors).map(([type, color]) => (
          <div key={type} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-muted-foreground capitalize">{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
