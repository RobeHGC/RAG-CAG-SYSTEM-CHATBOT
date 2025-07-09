# userbot20.md - Interfaz de Telegram con Memoria Emocional

## 1. Recepción de Mensajes
El bot recibe mensajes de múltiples usuarios de Telegram y los procesa con análisis emocional integrado.

## 2. Sistema de Debouncing Inteligente
### 2.1 Debouncing Adaptativo
- **Tiempo base**: 120 segundos
- **Reinicio dinámico**: Se reinicia con cada nuevo mensaje del usuario
- **Ajuste emocional**: Mensajes con alta carga emocional (arousal > 0.8) pueden reducir el debouncing a 60 segundos

### 2.2 Batching con Contexto Emocional
- Los mensajes se agrupan por usuario manteniendo su secuencia temporal
- Se analiza la trayectoria emocional del batch completo antes de enviar
- Delay de 6 segundos entre batches para no saturar a Gemini 2.0 Flash

### 2.3 Estructura del Batch
```python
message_batch = {
    'user_id': str,
    'messages': [
        {
            'text': str,
            'timestamp': datetime,
            'has_image': bool,
            'emotional_preview': dict  # VAD rápido
        }
    ],
    'emotional_trajectory': dict,  # Análisis del conjunto
    'priority': float  # Basado en urgencia emocional
}
```

## 3. Capacidad Proactiva Mejorada
### 3.1 Recuperación Inteligente al Reiniciar
- El bot busca el último mensaje procesado en Redis
- Compara timestamps y recupera mensajes no procesados
- **Filtro temporal**: Solo mensajes de las últimas 12 horas
- **Priorización**: Mensajes con contenido emocional se procesan primero

### 3.2 Análisis de Contexto Perdido
- Si hay más de 5 mensajes perdidos, se genera un resumen
- Se extrae el estado emocional probable del gap temporal
- Se ajusta la respuesta inicial considerando el tiempo transcurrido

## 4. Simulación de Typing Mejorada
### 4.1 Cálculo Dinámico de Duración
```python
typing_duration = base_time + (char_count * 0.05) + emotional_adjustment
# Donde:
# - base_time: 2 segundos mínimo
# - char_count: número de caracteres en la respuesta
# - emotional_adjustment: +1-3 segundos para respuestas emotivas
```

### 4.2 Patrones de Typing Realistas
- **Pausas naturales**: Entre 0.5-1.5 segundos entre "pulsos" de typing
- **Variación**: ±20% aleatorio para parecer más humano
- **Interrupción**: Si llega mensaje urgente, puede interrumpir typing

## 5. Separación Inteligente de Globos
### 5.1 Criterios de Separación
- **Por defecto**: Cada 15-20 palabras (configurable en dashboard)
- **Por puntuación**: Después de puntos, signos de exclamación o interrogación
- **Por emoción**: Cambios significativos en tono emocional
- **Por contexto**: Separar ideas o temas diferentes

### 5.2 Coherencia Visual
- Mantener frases completas juntas
- No cortar en medio de ideas
- Respetar estructura de párrafos originales

## 6. Gestión de Imágenes
### 6.1 Procesamiento de Imágenes
- Detección automática de contenido visual
- Análisis básico sin almacenamiento permanente (por defecto)
- Flag para memoria selectiva si la imagen es emocionalmente relevante

### 6.2 Integración con Texto
```python
if message.photo:
    image_context = {
        'has_image': True,
        'description': await analyze_image_content(message.photo),
        'emotional_relevance': calculate_relevance(image_context, user_emotion),
        'should_remember': emotional_relevance > 0.7
    }
```

## 7. Sistema de Prioridades
### 7.1 Cola de Prioridad para Usuarios
- **Alta prioridad**: Mensajes con alta carga emocional negativa
- **Media prioridad**: Conversaciones activas normales
- **Baja prioridad**: Mensajes informativos o neutrales

### 7.2 Gestión de Recursos
- Límite de procesamiento paralelo: 10 usuarios simultáneos
- Queue overflow: Respuesta automática de "alto volumen"
- Recuperación automática de mensajes en cola

## 8. Integración con Supervisor
### 8.1 Formato de Envío al Supervisor
```python
supervisor_payload = {
    'user_id': str,
    'session_id': str,
    'messages': list,
    'emotional_context': {
        'current_state': dict,  # VAD actual
        'trajectory': list,     # Evolución emocional
        'intensity': float      # Intensidad general
    },
    'metadata': {
        'platform': 'telegram',
        'timestamp': datetime,
        'has_media': bool,
        'message_count': int
    }
}
```

### 8.2 Manejo de Respuestas
- Recepción de respuestas estructuradas del supervisor
- Aplicación de reglas de separación de globos
- Simulación de typing antes de enviar
- Confirmación de entrega al supervisor

## 9. Características Avanzadas
### 9.1 Detección de Patrones de Usuario
- Identificación de horarios típicos de conversación
- Detección de temas recurrentes
- Análisis de velocidad de respuesta del usuario

### 9.2 Adaptación Dinámica
- Ajuste de velocidad de respuesta según el ritmo del usuario
- Modificación del estilo según el estado emocional detectado
- Personalización de longitud de mensajes según preferencias observadas

## 10. Monitoreo y Métricas
### 10.1 Métricas del Userbot
- Mensajes recibidos por minuto/hora
- Tiempo promedio de debouncing real
- Tasa de mensajes perdidos en reinicio
- Distribución de prioridades

### 10.2 Logs Estructurados
```python
log_entry = {
    'timestamp': datetime,
    'event_type': 'message_received|batch_sent|typing_started|error',
    'user_id': str,
    'details': dict,
    'emotional_state': dict,
    'performance_metrics': {
        'processing_time': float,
        'queue_depth': int,
        'memory_usage': float
    }
}
```

## 11. Manejo de Errores
### 11.1 Recuperación Resiliente
- Reconexión automática a Telegram
- Persistencia de mensajes no enviados
- Fallback a respuestas genéricas en caso de fallo del supervisor

### 11.2 Límites y Throttling
- Rate limiting por usuario: máximo 30 mensajes por minuto
- Protección contra spam con análisis de patrones
- Blacklist temporal para comportamiento abusivo

## 12. Configuración Dinámica
Todos los parámetros son modificables desde el dashboard sin reiniciar:
- `DEBOUNCE_TIME`: 120 segundos (default)
- `BATCH_DELAY`: 6 segundos
- `MAX_WORDS_PER_BUBBLE`: 20 palabras
- `TYPING_SPEED_FACTOR`: 1.0 (multiplicador)
- `EMOTIONAL_PRIORITY_THRESHOLD`: 0.7
- `MAX_PARALLEL_USERS`: 10
- `MESSAGE_AGE_LIMIT`: 12 horas