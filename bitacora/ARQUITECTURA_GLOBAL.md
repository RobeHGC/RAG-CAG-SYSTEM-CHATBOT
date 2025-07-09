# Documento Maestro: Arquitectura del AI Companion Emocional

## 1. Visión General del Sistema

### 1.1 Propósito
Este documento describe la arquitectura completa de un AI Companion con capacidades de memoria emocional-espacial-temporal, diseñado para mantener conversaciones significativas y contextualizadas a través de Telegram. El sistema implementa un modelo de memoria inspirado en la cognición humana, combinando memoria episódica (eventos específicos) y semántica (conocimiento general) con modulación emocional.

### 1.2 Características Principales
- **Identidad Persistente**: Nadia, 24 años, estudiante de medicina de Monterrey
- **Memoria Multi-nivel**: Corto plazo (Redis), largo plazo (Neo4j con grafos emocionales)
- **Comprensión Emocional**: Análisis VAD (Valencia-Arousal-Dominance) en tiempo real
- **Consolidación Inteligente**: Transformación automática de memorias episódicas a semánticas
- **Olvido Adaptativo**: Curvas de olvido moduladas por carga emocional
- **Recuperación Contextual**: Spreading activation con pesos emocionales

## 2. Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────┐
│                         CAPA DE ENTRADA                          │
│  ┌─────────────┐                                                │
│  │  Telegram   │ ← Usuarios múltiples, mensajes con imágenes    │
│  │   Bot API   │                                                │
│  └──────┬──────┘                                                │
│         │                                                        │
│  ┌──────▼──────┐                                                │
│  │  Userbot.py │ ← Debouncing 120s, Batching, Typing Simulation │
│  └──────┬──────┘                                                │
└─────────┼────────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────────┐
│                      CAPA DE ORQUESTACIÓN                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                      Supervisor.py                          │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │ │
│  │  │   Context   │  │   Semantic   │  │   Emotional     │  │ │
│  │  │   Window    │  │     CAG      │  │    Analysis     │  │ │
│  │  └─────────────┘  └──────────────┘  └─────────────────┘  │ │
│  │                                                            │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │ │
│  │  │   Memory    │  │  Coherence   │  │    Dashboard    │  │ │
│  │  │  Retrieval  │  │  Validation  │  │   Interface     │  │ │
│  │  └─────────────┘  └──────────────┘  └─────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────────┐
│                        CAPA DE MEMORIA                           │
│  ┌─────────────────┐                   ┌────────────────────┐   │
│  │  Redis Cache    │                   │    Neo4j Graph     │   │
│  │ ┌─────────────┐ │                   │ ┌────────────────┐ │   │
│  │ │Short-term   │ │ ←─────────────→  │ │  Long-term     │ │   │
│  │ │Context (100)│ │                   │ │  Episodic      │ │   │
│  │ └─────────────┘ │                   │ └────────────────┘ │   │
│  │ ┌─────────────┐ │                   │ ┌────────────────┐ │   │
│  │ │Vector Cache │ │                   │ │  Semantic      │ │   │
│  │ │(384 dims)   │ │                   │ │  Knowledge     │ │   │
│  │ └─────────────┘ │                   │ └────────────────┘ │   │
│  └─────────────────┘                   └────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Memory Processing Pipeline                   │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │  │
│  │  │   VAD    │→ │Spreading │→ │Consolid- │→ │Forgetting│ │  │
│  │  │Detection │  │Activation│  │  ation   │  │  Curves  │ │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────────┐
│                         CAPA DE IA                               │
│  ┌────────────────────┐        ┌────────────────────────────┐   │
│  │  Gemini 2.0 Flash  │        │  Modelos Especializados    │   │
│  │  ┌──────────────┐  │        │  ┌────────────────────┐   │   │
│  │  │ Generation   │  │        │  │ RoBERTa VAD       │   │   │
│  │  └──────────────┘  │        │  └────────────────────┘   │   │
│  │  ┌──────────────┐  │        │  ┌────────────────────┐   │   │
│  │  │ Pattern      │  │        │  │ all-MiniLM-L6-v2  │   │   │
│  │  │ Extraction   │  │        │  │ (embeddings)      │   │   │
│  │  └──────────────┘  │        │  └────────────────────┘   │   │
│  └────────────────────┘        └────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

## 3. Componentes Principales

### 3.1 Userbot.py - Interfaz de Entrada
**Responsabilidad**: Gestionar la comunicación con Telegram y pre-procesar mensajes

**Funcionalidades**:
- **Debouncing Inteligente**: Espera 120 segundos para agrupar mensajes consecutivos
- **Batching**: Agrupa mensajes del mismo usuario para procesamiento eficiente
- **Simulación de Typing**: Simula tiempo de escritura proporcional a la longitud de respuesta
- **Separación de Globos**: Divide respuestas largas en múltiples mensajes
- **Recuperación Proactiva**: Al reiniciar, busca mensajes no procesados (< 12 horas)

### 3.2 Supervisor.py - Orquestador Central
**Responsabilidad**: Coordinar todos los componentes del sistema y gestionar el flujo de datos

