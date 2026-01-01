import { useState } from "react";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SearchBoxProps {
  onSearch: (query: string) => void;
  placeholder?: string;
  className?: string;
}

export function SearchBox({ onSearch, placeholder = "Where's the login button handled?", className }: SearchBoxProps) {
  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className={cn("w-full", className)}>
      <div
        className={cn(
          "relative flex items-center w-full rounded-2xl border bg-card/50 backdrop-blur-sm transition-all duration-300",
          isFocused
            ? "border-primary/50 shadow-glow ring-2 ring-primary/10"
            : "border-border/50 hover:border-border"
        )}
      >
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={placeholder}
          className="flex-1 h-14 md:h-16 px-6 bg-transparent text-foreground text-base md:text-lg placeholder:text-muted-foreground focus:outline-none"
        />
        <Button
          type="submit"
          variant="glow"
          size="icon"
          className="absolute right-3 h-10 w-10 rounded-xl"
        >
          <Search className="h-5 w-5" />
        </Button>
      </div>
    </form>
  );
}
