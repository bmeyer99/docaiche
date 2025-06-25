// src/components/ui/Icon.tsx
import { LucideIcon } from 'lucide-react';
import { 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Info, 
  Loader, 
  Eye, 
  EyeOff, 
  ChevronDown, 
  ChevronUp,
  Settings,
  Save,
  RotateCcw
} from 'lucide-react';

export type IconName = 
  | 'checkCircle'
  | 'xCircle' 
  | 'alertTriangle'
  | 'info'
  | 'loader'
  | 'eye'
  | 'eyeOff'
  | 'chevronDown'
  | 'chevronUp'
  | 'settings'
  | 'save'
  | 'rotateCcw';

export type IconSize = 'sm' | 'md' | 'lg';

interface IconProps {
  name: IconName;
  size?: IconSize;
  className?: string;
  color?: string;
}

const iconMap: Record<IconName, LucideIcon> = {
  checkCircle: CheckCircle,
  xCircle: XCircle,
  alertTriangle: AlertTriangle,
  info: Info,
  loader: Loader,
  eye: Eye,
  eyeOff: EyeOff,
  chevronDown: ChevronDown,
  chevronUp: ChevronUp,
  settings: Settings,
  save: Save,
  rotateCcw: RotateCcw,
};

const sizeMap: Record<IconSize, string> = {
  sm: 'w-3 h-3',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
};

export const Icon: React.FC<IconProps> = ({ 
  name, 
  size = 'md', 
  className = '', 
  color 
}) => {
  const IconComponent = iconMap[name];
  const sizeClass = sizeMap[size];
  
  return (
    <IconComponent 
      className={`${sizeClass} ${className}`}
      style={color ? { color } : undefined}
    />
  );
};