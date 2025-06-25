import React, { useState } from "react";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { Label } from "../ui/Label";
import { Button } from "../ui/Button";
import { FormGroup } from "../ui/FormGroup";
import { FormRow } from "../ui/FormRow";

export interface CacheSettingsTabProps {
  className?: string;
}

const cacheStrategyOptions = [
  { value: "memory", label: "In-Memory" },
  { value: "redis", label: "Redis" },
  { value: "none", label: "Disabled" }
];

const cacheDurationOptions = [
  { value: "60", label: "1 minute" },
  { value: "300", label: "5 minutes" },
  { value: "900", label: "15 minutes" },
  { value: "3600", label: "1 hour" },
  { value: "86400", label: "24 hours" }
];

const CacheSettingsTab: React.FC<CacheSettingsTabProps> = ({ className }) => {
  const [cacheStrategy, setCacheStrategy] = useState("memory");
  const [searchCacheDuration, setSearchCacheDuration] = useState("300");
  const [contentCacheDuration, setContentCacheDuration] = useState("3600");
  const [maxCacheSize, setMaxCacheSize] = useState("");
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [success, setSuccess] = useState(false);

  const validate = () => {
    const errs: { [key: string]: string } = {};
    if (!maxCacheSize.trim() || isNaN(Number(maxCacheSize)) || Number(maxCacheSize) <= 0)
      errs.maxCacheSize = "Valid max cache size is required.";
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
            <h3 className="text-lg font-semibold text-text-primary mb-2">Cache Settings</h3>
            <p className="text-text-secondary mb-4">
              Configure cache strategy, search result caching, and content caching settings.
            </p>
          </div>
          <FormGroup>
            <FormRow>
              <Label htmlFor="cacheStrategy">Cache Strategy</Label>
              <Select
                value={cacheStrategy}
                onChange={setCacheStrategy}
                options={cacheStrategyOptions}
                aria-label="Cache Strategy"
              />
            </FormRow>
            <FormRow>
              <Label htmlFor="searchCacheDuration">Search Result Cache Duration</Label>
              <Select
                value={searchCacheDuration}
                onChange={setSearchCacheDuration}
                options={cacheDurationOptions}
                aria-label="Search Result Cache Duration"
              />
            </FormRow>
            <FormRow>
              <Label htmlFor="contentCacheDuration">Content Cache Duration</Label>
              <Select
                value={contentCacheDuration}
                onChange={setContentCacheDuration}
                options={cacheDurationOptions}
                aria-label="Content Cache Duration"
              />
            </FormRow>
            <FormRow>
              <Label htmlFor="maxCacheSize">Max Cache Size (MB)</Label>
              <Input
                value={maxCacheSize}
                onChange={setMaxCacheSize}
                error={errors.maxCacheSize}
                required
                aria-required="true"
                aria-describedby={errors.maxCacheSize ? "maxCacheSize-error" : undefined}
                placeholder="e.g. 512"
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

export default CacheSettingsTab;