import { Button } from "@/components/ui/button";
import { Icons } from "@/components/icons";

interface EmptyStateProps {
  icon?: keyof typeof Icons;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon = 'fileText', title, description, action }: EmptyStateProps) {
  const IconComponent = Icons[icon];
  
  return (
    <div className="text-center py-12">
      <IconComponent className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
      <div className="text-lg font-medium mb-2">{title}</div>
      <div className="text-muted-foreground mb-4 max-w-sm mx-auto">{description}</div>
      {action && (
        <Button onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
}