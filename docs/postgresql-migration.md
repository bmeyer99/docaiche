# PostgreSQL Migration Guide

This guide explains how to migrate DocAIche from SQLite to PostgreSQL for improved performance, concurrency, and scalability.

## Why PostgreSQL?

- **Better Concurrency**: PostgreSQL handles multiple concurrent writes efficiently, unlike SQLite
- **JSONB Support**: Native binary JSON storage with indexing for better performance
- **Production Ready**: Better suited for production workloads with proper connection pooling
- **Advanced Features**: Full-text search, partitioning, and extensions like TimescaleDB

## Migration Steps

### 1. Update Environment

The system now uses PostgreSQL by default. The `docker-compose.yml` includes a PostgreSQL service configured with:

- Database: `docaiche`
- User: `docaiche`
- Password: Set via `POSTGRES_PASSWORD` environment variable (default: `docaiche-secure-password-2025`)
- Optimized settings for DocAIche workload

### 2. Start PostgreSQL

```bash
# Start only the PostgreSQL service first
docker-compose up -d postgres

# Verify it's running
docker-compose ps postgres
docker-compose logs postgres
```

### 3. Initialize Database Schema

The database schema is automatically initialized when the API service starts. You can also manually initialize:

```bash
# Initialize PostgreSQL schema
docker-compose run --rm api python src/database/init_db.py
```

### 4. Migrate Existing Data (Optional)

If you have existing data in SQLite, use the migration script:

```bash
# Run migration from existing SQLite database
docker-compose run --rm -v /path/to/sqlite/db:/sqlite api python migrate_to_postgres.py \
  --sqlite-path /sqlite/docaiche.db

# Verify migration
docker-compose run --rm api python migrate_to_postgres.py \
  --sqlite-path /sqlite/docaiche.db \
  --verify-only
```

### 5. Start All Services

```bash
# Rebuild and start all services
docker-compose down
docker-compose build api
docker-compose up -d
```

## Configuration

### Environment Variables

Set these in your `.env` file or environment:

```bash
# PostgreSQL connection
DATABASE_URL=postgresql+asyncpg://docaiche:your-password@postgres:5432/docaiche
POSTGRES_PASSWORD=your-secure-password

# PostgreSQL connection details (used by some scripts)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=docaiche
POSTGRES_USER=docaiche
```

### Connection Pooling

The application uses SQLAlchemy with asyncpg for optimal performance:

- Pool size: 10 connections
- Max overflow: 20 connections
- Pool recycle: 3600 seconds
- Pre-ping enabled for connection health

## Database Features Used

### JSONB Columns

All JSON data is stored as JSONB in PostgreSQL for better performance:

- Search results
- Configuration values
- Metadata fields
- Audit logs

### Indexes

PostgreSQL-specific indexes are created:

- GIN indexes on JSONB columns for fast JSON queries
- B-tree indexes on frequently queried columns
- Composite indexes for complex queries

### Enums

PostgreSQL enum types are used for:

- `processing_status`: pending, processing, completed, failed, flagged, pending_context7
- `feedback_type`: helpful, not_helpful, outdated, incorrect, flag
- `signal_type`: click, dwell_time, copy, share, scroll_depth
- `source_type`: github, web, api
- `rate_limit_status`: normal, limited, exhausted

## Performance Tuning

The PostgreSQL container is configured with:

```yaml
# Memory settings
shared_buffers: 256MB
effective_cache_size: 1GB
work_mem: 4MB

# Write performance
checkpoint_completion_target: 0.9
wal_buffers: 16MB
min_wal_size: 1GB
max_wal_size: 4GB

# Query performance
random_page_cost: 1.1 (optimized for SSD)
effective_io_concurrency: 200
max_parallel_workers: 8
```

## Monitoring

### Check Database Health

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U docaiche -d docaiche

# Check table sizes
\dt+

# Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

# Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Backup and Restore

```bash
# Backup
docker-compose exec postgres pg_dump -U docaiche docaiche > backup.sql

# Restore
docker-compose exec -T postgres psql -U docaiche docaiche < backup.sql
```

## Rollback to SQLite

If needed, you can rollback to SQLite by:

1. Setting `DATABASE_URL` to use SQLite:
   ```bash
   DATABASE_URL=sqlite+aiosqlite:///data/docaiche.db
   ```

2. Removing PostgreSQL-specific environment variables

3. Rebuilding and restarting services

## Troubleshooting

### Connection Issues

```bash
# Test connection
docker-compose exec postgres pg_isready -U docaiche -d docaiche

# Check logs
docker-compose logs postgres

# Verify environment variables
docker-compose exec api env | grep -E '(DATABASE_URL|POSTGRES)'
```

### Performance Issues

1. Check connection pool usage:
   ```sql
   SELECT count(*) FROM pg_stat_activity WHERE datname = 'docaiche';
   ```

2. Analyze slow queries:
   ```sql
   EXPLAIN ANALYZE <your-query>;
   ```

3. Update table statistics:
   ```sql
   ANALYZE;
   ```

### Migration Issues

If migration fails:

1. Check source SQLite file exists and is readable
2. Verify PostgreSQL is running and accessible
3. Check for data type incompatibilities in logs
4. Try migrating tables individually

## Best Practices

1. **Regular Backups**: Set up automated PostgreSQL backups
2. **Monitor Connections**: Watch for connection pool exhaustion
3. **Vacuum Regularly**: Run `VACUUM ANALYZE` periodically
4. **Index Maintenance**: Monitor index bloat and rebuild if needed
5. **Query Optimization**: Use `EXPLAIN ANALYZE` for slow queries