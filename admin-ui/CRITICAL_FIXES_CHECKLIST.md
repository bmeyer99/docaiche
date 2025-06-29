# Critical Fixes Checklist
## Immediate Actions Required

### ✅ Completed
- [x] Remove duplicate `use-callback-ref.tsx` file

### 🔧 TODO - Critical (P0)

#### 1. Fix API Client Performance Issue
```typescript
// BAD - Current pattern in multiple components
const apiClient = new DocaicheApiClient(); // Creates new instance on every render!

// GOOD - Recommended fix
// In app/providers.tsx:
const ApiClientContext = createContext<DocaicheApiClient | null>(null);

export function ApiClientProvider({ children }: { children: React.ReactNode }) {
  const client = useMemo(() => new DocaicheApiClient(), []);
  return (
    <ApiClientContext.Provider value={client}>
      {children}
    </ApiClientContext.Provider>
  );
}

// In components:
const apiClient = useApiClient(); // Custom hook using useContext
```

#### 2. Add Global Error Boundary
```typescript
// In app/layout.tsx or create app/error.tsx:
'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-4">Something went wrong!</h2>
        <p className="text-muted-foreground mb-4">{error.message}</p>
        <button onClick={reset} className="btn btn-primary">
          Try again
        </button>
      </div>
    </div>
  );
}
```

#### 3. Fix ESLint Warnings
Run: `npm run lint` and fix all 29 warnings
- Remove unused imports
- Add missing dependencies to hooks
- Remove console.log statements

#### 4. Add Testing Infrastructure
```bash
# Install testing dependencies
npm install --save-dev jest @testing-library/react @testing-library/jest-dom jest-environment-jsdom

# Create jest.config.js
# Create __tests__ directories
# Add test scripts to package.json
```

### 📋 Components Needing Immediate Fixes

| Component | Issue | Fix |
|-----------|-------|-----|
| `overview-page.tsx` | LoadingSkeleton imported but not used | Remove import |
| `providers-config-page.tsx` | Badge imported but not used | Remove import |
| `analytics-page.tsx` | Missing loadAnalytics dependency | Add to useEffect deps |
| `content-upload-page.tsx` | Missing addFiles dependency | Add to useCallback deps |
| `app-sidebar.tsx` | isOpen assigned but not used | Remove or use variable |
| `profile-create-form.tsx` | setLoading never used | Implement loading state |

### 🚨 Files with Console.log Statements
1. Search for all: `grep -r "console.log" src/`
2. Remove or replace with proper logging

### ⚠️ Components Creating API Client on Every Render
1. `src/features/overview/components/overview-page.tsx`
2. `src/features/analytics/components/analytics-page.tsx`
3. `src/features/config/components/providers-config-page.tsx`
4. `src/features/content/components/content-search-page.tsx`
5. `src/features/content/components/content-upload-page.tsx`
6. `src/features/profile/components/profile-view-page.tsx`

### 🔍 Mock Data to Replace
1. `recent-sales.tsx:40` - Random results_count
2. Analytics time series data - Connect to real endpoints
3. Profile form countries/cities - Load from API or config

### 📝 Quick Fix Commands
```bash
# Remove all console.log statements
find src -name "*.tsx" -o -name "*.ts" | xargs sed -i '/console\.log/d'

# Find all TODO comments
grep -r "TODO" src/

# Check for any types
grep -r ": any" src/ --include="*.ts" --include="*.tsx"

# Run linter
npm run lint

# Build to check for errors
npm run build
```

### 🎯 Success Criteria
- [ ] Zero ESLint warnings
- [ ] No console.log in production
- [ ] API client singleton pattern implemented
- [ ] Global error boundary added
- [ ] All unused imports removed
- [ ] Basic test infrastructure in place
- [ ] All components handle loading/error states
- [ ] No TypeScript errors on build