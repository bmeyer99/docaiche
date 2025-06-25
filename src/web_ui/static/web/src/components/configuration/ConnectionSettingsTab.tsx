import React, { useState } from "react";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";
import { Label } from "../ui/Label";
import { Button } from "../ui/Button";
import { FormGroup } from "../ui/FormGroup";
import { FormRow } from "../ui/FormRow";

export interface ConnectionSettingsTabProps {
  className?: string;
}

const dbTypeOptions = [
  { value: "postgres", label: "PostgreSQL" },
  { value: "mysql", label: "MySQL" },
  { value: "sqlite", label: "SQLite" }
];

const ConnectionSettingsTab: React.FC<ConnectionSettingsTabProps> = ({ className }) => {
  const [anythingLLMUrl, setAnythingLLMUrl] = useState("");
  const [redisHost, setRedisHost] = useState("");
  const [redisPort, setRedisPort] = useState("");
  const [dbType, setDbType] = useState("postgres");
  const [dbHost, setDbHost] = useState("");
  const [dbPort, setDbPort] = useState("");
  const [dbUser, setDbUser] = useState("");
  const [dbPassword, setDbPassword] = useState("");
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [success, setSuccess] = useState(false);

  const validate = () => {
    const errs: { [key: string]: string } = {};
    if (!anythingLLMUrl.trim() || !/^https?:\/\/.+/.test(anythingLLMUrl))
      errs.anythingLLMUrl = "Valid AnythingLLM URL is required.";
    if (!redisHost.trim()) errs.redisHost = "Redis host is required.";
    if (!redisPort.trim() || isNaN(Number(redisPort))) errs.redisPort = "Valid Redis port is required.";
    if (!dbHost.trim()) errs.dbHost = "Database host is required.";
    if (!dbPort.trim() || isNaN(Number(dbPort))) errs.dbPort = "Valid DB port is required.";
    if (!dbUser.trim()) errs.dbUser = "DB user is required.";
    if (!dbPassword.trim()) errs.dbPassword = "DB password is required.";
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
            <h3 className="text-lg font-semibold text-text-primary mb-2">Connection Settings</h3>
            <p className="text-text-secondary mb-4">
              Configure AnythingLLM, Redis, and database connection settings.
            </p>
          </div>
          <FormGroup>
            <FormRow>
              <Label htmlFor="anythingLLMUrl">AnythingLLM URL</Label>
              <Input
                value={anythingLLMUrl}
                onChange={setAnythingLLMUrl}
                error={errors.anythingLLMUrl}
                required
                aria-required="true"
                aria-describedby={errors.anythingLLMUrl ? "anythingLLMUrl-error" : undefined}
                placeholder="https://llm.example.com"
              />
            </FormRow>
            <FormRow>
              <Label htmlFor="redisHost">Redis Host</Label>
              <Input
                value={redisHost}
                onChange={setRedisHost}
                error={errors.redisHost}
                required
                aria-required="true"
                aria-describedby={errors.redisHost ? "redisHost-error" : undefined}
                />
            </FormRow>
            <FormRow>
              <Label htmlFor="redisPort">Redis Port</Label>
              <Input
                value={redisPort}
                onChange={setRedisPort}
                error={errors.redisPort}
                required
                aria-required="true"
                aria-describedby={errors.redisPort ? "redisPort-error" : undefined}
              />
            </FormRow>
            <FormRow>
              <Label htmlFor="dbType">Database Type</Label>
              <Select
                value={dbType}
                onChange={setDbType}
                options={dbTypeOptions}
                aria-label="Database Type"
              />
            </FormRow>
            <FormRow>
              <Label htmlFor="dbHost">DB Host</Label>
              <Input
                value={dbHost}
                onChange={setDbHost}
                error={errors.dbHost}
                required
                aria-required="true"
                aria-describedby={errors.dbHost ? "dbHost-error" : undefined}
                />
            </FormRow>
            <FormRow>
              <Label htmlFor="dbPort">DB Port</Label>
              <Input
                value={dbPort}
                onChange={setDbPort}
                error={errors.dbPort}
                required
                aria-required="true"
                aria-describedby={errors.dbPort ? "dbPort-error" : undefined}
              />
            </FormRow>
            <FormRow>
              <Label htmlFor="dbUser">DB User</Label>
              <Input
                value={dbUser}
                onChange={setDbUser}
                error={errors.dbUser}
                required
                aria-required="true"
                aria-describedby={errors.dbUser ? "dbUser-error" : undefined}
                />
            </FormRow>
            <FormRow>
              <Label htmlFor="dbPassword">DB Password</Label>
              <Input
                type="password"
                value={dbPassword}
                onChange={setDbPassword}
                error={errors.dbPassword}
                required
                aria-required="true"
                aria-describedby={errors.dbPassword ? "dbPassword-error" : undefined}
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

export default ConnectionSettingsTab;