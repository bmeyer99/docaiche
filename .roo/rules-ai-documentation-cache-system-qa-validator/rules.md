# .roomodes - Universal Agent Definitions

- name: "Orchestrator"
  slug: "orchestrator"
  role: "Master coordinator for project architecture and task assignment. No automation - only work when explicitly assigned tasks."
  tools: ["read_file", "write_to_file", "list_files", "search_files", "web_search"]
  customInstructions: |
    - Assign tasks with clear success criteria and deliverables
    - Maintain architectural consistency across components
    - Priority: Requirements > Security > Maintainability > Performance

- name: "Implementation"
  slug: "implementation"
  role: "Expert engineer implementing clean, secure code following specifications exactly."
  tools: ["read_file", "write_to_file", "list_files", "search_files", "execute_command"]
  customInstructions: |
    - Implement exactly what is specified - no feature creep
    - Write secure, maintainable code with proper error handling
    - Include comprehensive tests and documentation

- name: "QA Validator"
  slug: "qa"
  role: "Quality assurance specialist creating tests first, validating implementations. Code passes only if ALL tests pass."
  tools: ["read_file", "write_to_file", "list_files", "search_files", "execute_command"]
  customInstructions: |
    - Create comprehensive test suites before validation
    - Test functionality, security, performance, integration
    - 100% test pass rate required - no partial compliance

- name: "Debugger"
  slug: "debugger"
  role: "System troubleshooter providing systematic analysis and actionable solutions."
  tools: ["read_file", "write_to_file", "list_files", "search_files", "execute_command", "web_search"]
  customInstructions: |
    - Perform root cause analysis with specific resolution steps
    - Document solutions and prevention measures
    - Test fixes thoroughly before completion

---

# .roo/rules/security.md - Universal Security Standards

## Input & Authentication
- Validate ALL inputs on server side - never trust client data
- Use parameterized queries - never string concatenation for SQL
- Implement proper authentication with secure session management
- Never store credentials in plain text or commit secrets to code
- Use HTTPS/TLS for all external communications
- Implement rate limiting to prevent abuse

## Data Protection
- Encrypt sensitive data in transit and at rest
- Use environment variables for configuration secrets
- Implement proper error handling without information leakage
- Use secure random generators for tokens and IDs
- Follow principle of least privilege for access controls

## Infrastructure
- Never run services with unnecessary privileges
- Use secure defaults and minimal configurations
- Keep dependencies updated and scan for vulnerabilities
- Implement proper logging without exposing sensitive data

---

# .roo/rules/code-quality.md - Universal Code Standards

## Core Principles
- Write self-documenting code with clear naming
- Implement comprehensive error handling and logging
- Follow single responsibility principle
- Use consistent formatting and style
- Include type hints/annotations where supported
- **Keep file sizes below 500 lines maximum** - split into smaller modules for maintainability
- Use only extreme exceptions for files exceeding 500 lines (must be justified and documented)

## Documentation
- Write clear docstrings for all functions and classes
- Maintain updated README with setup and usage
- Document configuration options and environment variables
- Comment complex business logic

## Testing
- Write unit tests for all business logic
- Include integration tests for external dependencies
- Test error conditions and edge cases
- Maintain meaningful test coverage for critical paths

## Performance
- Use efficient algorithms and appropriate data structures
- Implement proper connection pooling for external services
- Add caching only where beneficial and documented
- Monitor resource usage in production

---

# .roo/rules/architecture.md - Universal Design Standards

## Application Design
- Separate concerns with clear module boundaries
- Use dependency injection for loose coupling
- Design for testability and maintainability
- Implement proper configuration management

## API Design
- Use consistent RESTful conventions
- Implement proper HTTP status codes and error responses
- Include request/response validation
- Design with versioning in mind

## Data Management
- Design normalized schemas with proper relationships
- Use migrations for all schema changes
- Implement proper backup and recovery procedures
- Use transactions for multi-step operations

## Production Readiness
- Include health check endpoints
- Implement structured logging with correlation IDs
- Add monitoring for key metrics
- Design for graceful degradation and failure handling