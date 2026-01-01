import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, GitGraph, FileSearch, Zap, Sparkles } from "lucide-react";
import { SearchBox } from "@/components/SearchBox";
import { PromptChips } from "@/components/PromptChips";
import { FeatureCard } from "@/components/FeatureCard";
import { StatusBanner, StatusType } from "@/components/StatusBanner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function Index() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<{ type: StatusType; message: string } | null>(null);
  const [rootPath, setRootPath] = useState("");
  const [isScanning, setIsScanning] = useState(false);

  const handleSearch = (query: string) => {
    navigate(`/results?q=${encodeURIComponent(query)}`);
  };

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsScanning(true);
    setStatus({ type: "loading", message: "Scanning codebase..." });

    // Simulate scan - in real app, this would call the API
    setTimeout(() => {
      setIsScanning(false);
      setStatus({ type: "success", message: "Found 247 files indexed successfully!" });
    }, 2000);
  };

  const features = [
    {
      icon: Search,
      title: "Natural Language Search",
      description: "Ask questions about your code in plain English and get relevant results instantly.",
    },
    {
      icon: GitGraph,
      title: "Dependency Graph",
      description: "Visualize how your files connect with an interactive relationship graph.",
    },
    {
      icon: FileSearch,
      title: "Smart Related Files",
      description: "Discover connected files and understand code relationships at a glance.",
    },
    {
      icon: Zap,
      title: "Component Analysis",
      description: "Map frontend to backend connections and trace data flow through your app.",
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Background gradient effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-primary/5 rounded-full blur-3xl animate-pulse-slow" />
        <div className="absolute bottom-0 right-0 w-[600px] h-[400px] bg-primary/3 rounded-full blur-3xl" />
      </div>

      <main className="relative z-10 container px-4 md:px-8 py-12 md:py-20">
        {/* Hero Section */}
        <div className="max-w-4xl mx-auto text-center mb-16 md:mb-24">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-6 opacity-0 animate-fade-in">
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="text-sm text-primary font-medium">AI-Powered Code Intelligence</span>
          </div>

          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-foreground mb-6 opacity-0 animate-fade-in" style={{ animationDelay: "0.1s" }}>
            Ask your code{" "}
            <span className="text-gradient">anything</span>
          </h1>

          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 opacity-0 animate-fade-in" style={{ animationDelay: "0.2s" }}>
            Navigate complex codebases with natural language queries. 
            Understand relationships, trace dependencies, and find what you need in seconds.
          </p>

          {/* Search Box */}
          <div className="max-w-2xl mx-auto mb-6 opacity-0 animate-fade-in" style={{ animationDelay: "0.3s" }}>
            <SearchBox onSearch={handleSearch} />
          </div>

          {/* Prompt Chips */}
          <PromptChips onSelect={handleSearch} className="mb-8" />

          {/* Status Banner */}
          {status && (
            <div className="max-w-md mx-auto mb-8">
              <StatusBanner type={status.type} message={status.message} />
            </div>
          )}
        </div>

        {/* Scan Section */}
        <div className="max-w-md mx-auto mb-20 opacity-0 animate-fade-in-up" style={{ animationDelay: "0.5s" }}>
          <div className="glass-card rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-foreground mb-4">Index Your Codebase</h3>
            <form onSubmit={handleScan} className="space-y-4">
              <Input
                value={rootPath}
                onChange={(e) => setRootPath(e.target.value)}
                placeholder="Enter path (e.g., ./my-project)"
              />
              <Button type="submit" variant="glow" className="w-full" disabled={isScanning}>
                {isScanning ? "Scanning..." : "Scan Codebase"}
              </Button>
            </form>
          </div>
        </div>

        {/* Features Grid */}
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center text-foreground mb-12 opacity-0 animate-fade-in" style={{ animationDelay: "0.6s" }}>
            Powerful Code Intelligence
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {features.map((feature, index) => (
              <FeatureCard
                key={feature.title}
                {...feature}
                delay={0.7 + index * 0.1}
              />
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-border/50 py-8">
        <div className="container px-4 md:px-8 text-center">
          <p className="text-sm text-muted-foreground">
            CodeVI — Your codebase, understood.
          </p>
        </div>
      </footer>
    </div>
  );
}