**Funcionalidades**:
- **Gestión de Context Window**: Mantiene 20-100 mensajes recientes en Redis
- **Cache Augmented Generation (CAG)**: Búsqueda de respuestas predefinidas antes de generar
- **RAG + GraphRAG**: Recuperación semántica con exploración de relaciones en Neo4j
- **Validación de Coherencia**: Detecta y corrige inconsistencias en declaraciones
- **Detección de Hechos**: Identifica declaraciones importantes para memoria a largo plazo
- **API para Dashboard**: Endpoints RESTful para control en tiempo real

### 3.3 Sistema de Memoria Multi-Nivel

#### 3.3.1 Memoria a Corto Plazo (Redis)
- **Context Window**: Últimos 20-100 mensajes por usuario
- **Cache Semántico**: Respuestas frecuentes con vectores pre-calculados
- **Estado de Sesión**: Información temporal de la conversación actual
- **TTL Automático**: Limpieza de datos antiguos

#### 3.3.2 Memoria a Largo Plazo (Neo4j)
- **Memoria Episódica**: Eventos específicos con contexto completo
- **Memoria Semántica**: Patrones y conocimiento consolidado
- **Relaciones Emocionales**: Enlaces ponderados por similitud emocional
- **Relaciones Temporales**: Conexiones basadas en proximidad temporal
- **Relaciones Espaciales**: Vínculos por ubicación o contexto espacial

### 3.4 Pipeline de Procesamiento Emocional

#### 3.4.1 Análisis VAD
```python
# Estructura de análisis emocional
emotional_state = {
    'valence': 0.8,      # Positivo/Negativo (-1 a 1)
    'arousal': 0.6,      # Activación/Calma (0 a 1)
    'dominance': 0.7,    # Control/Sumisión (0 a 1)
    'emotion': 'joy',    # Categoría principal
    'confidence': 0.92   # Confianza del modelo
}
```

#### 3.4.2 Spreading Activation
- **Activación Inicial**: Nodos con alta similitud semántica
- **Propagación**: Activación se propaga con decay factor 0.6
- **Modulación Emocional**: Pesos ajustados por similitud VAD
- **Límite de Profundidad**: Máximo 3-5 saltos en el grafo
- **Threshold de Activación**: Mínimo 0.3 para inclusión en resultados

#### 3.4.3 Consolidación Episódica → Semántica
- **Trigger**: Patrones repetidos 3+ veces
- **Proceso**: Celery workers asíncronos
- **Criterios**: Frecuencia + peso emocional + relevancia temporal
- **Resultado**: Conocimiento general extraído de experiencias específicas

#### 3.4.4 Curvas de Olvido Adaptativas
```python
retention = base_retention * emotional_modifier * access_frequency
# Donde:
# - base_retention: Decaimiento exponencial estándar
# - emotional_modifier: 1 + (emotional_weight * 2.0)
# - access_frequency: 1 + (0.1 * access_count)
```

### 3.5 Generación de Respuestas (LLM)

#### 3.5.1 Gemini 2.0 Flash
- **Contexto Enriquecido**: Memorias relevantes + estado emocional + perfil
- **Prompts Especializados**: Templates para mantener personalidad consistente
- **Temperatura Baja**: 0.1 para respuestas coherentes
- **Validación Post-Generación**: Verificación de consistencia con memorias

### 3.6 Dashboard de Control

**Funcionalidades en Tiempo Real**:
- **Visualización de Interacciones**: Tarjetas de conversación por usuario
- **Aprobación de Mensajes**: Control manual antes de envío
- **Edición de Respuestas**: Modificación de mensajes generados
- **Configuración Dinámica**:
  - Tiempo de debouncing (default: 120s)
  - Tamaño de context window (20-100)
  - Palabras por globo de mensaje
  - Thresholds de CAG y RAG
- **Métricas y Costos**:
  - Tokens por mensaje
  - Costo acumulado por usuario
  - Estadísticas de uso de memoria
- **Exportación de Datos**: SQL dump para fine-tuning futuro

## 4. Flujo de Datos Detallado

### 4.1 Flujo de Mensaje Entrante
```
1. Usuario envía mensaje en Telegram
2. Userbot.py recibe y almacena en buffer
3. Debouncing timer se reinicia (120s)
4. Al vencer timer, se procesa batch:
   a. Análisis emocional VAD
   b. Extracción de embeddings
   c. Búsqueda en cache (CAG)
   d. Si no hay hit, activación en grafo
   e. Recuperación de memorias relevantes
   f. Generación con Gemini 2.0 Flash
   g. Validación de coherencia
   h. Respuesta al usuario
5. Async: Queue para consolidación de memoria
```

### 4.2 Flujo de Consolidación de Memoria
```
1. Celery worker recibe tarea de consolidación
2. Análisis de patrones en memorias recientes
3. Identificación de temas recurrentes
4. Extracción de conocimiento semántico
5. Creación/actualización de nodos semánticos
6. Establecimiento de relaciones en grafo
7. Aplicación de curvas de olvido
8. Limpieza de memorias obsoletas
```

