import { Link } from "react-router-dom";
import { ArrowLeft, Maximize2, ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GraphVisualization } from "@/components/GraphVisualization";

export default function Graph() {
  return (
    <div className="min-h-screen bg-background">
      {/* Background effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-primary/3 rounded-full blur-3xl" />
      </div>

      <main className="relative z-10 h-screen flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 md:p-6 border-b border-border/50 bg-background/80 backdrop-blur-xl">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/" className="gap-2">
                <ArrowLeft className="h-4 w-4" />
                <span className="hidden sm:inline">Back</span>
              </Link>
            </Button>
            <div>
              <h1 className="text-xl font-semibold text-foreground">Component Graph</h1>
              <p className="text-sm text-muted-foreground hidden sm:block">
                Visualize code relationships and dependencies
              </p>
            </div>
          </div>

          {/* Graph controls */}
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" className="hidden sm:flex">
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" className="hidden sm:flex">
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" className="hidden sm:flex">
              <RotateCcw className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon">
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Graph container */}
        <div className="flex-1 relative">
          <GraphVisualization className="absolute inset-0" />

          {/* Info panel */}
          <div className="absolute bottom-6 left-6 right-6 md:right-auto md:w-80">
            <div className="glass-card rounded-2xl p-4 opacity-0 animate-fade-in" style={{ animationDelay: "0.5s" }}>
              <h3 className="font-medium text-foreground mb-2">Graph Legend</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Click on nodes to explore file relationships and trace dependencies through your codebase.
              </p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-primary" />
                  <span className="text-muted-foreground">Frontend</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-emerald-500" />
                  <span className="text-muted-foreground">Backend</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "hsl(280, 84%, 67%)" }} />
                  <span className="text-muted-foreground">Component</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-yellow-500" />
                  <span className="text-muted-foreground">API</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
