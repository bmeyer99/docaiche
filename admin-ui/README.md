# Docaiche Admin Interface

A modern, responsive administration interface for the Docaiche documentation search system built with Next.js 15, React 19, and shadcn/ui.

## Features

### 🎛️ Dashboard Overview
- Real-time system metrics and statistics
- Quick access to key information
- Activity feed with recent system events
- Provider status overview

### 🔧 AI Provider Management
- Support for multiple AI providers (Ollama, OpenAI, Anthropic, OpenRouter)
- Easy configuration interface with form validation
- Connection testing and status monitoring
- Provider-specific settings and customization

### 📊 System Health Monitoring
- Real-time service status tracking
- System resource monitoring (CPU, memory, storage)
- Auto-refresh functionality
- Performance metrics and uptime tracking

### 📁 Content Management
- Advanced document search with filtering
- Collection management and organization
- Drag-and-drop file upload interface
- Support for multiple file formats (PDF, MD, TXT, DOCX, HTML)
- Batch operations and progress tracking

### 📈 Analytics Dashboard
- Search analytics and usage patterns
- Content performance metrics
- System performance monitoring
- Provider usage statistics

## Technology Stack

- **Framework**: Next.js 15 with React 19
- **Styling**: Tailwind CSS v4 with shadcn/ui components
- **TypeScript**: Full type safety throughout
- **Architecture**: Centralized design system with API client
- **Docker**: Multi-stage builds for production deployment

## Project Structure

```
src/
├── app/                    # Next.js app router pages
│   ├── api/               # API routes (health check)
│   └── dashboard/         # Admin dashboard pages
├── components/            # Reusable UI components
│   └── ui/               # shadcn/ui components
├── features/             # Feature-specific components
│   ├── analytics/        # Analytics dashboard
│   ├── config/          # Configuration management
│   ├── content/         # Content management
│   ├── health/          # System health monitoring
│   ├── overview/        # Dashboard overview
│   └── profile/         # System information
├── lib/                 # Utility libraries
│   ├── config/          # API and provider configurations
│   ├── design-system/   # Design tokens and theming
│   └── utils/           # API client and utilities
└── constants/           # Navigation and constants
```

## Getting Started

### Development

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

### Production with Docker

The admin interface is included in the main docker-compose setup:

```bash
# From the root docaiche directory
docker-compose up admin-ui
```

The interface will be available at [http://localhost:3000](http://localhost:3000)

## Environment Variables

```env
NEXT_PUBLIC_API_URL=http://api:8000/api/v1
NEXT_PUBLIC_APP_NAME=Docaiche Admin
NEXT_PUBLIC_ENABLE_AUTH=false
NODE_ENV=production
```

## API Integration

The admin interface communicates with the Docaiche API through a centralized API client (`src/lib/utils/api-client.ts`) that provides:

- Automatic retry logic with exponential backoff
- Comprehensive error handling
- Request/response type safety
- RFC 7807 Problem Details support
- Connection testing utilities

## Key Features

### Responsive Design
- Mobile-first approach with responsive layouts
- Dark/light theme support
- Consistent design system with design tokens

### Real-time Updates
- Auto-refresh functionality for live data
- Real-time status indicators
- Progressive loading states

### User Experience
- Loading skeletons for better perceived performance
- Comprehensive error handling with user-friendly messages
- Keyboard shortcuts and accessibility features
- Intuitive navigation with breadcrumbs

### Developer Experience
- Full TypeScript coverage
- Centralized configuration management
- Modular component architecture
- Consistent code patterns and conventions

## Deployment

The admin interface is designed for deployment in lab environments behind Traefik with:

- No authentication requirements
- Docker networking integration
- Health check endpoints
- Production-optimized builds

## Contributing

1. Follow the existing code patterns and TypeScript conventions
2. Use the centralized API client for all backend communications
3. Leverage the design system tokens for consistent styling
4. Add appropriate loading states and error handling
5. Test across different screen sizes and themes

## Architecture Decisions

- **No Authentication**: Designed for secure lab environments
- **Centralized API Client**: Single source of truth for API interactions
- **Design Tokens**: Consistent theming and branding
- **Feature-based Organization**: Logical grouping of related functionality
- **Modern React Patterns**: Hooks, functional components, and TypeScript

## Performance Optimizations

- Next.js 15 optimizations (React 19, Server Components)
- Efficient bundle splitting and code organization
- Optimized loading states and progressive enhancement
- Docker multi-stage builds for minimal production images