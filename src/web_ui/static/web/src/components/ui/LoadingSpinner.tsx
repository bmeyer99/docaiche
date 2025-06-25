import React from "react";
import classNames from "classnames";
import Icon from "./Icon";

export interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  color?: string;
  className?: string;
}

const sizePx: Record<string, number> = {
  sm: 12,
  md: 16,
  lg: 24,
};

/**
 * Animated loading spinner with accessibility.
 */
export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = "md",
  color,
  className,
}) => (
  <span
    role="status"
    aria-label="Loading"
    className={classNames(
      "inline-flex items-center justify-center animate-spin",
      className
    )}
    style={{
      width: sizePx[size],
      height: sizePx[size],
      color: color,
    }}
  >
    <Icon name="loader" size={size} color={color} />
    <style>
      {`
      .animate-spin {
        animation: spin 0.8s linear infinite;
      }
      @keyframes spin {
        100% { transform: rotate(360deg);}
      }
      `}
    </style>
  </span>
);

export default LoadingSpinner;