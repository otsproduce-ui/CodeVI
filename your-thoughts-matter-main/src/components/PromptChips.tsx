import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface PromptChipsProps {
  onSelect: (query: string) => void;
  className?: string;
}

const prompts = [
  "Where is authentication handled?",
  "Show me the API error handling",
  "How does the routing work?",
  "Find database queries",
];

export function PromptChips({ onSelect, className }: PromptChipsProps) {
  return (
    <div className={cn("flex flex-wrap justify-center gap-3", className)}>
      {prompts.map((prompt, index) => (
        <Button
          key={prompt}
          variant="chip"
          onClick={() => onSelect(prompt)}
          className="text-sm opacity-0 animate-fade-in"
          style={{ animationDelay: `${0.1 + index * 0.1}s` }}
        >
          {prompt}
        </Button>
      ))}
    </div>
  );
}
