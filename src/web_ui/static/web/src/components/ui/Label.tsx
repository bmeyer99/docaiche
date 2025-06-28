// src/components/ui/Label.tsx
import React from "react";
import { componentClasses } from "../../styles/componentClasses";

interface LabelProps {
  children: React.ReactNode;
  htmlFor?: string;
  required?: boolean;
  className?: string;
}

export const Label: React.FC<LabelProps> = ({
  children,
  htmlFor,
  required = false,
  className = "",
}) => (
  <label
    htmlFor={htmlFor}
    className={`${componentClasses.label} ${className}`}
  >
    {children}
    {required && <span className="text-status-error ml-1">*</span>}
  </label>
);