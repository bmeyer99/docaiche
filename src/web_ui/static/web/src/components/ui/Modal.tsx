import React, { useEffect, useRef } from "react";
import classNames from "classnames";
import { Logger } from "../../utils/logger";

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
}

const sizeClasses: Record<string, string> = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-2xl",
};

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  size = "md",
  className,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const lastFocusedElement = useRef<HTMLElement | null>(null);

  // Trap focus inside modal and log accessibility events
  useEffect(() => {
    if (!isOpen) return;
    lastFocusedElement.current = document.activeElement as HTMLElement;
    const focusable = modalRef.current?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    focusable?.[0]?.focus();

    Logger.info("Modal opened and focus trap activated", {
      category: "user",
      component: "Modal",
      event: "open",
      title,
    });

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        Logger.info("Modal closed via Escape key", {
          category: "user",
          component: "Modal",
          event: "close-escape",
          title,
        });
        onClose();
      }
      if (e.key === "Tab" && focusable && focusable.length > 0) {
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
            Logger.debug("Focus trap cycled to last element (Shift+Tab)", {
              category: "user",
              component: "Modal",
              event: "focus-trap-cycle",
              direction: "backward",
              title,
            });
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
            Logger.debug("Focus trap cycled to first element (Tab)", {
              category: "user",
              component: "Modal",
              event: "focus-trap-cycle",
              direction: "forward",
              title,
            });
          }
        }
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
      lastFocusedElement.current?.focus();
      Logger.info("Modal closed and focus trap deactivated", {
        category: "user",
        component: "Modal",
        event: "close",
        title,
      });
    };
  }, [isOpen, onClose, title]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      aria-modal="true"
      role="dialog"
      tabIndex={-1}
    >
      {/* Backdrop */}
      <div
        className={classNames(
          "fixed inset-0 bg-black bg-opacity-40 transition-opacity duration-200 animate-fade-in"
        )}
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Modal content */}
      <div
        ref={modalRef}
        className={classNames(
          "relative bg-white rounded-lg shadow-lg transition-all duration-200 animate-fade-in",
          sizeClasses[size],
          "w-full mx-4 sm:mx-0",
          className
        )}
        role="document"
        tabIndex={0}
        onClick={(e) => e.stopPropagation()}
        aria-labelledby={title ? "modal-title" : undefined}
      >
        {title && (
          <div className="px-6 pt-6 pb-2">
            <h2 className="text-lg font-semibold text-text-primary" id="modal-title">
              {title}
            </h2>
          </div>
        )}
        <div className="px-6 pb-6">{children}</div>
        <button
          aria-label="Close modal"
          className="absolute top-4 right-4 text-text-tertiary hover:text-text-primary focus:outline-none"
          onClick={onClose}
        >
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
      <style>
        {`
        .animate-fade-in {
          animation: fadeInModal 0.18s cubic-bezier(0.4,0,0.2,1);
        }
        @keyframes fadeInModal {
          from { opacity: 0; transform: translateY(16px);}
          to { opacity: 1; transform: translateY(0);}
        }
        `}
      </style>
    </div>
  );
};

export default Modal;