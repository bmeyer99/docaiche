// src/components/ui/Card.tsx
import React from "react";
import { componentClasses } from "../../styles/componentClasses";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = "",
  title,
  subtitle,
}) => (
  <div className={`${componentClasses.card} ${className}`}>
    {title && (
      <div className="mb-2 text-lg font-semibold text-text-primary">{title}</div>
    )}
    {subtitle && (
      <div className="mb-4 text-sm text-text-secondary">{subtitle}</div>
    )}
    {children}
  </div>
);