import React, { useState } from "react";
import { SkeletonCard } from "../ui/SkeletonCard";
import ApiErrorDisplay from "../ui/ApiErrorDisplay";
import { Logger } from "../../utils/logger";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { Label } from "../ui/Label";
import { Button } from "../ui/Button";
import { FormGroup } from "../ui/FormGroup";
import { FormRow } from "../ui/FormRow";
interface GeneralSettingsTabLoadingProps {
  loading: boolean;
  loadError?: string | null;
  onRetry?: () => void;
  correlationId?: string;
}

const GeneralSettingsTabLoading: React.FC<GeneralSettingsTabLoadingProps> = ({
  loading,
  loadError,
  onRetry,
  correlationId,
}) => {
  React.useEffect(() => {
    if (loading) {
      Logger.info("SkeletonCard displayed for GeneralSettingsTab", {
        category: "state",
        correlationId,
        action: "show_skeleton",
      });
    }
  }, [loading, correlationId]);

  if (loading) {
    return <SkeletonCard lines={6} showHeader className="mb-6" />;
  }
  if (loadError && onRetry) {
    return (
      <ApiErrorDisplay
        error={loadError}
        onRetry={onRetry}
        correlationId={correlationId}
        className="mb-6"
      />
    );
  }
  return null;
};

export interface GeneralSettingsTabProps {
  className?: string;
}

const loggingOptions = [
  { value: "info", label: "Info" },
  { value: "debug", label: "Debug" },
  { value: "warn", label: "Warning" },
  { value: "error", label: "Error" }
];

const monitoringOptions = [
  { value: "enabled", label: "Enabled" },
  { value: "disabled", label: "Disabled" }
];

export const GeneralSettingsTab: React.FC<GeneralSettingsTabProps> = ({ className }) => {
  const [systemName, setSystemName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [loggingLevel, setLoggingLevel] = useState("info");
  const [monitoring, setMonitoring] = useState("enabled");
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [success, setSuccess] = useState(false);

  const validate = () => {
    const errs: { [key: string]: string } = {};
    if (!systemName.trim()) errs.systemName = "System name is required.";
    if (!adminEmail.trim() || !/^[\w-.]+@[\w-]+\.[a-zA-Z]{2,}$/.test(adminEmail))
      errs.adminEmail = "Valid email is required.";
    return errs;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs = validate();
    setErrors(errs);
    setSuccess(false);
    if (Object.keys(errs).length === 0) {
      // TODO: Integrate API call to save settings
      setSuccess(true);
    }
  };

  return (
    <Card className={className}>
      <form onSubmit={handleSubmit} noValidate>
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">General System Settings</h3>
            <p className="text-text-secondary mb-4">
              Configure system information, preferences, and logging/monitoring settings.
            </p>
          </div>
          <FormGroup>
            <FormRow>
              <Label htmlFor="systemName">System Name</Label>
              <Input
                id="systemName"
                name="systemName"
                value={systemName}
                onChange={e => setSystemName(e.target.value)}
                error={errors.systemName}
                required
                aria-required="true"
                aria-describedby={errors.systemName ? "systemName-error" : undefined}
                autoComplete="off"
              />
            </FormRow>
            <FormRow>
              <Label htmlFor="adminEmail">Admin Email</Label>
              <Input
                id="adminEmail"
                name="adminEmail"
                type="email"
                value={adminEmail}
                onChange={e => setAdminEmail(e.target.value)}
                error={errors.adminEmail}
                required
                aria-required="true"
/**
 * Example usage of loading/error state wrapper in GeneralSettingsTab.
 * Integrate this logic at the top of the component's return or before rendering the form.
 *
 * Usage:
 *   <GeneralSettingsTabLoading
 *     loading={loading}
 *     loadError={loadError}
 *     onRetry={reloadFunction}
 *     correlationId={correlationId}
 *   />
 *
 * Only render the form if !loading && !loadError.
 */
                aria-describedby={errors.adminEmail ? "adminEmail-error" : undefined}
                autoComplete="off"
              />
            </FormRow>
            <FormRow>
              <Label htmlFor="loggingLevel">Logging Level</Label>
              <Select
                id="loggingLevel"
                name="loggingLevel"
                value={loggingLevel}
                onChange={e => setLoggingLevel(e.target.value)}
                options={loggingOptions}
                aria-label="Logging Level"
              />
            </FormRow>
            <FormRow>
              <Label htmlFor="monitoring">Monitoring</Label>
              <Select
                id="monitoring"
                name="monitoring"
                value={monitoring}
                onChange={e => setMonitoring(e.target.value)}
                options={monitoringOptions}
                aria-label="Monitoring"
              />
            </FormRow>
          </FormGroup>
          <div className="flex justify-end">
            <Button type="submit" variant="primary">
              Save Changes
            </Button>
          </div>
          {success && (
            <div className="text-success mt-2" role="status" aria-live="polite">
              Settings saved successfully.
            </div>
          )}
        </div>
      </form>
    </Card>
  );
};