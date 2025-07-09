# supervisor20.md - Orquestador Central con Memoria Emocional

## 1. Rol del Orquestador
El supervisor es el cerebro central del sistema, coordinando todos los componentes de memoria, análisis emocional y generación de respuestas.

## 2. Gestión de Endpoints del Dashboard
### 2.1 API RESTful Endpoints
```python
# Endpoints principales
POST   /api/messages/approve      # Aprobar mensaje antes de enviar
PUT    /api/messages/{id}/edit    # Editar mensaje generado
GET    /api/users/{id}/context    # Obtener contexto actual
POST   /api/config/update         # Actualizar configuración
GET    /api/metrics/realtime      # Métricas en tiempo real
POST   /api/memory/consolidate    # Forzar consolidación manual
```

### 2.2 WebSocket para Tiempo Real
- Canal de eventos para actualizaciones instantáneas
- Notificaciones de nuevos mensajes pendientes
- Alertas de coherencia detectadas
- Métricas de rendimiento en vivo

## 3. Recepción y Procesamiento de Mensajes
### 3.1 Pipeline de Entrada
```python
async def process_incoming_batch(user_id, messages, emotional_context):
    # 1. Validación de entrada
    validated_messages = validate_and_sanitize(messages)
    
    # 2. Análisis emocional profundo
    emotional_analysis = await analyze_emotional_trajectory(
        messages, 
        emotional_context
    )
    
    # 3. Enriquecimiento con memoria
    enriched_context = await enrich_with_memories(
        user_id, 
        validated_messages,
        emotional_analysis
    )
    
    # 4. Generación de respuesta
    response = await generate_contextual_response(enriched_context)
    
    # 5. Validación de coherencia
    validated_response = await validate_coherence(response, user_id)
    
    return validated_response
```

## 4. Gestión de Respuestas Generadas
### 4.1 Estructura de Respuesta
```python
response_structure = {
    'user_id': str,
    'session_id': str,
    'content': str,
    'emotional_tone': dict,  # VAD de la respuesta
    'memories_used': list,   # IDs de memorias relevantes
    'confidence': float,
    'requires_approval': bool,
    'suggested_bubbles': list,  # Pre-separado en globos
    'metadata': {
        'generation_time': float,
        'model_used': 'gemini-2.0-flash',
        'prompt_tokens': int,
        'completion_tokens': int
    }
}
```

## 5. Sistema de Context Window Mejorado (Redis)
### 5.1 Gestión Dinámica de Ventana
- **Rango configurable**: 20-100 mensajes
- **Modificable por usuario**: Personalización individual
- **Limpieza inteligente**: Mantiene mensajes emocionalmente significativos

### 5.2 Estructura en Redis
```python
# Key structure
context_key = f"context:{user_id}:messages"
emotional_key = f"context:{user_id}:emotional_state"
session_key = f"session:{user_id}:{session_id}"

# Stored data
context_data = {
    'messages': [
        {
            'id': str,
            'content': str,
            'timestamp': datetime,
            'role': 'user|assistant',
            'emotional_state': dict,
            'importance_score': float
        }
    ],
    'summary': str,  # Resumen automático de mensajes antiguos
    'emotional_baseline': dict  # Estado emocional promedio
}
```

### 5.3 Algoritmo de Ventana Deslizante
```python
def update_context_window(user_id, new_message):
    # Obtener ventana actual
    current_window = redis.get(f"context:{user_id}:messages")
    
    # Agregar nuevo mensaje
    current_window.append(new_message)
    
    # Si excede el límite, comprimir
    if len(current_window) > MAX_WINDOW_SIZE:
        # Mantener mensajes importantes
        important_messages = filter(
            lambda m: m['importance_score'] > 0.7, 
            current_window
        )
        
        # Generar resumen de los demás
        summary = generate_summary(current_window[:-KEEP_RECENT])
        
        # Nueva ventana: resumen + importantes + recientes
        new_window = [summary] + important_messages + current_window[-KEEP_RECENT:]
    
    redis.set(f"context:{user_id}:messages", new_window)
```

## 6. Cache Augmented Generation (CAG) Semántico
### 6.1 Sistema de Cache Inteligente
```python
class SemanticCAG:
    def __init__(self):
        self.cache_threshold = 0.85  # Similaridad mínima
        self.emotional_weight = 0.3   # Peso del contexto emocional
        
    async def search_cache(self, query, emotional_state):
        # Embedding del query
        query_embedding = await get_embedding(query)
        
        # Búsqueda vectorial en Redis
        cache_results = await redis.vector_search(
            index="semantic_cache",
            query_vector=query_embedding,
            top_k=5,
            filters={
                'emotional_distance': emotional_state
            }
        )
        
        # Scoring híbrido
        for result in cache_results:
            semantic_score = result['similarity']
            emotional_score = calculate_emotional_similarity(
                result['emotional_state'], 
                emotional_state
            )
            result['final_score'] = (
                semantic_score * (1 - self.emotional_weight) + 
                emotional_score * self.emotional_weight
            )
        
        # Retornar si hay hit fuerte
        best_match = max(cache_results, key=lambda x: x['final_score'])
        if best_match['final_score'] > self.cache_threshold:
            return best_match['response']
        
        return None
```

