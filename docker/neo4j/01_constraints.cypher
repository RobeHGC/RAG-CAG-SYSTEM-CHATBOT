// Neo4j Constraints for Bot Provisional Knowledge Graph
// This script creates unique constraints and indexes for data integrity and performance

// ============================================================================
// UNIQUE CONSTRAINTS
// ============================================================================

// User constraints
CREATE CONSTRAINT user_id_unique IF NOT EXISTS 
FOR (u:User) REQUIRE u.id IS UNIQUE;

CREATE CONSTRAINT user_telegram_id_unique IF NOT EXISTS 
FOR (u:User) REQUIRE u.telegram_id IS UNIQUE;

// Conversation constraints  
CREATE CONSTRAINT conversation_id_unique IF NOT EXISTS
FOR (c:Conversation) REQUIRE c.id IS UNIQUE;

// Message constraints
CREATE CONSTRAINT message_id_unique IF NOT EXISTS
FOR (m:Message) REQUIRE m.id IS UNIQUE;

// Fact constraints
CREATE CONSTRAINT fact_id_unique IF NOT EXISTS
FOR (f:Fact) REQUIRE f.id IS UNIQUE;

// Memory constraints
CREATE CONSTRAINT memory_id_unique IF NOT EXISTS
FOR (m:Memory) REQUIRE m.id IS UNIQUE;

// Topic constraints
CREATE CONSTRAINT topic_name_unique IF NOT EXISTS
FOR (t:Topic) REQUIRE t.name IS UNIQUE;

// Entity constraints
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.id IS UNIQUE;

// Relationship constraints
CREATE CONSTRAINT relationship_id_unique IF NOT EXISTS
FOR (r:Relationship) REQUIRE r.id IS UNIQUE;

// Session constraints
CREATE CONSTRAINT session_id_unique IF NOT EXISTS
FOR (s:Session) REQUIRE s.id IS UNIQUE;

// Context constraints
CREATE CONSTRAINT context_id_unique IF NOT EXISTS
FOR (ctx:Context) REQUIRE ctx.id IS UNIQUE;

// ============================================================================
// PROPERTY EXISTENCE CONSTRAINTS
// ============================================================================

// Ensure critical properties exist
CREATE CONSTRAINT user_created_at_exists IF NOT EXISTS
FOR (u:User) REQUIRE u.created_at IS NOT NULL;

CREATE CONSTRAINT conversation_timestamp_exists IF NOT EXISTS
FOR (c:Conversation) REQUIRE c.timestamp IS NOT NULL;

CREATE CONSTRAINT message_content_exists IF NOT EXISTS
FOR (m:Message) REQUIRE m.content IS NOT NULL;

CREATE CONSTRAINT fact_content_exists IF NOT EXISTS
FOR (f:Fact) REQUIRE f.content IS NOT NULL;

CREATE CONSTRAINT topic_category_exists IF NOT EXISTS
FOR (t:Topic) REQUIRE t.category IS NOT NULL;

// ============================================================================
// INDEXES FOR PERFORMANCE
// ============================================================================

// User indexes
CREATE INDEX user_name_index IF NOT EXISTS
FOR (u:User) ON (u.name);

CREATE INDEX user_type_index IF NOT EXISTS
FOR (u:User) ON (u.type);

CREATE INDEX user_created_at_index IF NOT EXISTS
FOR (u:User) ON (u.created_at);

CREATE INDEX user_last_active_index IF NOT EXISTS
FOR (u:User) ON (u.last_active);

// Conversation indexes
CREATE INDEX conversation_timestamp_index IF NOT EXISTS
FOR (c:Conversation) ON (c.timestamp);

CREATE INDEX conversation_status_index IF NOT EXISTS
FOR (c:Conversation) ON (c.status);

CREATE INDEX conversation_user_id_index IF NOT EXISTS
FOR (c:Conversation) ON (c.user_id);

// Message indexes
CREATE INDEX message_timestamp_index IF NOT EXISTS
FOR (m:Message) ON (m.timestamp);

