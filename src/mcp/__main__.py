"""
MCP Server Main Entry Point
===========================

Command-line interface and main entry point for running the MCP server.
Provides configuration loading, environment setup, and server lifecycle management.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import Optional
import argparse
import json
import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.mcp.server import run_server
from src.mcp.config import MCPServerConfig, MCPTransportConfig


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level
        log_file: Optional log file path
    """
    # Configure log format
    log_format = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    
    # Basic configuration
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[]
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def load_config(config_file: Optional[str] = None) -> MCPServerConfig:
    """
    Load server configuration from file or environment.
    
    Args:
        config_file: Configuration file path
        
    Returns:
        Server configuration
    """
    config_data = {}
    
    # Load from file if provided
    if config_file and Path(config_file).exists():
        with open(config_file, 'r') as f:
            if config_file.endswith('.json'):
                config_data = json.load(f)
            elif config_file.endswith(('.yml', '.yaml')):
                config_data = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported config format: {config_file}")
    
    # Override with environment variables
    env_mappings = {
        "MCP_SERVER_NAME": "server_name",
        "MCP_BIND_HOST": "transport_config.bind_host",
        "MCP_BIND_PORT": "transport_config.bind_port",
        "MCP_AUTH_REQUIRED": "require_authentication",
        "MCP_OAUTH_CLIENT_ID": "oauth_client_id",
        "MCP_OAUTH_CLIENT_SECRET": "oauth_client_secret",
        "MCP_LOG_LEVEL": "log_level",
        "MCP_MAX_CONNECTIONS": "transport_config.max_connections",
        "MCP_COMPRESSION_ENABLED": "transport_config.compression_enabled"
    }
    
    for env_var, config_path in env_mappings.items():
        value = os.environ.get(env_var)
        if value is not None:
            # Handle nested paths
            parts = config_path.split('.')
            current = config_data
            
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Convert value types
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            
            current[parts[-1]] = value
    
    # Create transport config if needed
    if 'transport_config' in config_data:
        config_data['transport_config'] = MCPTransportConfig(**config_data['transport_config'])
    
    return MCPServerConfig(**config_data)


def create_arg_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="DocaiChe MCP Server - AI Documentation Cache with Model Context Protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default configuration
  python -m src.mcp
  
  # Run with custom config file
  python -m src.mcp --config config.json
  
  # Run with specific host and port
  python -m src.mcp --host 0.0.0.0 --port 8080
  
  # Run with debug logging
  python -m src.mcp --log-level DEBUG
  
  # Run without authentication (development)
  python -m src.mcp --no-auth

Environment Variables:
  MCP_SERVER_NAME          Server name
  MCP_BIND_HOST            Bind host (default: localhost)
  MCP_BIND_PORT            Bind port (default: 3000)
  MCP_AUTH_REQUIRED        Require authentication (true/false)
  MCP_OAUTH_CLIENT_ID      OAuth client ID
  MCP_OAUTH_CLIENT_SECRET  OAuth client secret
  MCP_LOG_LEVEL            Log level (DEBUG/INFO/WARNING/ERROR)
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        help='Configuration file (JSON or YAML)',
        type=str,
        default=None
    )
    
    parser.add_argument(
        '--host',
        help='Bind host address',
        type=str,
        default=None
    )
    
    parser.add_argument(
        '--port',
        help='Bind port number',
        type=int,
        default=None
    )
    
    parser.add_argument(
        '--log-level',
        help='Logging level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO'
    )
    
    parser.add_argument(
        '--log-file',
        help='Log file path',
        type=str,
        default=None
    )
    
    parser.add_argument(
        '--no-auth',
        help='Disable authentication (development only)',
        action='store_true',
        default=False
    )
    
    parser.add_argument(
        '--max-connections',
        help='Maximum concurrent connections',
        type=int,
        default=None
    )
    
    parser.add_argument(
        '--compression',
        help='Enable compression',
        action='store_true',
        default=None
    )
    
    parser.add_argument(
        '--version', '-v',
        help='Show version information',
        action='store_true',
        default=False
    )
    
    return parser


async def main():
    """Main entry point."""
    # Parse arguments
    parser = create_arg_parser()
    args = parser.parse_args()
    
    # Show version if requested
    if args.version:
        from src.mcp.server import ServerMetadata
        metadata = ServerMetadata()
        print(f"{metadata.name} v{metadata.version}")
        print(f"Protocol Version: {metadata.protocol_version}")
        print(f"Vendor: {metadata.vendor}")
        return
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Apply command-line overrides
        if args.host:
            config.transport_config.bind_host = args.host
        if args.port:
            config.transport_config.bind_port = args.port
        if args.no_auth:
            config.require_authentication = False
        if args.max_connections is not None:
            config.transport_config.max_connections = args.max_connections
        if args.compression is not None:
            config.transport_config.compression_enabled = args.compression
        
        # Log startup information
        logger.info("=" * 60)
        logger.info("DocaiChe MCP Server Starting")
        logger.info("=" * 60)
        logger.info(f"Configuration:")
        logger.info(f"  Host: {config.transport_config.bind_host}")
        logger.info(f"  Port: {config.transport_config.bind_port}")
        logger.info(f"  Authentication: {'Enabled' if config.require_authentication else 'Disabled'}")
        logger.info(f"  Compression: {'Enabled' if config.transport_config.compression_enabled else 'Disabled'}")
        logger.info(f"  Max Connections: {config.transport_config.max_connections}")
        logger.info("=" * 60)
        
        # Run server
        await run_server(config)
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())