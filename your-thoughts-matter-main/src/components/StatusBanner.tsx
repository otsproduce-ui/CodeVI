import { CheckCircle2, AlertCircle, Loader2, Info } from "lucide-react";
import { cn } from "@/lib/utils";

export type StatusType = "success" | "error" | "loading" | "info";

interface StatusBannerProps {
  type: StatusType;
  message: string;
  className?: string;
}

const statusConfig = {
  success: {
    icon: CheckCircle2,
    bgClass: "bg-emerald-500/10 border-emerald-500/30",
    textClass: "text-emerald-400",
    iconClass: "text-emerald-400",
  },
  error: {
    icon: AlertCircle,
    bgClass: "bg-red-500/10 border-red-500/30",
    textClass: "text-red-400",
    iconClass: "text-red-400",
  },
  loading: {
    icon: Loader2,
    bgClass: "bg-primary/10 border-primary/30",
    textClass: "text-primary",
    iconClass: "text-primary animate-spin",
  },
  info: {
    icon: Info,
    bgClass: "bg-blue-500/10 border-blue-500/30",
    textClass: "text-blue-400",
    iconClass: "text-blue-400",
  },
};

export function StatusBanner({ type, message, className }: StatusBannerProps) {
  const config = statusConfig[type];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "flex items-center gap-3 px-4 py-3 rounded-xl border animate-fade-in",
        config.bgClass,
        className
      )}
    >
      <Icon className={cn("h-5 w-5 shrink-0", config.iconClass)} />
      <span className={cn("text-sm font-medium", config.textClass)}>
        {message}
      </span>
    </div>
  );
}
