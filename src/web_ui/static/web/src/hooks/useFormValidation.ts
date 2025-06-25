// src/web_ui/static/web/src/hooks/useFormValidation.ts

import { useCallback, useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { logValidationFailure } from "../utils/logger";

// --- Types ---
type ValidationRule =
  | { type: "required"; message: string }
  | { type: "minLength"; value: number; message: string }
  | { type: "maxLength"; value: number; message: string }
  | { type: "pattern"; value: RegExp; message: string }
  | { type: "url"; message: string }
  | { type: "apiKey"; min: number; max: number; message: string }
  | { type: "number"; min?: number; max?: number; message: string }
  | { type: "custom"; validate: (value: any) => boolean; message: string };

type ValidationSchema = {
  [field: string]: ValidationRule[];
};

type ValidationErrors = {
  [field: string]: string | undefined;
};

type UseFormValidationOptions<T> = {
  initialValues: T;
  validationSchema: ValidationSchema;
  sensitiveFields?: string[];
  correlationId?: string;
};

type UseFormValidationResult<T> = {
  values: T;
  setFieldValue: (field: keyof T, value: any) => void;
  errors: ValidationErrors;
  isValid: boolean;
  touched: { [field in keyof T]?: boolean };
  handleBlur: (field: keyof T) => void;
  validateForm: () => boolean;
  ariaProps: (field: keyof T) => {
    "aria-invalid": boolean;
    "aria-describedby"?: string;
  };
  errorSummary: string[];
  correlationId: string;
};

// --- Helper Functions ---

function sanitizeForError(input: string): string {
  // Remove angle brackets and encode basic HTML entities
  return input.replace(/[<>"'`]/g, "");
}

function redactIfSensitive(
  field: string,
  value: any,
  sensitiveFields: string[]
): string {
  if (sensitiveFields.includes(field)) return "[REDACTED]";
  if (typeof value === "string") return sanitizeForError(value);
  return String(value);
}

// --- Main Hook ---

export function useFormValidation<T extends Record<string, any>>(
  options: UseFormValidationOptions<T>
): UseFormValidationResult<T> {
  const {
    initialValues,
    validationSchema,
    sensitiveFields = [],
    correlationId: providedCorrelationId,
  } = options;

  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [touched, setTouched] = useState<{ [field in keyof T]?: boolean }>({});
  const [errorSummary, setErrorSummary] = useState<string[]>([]);
  const [isValid, setIsValid] = useState<boolean>(true);

  const debounceTimers = useRef<{ [field: string]: NodeJS.Timeout }>({});
  const correlationId = useRef<string>(
    providedCorrelationId || uuidv4()
  ).current;

  // --- Validation Logic ---

  const validateField = useCallback(
    (field: keyof T, value: any): string | undefined => {
      const rules = validationSchema[field as string];
      if (!rules) return undefined;

      for (const rule of rules) {
        switch (rule.type) {
          case "required":
            if (
              value === undefined ||
              value === null ||
              (typeof value === "string" && value.trim() === "")
            ) {
              return rule.message;
            }
            break;
          case "minLength":
            if (typeof value === "string" && value.length < rule.value) {
              return rule.message;
            }
            break;
          case "maxLength":
            if (typeof value === "string" && value.length > rule.value) {
              return rule.message;
            }
            break;
          case "pattern":
            if (typeof value === "string" && !rule.value.test(value)) {
              return rule.message;
            }
            break;
          case "url":
            try {
              const url = new URL(value);
              if (!/^https?:$/.test(url.protocol)) {
                return rule.message;
              }
            } catch {
              return rule.message;
            }
            break;
          case "apiKey":
            if (
              typeof value !== "string" ||
              value.length < rule.min ||
              value.length > rule.max ||
              !/^[A-Za-z0-9\-_]+$/.test(value)
            ) {
              return rule.message;
            }
            break;
          case "number":
            if (
              value === "" ||
              value === null ||
              isNaN(Number(value)) ||
              (rule.min !== undefined && Number(value) < rule.min) ||
              (rule.max !== undefined && Number(value) > rule.max)
            ) {
              return rule.message;
            }
            break;
          case "custom":
            if (!rule.validate(value)) {
              return rule.message;
            }
            break;
        }
      }
      return undefined;
    },
    [validationSchema]
  );

  const validateAllFields = useCallback(
    (vals: T): ValidationErrors => {
      const newErrors: ValidationErrors = {};
      Object.keys(validationSchema).forEach((field) => {
        const err = validateField(field as keyof T, vals[field]);
        if (err) newErrors[field] = err;
      });
      return newErrors;
    },
    [validateField, validationSchema]
  );

  // --- Debounced Validation ---

  const setFieldValue = useCallback(
    (field: keyof T, value: any) => {
      setValues((prev) => ({ ...prev, [field]: value }));

      // Debounce validation
      if (debounceTimers.current[field as string]) {
        clearTimeout(debounceTimers.current[field as string]);
      }
      debounceTimers.current[field as string] = setTimeout(() => {
        const error = validateField(field, value);
        setErrors((prev) => {
          const newErrors = { ...prev };
          if (error) {
            newErrors[field as string] = error;
            // Logging
            logValidationFailure({
              field: String(field),
              value: redactIfSensitive(String(field), value, sensitiveFields),
              rule: error,
              correlationId,
            });
          } else {
            delete newErrors[field as string];
          }
          return newErrors;
        });
      }, 400);
    },
    [validateField, sensitiveFields, correlationId]
  );

  // --- Immediate Validation on Blur ---

  const handleBlur = useCallback(
    (field: keyof T) => {
      setTouched((prev) => ({ ...prev, [field]: true }));
      if (debounceTimers.current[field as string]) {
        clearTimeout(debounceTimers.current[field as string]);
      }
      const error = validateField(field, values[field]);
      setErrors((prev) => {
        const newErrors = { ...prev };
        if (error) {
          newErrors[field as string] = error;
          logValidationFailure({
            field: String(field),
            value: redactIfSensitive(String(field), values[field], sensitiveFields),
            rule: error,
            correlationId,
          });
        } else {
          delete newErrors[field as string];
        }
        return newErrors;
      });
    },
    [validateField, values, sensitiveFields, correlationId]
  );

  // --- Validate All Fields (e.g., on submit) ---

  const validateForm = useCallback(() => {
    const newErrors = validateAllFields(values);
    setErrors(newErrors);
    setTouched(
      Object.keys(validationSchema).reduce(
        (acc, field) => ({ ...acc, [field]: true }),
        {}
      )
    );
    setErrorSummary(
      Object.entries(newErrors).map(([field, msg]) => `${msg}`)
    );
    setIsValid(Object.keys(newErrors).length === 0);
    // Log all errors
    Object.entries(newErrors).forEach(([field, msg]) => {
      logValidationFailure({
        field,
        value: redactIfSensitive(field, values[field], sensitiveFields),
        rule: msg || "",
        correlationId,
      });
    });
    return Object.keys(newErrors).length === 0;
  }, [validateAllFields, values, validationSchema, sensitiveFields, correlationId]);

  // --- Update isValid and error summary on errors change ---

  useEffect(() => {
    setIsValid(Object.keys(errors).length === 0);
    setErrorSummary(
      Object.entries(errors).map(([field, msg]) => `${msg}`)
    );
  }, [errors]);

  // --- Accessibility Props ---

  const ariaProps = useCallback(
    (field: keyof T) => {
      const hasError = !!errors[field as string];
      return {
        "aria-invalid": hasError,
        "aria-describedby": hasError ? `${String(field)}-error` : undefined,
      };
    },
    [errors]
  );

  // --- Cleanup on unmount ---
  useEffect(() => {
    return () => {
      Object.values(debounceTimers.current).forEach(clearTimeout);
    };
  }, []);

  return {
    values,
    setFieldValue,
    errors,
    isValid,
    touched,
    handleBlur,
    validateForm,
    ariaProps,
    errorSummary,
    correlationId,
  };
}