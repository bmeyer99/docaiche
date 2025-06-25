// src/context/ToastProvider.tsx
import React, { createContext, useContext, useReducer, useRef, useCallback } from "react";
import { ToastType, ToastProps, ToastContainer } from "../components/ui/Toast";
import { sanitize } from "../utils/sanitize";

// Toast State & Actions
interface ToastState {
  toasts: ToastProps[];
}
type ToastAction =
  | { type: "ADD_TOAST"; toast: Omit<ToastProps, "onDismiss"> }
  | { type: "DISMISS_TOAST"; id: string }
  | { type: "DISMISS_OLDEST" };

// Toast durations (ms)
const TOAST_DURATIONS: Record<ToastType, number> = {
  success: 4000,
  error: 8000,
  warning: 6000,
  info: 5000,
};

// Logging function (replace with real logger if needed)
function logToastDismiss(id: string, type: ToastType, reason: string) {
  // eslint-disable-next-line no-console
  console.log(`[Toast] Dismissed: id=${id}, type=${type}, reason=${reason}`);
}

function toastReducer(state: ToastState, action: ToastAction): ToastState {
  switch (action.type) {
    case "ADD_TOAST": {
      let toasts = [...state.toasts, { ...action.toast }];
      if (toasts.length > 3) {
        toasts = toasts.slice(toasts.length - 3);
      }
      return { toasts };
    }
    case "DISMISS_TOAST":
      return { toasts: state.toasts.filter((t) => t.id !== action.id) };
    case "DISMISS_OLDEST":
      return { toasts: state.toasts.slice(1) };
    default:
      return state;
  }
}

// Context
interface ToastContextValue {
  showToast: (opts: { type: ToastType; message: string }) => void;
  dismissToast: (id: string) => void;
}
const ToastContext = createContext<ToastContextValue | undefined>(undefined);

// Provider
export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(toastReducer, { toasts: [] });
  const timers = useRef<Record<string, NodeJS.Timeout>>({});

  // Dismiss logic
  const dismissToast = useCallback((id: string, type?: ToastType, reason = "manual") => {
    dispatch({ type: "DISMISS_TOAST", id });
    if (type) logToastDismiss(id, type, reason);
    if (timers.current[id]) {
      clearTimeout(timers.current[id]);
      delete timers.current[id];
    }
  }, []);

  // Show toast
  const showToast = useCallback(
    ({ type, message }: { type: ToastType; message: string }) => {
      const id = `${type}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const sanitized = sanitize(message);
      // If stack full, dismiss oldest
      if (state.toasts.length >= 3) {
        const oldest = state.toasts[0];
        dismissToast(oldest.id, oldest.type, "stack_limit");
      }
      dispatch({
        type: "ADD_TOAST",
        toast: {
          id,
          type,
          message: sanitized,
          onDismiss: (toastId: string) => dismissToast(toastId, type, "manual"),
        },
      });
      // Timer
      timers.current[id] = setTimeout(() => {
        dismissToast(id, type, "auto");
      }, TOAST_DURATIONS[type]);
    },
    [dismissToast, state.toasts]
  );

  // Pause/resume on hover/focus
  // (Handled in Toast component via props if needed)

  // Render
  return (
    <ToastContext.Provider value={{ showToast, dismissToast }}>
      {children}
      <ToastContainer
        toasts={state.toasts}
        onDismiss={(id: string) => {
          const toast = state.toasts.find((t) => t.id === id);
          dismissToast(id, toast?.type, "manual");
        }}
      />
    </ToastContext.Provider>
  );
};

// Hook
export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within a ToastProvider");
  return ctx;
}