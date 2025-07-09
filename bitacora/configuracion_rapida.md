# quick_start.md - Guía de Inicio Rápido del AI Companion

## 📋 Pre-requisitos

### Software Requerido
- Python 3.10+
- Redis 7.0+
- Neo4j 5.0+ (Community o Enterprise)
- Node.js 18+ (para el dashboard)
- Docker y Docker Compose (opcional pero recomendado)

### Cuentas y APIs
- Telegram Bot Token (de @BotFather)
- Google Cloud Account con Gemini API habilitada
- Neo4j Aura (opcional) o instalación local

### Recursos Mínimos
- RAM: 8GB mínimo, 16GB recomendado
- CPU: 4 cores mínimo
- Almacenamiento: 50GB SSD
- Red: Conexión estable para APIs

## 🚀 Instalación Rápida (15 minutos)

### Paso 1: Clonar y Configurar el Entorno

```bash
# Clonar el repositorio
git clone https://github.com/tuorganizacion/ai-companion.git
cd ai-companion

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
npm install --prefix dashboard
```

### Paso 2: Configuración con Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/your_password_here
      - NEO4J_dbms_memory_pagecache_size=1G
      - NEO4J_dbms_memory_heap_max__size=1G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs

  app:
    build: .
    depends_on:
      - redis
      - neo4j
    environment:
      - REDIS_URL=redis://redis:6379
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_PASSWORD=your_password_here
    volumes:
      - ./config:/app/config
      - ./prompts:/app/prompts

volumes:
  redis_data:
  neo4j_data:
  neo4j_logs:
```

Iniciar servicios:
```bash
docker-compose up -d
```

### Paso 3: Configuración de Variables de Entorno

```bash
# .env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Gemini
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash

# Redis
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=optional_password

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# Dashboard
DASHBOARD_PORT=3000
DASHBOARD_SECRET_KEY=generate_a_random_key_here

# Configuración de Memoria
CONTEXT_WINDOW_SIZE=50
MEMORY_CONSOLIDATION_THRESHOLD=3
EMOTIONAL_WEIGHT_FACTOR=0.7
DEBOUNCE_TIME=120

# Embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
```

### Paso 4: Inicialización de la Base de Datos

```bash
# Ejecutar script de inicialización
python scripts/init_database.py

# Esto creará:
# - Índices en Neo4j
# - Estructuras en Redis
# - Usuario admin para dashboard
# - Datos de prueba (opcional)
```

## 🔧 Configuración Inicial

### 1. Configurar Personalidad de Nadia

```bash
# Editar prompts/core/personality.txt
nano prompts/core/personality.txt

# Verificar que contenga:
# - Información básica (24 años, medicina, Monterrey)
# - Rasgos de personalidad
# - Estilo de comunicación
```

### 2. Configurar el Bot de Telegram

```python
# config/telegram_config.py
TELEGRAM_CONFIG = {
    'token': os.getenv('TELEGRAM_BOT_TOKEN'),
    'username': 'NadiaCompanionBot',  # Sin @
    'webhook': {
        'enabled': False,  # True para producción
        'url': 'https://tudominio.com/webhook',
        'port': 8443
    },
    'commands': [
        ('start', 'Iniciar conversación con Nadia'),
        ('reset', 'Reiniciar contexto de conversación'),
        ('status', 'Ver estado de la memoria'),
        ('help', 'Mostrar ayuda')
    ]
}
```

### 3. Inicializar Neo4j con Esquema

```cypher
# scripts/neo4j_init.cypher
// Crear constraints
CREATE CONSTRAINT memory_id IF NOT EXISTS 
FOR (m:Memory) REQUIRE m.id IS UNIQUE;

CREATE CONSTRAINT user_id IF NOT EXISTS 
FOR (u:User) REQUIRE u.telegram_id IS UNIQUE;

// Crear índices
CREATE INDEX memory_embedding IF NOT EXISTS 
FOR (m:Memory) ON (m.embedding);

CREATE INDEX memory_timestamp IF NOT EXISTS 
FOR (m:Memory) ON (m.timestamp);

CREATE INDEX emotional_state IF NOT EXISTS 
FOR (m:Memory) ON (m.valence, m.arousal, m.dominance);

// Crear vector index
CALL db.index.vector.createNodeIndex(
  'memory_embeddings',
  'Memory',
  'embedding',
  384,
  'cosine'
);
```

Ejecutar:
```bash
python scripts/run_cypher.py scripts/neo4j_init.cypher
```

## 🏃‍♂️ Primera Ejecución

### 1. Iniciar el Sistema

```bash
# Terminal 1: Iniciar el supervisor
python supervisor.py

# Terminal 2: Iniciar el userbot
python userbot.py

# Terminal 3: Iniciar workers de Celery
celery -A tasks worker --loglevel=info

# Terminal 4: Iniciar el dashboard
npm start --prefix dashboard
```

### 2. Verificar que Todo Funciona

```bash
# Check de salud del sistema
python scripts/health_check.py