### 6.2 Actualización de Cache
- Cache hits exitosos incrementan score de confianza
- Respuestas nuevas se evalúan para inclusión en cache
- TTL basado en frecuencia de uso y relevancia emocional

## 7. RAG con GraphRAG/PathRAG Mejorado
### 7.1 Búsqueda Semántica con Spreading Activation
```python
async def enhanced_rag_search(user_id, query, emotional_state):
    # Fase 1: Búsqueda vectorial inicial
    initial_nodes = await neo4j.vector_search(
        query_embedding=await get_embedding(query),
        user_id=user_id,
        limit=10
    )
    
    # Fase 2: Spreading Activation con pesos emocionales
    activated_memories = await spreading_activation(
        start_nodes=initial_nodes,
        emotional_state=emotional_state,
        max_hops=3,
        decay_factor=0.6,
        activation_threshold=0.3
    )
    
    # Fase 3: PathRAG para encontrar conexiones
    memory_paths = await find_memory_paths(
        source_memories=activated_memories,
        max_path_length=4,
        relationship_types=['EMOTIONALLY_SIMILAR', 'TEMPORALLY_RELATED']
    )
    
    # Fase 4: Ranking final
    ranked_memories = rank_by_relevance(
        memories=memory_paths,
        query_context=query,
        emotional_context=emotional_state,
        temporal_context=datetime.now()
    )
    
    return ranked_memories[:10]  # Top 10 memorias
```

### 7.2 Inyección de Memorias en Prompt
```python
def build_memory_enhanced_prompt(query, memories, user_profile):
    memory_context = "\n".join([
        f"[{mem['timestamp'].strftime('%Y-%m-%d')}] "
        f"(Emoción: {mem['emotion']}) {mem['content']}"
        for mem in memories
    ])
    
    prompt = f"""
    Eres {user_profile['name']}, {user_profile['description']}.
    
    Memorias relevantes:
    {memory_context}
    
    Estado emocional actual del usuario: {emotional_state}
    
    Mensaje del usuario: {query}
    
    Responde de manera coherente con las memorias y tu personalidad.
    """
    
    return prompt
```

## 8. Detección y Validación de Coherencia
### 8.1 Detección de Declaraciones Importantes
```python
class DeclarationDetector:
    def __init__(self):
        self.patterns = [
            r"mi .* es (mañana|pasado mañana|el \w+)",  # Eventos futuros
            r"me gusta(n)? .*",                          # Preferencias
            r"voy a .* (el|la|en) .*",                  # Planes
            r"tengo .* (examen|cita|reunión)",          # Compromisos
            r"mi .* se llama .*",                       # Información personal
        ]
    
    async def extract_declarations(self, message):
        declarations = []
        
        # Detección por patrones
        for pattern in self.patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            declarations.extend(matches)
        
        # Detección por LLM
        llm_declarations = await extract_facts_with_llm(message)
        declarations.extend(llm_declarations)
        
        return self.classify_declarations(declarations)
```

### 8.2 Verificación de Coherencia
```python
async def verify_coherence(new_declaration, user_id):
    # Buscar declaraciones similares previas
    similar_memories = await find_similar_declarations(
        user_id=user_id,
        declaration=new_declaration,
        similarity_threshold=0.7
    )
    
    if not similar_memories:
        return {'coherent': True, 'suggestion': None}
    
    # Validar con LLM
    validation_prompt = f"""
    Nueva declaración: "{new_declaration}"
    
    Memorias previas relacionadas:
    {format_memories(similar_memories)}
    
    ¿Hay alguna incoherencia? Si la hay, sugiere una respuesta corregida
    manteniendo la personalidad de Nadia.
    
    Responde en JSON: {{"coherent": bool, "suggestion": str o null}}
    """
    
    validation = await gemini.generate(validation_prompt, response_format="json")
    
    return validation
```

### 8.3 Dashboard de Correcciones
- Notificación inmediata de incoherencias detectadas
- Vista comparativa: declaración nueva vs memorias previas
- Opción de aprobar, editar o rechazar la corrección
- Historial de correcciones para análisis

## 9. Sistema de Guardado de Memorias
### 9.1 Pipeline de Procesamiento
```python
async def save_memory_pipeline(interaction_data):
    # 1. Clasificar tipo de memoria
    memory_type = classify_memory_type(interaction_data)
    
    # 2. Extraer entidades y relaciones
    entities = await extract_entities(interaction_data['content'])
    
    # 3. Calcular importancia
    importance_score = calculate_importance(
        emotional_weight=interaction_data['emotional_state']['arousal'],
        semantic_novelty=calculate_novelty(interaction_data['content']),
        user_engagement=interaction_data['response_time']
    )
    
    # 4. Crear nodo en Neo4j
    if importance_score > MEMORY_THRESHOLD:
        memory_node = await create_memory_node(
            user_id=interaction_data['user_id'],
            content=interaction_data['content'],
            memory_type=memory_type,
            emotional_state=interaction_data['emotional_state'],
            entities=entities,
            importance=importance_score
        )
        
        # 5. Establecer relaciones
        await create_memory_relationships(memory_node, entities)
        
        # 6. Queue para consolidación futura
        if memory_type == 'episodic':
            await queue_for_consolidation(memory_node)
    
    return memory_node
```

