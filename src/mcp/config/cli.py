"""
Configuration CLI Tool
=====================

Command-line interface for managing MCP server configuration.
"""

import asyncio
import click
import json
import yaml
from pathlib import Path
from typing import Optional

from .config_manager import ConfigurationManager, ConfigFormat
from .deployment import (
    Environment, DeploymentTarget, generate_deployment_files
)


@click.group()
@click.option('--config-dir', default='config', help='Configuration directory')
@click.option('--environment', default='development', help='Environment name')
@click.pass_context
def cli(ctx, config_dir: str, environment: str):
    """MCP Configuration Management CLI"""
    ctx.ensure_object(dict)
    ctx.obj['config_dir'] = config_dir
    ctx.obj['environment'] = environment


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize configuration directory with defaults."""
    config_dir = Path(ctx.obj['config_dir'])
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Create default configuration
    default_config = {
        "server": {
            "host": "0.0.0.0",
            "port": 8080,
            "workers": 4
        },
        "database": {
            "url": "postgresql://localhost/docaiche",
            "pool_size": 20
        },
        "redis": {
            "url": "redis://localhost:6379/0"
        },
        "security": {
            "require_authentication": True,
            "rate_limit_enabled": True,
            "rate_limit_requests": 60
        },
        "logging": {
            "level": "INFO",
            "format": "json"
        }
    }
    
    # Write default config
    config_file = config_dir / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False)
    
    click.echo(f"✓ Initialized configuration in {config_dir}")
    click.echo(f"✓ Created default configuration: {config_file}")
    
    # Create environment-specific configs
    for env in ['development', 'staging', 'production']:
        env_file = config_dir / f"{env}.yaml"
        env_config = {
            "environment": env,
            "debug": env == 'development',
            "ssl_enabled": env != 'development'
        }
        
        with open(env_file, 'w') as f:
            yaml.dump(env_config, f, default_flow_style=False)
        
        click.echo(f"✓ Created {env} configuration: {env_file}")


@cli.command()
@click.option('--key', required=True, help='Configuration key')
@click.pass_context
def get(ctx, key: str):
    """Get configuration value."""
    async def _get():
        manager = ConfigurationManager(
            base_path=ctx.obj['config_dir'],
            environment=ctx.obj['environment']
        )
        await manager.initialize()
        
        value = manager.get(key)
        if value is not None:
            if isinstance(value, (dict, list)):
                click.echo(json.dumps(value, indent=2))
            else:
                click.echo(value)
        else:
            click.echo(f"Configuration key '{key}' not found", err=True)
        
        await manager.close()
    
    asyncio.run(_get())


@cli.command()
@click.option('--key', required=True, help='Configuration key')
@click.option('--value', required=True, help='Configuration value')
@click.option('--persist', is_flag=True, help='Persist to file')
@click.pass_context
def set(ctx, key: str, value: str, persist: bool):
    """Set configuration value."""
    async def _set():
        manager = ConfigurationManager(
            base_path=ctx.obj['config_dir'],
            environment=ctx.obj['environment']
        )
        await manager.initialize()
        
        # Try to parse value as JSON
        try:
            parsed_value = json.loads(value)
        except:
            parsed_value = value
        
        await manager.set(key, parsed_value, persist=persist)
        click.echo(f"✓ Set {key} = {parsed_value}")
        
        if persist:
            click.echo(f"✓ Persisted to {ctx.obj['environment']}_override.yaml")
        
        await manager.close()
    
    asyncio.run(_set())


@cli.command()
@click.option('--format', type=click.Choice(['json', 'yaml']), default='yaml', help='Output format')
@click.option('--include-secrets', is_flag=True, help='Include secret values')
@click.pass_context
def export(ctx, format: str, include_secrets: bool):
    """Export configuration."""
    async def _export():
        manager = ConfigurationManager(
            base_path=ctx.obj['config_dir'],
            environment=ctx.obj['environment']
        )
        await manager.initialize()
        
        config_format = ConfigFormat.JSON if format == 'json' else ConfigFormat.YAML
        output = await manager.export_config(
            format=config_format,
            include_secrets=include_secrets
        )
        
        click.echo(output)
        
        await manager.close()
    
    asyncio.run(_export())


@cli.command()
@click.pass_context
def validate(ctx):
    """Validate configuration for deployment."""
    async def _validate():
        manager = ConfigurationManager(
            base_path=ctx.obj['config_dir'],
            environment=ctx.obj['environment']
        )
        await manager.initialize()
        
        report = await manager.validate_deployment_config()
        
        # Display report
        click.echo(f"\nConfiguration Validation Report")
        click.echo(f"Environment: {report['environment']}")
        click.echo(f"Timestamp: {report['timestamp']}")
        click.echo(f"Valid: {'✓' if report['valid'] else '✗'}")
        
        if report['errors']:
            click.echo("\nErrors:")
            for error in report['errors']:
                click.echo(f"  ✗ {error}", err=True)
        
        if report['warnings']:
            click.echo("\nWarnings:")
            for warning in report['warnings']:
                click.echo(f"  ⚠ {warning}")
        
        if report['valid'] and not report['warnings']:
            click.echo("\n✓ Configuration is valid for deployment")
        
        await manager.close()
        
        # Exit with error code if invalid
        if not report['valid']:
            ctx.exit(1)
    
    asyncio.run(_validate())


@cli.group()
def generate():
    """Generate deployment configurations."""
    pass


@generate.command()
@click.option('--environment', type=click.Choice(['development', 'staging', 'production']), 
              default='development', help='Target environment')
@click.option('--output-dir', default='deployment/docker', help='Output directory')
def docker(environment: str, output_dir: str):
    """Generate Docker deployment files."""
    env = Environment(environment)
    generate_deployment_files(env, DeploymentTarget.DOCKER, output_dir)
    click.echo(f"✓ Generated Docker deployment files in {output_dir}")


@generate.command()
@click.option('--environment', type=click.Choice(['development', 'staging', 'production']), 
              default='development', help='Target environment')
@click.option('--output-dir', default='deployment/k8s', help='Output directory')
def kubernetes(environment: str, output_dir: str):
    """Generate Kubernetes deployment files."""
    env = Environment(environment)
    generate_deployment_files(env, DeploymentTarget.KUBERNETES, output_dir)
    click.echo(f"✓ Generated Kubernetes deployment files in {output_dir}")


@generate.command()
@click.option('--environment', type=click.Choice(['development', 'staging', 'production']), 
              default='development', help='Target environment')
@click.option('--output-dir', default='deployment/compose', help='Output directory')
def compose(environment: str, output_dir: str):
    """Generate Docker Compose deployment files."""
    env = Environment(environment)
    generate_deployment_files(env, DeploymentTarget.DOCKER_COMPOSE, output_dir)
    click.echo(f"✓ Generated Docker Compose deployment files in {output_dir}")


@cli.command()
@click.pass_context
def show_env(ctx):
    """Show environment variables for current configuration."""
    async def _show_env():
        manager = ConfigurationManager(
            base_path=ctx.obj['config_dir'],
            environment=ctx.obj['environment']
        )
        await manager.initialize()
        
        # Convert to env vars
        config = manager.get_all()
        
        click.echo("# MCP Server Environment Variables")
        click.echo(f"# Environment: {ctx.obj['environment']}")
        click.echo("")
        
        for key, value in config.items():
            env_key = f"MCP_{key.upper().replace('.', '_')}"
            if isinstance(value, (dict, list)):
                env_value = json.dumps(value)
            else:
                env_value = str(value)
            
            # Mask secrets
            if manager.is_secret(key):
                env_value = "***REDACTED***"
            
            click.echo(f"export {env_key}=\"{env_value}\"")
        
        await manager.close()
    
    asyncio.run(_show_env())


if __name__ == '__main__':
    cli()