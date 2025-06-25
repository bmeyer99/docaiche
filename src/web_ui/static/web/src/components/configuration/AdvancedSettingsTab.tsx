import React, { useState } from "react";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { Label } from "../ui/Label";
import { Button } from "../ui/Button";
import { FormGroup } from "../ui/FormGroup";
import { FormRow } from "../ui/FormRow";

export interface AdvancedSettingsTabProps {
  className?: string;
}

const debugModeOptions = [
  { value: "enabled", label: "Enabled" },
  { value: "disabled", label: "Disabled" }
];

const performanceModeOptions = [
  { value: "standard", label: "Standard" },
  { value: "high", label: "High Performance" },
  { value: "balanced", label: "Balanced" }
];

const AdvancedSettingsTab: React.FC<AdvancedSettingsTabProps> = ({ className }) => {
  const [debugMode, setDebugMode] = useState("disabled");
  const [performanceMode, setPerformanceMode] = useState("standard");
  const [maxWorkers, setMaxWorkers] = useState("");
  const [timeoutDuration, setTimeoutDuration] = useState("");
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [success, setSuccess] = useState(false);

  const validate = () => {
    const errs: { [key: string]: string } = {};
    if (!maxWorkers.trim() || isNaN(Number(maxWorkers)) || Number(maxWorkers) <= 0)
      errs.maxWorkers = "Valid max workers count is required.";
    if (!timeoutDuration.trim() || isNaN(Number(timeoutDuration)) || Number(timeoutDuration) <= 0)
      errs.timeoutDuration = "Valid timeout duration is required.";
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
            <h3 className="text-lg font-semibold text-text-primary mb-2">Advanced Settings</h3>
            <p className="text-text-secondary mb-4">
              Configure advanced system settings, debugging, and performance options.
            </p>
          </div>
          <FormGroup>
            <FormRow>
              <Label htmlFor="debugMode">Debug Mode</Label>
              <Select
                value={debugMode}
                onChange={setDebugMode}
                options={debugModeOptions}
                aria-label="Debug Mode"
              />
            </FormRow>
            <FormRow>
              <Label htmlFor="performanceMode">Performance Mode</Label>
              <Select
                value={performanceMode}
                onChange={setPerformanceMode}
                options={performanceModeOptions}
                aria-label="Performance Mode"
              />
            </FormRow>
            <FormRow>
              <Label htmlFor="maxWorkers">Max Workers</Label>
              <Input
                value={maxWorkers}
                onChange={setMaxWorkers}
                error={errors.maxWorkers}
                required
                aria-required="true"
                aria-describedby={errors.maxWorkers ? "maxWorkers-error" : undefined}
                placeholder="e.g. 4"
              />
            </FormRow>
            <FormRow>
              <Label htmlFor="timeoutDuration">Timeout Duration (seconds)</Label>
              <Input
                value={timeoutDuration}
                onChange={setTimeoutDuration}
                error={errors.timeoutDuration}
                required
                aria-required="true"
                aria-describedby={errors.timeoutDuration ? "timeoutDuration-error" : undefined}
                placeholder="e.g. 30"
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

export default AdvancedSettingsTab;