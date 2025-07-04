# Ollama Setup Guide for DocAIche

## Overview
DocAIche supports Ollama as a local LLM provider. Since DocAIche runs in Docker containers, there are some specific configuration requirements to connect to Ollama running on your host machine.

## Prerequisites
1. Install Ollama on your host machine: https://ollama.ai/download
2. Start Ollama service: `ollama serve` (usually starts automatically)
3. Pull at least one model: `ollama pull llama2` (or any other model)

## Configuration

### Linux
On Linux, Docker containers cannot access `host.docker.internal`. Use the Docker bridge gateway IP instead:

1. Find your Docker bridge gateway IP:
   ```bash
   docker network inspect docaiche_docaiche | jq -r '.[0].IPAM.Config[0].Gateway'
   ```
   Usually this is `172.17.0.1` or `172.18.0.1`

2. In the DocAIche admin UI, configure Ollama with:
   - Base URL: `http://172.18.0.1:11434` (replace with your gateway IP)

### macOS and Windows
On macOS and Windows, Docker Desktop provides `host.docker.internal`:

1. In the DocAIche admin UI, configure Ollama with:
   - Base URL: `http://host.docker.internal:11434`

## Troubleshooting

### Connection Failed
If you get "Cannot connect to Ollama" error:

1. Verify Ollama is running:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. Check Ollama is listening on all interfaces:
   ```bash
   # Look for the OLLAMA_HOST environment variable
   ps aux | grep ollama
   ```

3. If needed, start Ollama with:
   ```bash
   OLLAMA_HOST=0.0.0.0 ollama serve
   ```

### Firewall Issues
Some Linux distributions may block Docker containers from accessing host services:

1. Check if firewall is blocking:
   ```bash
   sudo iptables -L | grep 11434
   ```

2. Allow Docker containers to access Ollama:
   ```bash
   sudo iptables -A INPUT -p tcp --dport 11434 -j ACCEPT
   ```

### Test Connection
From within the API container:
```bash
# Replace with your appropriate IP
docker exec docaiche-api-1 curl http://172.18.0.1:11434/api/tags
```

## Security Considerations
- By default, Ollama only listens on localhost (127.0.0.1)
- Setting `OLLAMA_HOST=0.0.0.0` exposes Ollama to all network interfaces
- Consider using firewall rules to restrict access if needed