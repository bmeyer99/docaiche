// src/components/ui/ApiErrorDisplay.tsx
import React from "react";
import { Button } from "./Button";
import { Logger } from "../../utils/logger";

interface ApiErrorDisplayProps {
  error: string;
  onRetry: () => void;
  correlationId?: string;
  className?: string;
}

export const ApiErrorDisplay: React.FC<ApiErrorDisplayProps> = ({
  error,
  onRetry,
  correlationId,
  className = "",
}) => {
  // Sanitize error message (never echo user input directly)
  const safeError =
    typeof error === "string"
      ? error.replace(/(apiKey|password|token)[^ ]*/gi, "[REDACTED]")
      : "An unexpected error occurred.";

  React.useEffect(() => {
    Logger.error("API error displayed to user", {
      category: "api",
      correlationId,
      action: "display_api_error",
      error: safeError,
    });
  }, [safeError, correlationId]);

  const handleRetry = () => {
    Logger.info("User clicked retry on API error", {
      category: "user",
      correlationId,
      action: "retry_api_error",
    });
    onRetry();
  };

  return (
    <div
      className={`bg-destructive/10 border border-destructive rounded p-4 flex flex-col items-start gap-2 ${className}`}
      role="alert"
      aria-live="assertive"
      tabIndex={-1}
    >
      <span className="text-destructive font-medium" data-testid="api-error-message">
        {safeError}
      </span>
      <Button variant="primary" onClick={handleRetry}>
        Retry
      </Button>
    </div>
  );
};

export default ApiErrorDisplay;