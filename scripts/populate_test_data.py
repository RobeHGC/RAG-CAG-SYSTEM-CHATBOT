#!/usr/bin/env python3
"""
Bot Provisional - Test Data Population Script
This script populates databases with test data for development and testing.
"""

import asyncio
import logging
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from common.config import settings, setup_logging
from common.database import DatabaseManager

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Test data templates
SAMPLE_USERS = [
    {
        "telegram_id": 123456789,
        "username": "test_user_1",
        "first_name": "María",
        "last_name": "García",
        "language_code": "es",
        "is_active": True
    },
    {
        "telegram_id": 987654321,
        "username": "test_user_2", 
        "first_name": "Carlos",
        "last_name": "López",
        "language_code": "es",
        "is_active": True
    },
    {
        "telegram_id": 555666777,
        "username": "test_user_3",
        "first_name": "Ana",
        "last_name": "Martínez",
        "language_code": "es",
        "is_active": False
    }
]

SAMPLE_CONVERSATIONS = [
    "Hola, ¿cómo estás?",
    "Me gusta mucho la música clásica",
    "¿Qué opinas sobre los libros de ciencia ficción?",
    "Tengo una reunión importante mañana",
    "El clima está muy agradable hoy",
    "¿Conoces algún buen restaurante italiano?",
    "Estoy aprendiendo a tocar la guitarra",
    "Mi color favorito es el azul",
    "¿Has visto alguna buena película últimamente?",
    "Me encanta viajar y conocer nuevos lugares"
]

SAMPLE_MEMORIES = [
    {
        "entity": "María García",
        "fact": "Le gusta la música clásica",
        "context": "Conversación sobre gustos musicales",
        "confidence": 0.9
    },
    {
        "entity": "Carlos López", 
        "fact": "Está aprendiendo a tocar la guitarra",
        "context": "Compartió sus hobbies",
        "confidence": 0.85
    },
    {
        "entity": "Ana Martínez",
        "fact": "Su color favorito es el azul",
        "context": "Conversación sobre preferencias",
        "confidence": 0.8
    },
    {
        "entity": "Restaurant Recommendations",
        "fact": "Se solicitó información sobre restaurantes italianos",
        "context": "Búsqueda de recomendaciones gastronómicas",
        "confidence": 0.75
    }
]

SAMPLE_TOPICS = [
    "música", "libros", "películas", "viajes", "comida", 
    "trabajo", "hobbies", "clima", "deportes", "tecnología"
]


