/**
 * Shared store types for slice pattern
 */

import type { StateCreator } from 'zustand';
import type { ProviderSlice } from './slices/provider-slice';
import type { SystemSlice } from './slices/system-slice';
import type { UserSlice } from './slices/user-slice';
import type { UISlice } from './slices/ui-slice';
import type { RealtimeSlice } from './slices/realtime-slice';

// Combined store type
export type AppStore = ProviderSlice & SystemSlice & UserSlice & UISlice & RealtimeSlice;

// Immer middleware type helper
export type ImmerStateCreator<T> = StateCreator<
  AppStore,
  [["zustand/immer", never]],
  [],
  T
>;