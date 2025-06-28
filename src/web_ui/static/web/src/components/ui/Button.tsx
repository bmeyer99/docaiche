// src/components/ui/Button.tsx
import React from "react";
import { componentClasses } from "../../styles/componentClasses";
import { Icon } from "./Icon";

interface ButtonProps {
  variant?: "primary" | "secondary" | "destructive";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  loading?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
  type?: "button" | "submit" | "reset";
  className?: string;
  // Additional props for compatibility
  style?: React.CSSProperties;
  tabIndex?: number;
  'aria-label'?: string;
  'aria-busy'?: boolean;
  'aria-live'?: string;
}

const sizeMap: Record<NonNullable<ButtonProps["size"]>, string> = {
  sm: "text-sm px-3 py-1.5",
  md: "text-base px-4 py-2",
  lg: "text-lg px-5 py-3",
};

const variantMap: Record<
  NonNullable<ButtonProps["variant"]>,
  string
> = {
  primary: componentClasses.buttonPrimary,
  secondary: componentClasses.buttonSecondary,
  destructive: componentClasses.buttonDestructive,
};

export const Button: React.FC<ButtonProps> = ({
  variant = "primary",
  size = "md",
  disabled = false,
  loading = false,
  children,
  onClick,
  type = "button",
  className = "",
}) => {
  return (
    <button
      type={type}
      className={`${variantMap[variant]} ${sizeMap[size]} ${className} ${disabled || loading ? "opacity-60 cursor-not-allowed" : ""} flex items-center justify-center`}
      onClick={disabled || loading ? undefined : onClick}
      disabled={disabled || loading}
      tabIndex={0}
      style={{ minWidth: 44, minHeight: 44 }}
    >
      {loading && (
        <Icon name="loader" size="md" className="animate-spin mr-2" />
      )}
      {children}
    </button>
  );
};