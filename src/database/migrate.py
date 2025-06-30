"""
Database migration runner.

This module handles running database migrations in order.
"""

import sqlite3
import logging
import importlib.util
import os
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Handles database migration execution."""
    
    def __init__(self, db_path: str):
        """Initialize migration runner with database path."""
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent / "migrations"
        
    def get_current_version(self) -> str:
        """Get current database schema version."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT version_id FROM schema_versions 
                    ORDER BY applied_at DESC LIMIT 1
                """)
                result = cursor.fetchone()
                return result[0] if result else "0.0.0"
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return "0.0.0"
    
    def get_available_migrations(self) -> List[Dict[str, Any]]:
        """Get list of available migration files."""
        migrations = []
        
        if not self.migrations_dir.exists():
            return migrations
            
        for file_path in sorted(self.migrations_dir.glob("*.py")):
            if file_path.name == "__init__.py":
                continue
                
            # Load migration module
            spec = importlib.util.spec_from_file_location(
                f"migration_{file_path.stem}", 
                file_path
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if hasattr(module, 'get_migration_info'):
                    info = module.get_migration_info()
                    info['file_path'] = file_path
                    info['file_name'] = file_path.name
                    migrations.append(info)
                    
        return migrations
    
    def get_applied_versions(self) -> List[str]:
        """Get list of applied migration versions."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT version_id FROM schema_versions 
                    ORDER BY applied_at
                """)
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            return []
    
    def run_migrations(self, target_version: str = None) -> None:
        """Run pending migrations up to target version."""
        current_version = self.get_current_version()
        applied_versions = self.get_applied_versions()
        available_migrations = self.get_available_migrations()
        
        logger.info(f"Current database version: {current_version}")
        
        # Filter migrations to apply
        pending_migrations = []
        for migration in available_migrations:
            if migration['version'] not in applied_versions:
                if target_version is None or migration['version'] <= target_version:
                    pending_migrations.append(migration)
        
        if not pending_migrations:
            logger.info("No pending migrations to apply")
            return
            
        logger.info(f"Found {len(pending_migrations)} pending migrations")
        
        # Apply migrations in order
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            for migration in sorted(pending_migrations, key=lambda x: x['version']):
                logger.info(f"Applying migration {migration['version']}: {migration['description']}")
                
                try:
                    migration['upgrade_function'](conn)
                    conn.commit()
                    logger.info(f"Migration {migration['version']} applied successfully")
                except Exception as e:
                    logger.error(f"Failed to apply migration {migration['version']}: {e}")
                    conn.rollback()
                    raise
    
    def rollback_migration(self, version: str) -> None:
        """Rollback a specific migration."""
        applied_versions = self.get_applied_versions()
        
        if version not in applied_versions:
            logger.warning(f"Migration {version} is not applied")
            return
            
        # Find migration
        available_migrations = self.get_available_migrations()
        migration = None
        for m in available_migrations:
            if m['version'] == version:
                migration = m
                break
                
        if not migration:
            raise ValueError(f"Migration {version} not found")
            
        if 'downgrade_function' not in migration:
            raise ValueError(f"Migration {version} does not support rollback")
            
        logger.info(f"Rolling back migration {version}: {migration['description']}")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            try:
                migration['downgrade_function'](conn)
                conn.commit()
                logger.info(f"Migration {version} rolled back successfully")
            except Exception as e:
                logger.error(f"Failed to rollback migration {version}: {e}")
                conn.rollback()
                raise
    
    def show_status(self) -> None:
        """Show migration status."""
        current_version = self.get_current_version()
        applied_versions = self.get_applied_versions()
        available_migrations = self.get_available_migrations()
        
        print(f"\nDatabase: {self.db_path}")
        print(f"Current version: {current_version}")
        print(f"\nApplied migrations ({len(applied_versions)}):")
        
        for version in applied_versions:
            migration = next((m for m in available_migrations if m['version'] == version), None)
            if migration:
                print(f"  ✓ {version} - {migration['description']}")
            else:
                print(f"  ✓ {version} - (migration file not found)")
        
        # Show pending migrations
        pending = []
        for migration in available_migrations:
            if migration['version'] not in applied_versions:
                pending.append(migration)
                
        if pending:
            print(f"\nPending migrations ({len(pending)}):")
            for migration in sorted(pending, key=lambda x: x['version']):
                print(f"  ○ {migration['version']} - {migration['description']}")
        else:
            print("\nNo pending migrations")


def main():
    """CLI interface for database migrations."""
    import argparse
    from src.database.init_db import DatabaseInitializer
    
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument("--db-path", help="Database file path")
    parser.add_argument("--status", action="store_true", help="Show migration status")
    parser.add_argument("--migrate", action="store_true", help="Run pending migrations")
    parser.add_argument("--target", help="Target version to migrate to")
    parser.add_argument("--rollback", help="Rollback specific migration version")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Get database path
    if args.db_path:
        db_path = args.db_path
    else:
        initializer = DatabaseInitializer()
        db_path = initializer.get_database_path()
    
    runner = MigrationRunner(db_path)
    
    if args.status:
        runner.show_status()
    elif args.migrate:
        runner.run_migrations(target_version=args.target)
    elif args.rollback:
        runner.rollback_migration(args.rollback)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()