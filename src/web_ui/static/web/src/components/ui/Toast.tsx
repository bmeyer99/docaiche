// src/components/ui/Toast.tsx
import React, { useEffect, useRef, useState } from "react";
import { sanitize } from "../../utils/sanitize";
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

// Toast durations (ms)
const TOAST_DURATIONS: Record<ToastType, number> = {
  success: 4000,
  error: 8000,
  warning: 6000,
  info: 5000,
};

export const Toast: React.FC<ToastProps> = ({ id, type, message, onDismiss }) => {
  const [hovered, setHovered] = useState(false);
  const [visible, setVisible] = useState(true);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const fadeOutRef = useRef<NodeJS.Timeout | null>(null);

  // Sanitize message
  const safeMessage = sanitize(message);

  // Accessibility: role per type
  const role = type === "error" || type === "warning" ? "alert" : "status";
  const ariaLive = type === "error" || type === "warning" ? "assertive" : "polite";

  // Timer logic
  useEffect(() => {
    if (!hovered) {
      timerRef.current = setTimeout(() => {
        setVisible(false);
        fadeOutRef.current = setTimeout(() => onDismiss(id), 200);
      }, TOAST_DURATIONS[type]);
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (fadeOutRef.current) clearTimeout(fadeOutRef.current);
    };
  }, [id, onDismiss, type, hovered]);

  // Pause timer on hover/focus
  const handleMouseEnter = () => setHovered(true);
  const handleMouseLeave = () => setHovered(false);
  const handleFocus = () => setHovered(true);
  const handleBlur = () => setHovered(false);

  // Animation classes
  const animationClass = visible
    ? "animate-toast-slide-in"
    : "animate-toast-fade-out";

  return (
    <div
      className={`flex items-center ${typeConfig[type].bg} ${typeConfig[type].border} border-l-4 rounded-md shadow-md px-4 py-3 mb-3 ${animationClass}`}
      role={role}
      aria-live={ariaLive}
      tabIndex={0}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocus={handleFocus}
      onBlur={handleBlur}
      style={{ outline: "none" }}
    >
      <Icon
        name={typeConfig[type].icon}
        size="md"
        className={`${typeConfig[type].iconColor} mr-3 flex-shrink-0`}
        aria-hidden="true"
      />
      <div className="flex-1 text-sm text-text-primary" tabIndex={-1}>
        {safeMessage}
      </div>
      <button
        onClick={() => {
          setVisible(false);
          setTimeout(() => onDismiss(id), 200);
        }}
        className="ml-4 p-1 rounded hover:bg-neutral-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
        aria-label="Close notification"
        tabIndex={0}
      >
        <Icon name="xCircle" size="sm" className="text-text-tertiary" aria-hidden="true" />
      </button>
      <style>
        {`
          @keyframes toast-slide-in {
            from { transform: translateX(120%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
          }
          .animate-toast-slide-in {
            animation: toast-slide-in 0.3s cubic-bezier(0.4,0,0.2,1);
          }
          @keyframes toast-fade-out {
            from { opacity: 1; }
            to { opacity: 0; }
          }
          .animate-toast-fade-out {
            animation: toast-fade-out 0.2s ease-in;
          }
        `}
      </style>
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
  </div>
);