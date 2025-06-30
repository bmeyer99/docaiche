/**
 * Field path utilities for tracking dirty fields
 */

import { FIELD_PATH_PREFIXES } from '../constants';

export function createProviderFieldPath(providerId: string, fieldName: string): string {
  return `${FIELD_PATH_PREFIXES.PROVIDER}${providerId}.${fieldName}`;
}

export function createModelSelectionFieldPath(fieldName: string): string {
  return `${FIELD_PATH_PREFIXES.MODEL_SELECTION}${fieldName}`;
}

export function parseProviderFieldPath(fieldPath: string): { providerId: string; fieldName: string } | null {
  if (!fieldPath.startsWith(FIELD_PATH_PREFIXES.PROVIDER)) {
    return null;
  }
  
  const parts = fieldPath.substring(FIELD_PATH_PREFIXES.PROVIDER.length).split('.');
  if (parts.length < 2) {
    return null;
  }
  
  return {
    providerId: parts[0],
    fieldName: parts.slice(1).join('.'),
  };
}

export function isProviderFieldPath(fieldPath: string): boolean {
  return fieldPath.startsWith(FIELD_PATH_PREFIXES.PROVIDER);
}

export function isModelSelectionFieldPath(fieldPath: string): boolean {
  return fieldPath.startsWith(FIELD_PATH_PREFIXES.MODEL_SELECTION);
}