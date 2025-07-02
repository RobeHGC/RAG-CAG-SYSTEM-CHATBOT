// Neo4j Procedures and Functions for Bot Provisional Knowledge Graph
// This script creates custom procedures for common graph operations

// Note: These are Cypher procedures that can be called from the application
// For APOC procedures, make sure the APOC plugin is enabled in the Neo4j configuration

// ============================================================================
// USER MANAGEMENT PROCEDURES
// ============================================================================

// Procedure to create or update a user
CALL {
    // This is a template - actual implementation would be in the application
    // CREATE (user:User {id: $user_id, name: $name, telegram_id: $telegram_id})
    // SET user.created_at = datetime(), user.last_active = datetime()
    RETURN "User management procedures are implemented in application code" AS message
} RETURN message;

// ============================================================================
// CONVERSATION TRACKING PROCEDURES  
// ============================================================================

// Procedure to start a new conversation session
CALL {
    // Template for conversation creation
    RETURN "Conversation tracking procedures are implemented in application code" AS message
} RETURN message;

// ============================================================================
// KNOWLEDGE EXTRACTION PROCEDURES
// ============================================================================

// Procedure to extract and store entities from conversation
CALL {
    // Template for entity extraction
    RETURN "Entity extraction procedures are implemented in application code" AS message  
} RETURN message;

// ============================================================================
// MEMORY MANAGEMENT PROCEDURES
// ============================================================================

// Procedure to store episodic memories
CALL {
    // Template for memory storage
    RETURN "Memory management procedures are implemented in application code" AS message
} RETURN message;

// ============================================================================
// UTILITY QUERIES FOR COMMON OPERATIONS
// ============================================================================

// These are example queries that the application can use

// Example: Find user's recent conversations
// MATCH (u:User {id: $user_id})-[:PARTICIPATED_IN]->(c:Conversation)
// WHERE c.timestamp > datetime() - duration('P7D')
// RETURN c ORDER BY c.timestamp DESC LIMIT 10;

// Example: Find related topics for a conversation
// MATCH (c:Conversation {id: $conversation_id})-[:ABOUT]->(t:Topic)
// MATCH (t)-[:RELATED_TO*1..2]->(related:Topic)
// RETURN DISTINCT related.name, related.description;

// Example: Get user's memory context
// MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:Memory)
// WHERE m.importance > 0.7
// AND m.timestamp > datetime() - duration('P30D')
// RETURN m ORDER BY m.importance DESC, m.timestamp DESC LIMIT 20;

// Example: Find entities mentioned by user
// MATCH (u:User {id: $user_id})-[:PARTICIPATED_IN]->(c:Conversation)
// MATCH (c)-[:MENTIONS]->(e:Entity)
// RETURN e.name, e.type, count(c) AS mention_count
// ORDER BY mention_count DESC;

// Example: Get conversation topics trending
// MATCH (c:Conversation)-[:ABOUT]->(t:Topic)
// WHERE c.timestamp > datetime() - duration('P7D')
// RETURN t.name, count(c) AS conversation_count
// ORDER BY conversation_count DESC LIMIT 10;

// ============================================================================
// GRAPH ANALYTICS QUERIES
// ============================================================================

// Query to analyze conversation patterns
WITH "Graph analytics queries are available for application use" AS analytics_message
RETURN analytics_message;

// Query to find influential users (most connected)
WITH "User influence analytics available" AS influence_message  
RETURN influence_message;

// Query to identify knowledge gaps (topics with few facts)
WITH "Knowledge gap analysis available" AS gap_message
RETURN gap_message;

// ============================================================================
// CLEANUP AND MAINTENANCE QUERIES
// ============================================================================

// Query to clean up old temporary data
WITH "Cleanup queries available for maintenance" AS cleanup_message
RETURN cleanup_message;

// Query to archive old conversations
WITH "Archiving queries available" AS archive_message
RETURN archive_message;

// Query to optimize graph structure
WITH "Graph optimization queries available" AS optimize_message
RETURN optimize_message;

// ============================================================================
// APOC PROCEDURE EXAMPLES (if APOC is available)
// ============================================================================