CREATE INDEX message_type_index IF NOT EXISTS
FOR (m:Message) ON (m.type);

CREATE INDEX message_sender_index IF NOT EXISTS
FOR (m:Message) ON (m.sender);

// Fact indexes
CREATE INDEX fact_timestamp_index IF NOT EXISTS
FOR (f:Fact) ON (f.timestamp);

CREATE INDEX fact_type_index IF NOT EXISTS
FOR (f:Fact) ON (f.type);

CREATE INDEX fact_confidence_index IF NOT EXISTS
FOR (f:Fact) ON (f.confidence);

CREATE INDEX fact_source_index IF NOT EXISTS
FOR (f:Fact) ON (f.source);

// Memory indexes
CREATE INDEX memory_type_index IF NOT EXISTS
FOR (m:Memory) ON (m.type);

CREATE INDEX memory_timestamp_index IF NOT EXISTS
FOR (m:Memory) ON (m.timestamp);

CREATE INDEX memory_importance_index IF NOT EXISTS
FOR (m:Memory) ON (m.importance);

// Topic indexes
CREATE INDEX topic_category_index IF NOT EXISTS
FOR (t:Topic) ON (t.category);

CREATE INDEX topic_popularity_index IF NOT EXISTS
FOR (t:Topic) ON (t.popularity);

CREATE INDEX topic_created_at_index IF NOT EXISTS
FOR (t:Topic) ON (t.created_at);

// Entity indexes
CREATE INDEX entity_type_index IF NOT EXISTS
FOR (e:Entity) ON (e.type);

CREATE INDEX entity_name_index IF NOT EXISTS
FOR (e:Entity) ON (e.name);

CREATE INDEX entity_created_at_index IF NOT EXISTS
FOR (e:Entity) ON (e.created_at);

// Session indexes
CREATE INDEX session_start_time_index IF NOT EXISTS
FOR (s:Session) ON (s.start_time);

CREATE INDEX session_end_time_index IF NOT EXISTS
FOR (s:Session) ON (s.end_time);

CREATE INDEX session_status_index IF NOT EXISTS
FOR (s:Session) ON (s.status);

// Context indexes
CREATE INDEX context_type_index IF NOT EXISTS
FOR (ctx:Context) ON (ctx.type);

CREATE INDEX context_timestamp_index IF NOT EXISTS
FOR (ctx:Context) ON (ctx.timestamp);

// ============================================================================
// FULL-TEXT SEARCH INDEXES
// ============================================================================

// Create full-text search indexes for content search
CREATE FULLTEXT INDEX message_content_fulltext IF NOT EXISTS
FOR (m:Message) ON EACH [m.content];

CREATE FULLTEXT INDEX fact_content_fulltext IF NOT EXISTS
FOR (f:Fact) ON EACH [f.content, f.description];

CREATE FULLTEXT INDEX entity_search_fulltext IF NOT EXISTS
FOR (e:Entity) ON EACH [e.name, e.description];

CREATE FULLTEXT INDEX topic_search_fulltext IF NOT EXISTS
FOR (t:Topic) ON EACH [t.name, t.description];

// ============================================================================
// COMPOSITE INDEXES
// ============================================================================

// User-conversation composite index
CREATE INDEX user_conversation_composite_index IF NOT EXISTS
FOR (c:Conversation) ON (c.user_id, c.timestamp);

// Message-conversation composite index  
CREATE INDEX message_conversation_composite_index IF NOT EXISTS
FOR (m:Message) ON (m.conversation_id, m.timestamp);

// Fact-confidence-timestamp composite index
CREATE INDEX fact_confidence_timestamp_index IF NOT EXISTS
FOR (f:Fact) ON (f.confidence, f.timestamp);

// Memory-importance-timestamp composite index
CREATE INDEX memory_importance_timestamp_index IF NOT EXISTS
FOR (m:Memory) ON (m.importance, m.timestamp);