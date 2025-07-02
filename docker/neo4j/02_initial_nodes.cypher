// Neo4j Initial Nodes for Bot Provisional Knowledge Graph
// This script creates essential initial nodes and basic relationships

// ============================================================================
// SYSTEM NODES
// ============================================================================

// Create system user for automated processes
MERGE (system:User {id: 'system'})
ON CREATE SET 
    system.name = 'System',
    system.type = 'system',
    system.telegram_id = 'system',
    system.created_at = datetime(),
    system.last_active = datetime(),
    system.description = 'System user for automated processes and internal operations',
    system.is_active = true,
    system.permissions = ['system', 'admin'];

// Create bot user representing the chatbot itself
MERGE (bot:User {id: 'bot_nadia'})
ON CREATE SET 
    bot.name = 'Nadia',
    bot.type = 'bot',
    bot.telegram_id = 'bot',
    bot.created_at = datetime(),
    bot.last_active = datetime(),
    bot.description = 'Nadia - The conversational companion bot',
    bot.is_active = true,
    bot.personality = 'empathetic, supportive, intelligent',
    bot.version = '0.1.0';

// ============================================================================
// ROOT TOPIC NODES
// ============================================================================

// Create root topics for conversation categorization
MERGE (general:Topic {name: 'General'})
ON CREATE SET 
    general.category = 'root',
    general.description = 'General conversations and miscellaneous topics',
    general.created_at = datetime(),
    general.popularity = 0,
    general.parent_topic = null,
    general.is_active = true;

MERGE (personal:Topic {name: 'Personal'})
ON CREATE SET 
    personal.category = 'root',
    personal.description = 'Personal matters, feelings, and individual experiences',
    personal.created_at = datetime(),
    personal.popularity = 0,
    personal.parent_topic = null,
    personal.is_active = true;

MERGE (technical:Topic {name: 'Technical'})
ON CREATE SET 
    technical.category = 'root',
    technical.description = 'Technical discussions, programming, and technology',
    technical.created_at = datetime(),
    technical.popularity = 0,
    technical.parent_topic = null,
    technical.is_active = true;

MERGE (emotional:Topic {name: 'Emotional Support'})
ON CREATE SET 
    emotional.category = 'root',
    emotional.description = 'Emotional support, mental health, and wellbeing',
    emotional.created_at = datetime(),
    emotional.popularity = 0,
    emotional.parent_topic = null,
    emotional.is_active = true;

MERGE (creative:Topic {name: 'Creative'})
ON CREATE SET 
    creative.category = 'root',
    creative.description = 'Creative activities, art, writing, and imagination',
    creative.created_at = datetime(),
    creative.popularity = 0,
    creative.parent_topic = null,
    creative.is_active = true;

// ============================================================================
// ENTITY TYPES
// ============================================================================

// Create fundamental entity types
MERGE (person_type:EntityType {name: 'Person'})
ON CREATE SET 
    person_type.description = 'Individual people mentioned in conversations',
    person_type.created_at = datetime(),
    person_type.attributes = ['name', 'relationship', 'description', 'importance'];

MERGE (place_type:EntityType {name: 'Place'})
ON CREATE SET 
    place_type.description = 'Locations, cities, countries, venues',
    place_type.created_at = datetime(),
    place_type.attributes = ['name', 'type', 'coordinates', 'description'];

MERGE (organization_type:EntityType {name: 'Organization'})
ON CREATE SET 
    organization_type.description = 'Companies, institutions, groups',
    organization_type.created_at = datetime(),
    organization_type.attributes = ['name', 'type', 'industry', 'description'];

MERGE (event_type:EntityType {name: 'Event'})
ON CREATE SET 
    event_type.description = 'Events, occasions, meetings, activities',
    event_type.created_at = datetime(),
    event_type.attributes = ['name', 'date', 'location', 'participants', 'description'];

MERGE (concept_type:EntityType {name: 'Concept'})
ON CREATE SET 
    concept_type.description = 'Abstract concepts, ideas, theories',
    concept_type.created_at = datetime(),
    concept_type.attributes = ['name', 'definition', 'category', 'related_concepts'];

// ============================================================================
// MEMORY TYPES
// ============================================================================

// Create memory type nodes for organizing different kinds of memories
MERGE (episodic:MemoryType {name: 'Episodic'})
ON CREATE SET 
    episodic.description = 'Specific events and experiences',
    episodic.retention_days = 365,
    episodic.importance_threshold = 0.7,
    episodic.created_at = datetime();

MERGE (semantic:MemoryType {name: 'Semantic'})
ON CREATE SET 
    semantic.description = 'Facts and general knowledge',
    semantic.retention_days = 730,
    semantic.importance_threshold = 0.8,
    semantic.created_at = datetime();

MERGE (procedural:MemoryType {name: 'Procedural'})
ON CREATE SET 
    procedural.description = 'How-to knowledge and procedures',
    procedural.retention_days = 1095,
    procedural.importance_threshold = 0.9,
    procedural.created_at = datetime();

