import { Link, useLocation } from "react-router-dom";
import { Code2, GitGraph, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function Header() {
  const location = useLocation();

  const navItems = [
    { path: "/", label: "Ask", icon: Search },
    { path: "/graph", label: "Graph", icon: GitGraph },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/50 bg-background/80 backdrop-blur-xl">
      <div className="container flex h-16 items-center justify-between px-4 md:px-8">
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
            <Code2 className="h-5 w-5 text-primary" />
          </div>
          <span className="text-xl font-semibold text-foreground">
            Code<span className="text-gradient">VI</span>
          </span>
        </Link>

        <nav className="flex items-center gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <Button
                key={item.path}
                variant="ghost"
                size="sm"
                asChild
                className={cn(
                  "gap-2",
                  isActive && "bg-secondary text-foreground"
                )}
              >
                <Link to={item.path}>
                  <Icon className="h-4 w-4" />
                  <span className="hidden sm:inline">{item.label}</span>
                </Link>
              </Button>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
