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