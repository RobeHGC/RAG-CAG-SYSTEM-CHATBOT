# Database Schema Evolution Process

## Overview

This document outlines the process for evolving database schemas in the Bot Provisional project across PostgreSQL, Redis, and Neo4j databases.

## Migration System Architecture

### Core Components

1. **Migration Manager** (`scripts/migrate_database.py`)
   - Tracks migration history in PostgreSQL
   - Executes migrations across all databases
   - Provides rollback capabilities

2. **Migration History Table**
   ```sql
   CREATE TABLE migration_history (
       id SERIAL PRIMARY KEY,
       migration_id VARCHAR(255) UNIQUE NOT NULL,
       migration_name VARCHAR(255) NOT NULL,
       database_name VARCHAR(50) NOT NULL,
       version VARCHAR(50) NOT NULL,
       applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       applied_by VARCHAR(255) DEFAULT 'system',
       checksum VARCHAR(64) NOT NULL,
       success BOOLEAN DEFAULT TRUE,
       error_message TEXT,
       rollback_available BOOLEAN DEFAULT FALSE
   );
   ```

3. **Migration Definition Structure**
   ```python
   @dataclass
   class Migration:
       id: str                    # Unique migration identifier
       name: str                  # Human-readable name
       description: str           # What this migration does
       database: str              # 'postgres', 'redis', 'neo4j', or 'all'
       version: str               # Target version
       sql_script: Optional[str]  # SQL/Cypher for postgres/neo4j
       python_function: Optional[str]  # Python code for redis
       rollback_script: Optional[str]  # Rollback instructions
       dependencies: List[str]    # Required previous migrations
   ```

## Migration Workflow

### 1. Planning Phase

#### Schema Change Requirements
- **Identify the need** for schema changes
- **Assess impact** on existing data
- **Plan migration strategy** (additive vs. breaking changes)
- **Determine rollback requirements**

#### Migration Design
- **Create migration ID** using format: `{number}_{descriptive_name}`
- **Write migration scripts** for each affected database
- **Design rollback procedures** when possible
- **Document breaking changes** and data transformation needs

### 2. Development Phase

#### Creating New Migrations

1. **Add migration to `load_migrations()` function** in `migrate_database.py`:

```python
migrations.append(Migration(
    id="003_add_user_preferences",
    name="Add user preferences table",
    description="Add table to store user-specific settings and preferences",
    database="postgres",
    version="1.2.0",
    sql_script="""
    CREATE TABLE IF NOT EXISTS user_preferences (
        id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        preference_key VARCHAR(100) NOT NULL,
        preference_value JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE(user_id, preference_key)
    );
    
    CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id 
    ON user_preferences(user_id);
    """,
    rollback_script="DROP TABLE IF EXISTS user_preferences;",
    dependencies=["001_initial_schema", "002_add_indexes"]
))
```

2. **For Redis migrations** (Python-based):

```python
migrations.append(Migration(
    id="004_update_redis_config",
    name="Update Redis configuration",
    description="Add new cache namespaces and configuration keys",
    database="redis",
    version="1.2.0",
    python_function="""
# Update Redis configuration
redis_client = self.db_manager.redis.client

# Add new configuration keys
redis_client.hset('config:features', 
    'new_feature_enabled', 'true',
    'cache_ttl_extended', '7200'
)

# Create new namespace markers
redis_client.hset('app:namespaces', 'cache:extended', 'initialized')

print_status("Redis configuration updated for v1.2.0", "success")
"""
))
```

3. **For Neo4j migrations** (Cypher-based):

```python
migrations.append(Migration(
    id="005_add_node_properties",
    name="Add properties to existing nodes",
    description="Add new properties to User and Conversation nodes",
    database="neo4j", 
    version="1.2.0",
    sql_script="""
    // Add new properties to User nodes
    MATCH (u:User)
    WHERE u.last_login IS NULL
    SET u.last_login = datetime(),
        u.preferences = {},
        u.activity_score = 0.0;
    
    // Add new properties to Conversation nodes
    MATCH (c:Conversation)
    WHERE c.sentiment IS NULL
    SET c.sentiment = 'neutral',
        c.complexity_score = 0.5;
    """
))
```

#### Migration Best Practices

1. **Use descriptive IDs**: `001_initial_schema`, `002_add_indexes`, `003_user_preferences`

2. **Make migrations idempotent**: Use `IF NOT EXISTS`, `MERGE`, or conditional checks

