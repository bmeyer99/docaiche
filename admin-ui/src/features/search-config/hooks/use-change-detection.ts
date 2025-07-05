import { useCallback, useRef, useState } from 'react';

export type ChangeSource = 'user' | 'system';

export interface ChangeEvent {
  source: ChangeSource;
  fieldPath: string;
  timestamp: number;
  oldValue?: any;
  newValue?: any;
}

export interface ChangeDetectionState {
  isDirty: boolean;
  lastUserChange: ChangeEvent | null;
  changeHistory: ChangeEvent[];
}

export interface UseChangeDetectionOptions {
  onUserChange?: (event: ChangeEvent) => void;
  onSystemChange?: (event: ChangeEvent) => void;
  maxHistorySize?: number;
}

export interface ChangeDetectionResult {
  // State
  isDirty: boolean;
  lastUserChange: ChangeEvent | null;
  changeHistory: ChangeEvent[];
  
  // Methods
  trackChange: (fieldPath: string, newValue: any, oldValue?: any, source?: ChangeSource) => void;
  createUserUpdater: <T>(fieldPath: string, updateFn: (value: T) => void) => (value: T) => void;
  createSystemUpdater: <T>(fieldPath: string, updateFn: (value: T) => void) => (value: T) => void;
  markAsClean: () => void;
  reset: () => void;
  
  // Utilities
  hasUserChanges: () => boolean;
  getChangesByField: (fieldPath: string) => ChangeEvent[];
  getChangesBySource: (source: ChangeSource) => ChangeEvent[];
}

export function useChangeDetection(options: UseChangeDetectionOptions = {}): ChangeDetectionResult {
  const { 
    onUserChange, 
    onSystemChange, 
    maxHistorySize = 100 
  } = options;

  const [state, setState] = useState<ChangeDetectionState>({
    isDirty: false,
    lastUserChange: null,
    changeHistory: []
  });

  // Use ref to store current values to avoid stale closures
  const stateRef = useRef(state);
  stateRef.current = state;

  const trackChange = useCallback((
    fieldPath: string,
    newValue: any,
    oldValue?: any,
    source: ChangeSource = 'user'
  ) => {
    const changeEvent: ChangeEvent = {
      source,
      fieldPath,
      timestamp: Date.now(),
      oldValue,
      newValue
    };

    setState(prevState => {
      const newHistory = [...prevState.changeHistory, changeEvent];
      
      // Limit history size
      if (newHistory.length > maxHistorySize) {
        newHistory.splice(0, newHistory.length - maxHistorySize);
      }

      const newState: ChangeDetectionState = {
        ...prevState,
        changeHistory: newHistory,
        isDirty: source === 'user' ? true : prevState.isDirty,
        lastUserChange: source === 'user' ? changeEvent : prevState.lastUserChange
      };

      return newState;
    });

    // Call appropriate callback
    if (source === 'user' && onUserChange) {
      onUserChange(changeEvent);
    } else if (source === 'system' && onSystemChange) {
      onSystemChange(changeEvent);
    }
  }, [maxHistorySize, onUserChange, onSystemChange]);

  const createUserUpdater = useCallback(<T,>(
    fieldPath: string,
    updateFn: (value: T) => void
  ) => {
    return (value: T) => {
      // Track the change as user-initiated
      trackChange(fieldPath, value, undefined, 'user');
      // Call the actual update function
      updateFn(value);
    };
  }, [trackChange]);

  const createSystemUpdater = useCallback(<T,>(
    fieldPath: string,
    updateFn: (value: T) => void
  ) => {
    return (value: T) => {
      // Track the change as system-initiated
      trackChange(fieldPath, value, undefined, 'system');
      // Call the actual update function
      updateFn(value);
    };
  }, [trackChange]);

  const markAsClean = useCallback(() => {
    setState(prevState => ({
      ...prevState,
      isDirty: false
    }));
  }, []);

  const reset = useCallback(() => {
    setState({
      isDirty: false,
      lastUserChange: null,
      changeHistory: []
    });
  }, []);

  const hasUserChanges = useCallback(() => {
    return stateRef.current.changeHistory.some(change => change.source === 'user');
  }, []);

  const getChangesByField = useCallback((fieldPath: string) => {
    return stateRef.current.changeHistory.filter(change => change.fieldPath === fieldPath);
  }, []);

  const getChangesBySource = useCallback((source: ChangeSource) => {
    return stateRef.current.changeHistory.filter(change => change.source === source);
  }, []);

  return {
    // State
    isDirty: state.isDirty,
    lastUserChange: state.lastUserChange,
    changeHistory: state.changeHistory,
    
    // Methods
    trackChange,
    createUserUpdater,
    createSystemUpdater,
    markAsClean,
    reset,
    
    // Utilities
    hasUserChanges,
    getChangesByField,
    getChangesBySource
  };
}

