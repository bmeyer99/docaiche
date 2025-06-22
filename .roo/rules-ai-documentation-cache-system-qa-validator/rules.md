# AI Documentation Cache System - Roo Code Rules

## Project Context
This is an AI Documentation Cache System with microservices architecture using Docker, FastAPI, AnythingLLM, Ollama, Redis, and SQLite. The system follows PRD specifications (PRD-001 through PRD-013) for component implementation.

## Core Implementation Rules

### PRD Strict Adherence
- Implement ONLY what is explicitly stated in PRD specifications
- Never add features beyond what is documented in requirements
- Use exact data structures, APIs, and interfaces as specified
- When ambiguous, follow priority: Project Conformity > Security > Ease of Deployment > Simplicity > Efficiency

### Technology Stack (Required)
- **API Framework**: FastAPI with async/await for all I/O operations
- **Database**: SQLite for metadata, Redis for caching
- **Vector Database**: AnythingLLM via HTTP API
- **LLM Provider**: Ollama via HTTP API
- **Containerization**: Docker with Docker Compose
- **Background Tasks**: FastAPI BackgroundTasks or asyncio

### Security Requirements (Based on Secure Code Warrior AI Security Rules)
- Use parameterized queries to prevent SQL injection
- Validate all user inputs on both client and server side
- Implement proper authentication with JWT tokens
- Never store credentials in plain text or hardcode secrets
- Use HTTPS/TLS for all external communications
- Sanitize all external data before processing or storage
- Never run containers as root user
- Implement rate limiting to prevent abuse
- Use environment variables for configuration secrets

### Code Quality Standards
- Use type hints for all function parameters and returns
- Implement comprehensive error handling with structured exceptions
- Include structured logging (JSON format) for container environments
- Use Pydantic models for data validation and serialization
- Include health check endpoints (`/health`) for all services
- Follow async/await patterns consistently
- Achieve 80%+ test coverage for critical components

### Architecture Requirements
- Follow microservices pattern with clear component separation
- Maintain PRD component boundaries (001-013)
- Use dependency injection through FastAPI's system
- Implement connection pooling for databases and external services
- Include proper timeout handling for all external operations
- Support graceful shutdown with signal handling

### Docker & Deployment Standards
- Use multi-stage builds for optimized images
- Implement health checks for all containers
- Configure proper resource limits and networking
- Use proper volume management for persistent data
- Never include secrets in container images
- Use minimal, updated base images

### Testing Requirements
- Create unit tests for all business logic
- Include integration tests for API endpoints
- Add security tests for authentication and input validation
- Implement performance tests for load and resource usage
- Test error conditions and edge cases
- Mock external dependencies in tests

### Documentation Standards
- Include comprehensive docstrings for all functions and classes
- Maintain API documentation using OpenAPI/FastAPI auto-generation
- Document all configuration options and environment variables
- Provide clear setup, deployment, and troubleshooting guides
- Keep README files updated with current usage instructions

### AI/LLM Specific Security
- Sanitize prompts to prevent injection attacks
- Validate and sanitize LLM outputs before use
- Implement timeouts and resource limits for AI operations
- Use structured output parsing with error handling
- Monitor for prompt injection attempts
- Never expose raw AI model outputs without validation

## Component-Specific Guidelines

### API Components (PRD-001)
- Use FastAPI with Pydantic models for validation
- Implement authentication middleware for protected endpoints
- Include CORS configuration for web UI integration
- Return appropriate HTTP status codes and error formats

### Database Components (PRD-002)
- Use SQLite with proper connection pooling
- Implement Redis caching with appropriate TTL values
- Use database migrations for schema changes
- Include backup and restore procedures

### Vector Database (PRD-004)
- Handle AnythingLLM authentication and workspace management
- Implement retry logic for connection failures
- Support document operations with proper chunking
- Include health checks for service availability

### LLM Integration (PRD-005)
- Support Ollama model management and switching
- Implement prompt templates with response parsing
- Handle streaming responses when applicable
- Include model availability checks

### Content Processing (PRD-008)
- Implement content cleaning and standardization
- Support specified input formats with validation
- Use defined chunking strategies
- Extract metadata as specified in PRDs

## Error Handling Patterns
- Use structured exceptions with appropriate HTTP status codes
- Log errors with context for debugging without exposing sensitive information
- Implement retry logic for transient failures
- Provide helpful error messages for API consumers
- Never expose internal system details in error responses

## Performance Guidelines
- Use caching strategies where specified in PRDs
- Implement efficient algorithms prioritizing clarity over premature optimization
- Monitor resource usage in containerized environments
- Use connection pooling for external services
- Implement proper indexing for database queries

Remember: Focus on correctness, completeness, and PRD compliance rather than creative enhancements. Every implementation should be traceable back to specific PRD requirements.