3. **Handle dependencies**: List required previous migrations

4. **Include rollback scripts** when possible

5. **Test thoroughly** in development environment

### 3. Testing Phase

#### Pre-Migration Testing

1. **Backup databases** before testing:
```bash
# PostgreSQL backup
pg_dump bot_provisional > backup_pre_migration.sql

# Neo4j backup
neo4j-admin dump --database=neo4j --to=backup_pre_migration.dump
```

2. **Run migration in dry-run mode**:
```bash
python scripts/migrate_database.py --action migrate --dry-run
```

3. **Execute migration**:
```bash
python scripts/migrate_database.py --action migrate
```

4. **Verify migration success**:
```bash
python scripts/migrate_database.py --action status
python scripts/check_connections.py
```

#### Post-Migration Testing

1. **Run application tests**:
```bash
pytest tests/test_databases.py -v
pytest tests/ -k "not integration" -v
```

2. **Test application functionality**:
```bash
python scripts/init_databases.py  # Should not fail
python scripts/check_connections.py  # Should show healthy
```

3. **Verify data integrity**:
```bash
# Check record counts, data consistency, etc.
python -c "
from src.common.database import DatabaseManager
db = DatabaseManager()
# Run data verification queries
"
```

### 4. Deployment Phase

#### Production Migration Process

1. **Schedule maintenance window** if breaking changes

2. **Create production backups**:
```bash
# Automated backup before migration
./scripts/backup_production.sh
```

3. **Deploy migration code**:
```bash
git pull origin master
```

4. **Run migrations**:
```bash
# Check current status
python scripts/migrate_database.py --action status

# Execute pending migrations
python scripts/migrate_database.py --action migrate
```

5. **Verify deployment**:
```bash
python scripts/check_connections.py
# Run smoke tests
```

6. **Monitor application** for errors or performance issues

## Database-Specific Evolution Patterns

### PostgreSQL Schema Evolution

#### Additive Changes (Safe)
- Adding new tables
- Adding new columns (with defaults)
- Adding new indexes
- Adding new constraints (non-conflicting)

```sql
-- Safe: Adding new column with default
ALTER TABLE fine_tuning.conversations 
ADD COLUMN IF NOT EXISTS sentiment VARCHAR(20) DEFAULT 'neutral';

-- Safe: Adding new index
CREATE INDEX IF NOT EXISTS idx_conversations_sentiment 
ON fine_tuning.conversations(sentiment);
```

#### Breaking Changes (Require Care)
- Dropping columns
- Changing column types
- Renaming tables/columns
- Adding NOT NULL constraints to existing columns

```sql
-- Careful: Requires data migration
ALTER TABLE fine_tuning.conversations 
ALTER COLUMN quality_score TYPE NUMERIC(3,2);

-- Safer approach with new column + migration
ALTER TABLE fine_tuning.conversations 
ADD COLUMN quality_score_new NUMERIC(3,2);

UPDATE fine_tuning.conversations 
SET quality_score_new = quality_score::NUMERIC(3,2);

-- Later migration: drop old column
ALTER TABLE fine_tuning.conversations 
DROP COLUMN quality_score;

ALTER TABLE fine_tuning.conversations 
RENAME COLUMN quality_score_new TO quality_score;
```

### Redis Schema Evolution

#### Configuration Updates
```python
# Safe: Adding new configuration keys
redis_client.hset('config:features', 'new_feature', 'enabled')

# Safe: Adding new namespaces
redis_client.hset('app:namespaces', 'cache:new_feature', 'initialized')
```

#### Data Structure Changes
```python
# Careful: Changing existing data structures
# Get existing data
old_data = redis_client.hgetall('metrics:totals')

# Transform data
new_data = transform_metrics_structure(old_data)

# Atomic replacement
pipeline = redis_client.pipeline()
pipeline.delete('metrics:totals')
pipeline.hset('metrics:totals', mapping=new_data)
pipeline.execute()
```

### Neo4j Schema Evolution

#### Safe Changes
- Adding new node labels
- Adding new properties to existing nodes
- Adding new relationship types
- Creating new indexes

```cypher
// Safe: Adding new properties
MATCH (u:User)
SET u.created_version = '1.2.0'
WHERE u.created_version IS NULL;

// Safe: Adding new labels
MATCH (u:User {type: 'premium'})
SET u:PremiumUser;
```

