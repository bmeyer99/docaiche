# DocaiChe MCP Implementation

## Overview

This directory contains the Model Context Protocol (MCP) implementation for DocaiChe, enabling AI agents to intelligently search and access documentation through a standardized interface.

## What is MCP?

The Model Context Protocol (MCP) is a standard protocol that enables AI assistants to securely access and interact with external systems. Our implementation provides:

- 🔍 **Intelligent Search**: AI-powered documentation discovery
- 📚 **Resource Access**: Structured access to documentation collections
- 🔒 **Secure Authentication**: OAuth 2.1 with fine-grained permissions
- 📊 **Rich Metadata**: Context-aware results with relevance scoring
- ⚡ **High Performance**: Caching and optimization for fast responses

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run the server
python -m src.mcp.main
```

See the [Quick Start Guide](docs/MCP_QUICKSTART.md) for detailed instructions.

## Documentation

- 📖 [API Reference](docs/MCP_API_REFERENCE.md) - Complete API documentation
- 🚀 [Deployment Guide](docs/MCP_DEPLOYMENT_GUIDE.md) - Production deployment instructions
- 👩‍💻 [Developer Guide](docs/MCP_DEVELOPER_GUIDE.md) - Extending and customizing
- 🏗️ [Architecture](docs/MCP_ARCHITECTURE.md) - System design and architecture

## Features

### Tools

- **docaiche/search** - Search documentation with intelligent ranking
- **docaiche/ingest** - Add new documentation with consent management
- **docaiche/feedback** - Submit feedback for continuous improvement

### Resources

- **docaiche://collections** - Browse available documentation collections
- **docaiche://status** - Check system health and metrics

### Security

- OAuth 2.1 authentication with JWT tokens
- Resource-based access control
- Rate limiting and threat detection
- Comprehensive audit logging

### Monitoring

- Prometheus metrics export
- Structured JSON logging
- Distributed tracing support
- Health check endpoints

## Examples

### Python Client

```python
from mcp import MCPClient

client = MCPClient(
    endpoint="https://mcp.docaiche.example.com",
    client_id="your_client_id",
    client_secret="your_client_secret"
)

# Search documentation
results = await client.call_tool(
    "docaiche/search",
    {"query": "authentication", "max_results": 10}
)

print(f"Found {results['total_count']} documents")
```

### JavaScript Client

```javascript
const client = new MCPClient({
    endpoint: 'https://mcp.docaiche.example.com',
    clientId: 'your_client_id',
    clientSecret: 'your_client_secret'
});

// Search documentation
const results = await client.callTool('docaiche/search', {
    query: 'authentication',
    maxResults: 10
});

console.log(`Found ${results.total_count} documents`);
```

See [examples/](examples/) for more client examples.

## Project Structure

```
src/mcp/
├── main.py              # Application entry point
├── server.py            # MCP server implementation
├── auth/                # Authentication (OAuth 2.1)
├── transport/           # HTTP/WebSocket transports
├── tools/               # MCP tools (search, ingest, feedback)
├── resources/           # MCP resources (collections, status)
├── security/            # Security framework
├── monitoring/          # Logging, metrics, tracing
└── adapters/            # Integration with DocaiChe core

tests/mcp/               # Comprehensive test suite
docs/                    # Documentation
examples/                # Client examples
deployment/              # Deployment configurations
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/mcp

# Run specific test
pytest tests/mcp/tools/test_search_tool.py
```

### Code Quality

```bash
# Format code
black src/

# Type checking
mypy src/

# Linting
pylint src/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.

## Deployment

### Docker

```bash
docker build -t docaiche-mcp .
docker run -p 8000:8000 --env-file .env docaiche-mcp
```

### Kubernetes

```bash
kubectl apply -f deployment/kubernetes/
```

### Production Checklist

- [ ] Generate strong secret keys
- [ ] Configure TLS/HTTPS
- [ ] Set up monitoring
- [ ] Configure rate limits
- [ ] Enable audit logging
- [ ] Set up backups

See the [Deployment Guide](docs/MCP_DEPLOYMENT_GUIDE.md) for detailed instructions.

## Performance

- **Search Latency**: < 100ms p95
- **Throughput**: 1000+ requests/second
- **Cache Hit Rate**: > 80%
- **Availability**: 99.9% SLA

## Security

- OAuth 2.1 with Resource Indicators (RFC 8707)
- JWT with RS256 signatures
- Rate limiting per client
- Comprehensive audit trail
- No sensitive data in logs

## License

This project is licensed under the same license as DocaiChe. See [LICENSE](../LICENSE) for details.

## Support

- 📧 Email: mcp-support@docaiche.example.com
- 💬 Slack: #docaiche-mcp
- 🐛 Issues: [GitHub Issues](https://github.com/your-org/docaiche/issues)
- 📖 Docs: [https://docs.docaiche.example.com/mcp](https://docs.docaiche.example.com/mcp)

## Acknowledgments

Built following the [Model Context Protocol](https://modelcontextprotocol.io) specification by Anthropic.