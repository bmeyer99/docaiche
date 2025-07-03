Integration Architecture

  1. Create a New MCP Provider:
  # backend/src/mcp/providers/implementations/context7_provider.py
  class Context7Provider(BaseMCPProvider):
      """Fetches real-time documentation via Context7 MCP"""

  2. Integration Points:
  - Add to existing MCP external search providers
  - Leverage DocAIche's MCP infrastructure at /api/v1/mcp/
  - Use as enrichment source in SearchOrchestrator

  Implementation Plan

  Phase 1: Provider Implementation
  1. Create Context7Provider class extending BaseMCPProvider
  2. Implement MCP client to communicate with Context7 server
  3. Add configuration schema for Context7 settings

  Phase 2: MCP Protocol Integration
  1. Implement Context7's two main tools:
    - resolve-library-id: Map library names to Context7 IDs
    - get-library-docs: Fetch documentation with topic filtering
  2. Handle stdio transport for subprocess communication

  Phase 3: DocAIche Integration
  1. Add Context7 to provider registry
  2. Create enrichment strategy for library-specific queries
  3. Integrate with existing caching layer

  Phase 4: Configuration & Deployment
  1. Add Context7 configuration to config.yaml:
  mcp:
    external_search:
      providers:
        context7:
          enabled: true
          priority: 1
          command: "npx"
          args: ["-y", "@upstash/context7-mcp"]

  Phase 5: Enhancement Features
  1. Auto-detect library mentions in search queries
  2. Cache Context7 responses in Weaviate
  3. Version-aware documentation tracking

  Technical Implementation Details

  Key Components:
  - Use asyncio.create_subprocess_exec for stdio communication
  - Implement JSON-RPC 2.0 protocol for Context7 interaction
  - Add circuit breaker for Context7 availability
  - Monitor documentation freshness metrics

  Benefits:
  - Real-time, version-specific documentation
  - Complements DocAIche's static ingestion
  - Zero storage overhead for external docs
  - Automatic updates as libraries evolve