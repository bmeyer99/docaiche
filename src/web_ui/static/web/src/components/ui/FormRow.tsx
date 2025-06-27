import React from "react";
import classNames from "classnames";
import { componentClasses } from "../../styles/componentClasses";

export interface FormRowProps {
  children: React.ReactNode;
  columns?: 1 | 2 | 3;
  className?: string;
}

/**
 * Responsive form row with configurable columns.
 */
export const FormRow: React.FC<FormRowProps> = ({
  children,
  columns = 1,
  className,
}) => {
  // Responsive grid: always 1 column on mobile, up to columns on md+
  const gridCols =
    columns === 3
      ? "md:grid-cols-3"
      : columns === 2
      ? "md:grid-cols-2"
      : "md:grid-cols-1";
  return (
    <div
      className={classNames(
        componentClasses.formRow,
        gridCols,
        className
      )}
    >
      {children}
    </div>
  );
};

export default FormRow;