MERGE (emotional_memory:MemoryType {name: 'Emotional'})
ON CREATE SET 
    emotional_memory.description = 'Emotional contexts and feelings',
    emotional_memory.retention_days = 180,
    emotional_memory.importance_threshold = 0.6,
    emotional_memory.created_at = datetime();

// ============================================================================
// RELATIONSHIP TYPES
// ============================================================================

// Create relationship type definitions
MERGE (knows:RelationshipType {name: 'KNOWS'})
ON CREATE SET 
    knows.description = 'General acquaintance or knowledge relationship',
    knows.created_at = datetime(),
    knows.is_directional = false;

MERGE (mentioned:RelationshipType {name: 'MENTIONED'})
ON CREATE SET 
    mentioned.description = 'Entity mentioned in conversation',
    mentioned.created_at = datetime(),
    mentioned.is_directional = true;

MERGE (related_to:RelationshipType {name: 'RELATED_TO'})
ON CREATE SET 
    related_to.description = 'General relationship between entities',
    related_to.created_at = datetime(),
    related_to.is_directional = false;

MERGE (part_of:RelationshipType {name: 'PART_OF'})
ON CREATE SET 
    part_of.description = 'Part-whole relationship',
    part_of.created_at = datetime(),
    part_of.is_directional = true;

// ============================================================================
// CONTEXT NODES
// ============================================================================

// Create default context nodes
MERGE (default_context:Context {id: 'default'})
ON CREATE SET 
    default_context.name = 'Default Context',
    default_context.type = 'default',
    default_context.description = 'Default conversation context',
    default_context.created_at = datetime(),
    default_context.is_active = true;

MERGE (initial_context:Context {id: 'initial'})
ON CREATE SET 
    initial_context.name = 'Initial Meeting Context',
    initial_context.type = 'initial',
    initial_context.description = 'Context for first-time conversations',
    initial_context.created_at = datetime(),
    initial_context.is_active = true;

// ============================================================================
// CONFIGURATION NODES
// ============================================================================

// Create configuration node for graph settings
MERGE (config:GraphConfig {id: 'main'})
ON CREATE SET 
    config.name = 'Main Graph Configuration',
    config.version = '1.0.0',
    config.created_at = datetime(),
    config.max_conversation_depth = 10,
    config.max_entity_relationships = 100,
    config.fact_confidence_threshold = 0.7,
    config.memory_decay_rate = 0.1,
    config.context_window_size = 20;

// ============================================================================
// INITIAL RELATIONSHIPS
// ============================================================================

// Create relationships between root topics
MATCH (general:Topic {name: 'General'}), (technical:Topic {name: 'Technical'})
MERGE (general)-[:RELATED_TO {strength: 0.3, created_at: datetime()}]->(technical);

MATCH (personal:Topic {name: 'Personal'}), (emotional:Topic {name: 'Emotional Support'})
MERGE (personal)-[:RELATED_TO {strength: 0.8, created_at: datetime()}]->(emotional);

MATCH (creative:Topic {name: 'Creative'}), (technical:Topic {name: 'Technical'})
MERGE (creative)-[:RELATED_TO {strength: 0.4, created_at: datetime()}]->(technical);

// Connect bot to its personality topics
MATCH (bot:User {id: 'bot_nadia'}), (emotional:Topic {name: 'Emotional Support'})
MERGE (bot)-[:SPECIALIZES_IN {strength: 0.9, created_at: datetime()}]->(emotional);

MATCH (bot:User {id: 'bot_nadia'}), (personal:Topic {name: 'Personal'})
MERGE (bot)-[:SPECIALIZES_IN {strength: 0.8, created_at: datetime()}]->(personal);

// Connect system user to technical topics
MATCH (system:User {id: 'system'}), (technical:Topic {name: 'Technical'})
MERGE (system)-[:MANAGES {created_at: datetime()}]->(technical);

// ============================================================================
// VALIDATION QUERIES
// ============================================================================

// Count created nodes by type (for verification)
MATCH (n:User) 
WITH count(n) as user_count
MATCH (t:Topic)
WITH user_count, count(t) as topic_count
MATCH (et:EntityType)
WITH user_count, topic_count, count(et) as entity_type_count
MATCH (mt:MemoryType)
WITH user_count, topic_count, entity_type_count, count(mt) as memory_type_count
MATCH (rt:RelationshipType)
WITH user_count, topic_count, entity_type_count, memory_type_count, count(rt) as rel_type_count
MATCH (ctx:Context)
WITH user_count, topic_count, entity_type_count, memory_type_count, rel_type_count, count(ctx) as context_count
MATCH (gc:GraphConfig)
WITH user_count, topic_count, entity_type_count, memory_type_count, rel_type_count, context_count, count(gc) as config_count

RETURN 
    user_count,
    topic_count,
    entity_type_count,
    memory_type_count,
    rel_type_count,
    context_count,
    config_count;