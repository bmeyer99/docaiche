import React from "react";
import { componentClasses } from "../../styles/componentClasses";

export interface FormGroupProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Form group with vertical spacing.
 */
export const FormGroup: React.FC<FormGroupProps> = ({ children, className }) => (
  <div className={`${componentClasses.formGroup} ${className ?? ""}`}>
    {children}
  </div>
);

export default FormGroup;