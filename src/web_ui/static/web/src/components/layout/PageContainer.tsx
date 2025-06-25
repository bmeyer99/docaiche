import React from "react";
import { componentClasses } from "../../styles/componentClasses";

export interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Responsive page container with max-width and padding.
 */
export const PageContainer: React.FC<PageContainerProps> = ({
  children,
  className,
}) => (
  <div className={`${componentClasses.pageContainer} ${className ?? ""}`}>
    {children}
  </div>
);

export default PageContainer;