# Output esperado:
✅ Redis: Connected
✅ Neo4j: Connected (0 memories)
✅ Gemini API: Authenticated
✅ Telegram Bot: Active (@NadiaCompanionBot)
✅ Dashboard: Running on http://localhost:3000
✅ Celery: 4 workers active
```

### 3. Primer Test con el Bot

1. Abre Telegram y busca @NadiaCompanionBot
2. Envía `/start`
3. Deberías recibir:
   ```
   ¡Hola! Soy Nadia 😊 
   Mucho gusto en conocerte. ¿Cómo has estado?
   ```

### 4. Acceder al Dashboard

1. Navega a http://localhost:3000
2. Login con:
   - Usuario: `admin`
   - Password: `admin123` (cambiar inmediatamente)
3. Deberías ver:
   - Panel de conversaciones vacío
   - Métricas en cero
   - Configuración editable

## 🧪 Pruebas Iniciales

### Test 1: Memoria Emocional Básica

```python
# tests/test_emotional_memory.py
def test_emotional_memory():
    # Enviar mensaje con alta carga emocional
    send_message("Estoy muy feliz, acabo de graduarme!")
    
    # Esperar respuesta
    response = wait_for_response()
    assert "felicit" in response.lower()
    
    # Verificar que se guardó la memoria
    memory = get_latest_memory()
    assert memory['valence'] > 0.7
    assert memory['arousal'] > 0.6
```

### Test 2: Continuidad de Conversación

```bash
# Enviar serie de mensajes para probar contexto
python tests/conversation_flow_test.py

# Verifica:
# - Debouncing funciona (120s)
# - Contexto se mantiene
# - Memorias se relacionan
```

### Test 3: Dashboard en Tiempo Real

1. Inicia una conversación en Telegram
2. Observa en el dashboard:
   - Aparece tarjeta de usuario
   - Estado emocional se actualiza
   - Puedes aprobar/editar mensajes

## 🔍 Troubleshooting Común

### Error: "No connection to Redis"
```bash
# Verificar que Redis está corriendo
redis-cli ping
# Debe responder: PONG

# Si no:
sudo systemctl start redis
# o
docker-compose up -d redis
```

### Error: "Neo4j authentication failed"
```bash
# Resetear password de Neo4j
docker-compose exec neo4j cypher-shell -u neo4j -p neo4j
# ALTER USER neo4j SET PASSWORD 'nueva_password';

# Actualizar .env
```

### Error: "Gemini API quota exceeded"
```python
# config/gemini_config.py
FALLBACK_RESPONSES = {
    'greeting': "¡Hola! Disculpa, estoy teniendo algunos problemitas técnicos 😅",
    'default': "Perdón, mi cerebro de estudiante necesita un break. ¿Podemos intentar en un momento?"
}
```

### Bot no responde
```bash
# Verificar webhook
curl https://api.telegram.org/bot{TOKEN}/getWebhookInfo

# Para desarrollo, usar polling:
# config/telegram_config.py
WEBHOOK_ENABLED = False
```

## 📊 Monitoreo Básico

### 1. Logs en Tiempo Real

```bash
# Ver todos los logs
docker-compose logs -f

# Solo userbot
docker-compose logs -f app | grep userbot

# Solo errores
docker-compose logs -f | grep ERROR
```

### 2. Métricas Rápidas

```bash
# Estado de memoria
python scripts/memory_stats.py

# Output:
Users: 5
Total Memories: 127
- Episodic: 98
- Semantic: 29
Avg Memories/User: 25.4
Cache Hit Rate: 34%
```

### 3. Dashboard Metrics

Acceder a: http://localhost:3000/metrics

Métricas clave a observar:
- Response time < 3s
- Cache hit rate > 30%
- Memory consolidation rate
- Emotional coherence score

## 🚀 Próximos Pasos

### 1. Personalización
- [ ] Ajustar personalidad en `prompts/core/personality.txt`
- [ ] Configurar modismos regionales
- [ ] Afinar umbrales emocionales

### 2. Optimización
- [ ] Aumentar cache Redis
- [ ] Configurar índices adicionales
- [ ] Ajustar parámetros de consolidación

### 3. Producción
- [ ] Configurar HTTPS
- [ ] Establecer backups automáticos
- [ ] Configurar monitoreo avanzado
- [ ] Implementar rate limiting

## 📚 Recursos Adicionales

- [Documentación Completa](./docs/README.md)
- [API Reference](./api_reference.md)
- [Guía de Arquitectura](./architecture_master.md)
- [FAQ y Soluciones](./troubleshooting.md)

## 🆘 Soporte

Si encuentras problemas:
1. Revisa los logs: `docker-compose logs`
2. Consulta el [Troubleshooting Guide](./troubleshooting.md)
3. Abre un issue en GitHub
4. Únete a nuestro Discord: [link]

---

**¡Felicidades!** 🎉 Ya tienes tu AI Companion con memoria emocional funcionando. 

Tiempo estimado hasta aquí: 15-30 minutos.

Para configuración avanzada y optimización, consulta la [Guía de Implementación Completa](./implementation_guide.md).