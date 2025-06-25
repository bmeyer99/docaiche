// src/components/ui/Input.tsx
import React from "react";
import { componentClasses } from "../../styles/componentClasses";
import { Label } from "./Label";

interface InputProps {
  type?: "text" | "password" | "email" | "number";
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  error?: string;
  helperText?: string;
  label?: string;
  required?: boolean;
  className?: string;
}

export const Input: React.FC<InputProps> = ({
  type = "text",
  value,
  onChange,
  placeholder,
  disabled = false,
  error,
  helperText,
  label,
  required = false,
  className = "",
}) => {
  const inputClass = error
    ? componentClasses.inputError
    : componentClasses.input;

  return (
    <div>
      {label && (
        <Label htmlFor={label} required={required}>
          {label}
        </Label>
      )}
      <input
        id={label}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        required={required}
        className={`${inputClass} ${className}`}
        aria-invalid={!!error}
        aria-describedby={error ? `${label}-error` : helperText ? `${label}-helper` : undefined}
        tabIndex={0}
      />
      {error ? (
        <div id={`${label}-error`} className={componentClasses.errorText}>
          {error}
        </div>
      ) : helperText ? (
        <div id={`${label}-helper`} className={componentClasses.helperText}>
          {helperText}
        </div>
      ) : null}
    </div>
  );
};