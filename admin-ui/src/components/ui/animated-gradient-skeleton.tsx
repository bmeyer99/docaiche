import { cn } from "@/lib/utils";

interface AnimatedGradientSkeletonProps {
  className?: string;
  variant?: 'card' | 'text' | 'metric' | 'chart' | 'health';
}

export function AnimatedGradientSkeleton({ className, variant = 'text' }: AnimatedGradientSkeletonProps) {
  const baseClasses = "relative overflow-hidden rounded-md bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 bg-[length:200%_100%] animate-shimmer";
  
  const variantClasses = {
    card: "h-32 w-full",
    text: "h-4 w-full",
    metric: "h-8 w-24",
    chart: "h-64 w-full",
    health: "h-20 w-full"
  };

  return (
    <div className={cn(baseClasses, variantClasses[variant], className)}>
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full animate-shimmer-slide" />
    </div>
  );
}

export function AnimatedGradientSkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn("space-y-3 p-4 border rounded-lg bg-card", className)}>
      <AnimatedGradientSkeleton variant="text" className="w-1/3" />
      <AnimatedGradientSkeleton variant="metric" />
      <AnimatedGradientSkeleton variant="text" className="w-1/2 h-3" />
    </div>
  );
}

export function AnimatedGradientSkeletonChart({ className }: { className?: string }) {
  return (
    <div className={cn("space-y-3 p-4 border rounded-lg bg-card", className)}>
      <div className="space-y-2">
        <AnimatedGradientSkeleton variant="text" className="w-1/4" />
        <AnimatedGradientSkeleton variant="text" className="w-1/3 h-3" />
      </div>
      <AnimatedGradientSkeleton variant="chart" />
    </div>
  );
}

export function AnimatedGradientSkeletonHealth({ className }: { className?: string }) {
  return (
    <div className={cn("space-y-3 p-4 border rounded-lg bg-card", className)}>
      <div className="flex items-center gap-3">
        <AnimatedGradientSkeleton className="h-8 w-8 rounded-full" />
        <div className="flex-1 space-y-2">
          <AnimatedGradientSkeleton variant="text" className="w-1/3" />
          <AnimatedGradientSkeleton variant="text" className="w-1/2 h-3" />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {[1, 2, 3].map((i) => (
          <AnimatedGradientSkeleton key={i} variant="health" />
        ))}
      </div>
    </div>
  );
}