class TestDataPopulator:
    """Handles population of test data across all databases."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        
    async def populate_all(self, clear_existing: bool = True) -> bool:
        """Populate all databases with test data."""
        try:
            logger.info("Starting test data population...")
            
            if clear_existing:
                logger.info("Clearing existing test data...")
                await self._clear_test_data()
            
            # Populate each database
            await self._populate_postgres()
            await self._populate_redis()
            await self._populate_neo4j()
            
            logger.info("Test data population completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error during test data population: {e}")
            return False
            
    async def _clear_test_data(self):
        """Clear existing test data from all databases."""
        # Clear PostgreSQL test data
        postgres_conn = await self.db_manager.get_postgres_connection()
        async with postgres_conn.transaction():
            await postgres_conn.execute("DELETE FROM conversations WHERE user_id IN (123456789, 987654321, 555666777)")
            await postgres_conn.execute("DELETE FROM users WHERE telegram_id IN (123456789, 987654321, 555666777)")
            
        # Clear Redis test data
        redis_conn = await self.db_manager.get_redis_connection()
        await redis_conn.flushdb()
        
        # Clear Neo4j test data
        neo4j_session = await self.db_manager.get_neo4j_session()
        await neo4j_session.run("MATCH (n) WHERE n.test_data = true DELETE n")
        
        logger.info("Test data cleared successfully")
        
    async def _populate_postgres(self):
        """Populate PostgreSQL with test users and conversations."""
        logger.info("Populating PostgreSQL with test data...")
        
        postgres_conn = await self.db_manager.get_postgres_connection()
        
        # Insert test users
        for user in SAMPLE_USERS:
            await postgres_conn.execute("""
                INSERT INTO users (telegram_id, username, first_name, last_name, language_code, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (telegram_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    updated_at = NOW()
            """, user["telegram_id"], user["username"], user["first_name"], 
                user["last_name"], user["language_code"], user["is_active"], datetime.now())
            
        # Insert test conversations
        for i, user in enumerate(SAMPLE_USERS[:2]):  # Only active users
            for j in range(5):  # 5 conversations per user
                message = random.choice(SAMPLE_CONVERSATIONS)
                response = f"Respuesta del bot a: {message}"
                
                await postgres_conn.execute("""
                    INSERT INTO conversations (user_id, message, response, tokens_used, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                """, user["telegram_id"], message, response, 
                    random.randint(50, 200), datetime.now() - timedelta(days=random.randint(0, 7)))
                    
        logger.info("PostgreSQL test data populated successfully")
        
    async def _populate_redis(self):
        """Populate Redis with test cache data."""
        logger.info("Populating Redis with test cache data...")
        
        redis_conn = await self.db_manager.get_redis_connection()
        
        # Add some cached conversation contexts
        for user in SAMPLE_USERS[:2]:
            context_key = f"context:{user['telegram_id']}"
            context_data = {
                "user_name": f"{user['first_name']} {user['last_name']}",
                "last_topics": random.sample(SAMPLE_TOPICS, 3),
                "conversation_count": random.randint(5, 20),
                "last_interaction": datetime.now().isoformat()
            }
            
            await redis_conn.hset(context_key, mapping=context_data)
            await redis_conn.expire(context_key, 3600)  # 1 hour TTL
            
        # Add some cached responses
        for i in range(5):
            cache_key = f"response_cache:{hash(random.choice(SAMPLE_CONVERSATIONS))}"
            cache_value = {
                "response": f"Cached response {i+1}",
                "timestamp": datetime.now().isoformat(),
                "tokens": random.randint(30, 100)
            }
            
            await redis_conn.set(cache_key, str(cache_value), ex=1800)  # 30 min TTL
            
        logger.info("Redis test data populated successfully")
        
    async def _populate_neo4j(self):
        """Populate Neo4j with test knowledge graph data."""
        logger.info("Populating Neo4j with test knowledge graph...")
        
        neo4j_session = await self.db_manager.get_neo4j_session()
        
        # Create user nodes
        for user in SAMPLE_USERS:
            await neo4j_session.run("""
                MERGE (u:User {telegram_id: $telegram_id})
                SET u.name = $name,
                    u.username = $username,
                    u.test_data = true,
                    u.created_at = datetime()
            """, telegram_id=user["telegram_id"], 
                name=f"{user['first_name']} {user['last_name']}",
                username=user["username"])
                
        # Create memory/fact nodes
        for memory in SAMPLE_MEMORIES:
            await neo4j_session.run("""
                MERGE (f:Fact {entity: $entity, fact: $fact})
                SET f.context = $context,
                    f.confidence = $confidence,
                    f.test_data = true,
                    f.created_at = datetime()
            """, **memory)
            
        # Create topic nodes and relationships
        for topic in SAMPLE_TOPICS:
            await neo4j_session.run("""
                MERGE (t:Topic {name: $topic})
                SET t.test_data = true,
                    t.created_at = datetime()
            """, topic=topic)
            
        # Create some relationships between users and topics
        for user in SAMPLE_USERS[:2]:
            user_topics = random.sample(SAMPLE_TOPICS, 3)
            for topic in user_topics:
                await neo4j_session.run("""
                    MATCH (u:User {telegram_id: $telegram_id})
                    MATCH (t:Topic {name: $topic})
                    MERGE (u)-[r:INTERESTED_IN]->(t)
                    SET r.strength = $strength,
                        r.test_data = true,
                        r.created_at = datetime()
                """, telegram_id=user["telegram_id"], topic=topic, 
                    strength=random.uniform(0.5, 1.0))
                    
        logger.info("Neo4j test data populated successfully")
        
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about populated test data."""
        stats = {}
        
        try:
            # PostgreSQL stats
            postgres_conn = await self.db_manager.get_postgres_connection()
            user_count = await postgres_conn.fetchval("SELECT COUNT(*) FROM users WHERE telegram_id IN (123456789, 987654321, 555666777)")
            conv_count = await postgres_conn.fetchval("SELECT COUNT(*) FROM conversations WHERE user_id IN (123456789, 987654321, 555666777)")
            
            stats["postgresql"] = {
                "users": user_count,
                "conversations": conv_count
            }
            
            # Redis stats
            redis_conn = await self.db_manager.get_redis_connection()
            redis_keys = await redis_conn.keys("*")
            stats["redis"] = {
                "keys": len(redis_keys)
            }
            
            # Neo4j stats
            neo4j_session = await self.db_manager.get_neo4j_session()
            result = await neo4j_session.run("MATCH (n) WHERE n.test_data = true RETURN labels(n) as label, count(n) as count")
            neo4j_stats = {}
            async for record in result:
                label = record["label"][0] if record["label"] else "Unknown"
                neo4j_stats[label] = record["count"]
            stats["neo4j"] = neo4j_stats
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            stats["error"] = str(e)
            
        return stats
        
    async def cleanup(self):
        """Clean up database connections."""
        await self.db_manager.close_all()


async def main():
    """Main function to run test data population."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Populate databases with test data")
    parser.add_argument("--clear", action="store_true", help="Clear existing test data first")
    parser.add_argument("--stats-only", action="store_true", help="Only show statistics")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
        
    populator = TestDataPopulator()
    
    try:
        if args.stats_only:
            stats = await populator.get_stats()
            print("\n=== Test Data Statistics ===")
            for db_name, db_stats in stats.items():
                print(f"\n{db_name.upper()}:")
                if isinstance(db_stats, dict):
                    for key, value in db_stats.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"  {db_stats}")
        else:
            success = await populator.populate_all(clear_existing=args.clear)
            
            if success:
                print("\n✅ Test data populated successfully!")
                
                stats = await populator.get_stats()
                print("\n=== Population Summary ===")
                for db_name, db_stats in stats.items():
                    print(f"{db_name}: {db_stats}")
                    
                print("\nTest data includes:")
                print("- 3 test users (2 active, 1 inactive)")
                print("- Sample conversations and responses")
                print("- Cached context data in Redis")
                print("- Knowledge graph with users, topics, and relationships")
                
            else:
                print("\n❌ Test data population failed!")
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        await populator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())