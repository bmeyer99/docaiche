import { cn } from '@/lib/utils';

interface GradientHeaderProps {
  title: string;
  subtitle?: string;
  gradient?: 'primary' | 'accent' | 'success' | 'warning' | 'danger';
  className?: string;
}

export function GradientHeader({ 
  title, 
  subtitle, 
  gradient = 'accent',
  className 
}: GradientHeaderProps) {
  const gradientClasses = {
    primary: 'gradient-primary',
    accent: 'gradient-accent',
    success: 'gradient-success',
    warning: 'gradient-warning',
    danger: 'gradient-danger'
  };

  return (
    <div className={cn("relative overflow-hidden rounded-lg p-8 mb-6", className)}>
      <div className={cn(
        "absolute inset-0 opacity-10",
        gradientClasses[gradient]
      )} />
      <div className="relative z-10">
        <h1 className="text-4xl font-bold mb-2">{title}</h1>
        {subtitle && (
          <p className="text-lg text-muted-foreground">{subtitle}</p>
        )}
      </div>
      <div className="absolute -top-20 -right-20 w-40 h-40 rounded-full bg-white/5 blur-3xl" />
      <div className="absolute -bottom-20 -left-20 w-40 h-40 rounded-full bg-white/5 blur-3xl" />
    </div>
  );
}