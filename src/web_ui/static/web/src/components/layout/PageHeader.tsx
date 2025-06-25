import React from "react";
import { typographyClasses } from "../../styles/componentClasses";

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
}

/**
 * Responsive page header with title, subtitle, and actions.
 */
export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  actions,
  className,
}) => (
  <div
    className={`flex flex-col gap-2 md:flex-row md:items-center md:justify-between mb-6 ${className ?? ""}`}
  >
    <div>
      <h1 className={typographyClasses.heading2}>{title}</h1>
      {subtitle && (
        <div className={typographyClasses.bodySecondary}>{subtitle}</div>
      )}
    </div>
    {actions && <div className="mt-2 md:mt-0">{actions}</div>}
  </div>
);

export default PageHeader;