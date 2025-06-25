// src/components/ui/Select.tsx
import React from "react";
import { componentClasses } from "../../styles/componentClasses";
import { Label } from "./Label";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  options?: SelectOption[];
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  error?: string;
  label?: string;
  required?: boolean;
  className?: string;
  children?: React.ReactNode;
  // Additional props for compatibility
  'aria-invalid'?: boolean;
  'aria-describedby'?: string;
}

export const Select: React.FC<SelectProps> = ({
  options,
  value,
  onChange,
  placeholder,
  disabled = false,
  error,
  label,
  required = false,
  className = "",
}) => {
  const selectClass = error
    ? componentClasses.inputError
    : componentClasses.select;

  return (
    <div>
      {label && (
        <Label htmlFor={label} required={required}>
          {label}
        </Label>
      )}
      <select
        id={label}
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        disabled={disabled}
        required={required}
        className={`${selectClass} ${className}`}
        aria-invalid={!!error}
        aria-describedby={error ? `${label}-error` : undefined}
        tabIndex={0}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options?.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && (
        <div id={`${label}-error`} className={componentClasses.errorText}>
          {error}
        </div>
      )}
    </div>
  );
};