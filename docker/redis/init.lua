-- Redis Lua initialization script for Bot Provisional
-- This script sets up initial data structures and configuration keys

-- Set up application metadata
redis.call('HSET', 'app:metadata', 
    'name', 'Bot Provisional',
    'version', '0.1.0', 
    'initialized_at', redis.call('TIME')[1],
    'environment', 'development'
)

-- Create namespace keys for organized data storage
local namespaces = {
    'context:conversations',
    'context:memory',
    'session:active', 
    'session:history',
    'cache:llm_responses',
    'cache:user_data',
    'metrics:requests',
    'metrics:errors',
    'config:settings',
    'config:limits'
}

-- Initialize namespace markers
for i, namespace in ipairs(namespaces) do
    redis.call('HSET', 'app:namespaces', namespace, 'initialized')
end

-- Set up default configuration
redis.call('HSET', 'config:cache',
    'default_ttl', '3600',           -- 1 hour default TTL
    'conversation_ttl', '86400',     -- 24 hours for conversations
    'session_ttl', '604800',         -- 1 week for sessions
    'llm_response_ttl', '7200',      -- 2 hours for LLM responses
    'max_conversation_length', '100',
    'max_session_conversations', '1000'
)

-- Set up rate limiting configuration
redis.call('HSET', 'config:limits',
    'requests_per_minute', '60',
    'requests_per_hour', '1000', 
    'max_message_length', '4000',
    'max_context_length', '8000'
)

-- Initialize metrics counters
redis.call('HSET', 'metrics:totals',
    'total_conversations', '0',
    'total_messages', '0',
    'total_llm_calls', '0',
    'total_errors', '0',
    'cache_hits', '0',
    'cache_misses', '0'
)

-- Set up daily metrics key pattern (will be created as needed)
local today = os.date('%Y-%m-%d')
redis.call('HSET', 'metrics:daily:' .. today,
    'conversations', '0',
    'messages', '0', 
    'llm_calls', '0',
    'errors', '0',
    'unique_users', '0'
)

-- Set TTL for daily metrics (30 days)
redis.call('EXPIRE', 'metrics:daily:' .. today, 2592000)

-- Create sorted sets for leaderboards and analytics
redis.call('ZADD', 'analytics:active_users', 0, 'placeholder')
redis.call('ZADD', 'analytics:popular_topics', 0, 'placeholder')
redis.call('ZADD', 'analytics:conversation_lengths', 0, 'placeholder')

-- Set up health check key
redis.call('SET', 'health:status', 'healthy')
redis.call('EXPIRE', 'health:status', 300) -- 5 minutes

-- Initialize Celery-related structures for task queue
redis.call('HSET', 'celery:config',
    'broker_db', '1',
    'result_db', '2',
    'task_default_queue', 'bot_tasks',
    'task_default_exchange', 'bot_exchange',
    'task_default_routing_key', 'bot.default'
)

-- Set up user session tracking
redis.call('HSET', 'session:config',
    'cleanup_interval', '3600',      -- Clean up sessions every hour
    'max_idle_time', '1800',         -- 30 minutes max idle
    'max_session_time', '86400'      -- 24 hours max session length
)

-- Create indexes for fast lookups
redis.call('SADD', 'indexes:active_sessions', 'placeholder')
redis.call('SADD', 'indexes:conversation_topics', 'placeholder')

-- Set up cache warming keys (for frequently accessed data)
redis.call('HSET', 'cache:warm',
    'user_preferences', 'enabled',
    'conversation_starters', 'enabled',
    'common_responses', 'enabled'
)

-- Initialize circuit breaker state for external services
redis.call('HSET', 'circuit_breaker:openai',
    'state', 'closed',
    'failure_count', '0',
    'last_failure', '0',
    'threshold', '5'
)

redis.call('HSET', 'circuit_breaker:anthropic', 
    'state', 'closed',
    'failure_count', '0',
    'last_failure', '0',
    'threshold', '5'
)

-- Set up Redis Streams for real-time events (if using Redis 5.0+)
-- redis.call('XGROUP', 'CREATE', 'events:conversations', 'processors', '$', 'MKSTREAM')
-- redis.call('XGROUP', 'CREATE', 'events:errors', 'processors', '$', 'MKSTREAM')

-- Create backup and cleanup tracking
redis.call('HSET', 'maintenance:schedule',
    'last_cleanup', '0',
    'next_cleanup', redis.call('TIME')[1] + 86400, -- Tomorrow
    'cleanup_enabled', 'true'
)

-- Set up feature flags
redis.call('HSET', 'features:flags',
    'conversation_analytics', 'true',
    'cache_llm_responses', 'true',
    'user_preference_learning', 'true',
    'advanced_context_memory', 'true',
    'rate_limiting', 'true'
)

-- Initialize success marker
redis.call('SET', 'init:completed', 'true')
redis.call('SET', 'init:timestamp', redis.call('TIME')[1])

-- Log initialization completion
return "Bot Provisional Redis initialization completed successfully"