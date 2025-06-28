import React from "react";
import classNames from "classnames";
import { componentClasses } from "../../styles/componentClasses";

export interface SkeletonCardProps {
  lines?: number;
  showHeader?: boolean;
  className?: string;
}

/**
 * Skeleton card with pulse animation for loading states.
 */
export const SkeletonCard: React.FC<SkeletonCardProps> = ({
  lines = 3,
  showHeader = false,
  className,
}) => (
  <div
    className={classNames(
      componentClasses.card,
      "animate-pulse bg-neutral-100 border border-border-light",
      className
    )}
    aria-busy="true"
    aria-label="Loading"
  >
    {showHeader && (
      <div className="h-6 w-1/3 bg-neutral-200 rounded mb-4" />
    )}
    <div className="space-y-3">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-4 w-full bg-neutral-200 rounded"
          style={{
            width: `${90 - i * 10}%`,
            maxWidth: "100%",
          }}
        />
      ))}
    </div>
    <style>
      {`
      .animate-pulse {
        animation: pulse 1.2s cubic-bezier(0.4,0,0.6,1) infinite;
      }
      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
      }
      `}
    </style>
  </div>
);

export default SkeletonCard;