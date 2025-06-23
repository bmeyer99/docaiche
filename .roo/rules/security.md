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