// Helper hook for form integration
export interface UseFormChangeDetectionOptions extends UseChangeDetectionOptions {
  onSave?: () => void;
}

export function useFormChangeDetection(options: UseFormChangeDetectionOptions = {}) {
  const { onSave, ...changeDetectionOptions } = options;
  
  const changeDetection = useChangeDetection(changeDetectionOptions);
  
  const handleSave = useCallback(() => {
    if (onSave) {
      onSave();
    }
    changeDetection.markAsClean();
  }, [onSave, changeDetection]);
  
  return {
    ...changeDetection,
    handleSave,
    canSave: changeDetection.isDirty,
    hasUnsavedChanges: changeDetection.isDirty
  };
}

// Utility function to create field-specific updaters
export function createFieldUpdaters<T extends Record<string, any>>(
  changeDetection: Pick<ChangeDetectionResult, 'createUserUpdater' | 'createSystemUpdater'>,
  setters: { [K in keyof T]: (value: T[K]) => void }
) {
  const userUpdaters = {} as { [K in keyof T]: (value: T[K]) => void };
  const systemUpdaters = {} as { [K in keyof T]: (value: T[K]) => void };
  
  for (const [field, setter] of Object.entries(setters) as [keyof T, (value: any) => void][]) {
    userUpdaters[field] = changeDetection.createUserUpdater(String(field), setter);
    systemUpdaters[field] = changeDetection.createSystemUpdater(String(field), setter);
  }
  
  return { userUpdaters, systemUpdaters };
}

// Example usage documentation
/**
 * Example usage in a component:
 * 
 * ```tsx
 * function MyConfigForm() {
 *   const [config, setConfig] = useState({ apiKey: '', model: '' });
 *   
 *   const changeDetection = useFormChangeDetection({
 *     onUserChange: (event) => {
 *       console.log('User changed:', event.fieldPath, event.newValue);
 *     }
 *   });
 *   
 *   // Create wrapped updaters
 *   const { userUpdaters, systemUpdaters } = createFieldUpdaters(changeDetection, {
 *     apiKey: (value) => setConfig(prev => ({ ...prev, apiKey: value })),
 *     model: (value) => setConfig(prev => ({ ...prev, model: value }))
 *   });
 *   
 *   // Load saved config (system update - won't mark as dirty)
 *   useEffect(() => {
 *     loadSavedConfig().then(saved => {
 *       systemUpdaters.apiKey(saved.apiKey);
 *       systemUpdaters.model(saved.model);
 *     });
 *   }, []);
 *   
 *   return (
 *     <form>
 *       <input 
 *         value={config.apiKey}
 *         onChange={(e) => userUpdaters.apiKey(e.target.value)} // User change - marks as dirty
 *       />
 *       <button 
 *         disabled={!changeDetection.canSave}
 *         onClick={changeDetection.handleSave}
 *       >
 *         Save
 *       </button>
 *       {changeDetection.hasUnsavedChanges && (
 *         <p>You have unsaved changes!</p>
 *       )}
 *     </form>
 *   );
 * }
 * ```
 */