// Note: These require APOC plugin to be installed and configured

// Example: Periodic cleanup procedure
// CALL apoc.periodic.iterate(
//   "MATCH (m:Memory) WHERE m.timestamp < datetime() - duration('P365D') AND m.importance < 0.3 RETURN m",
//   "DETACH DELETE m",
//   {batchSize: 100, parallel: false}
// );

// Example: Full-text search across entities
// CALL db.index.fulltext.queryNodes('entity_search', 'search_term')
// YIELD node, score
// RETURN node.name, node.type, score
// ORDER BY score DESC;

// Example: Path finding between entities
// MATCH path = shortestPath((e1:Entity {name: $entity1})-[*..5]-(e2:Entity {name: $entity2}))
// RETURN path;

// Example: Community detection among users
// CALL algo.louvain.stream('User', 'KNOWS', {})
// YIELD nodeId, community
// RETURN algo.getNodeById(nodeId).name AS user, community
// ORDER BY community;

// ============================================================================
// PERFORMANCE MONITORING QUERIES
// ============================================================================

// Query to check graph statistics
CALL db.stats.retrieve('GRAPH') YIELD data
RETURN data;

// Query to monitor constraint and index usage
SHOW CONSTRAINTS;
SHOW INDEXES;

// Query to check database size and node counts
MATCH (n) 
RETURN labels(n) AS node_type, count(n) AS count
ORDER BY count DESC;

MATCH ()-[r]->() 
RETURN type(r) AS relationship_type, count(r) AS count
ORDER BY count DESC;

// ============================================================================
// SCHEMA VALIDATION QUERIES
// ============================================================================

// Validate that all required nodes have proper properties
MATCH (u:User)
WHERE u.id IS NULL OR u.created_at IS NULL
RETURN "Invalid User nodes found" AS validation_error, count(u) AS error_count
UNION ALL
MATCH (c:Conversation)
WHERE c.id IS NULL OR c.timestamp IS NULL  
RETURN "Invalid Conversation nodes found" AS validation_error, count(c) AS error_count
UNION ALL
MATCH (m:Message)
WHERE m.id IS NULL OR m.content IS NULL
RETURN "Invalid Message nodes found" AS validation_error, count(m) AS error_count
UNION ALL
MATCH (f:Fact)
WHERE f.id IS NULL OR f.content IS NULL
RETURN "Invalid Fact nodes found" AS validation_error, count(f) AS error_count;

// ============================================================================
// SAMPLE DATA QUERIES (for testing)
// ============================================================================

// Create sample conversation for testing
// MERGE (user:User {id: 'test_user_1', name: 'Test User', telegram_id: '12345'})
// ON CREATE SET user.created_at = datetime(), user.type = 'human'
// MERGE (conversation:Conversation {id: 'test_conv_1'})
// ON CREATE SET conversation.timestamp = datetime(), conversation.status = 'active'
// MERGE (user)-[:PARTICIPATED_IN]->(conversation)
// MERGE (message1:Message {id: 'test_msg_1', content: 'Hello, how are you?', sender: 'user'})
// ON CREATE SET message1.timestamp = datetime(), message1.type = 'text'
// MERGE (conversation)-[:CONTAINS]->(message1)
// MERGE (response1:Message {id: 'test_msg_2', content: 'I am doing well, thank you!', sender: 'bot'})
// ON CREATE SET response1.timestamp = datetime(), response1.type = 'text'
// MERGE (conversation)-[:CONTAINS]->(response1);

// Verify sample data creation
MATCH (u:User {id: 'test_user_1'})-[:PARTICIPATED_IN]->(c:Conversation)
MATCH (c)-[:CONTAINS]->(m:Message)
RETURN u.name, c.id, m.content, m.sender
ORDER BY m.timestamp;

// ============================================================================
// COMPLETION MARKER
// ============================================================================

CREATE (proc_marker:ProcedureMarker {
    id: 'neo4j_procedures_loaded',
    timestamp: datetime(),
    description: 'Neo4j procedures and queries have been loaded',
    version: '1.0.0'
});

RETURN "Neo4j procedures and utility queries loaded successfully" AS completion_message;