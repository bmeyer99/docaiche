// Simple delay utility for development/testing
export const delay = (ms: number) =>
  new Promise((resolve) => setTimeout(resolve, ms));