#### Complex Changes
- Changing relationship structures
- Merging/splitting node types
- Complex data transformations

```cypher
// Complex: Restructuring relationships
MATCH (u:User)-[r:HAS_CONVERSATION]->(c:Conversation)
CREATE (u)-[:PARTICIPATED_IN {role: 'participant', started_at: r.created_at}]->(c)
DELETE r;
```

## Version Management

### Semantic Versioning for Schemas

- **Major version** (1.0.0 → 2.0.0): Breaking changes requiring data migration
- **Minor version** (1.0.0 → 1.1.0): Additive changes, backward compatible
- **Patch version** (1.0.0 → 1.0.1): Bug fixes, constraint updates

### Schema Version Tracking

```sql
-- Track schema versions in PostgreSQL
CREATE TABLE IF NOT EXISTS schema_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) UNIQUE NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    description TEXT,
    breaking_changes BOOLEAN DEFAULT FALSE
);
```

```python
# Track in Redis
redis_client.hset('app:metadata', 'schema_version', '1.2.0')
```

```cypher
// Track in Neo4j
MERGE (v:SchemaVersion {version: '1.2.0'})
ON CREATE SET v.applied_at = datetime(), v.description = 'Added user preferences'
```

## Rollback Procedures

### Automatic Rollback
```bash
# If rollback script is available
python scripts/migrate_database.py --action rollback --migration-id 003_user_preferences
```

### Manual Rollback
1. **Stop application** to prevent new data
2. **Restore from backup** if necessary
3. **Run rollback scripts** manually
4. **Update migration history**
5. **Restart application**

### Point-in-Time Recovery
```bash
# PostgreSQL point-in-time recovery
pg_restore --clean --if-exists backup_pre_migration.sql

# Neo4j restore
neo4j-admin load --database=neo4j --from=backup_pre_migration.dump
```

## Monitoring and Maintenance

### Migration Health Checks
```bash
# Daily check for failed migrations
python scripts/migrate_database.py --action status | grep -i failed

# Weekly schema validation
python scripts/validate_schema.py --all-databases
```

### Performance Monitoring
- **Monitor query performance** after schema changes
- **Check index usage** and effectiveness
- **Monitor database size** growth
- **Track migration execution times**

### Documentation Updates
- **Update API documentation** for schema changes
- **Update data models** in code
- **Update ETL processes** if affected
- **Notify team** of breaking changes

## Tools and Scripts

### Available Commands

```bash
# Check migration status
python scripts/migrate_database.py --action status

# Run pending migrations
python scripts/migrate_database.py --action migrate

# Dry run (show what would be executed)
python scripts/migrate_database.py --action migrate --dry-run

# Run specific migration
python scripts/migrate_database.py --action migrate --migration-id 003_user_preferences

# Check database health
python scripts/check_connections.py

# Initialize databases (idempotent)
python scripts/init_databases.py
```

### Integration with CI/CD

```yaml
# Example GitHub Actions workflow
- name: Run Database Migrations
  run: |
    python scripts/migrate_database.py --action status
    python scripts/migrate_database.py --action migrate
    python scripts/check_connections.py

- name: Run Database Tests
  run: |
    pytest tests/test_databases.py -v
```

## Troubleshooting Common Issues

### Migration Failures
1. **Check dependencies**: Ensure prerequisite migrations are applied
2. **Verify permissions**: Database user has required privileges
3. **Check syntax**: SQL/Cypher syntax errors
4. **Resource constraints**: Disk space, memory, timeouts

### Data Consistency Issues
1. **Run integrity checks** after migrations
2. **Compare row counts** before/after
3. **Validate foreign key relationships**
4. **Check constraint violations**

### Performance Degradation
1. **Analyze query plans** after schema changes
2. **Update statistics** on affected tables
3. **Consider index optimization**
4. **Monitor resource utilization**

## Best Practices Summary

1. ✅ **Always backup** before migrations
2. ✅ **Test thoroughly** in development
3. ✅ **Make migrations idempotent**
4. ✅ **Use descriptive naming**
5. ✅ **Document breaking changes**
6. ✅ **Monitor after deployment**
7. ✅ **Plan rollback procedures**
8. ✅ **Track schema versions**
9. ✅ **Automate where possible**
10. ✅ **Communicate changes** to team

This process ensures safe, reliable, and trackable evolution of the Bot Provisional database schemas across all three database systems.