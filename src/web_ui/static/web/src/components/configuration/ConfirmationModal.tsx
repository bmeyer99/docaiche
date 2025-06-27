import React, { useEffect, useRef } from "react";
import Modal from "../ui/Modal";
import { componentClasses } from "../../styles/componentClasses";
import classNames from "classnames";

export interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "warning" | "info";
}

const variantClasses: Record<string, string> = {
  danger: "text-status-error",
  warning: "text-status-warning",
  info: "text-status-info",
};

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "info",
}) => {
  const confirmBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (isOpen && variant === "danger") {
      confirmBtnRef.current?.focus();
    }
  }, [isOpen, variant]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm">
      <div className="space-y-4">
        <div className={classNames("text-base", variantClasses[variant])}>
          {message}
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button
            type="button"
            className={componentClasses.buttonSecondary}
            onClick={onClose}
            autoFocus={variant !== "danger"}
          >
            {cancelText}
          </button>
          <button
            type="button"
            className={classNames(
              variant === "danger"
                ? componentClasses.buttonDestructive
                : componentClasses.buttonPrimary
            )}
            onClick={onConfirm}
            ref={confirmBtnRef}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default ConfirmationModal;