/**
 * Centralized Design Tokens for Docaiche Admin Interface
 * 
 * This file contains all design tokens used throughout the application
 * to ensure consistency and easy maintenance.
 */

export const designTokens = {
  // Brand Colors
  colors: {
    // Primary brand colors (blue theme for tech/admin interface)
    brand: {
      50: '#eff6ff',
      100: '#dbeafe', 
      200: '#bfdbfe',
      300: '#93c5fd',
      400: '#60a5fa',
      500: '#3b82f6', // Primary brand color
      600: '#2563eb',
      700: '#1d4ed8',
      800: '#1e40af',
      900: '#1e3a8a',
      950: '#172554'
    },
    
    // Success colors (green)
    success: {
      50: '#f0fdf4',
      100: '#dcfce7',
      200: '#bbf7d0',
      300: '#86efac',
      400: '#4ade80',
      500: '#22c55e', // Primary success
      600: '#16a34a',
      700: '#15803d',
      800: '#166534',
      900: '#14532d'
    },
    
    // Warning colors (amber)
    warning: {
      50: '#fffbeb',
      100: '#fef3c7',
      200: '#fde68a',
      300: '#fcd34d',
      400: '#fbbf24',
      500: '#f59e0b', // Primary warning
      600: '#d97706',
      700: '#b45309',
      800: '#92400e',
      900: '#78350f'
    },
    
    // Error colors (red)
    error: {
      50: '#fef2f2',
      100: '#fee2e2',
      200: '#fecaca',
      300: '#fca5a5',
      400: '#f87171',
      500: '#ef4444', // Primary error
      600: '#dc2626',
      700: '#b91c1c',
      800: '#991b1b',
      900: '#7f1d1d'
    },
    
    // Neutral colors (gray scale)
    neutral: {
      50: '#f9fafb',
      100: '#f3f4f6',
      200: '#e5e7eb',
      300: '#d1d5db',
      400: '#9ca3af',
      500: '#6b7280', // Primary neutral
      600: '#4b5563',
      700: '#374151',
      800: '#1f2937',
      900: '#111827',
      950: '#030712'
    },
    
    // AI/Provider specific colors
    provider: {
      ollama: '#007bff',
      openai: '#00a67e',
      anthropic: '#d4a574',
      openrouter: '#6366f1'
    }
  },
  
  // Spacing scale (rem values)
  spacing: {
    xs: '0.25rem',  // 4px
    sm: '0.5rem',   // 8px
    md: '0.75rem',  // 12px
    lg: '1rem',     // 16px
    xl: '1.25rem',  // 20px
    '2xl': '1.5rem', // 24px
    '3xl': '2rem',   // 32px
    '4xl': '2.5rem', // 40px
    '5xl': '3rem',   // 48px
    '6xl': '4rem'    // 64px
  },
  
  // Typography scale
  typography: {
    fontFamily: {
      sans: ['Inter', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'Consolas', 'Monaco', 'monospace']
    },
    fontSize: {
      xs: '0.75rem',    // 12px
      sm: '0.875rem',   // 14px
      base: '1rem',     // 16px
      lg: '1.125rem',   // 18px
      xl: '1.25rem',    // 20px
      '2xl': '1.5rem',  // 24px
      '3xl': '1.875rem', // 30px
      '4xl': '2.25rem', // 36px
      '5xl': '3rem'     // 48px
    },
    fontWeight: {
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700'
    },
    lineHeight: {
      tight: '1.25',
      normal: '1.5',
      relaxed: '1.75'
    }
  },
  
  // Border radius scale
  borderRadius: {
    none: '0',
    sm: '0.25rem',   // 4px
    md: '0.375rem',  // 6px
    lg: '0.5rem',    // 8px
    xl: '0.75rem',   // 12px
    '2xl': '1rem',   // 16px
    full: '9999px'
  },
  
  // Shadow scale
  shadows: {
    xs: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    sm: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)'
  },
  
  // Transition timings
  transitions: {
    fast: '150ms',
    normal: '200ms',
    slow: '300ms'
  },
  
  // Z-index scale
  zIndex: {
    modal: 1000,
    dropdown: 900,
    tooltip: 800,
    header: 100,
    sidebar: 90
  }
} as const;

// Export individual token categories for easier imports
export const { colors, spacing, typography, borderRadius, shadows, transitions, zIndex } = designTokens;

// Theme variants for components
export const componentVariants = {
  button: {
    primary: {
      bg: colors.brand[500],
      hoverBg: colors.brand[600],
      text: 'white',
      border: colors.brand[500]
    },
    secondary: {
      bg: colors.neutral[100],
      hoverBg: colors.neutral[200],
      text: colors.neutral[900],
      border: colors.neutral[300]
    },
    success: {
      bg: colors.success[500],
      hoverBg: colors.success[600],
      text: 'white',
      border: colors.success[500]
    },
    warning: {
      bg: colors.warning[500],
      hoverBg: colors.warning[600],
      text: 'white',
      border: colors.warning[500]
    },
    error: {
      bg: colors.error[500],
      hoverBg: colors.error[600],
      text: 'white',
      border: colors.error[500]
    }
  },
  
  status: {
    healthy: colors.success[500],
    degraded: colors.warning[500],
    unhealthy: colors.error[500],
    unknown: colors.neutral[400]
  }
} as const;