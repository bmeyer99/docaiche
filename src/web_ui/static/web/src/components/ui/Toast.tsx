// src/components/ui/Toast.tsx
import React, { useEffect } from "react";
import { Icon } from "./Icon";

export type ToastType = "success" | "error" | "warning" | "info";

export interface ToastProps {
  id: string;
  type: ToastType;
  message: string;
  onDismiss: (id: string) => void;
}

const typeConfig: Record<
  ToastType,
  { icon: any; iconColor: string; bg: string; border: string }
> = {
  success: {
    icon: "checkCircle",
    iconColor: "text-status-success",
    bg: "bg-status-success/10",
    border: "border-status-success",
  },
  error: {
    icon: "xCircle",
    iconColor: "text-status-error",
    bg: "bg-status-error/10",
    border: "border-status-error",
  },
  warning: {
    icon: "alertTriangle",
    iconColor: "text-status-warning",
    bg: "bg-status-warning/10",
    border: "border-status-warning",
  },
  info: {
    icon: "info",
    iconColor: "text-status-info",
    bg: "bg-status-info/10",
    border: "border-status-info",
  },
};

export const Toast: React.FC<ToastProps> = ({ id, type, message, onDismiss }) => {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(id), 5000);
    return () => clearTimeout(timer);
  }, [id, onDismiss]);

  const { icon, iconColor, bg, border } = typeConfig[type];

  return (
    <div
      className={`flex items-center ${bg} ${border} border-l-4 rounded-md shadow-md px-4 py-3 mb-3 animate-toast-slide-in`}
      role="alert"
      tabIndex={0}
    >
      <Icon name={icon} size="md" className={`${iconColor} mr-3 flex-shrink-0`} />
      <div className="flex-1 text-sm text-text-primary">{message}</div>
      <button
        onClick={() => onDismiss(id)}
        className="ml-4 p-1 rounded hover:bg-neutral-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
        aria-label="Dismiss notification"
        tabIndex={0}
      >
        <Icon name="xCircle" size="sm" className="text-text-tertiary" />
      </button>
    </div>
  );
};

// ToastContainer manages stacking and animation
interface ToastContainerProps {
  toasts: ToastProps[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({
  toasts,
  onDismiss,
}) => (
  <div className="fixed top-6 right-6 z-50 flex flex-col items-end space-y-0 pointer-events-none">
    {toasts.slice(0, 3).map((toast) => (
      <div
        key={toast.id}
        className="pointer-events-auto w-80 transition-transform duration-300"
      >
        <Toast {...toast} onDismiss={onDismiss} />
      </div>
    ))}
    <style>
      {`
        @keyframes toast-slide-in {
          from { transform: translateX(120%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        .animate-toast-slide-in {
          animation: toast-slide-in 0.4s cubic-bezier(0.4,0,0.2,1);
        }
      `}
    </style>
  </div>
);