### 9.2 Categorización de Memorias
- **Eventos**: Acciones con tiempo/lugar específico
- **Hechos**: Información declarativa sobre el usuario
- **Preferencias**: Gustos y disgustos expresados
- **Relaciones**: Personas mencionadas y su contexto
- **Estados**: Condiciones emocionales o físicas

## 10. Integración con Dashboard
### 10.1 Funciones Modificables en Tiempo Real
```python
class DynamicConfiguration:
    def __init__(self):
        self.config = {
            'debounce_time': 120,
            'bubble_word_count': 20,
            'context_window_size': 50,
            'cache_hit_threshold': 0.85,
            'rag_similarity_threshold': 0.7,
            'emotional_weight': 0.3,
            'consolidation_frequency': 3,
            'max_spreading_hops': 3
        }
    
    async def update_config(self, key, value):
        # Validar nuevo valor
        if self.validate_config_value(key, value):
            self.config[key] = value
            
            # Propagar cambio a componentes
            await self.propagate_config_change(key, value)
            
            # Log para auditoría
            await log_config_change(key, value)
            
            return {'success': True}
        
        return {'success': False, 'error': 'Invalid value'}
```

### 10.2 Métricas y Costos
```python
class MetricsCollector:
    async def collect_user_metrics(self, user_id):
        return {
            'tokens': {
                'input_total': await get_total_input_tokens(user_id),
                'output_total': await get_total_output_tokens(user_id),
                'cost_usd': calculate_cost(input_tokens, output_tokens)
            },
            'messages': {
                'sent': await count_messages_sent(user_id),
                'received': await count_messages_received(user_id),
                'average_length': await get_average_message_length(user_id)
            },
            'memory': {
                'episodic_count': await count_episodic_memories(user_id),
                'semantic_count': await count_semantic_memories(user_id),
                'total_relationships': await count_relationships(user_id)
            },
            'performance': {
                'average_response_time': await get_avg_response_time(user_id),
                'cache_hit_rate': await get_cache_hit_rate(user_id),
                'coherence_corrections': await count_corrections(user_id)
            }
        }
```

## 11. Gestión de Sesiones y Estado
### 11.1 Sesión por Usuario
```python
class SessionManager:
    async def create_session(self, user_id):
        session_id = generate_uuid()
        session_data = {
            'id': session_id,
            'user_id': user_id,
            'started_at': datetime.now(),
            'emotional_baseline': await get_user_emotional_baseline(user_id),
            'context_summary': await generate_context_summary(user_id),
            'active': True
        }
        
        await redis.set(
            f"session:{user_id}:{session_id}", 
            session_data,
            ex=86400  # 24 horas TTL
        )
        
        return session_id
```

## 12. Optimizaciones y Rendimiento
### 12.1 Estrategias de Optimización
- **Batch Processing**: Agrupar operaciones de Neo4j
- **Async Everything**: Todas las operaciones IO son asíncronas
- **Connection Pooling**: Pools para Redis y Neo4j
- **Caching Agresivo**: Cache multinivel (L1: memoria, L2: Redis, L3: Neo4j)
- **Lazy Loading**: Cargar memorias solo cuando se necesitan

### 12.2 Configuración de Rendimiento
```python
PERFORMANCE_CONFIG = {
    'neo4j_connection_pool_size': 50,
    'redis_connection_pool_size': 100,
    'max_concurrent_users': 100,
    'batch_size': 50,
    'cache_ttl_seconds': 3600,
    'memory_prefetch_limit': 20,
    'embedding_batch_size': 32
}
```

## 13. Manejo de Errores y Recuperación
### 13.1 Estrategia de Fallback
```python
async def safe_process_message(user_id, message):
    try:
        return await process_message_pipeline(user_id, message)
    except RedisConnectionError:
        # Fallback a memoria local
        return await process_with_local_cache(user_id, message)
    except Neo4jConnectionError:
        # Usar solo contexto inmediato
        return await process_with_context_only(user_id, message)
    except GeminiAPIError:
        # Respuesta predefinida personalizada
        return await get_fallback_response(user_id, message)
    except Exception as e:
        # Log y respuesta genérica
        await log_critical_error(e, user_id, message)
        return "Disculpa, estoy teniendo problemas técnicos. ¿Podemos intentar de nuevo?"
```

## 14. Seguridad y Validación
### 14.1 Validación de Entrada
- Sanitización de mensajes contra injection
- Límites de longitud de mensaje (max 4000 caracteres)
- Detección de contenido malicioso
- Rate limiting por usuario

### 14.2 Protección de Datos
- Encriptación de memorias sensibles
- Anonimización opcional de datos
- Logs sin información personal identificable
- Acceso segregado por usuario