## 5. Esquema de Datos

### 5.1 Nodo de Memoria en Neo4j
```cypher
(:Memory {
    id: UUID,
    user_id: String,
    content: String,
    embedding: Vector[384],
    
    // Dimensiones emocionales
    valence: Float,
    arousal: Float,
    dominance: Float,
    emotional_weight: Float,
    
    // Metadata temporal
    timestamp: DateTime,
    session_id: String,
    
    // Control de retención
    retention_strength: Float,
    access_count: Integer,
    last_accessed: DateTime,
    
    // Tipo y estado
    memory_type: 'episodic' | 'semantic',
    status: 'active' | 'consolidating' | 'archived'
})
```

### 5.2 Relaciones en el Grafo
```cypher
// Relaciones con propiedades
(:Memory)-[:EMOTIONALLY_SIMILAR {weight: Float, similarity: Float}]->(:Memory)
(:Memory)-[:TEMPORALLY_RELATED {time_distance: Integer, weight: Float}]->(:Memory)
(:Memory)-[:SEMANTICALLY_RELATED {similarity: Float, weight: Float}]->(:Memory)
(:Memory)-[:CONSOLIDATED_FROM {timestamp: DateTime}]->(:Memory)
(:User)-[:HAS_MEMORY {created: DateTime}]->(:Memory)
```

## 6. Configuración y Escalabilidad

### 6.1 Parámetros Configurables
- **Context Window**: 20-100 mensajes (modificable en dashboard)
- **Debouncing Time**: 120 segundos (ajustable por usuario)
- **Consolidation Threshold**: 3 repeticiones mínimas
- **Emotional Weight Threshold**: 0.6 para memorias prioritarias
- **Max Memories per User**: 1000 (con archivado automático)
- **Forgetting Check Interval**: 1 hora

### 6.2 Estrategias de Escalabilidad
- **Sharding por Usuario**: Distribución de datos en múltiples instancias
- **Cache Distribuido**: Redis Cluster para alta disponibilidad
- **Queue Management**: Celery con múltiples workers
- **Batch Processing**: Agrupación de operaciones costosas
- **Índices Optimizados**: HNSW para búsquedas vectoriales rápidas

## 7. Seguridad y Privacidad

### 7.1 Protección de Datos
- **Encriptación en Reposo**: Datos sensibles encriptados en BD
- **Encriptación en Tránsito**: TLS para todas las comunicaciones
- **Aislamiento por Usuario**: Strict data segregation
- **Anonimización**: Opción de anonimizar datos para análisis

### 7.2 Cumplimiento GDPR
- **Derecho al Olvido**: Botón para borrado completo de datos
- **Exportación de Datos**: API para descarga de información personal
- **Consentimiento Explícito**: Opt-in para funciones de memoria
- **Auditoría**: Logs detallados de acceso y modificación

## 8. Monitoreo y Observabilidad

### 8.1 Métricas Clave
- **Latencia de Respuesta**: P50, P95, P99
- **Tasa de Cache Hit**: CAG y memoria semántica
- **Uso de Memoria**: Por usuario y global
- **Precisión Emocional**: Validación contra ground truth
- **Coherencia de Respuestas**: Tasa de correcciones necesarias

### 8.2 Herramientas de Monitoreo
- **Prometheus**: Métricas del sistema
- **Grafana**: Dashboards de visualización
- **ELK Stack**: Análisis de logs
- **Sentry**: Error tracking
- **Custom Dashboard**: Métricas específicas del dominio

## 9. Roadmap de Desarrollo

### Fase 1: MVP (Completado)
- ✓ Arquitectura base con Redis + Neo4j
- ✓ Integración Telegram
- ✓ Análisis emocional básico
- ✓ Sistema de memoria simple

### Fase 2: Memoria Avanzada (En Desarrollo)
- ⚡ Spreading activation con pesos emocionales
- ⚡ Consolidación episódica → semántica
- ⚡ Curvas de olvido adaptativas
- ⚡ Dashboard mejorado

### Fase 3: Optimización (Planificado)
- 🔄 Cache distribuido
- 🔄 Procesamiento paralelo
- 🔄 Compresión de memorias
- 🔄 A/B testing framework

### Fase 4: Características Avanzadas (Futuro)
- 🔮 Memoria visual selectiva
- 🔮 Predicción de estado emocional
- 🔮 Personalización automática
- 🔮 Multi-modalidad completa

## 10. Conclusiones

Esta arquitectura representa un sistema de AI Companion de vanguardia que combina:
- **Comprensión emocional profunda** a través de análisis VAD
- **Memoria similar a la humana** con consolidación y olvido naturales
- **Escalabilidad práctica** para cientos de usuarios simultáneos
- **Control granular** mediante dashboard en tiempo real
- **Privacidad y seguridad** como principios fundamentales

El diseño modular permite evolución continua mientras se mantiene estabilidad en producción, creando una experiencia de usuario que se siente genuinamente personal y emocionalmente inteligente.