# Bot Provisional 🤖

Un chatbot de compañía con memoria persistente y coherencia verificada, diseñado para mantener conversaciones naturales y consistentes a lo largo del tiempo.

## 🎯 Visión del Proyecto

Este proyecto trasciende los límites de los chatbots convencionales para crear un compañero digital creíble y persistente. No es un simple asistente de preguntas y respuestas, sino una entidad con:

- **Personalidad definida**: Mantiene consistencia en su forma de comunicarse
- **Memoria persistente**: Recuerda interacciones pasadas y aprende del usuario
- **Coherencia verificada**: Valida sus propias respuestas para evitar contradicciones
- **Supervisión humana**: Sistema transparente con capacidad de mejora continua

## 🏗️ Arquitectura

El sistema está compuesto por varios módulos interconectados:

- **Userbot de Telegram**: Interfaz de comunicación con el usuario
- **Orquestador Central**: Coordina todos los componentes del sistema
- **Sistema de Memoria**: Caché (Redis) + Grafo de conocimiento (Neo4j)
- **Agente Verificador de Coherencia**: Valida las respuestas antes de enviarlas
- **Dashboard de Gestión**: Interfaz web para supervisión y curación
- **Base de datos de Fine-tuning**: Almacena conversaciones curadas para mejorar el modelo

Para más detalles, consulta [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 📋 Requisitos del Sistema

### Con Docker (recomendado) 🐳
- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM mínimo, 8GB recomendado

### Instalación Local
- Python 3.10 o superior
- PostgreSQL 14+
- Redis 7+
- Neo4j 5+

## 🚀 Instalación Rápida

### 1. Clonar el repositorio

```bash
git clone https://github.com/RobeHGC/bot_provisional.git
cd bot_provisional
```

### 2. Configurar el entorno

```bash
# Ejecutar el script de setup (crea venv e instala dependencias)
./scripts/setup_dev.sh

# O manualmente:
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar con tus valores
nano .env  # o tu editor preferido
```

### 4. Configurar Telegram API

1. Ve a https://my.telegram.org/apps
2. Crea una nueva aplicación
3. Copia el `API ID` y `API Hash` a tu archivo `.env`

### 5. Configurar bases de datos

#### Opción A: Con Docker (recomendado) 🐳

```bash
# Desarrollo: Levantar todos los servicios básicos
docker-compose up -d

# O solo las bases de datos
docker-compose up -d postgres redis neo4j

# Desarrollo con hot-reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Ver logs
docker-compose logs -f

# Parar servicios
docker-compose down
```

#### Opción B: Instalación manual

- **PostgreSQL**: Instalar y crear la base de datos `bot_provisional`
- **Redis**: Instalar y ejecutar con configuración por defecto
- **Neo4j**: Instalar y configurar con las credenciales del `.env`

## 🏃 Ejecutar el Proyecto

### Con Docker (recomendado) 🐳

```bash
# Desarrollo completo (todos los servicios)
docker-compose --profile full up -d

# Solo servicios básicos (sin userbot/celery)
docker-compose up -d

# Con monitoring (incluye Flower para Celery)
docker-compose --profile monitoring up -d

# Producción
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Acceder a los servicios:
# - Dashboard: http://localhost:8000
# - Neo4j Browser: http://localhost:7474
# - Flower (monitoring): http://localhost:5555
```

### Instalación Local (sin Docker)

#### Userbot de Telegram

```bash
python -m src.userbot
```

#### Dashboard de Gestión

```bash
python -m src.dashboard
# Acceder en: http://localhost:8000
```

#### Orquestador Central

```bash
python -m src.orquestador
```

## 🧪 Tests

```bash
# Ejecutar todos los tests
pytest

# Con coverage
pytest --cov=src

# Tests específicos
pytest tests/test_imports.py -v
```

## 🛠️ Desarrollo

### Estructura del Proyecto

```
bot_provisional/
├── src/               # Código fuente
│   ├── userbot/      # Bot de Telegram
│   ├── orquestador/  # Coordinador central
│   ├── memoria/      # Sistema de memoria
│   ├── verificador/  # Agente de coherencia
│   ├── dashboard/    # Interfaz web
│   └── common/       # Utilidades compartidas
├── tests/            # Tests unitarios e integración
├── docs/             # Documentación
├── scripts/          # Scripts de utilidad
├── config/           # Archivos de configuración
└── bitacora/         # Documentación del proyecto
```

### Estilo de Código

- Usamos `black` para formateo automático
- `flake8` para linting
- `mypy` para type checking

```bash
# Formatear código
black src/

# Verificar estilo
flake8 src/

# Type checking
mypy src/
```

## 🐳 Docker - Guía Completa

### Configuraciones Disponibles

1. **Desarrollo básico**: Solo bases de datos
   ```bash
   docker-compose up -d postgres redis neo4j
   ```

2. **Desarrollo completo**: Todos los servicios con hot-reload
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml --profile full up -d
   ```

3. **Producción**: Optimizado para deployment
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

### Comandos Útiles

```bash
# Ver estado de los servicios
docker-compose ps

# Logs de todos los servicios
docker-compose logs -f

# Logs de un servicio específico
docker-compose logs -f app

# Reiniciar un servicio
docker-compose restart app

# Reconstruir imágenes
docker-compose build --no-cache

# Limpiar volúmenes (¡CUIDADO: borra datos!)
docker-compose down -v

# Ejecutar comandos dentro del contenedor
docker-compose exec app python -m pytest
docker-compose exec postgres psql -U postgres -d bot_provisional
```

### Puertos Expuestos

- **Dashboard**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Neo4j HTTP**: http://localhost:7474
- **Neo4j Bolt**: bolt://localhost:7687
- **Flower** (monitoring): http://localhost:5555

### Volúmenes Persistentes

- `bot_postgres_data`: Datos de PostgreSQL
- `bot_redis_data`: Datos de Redis
- `bot_neo4j_data`: Datos de Neo4j
- `bot_app_logs`: Logs de la aplicación
- `bot_userbot_sessions`: Sesiones de Telegram

### Troubleshooting

**Problema**: Los servicios no se conectan
```bash
# Verificar la red
docker network ls
docker network inspect bot_provisional_network

# Reiniciar la red
docker-compose down && docker-compose up -d
```

**Problema**: Permisos de archivos
```bash
# Cambiar ownership (Linux/Mac)
sudo chown -R $USER:$USER logs/ data/
```

**Problema**: Base de datos no inicializa
```bash
# Limpiar volumen de PostgreSQL y reiniciar
docker-compose down
docker volume rm bot_postgres_data
docker-compose up -d postgres
```

## 📚 Documentación

- [Arquitectura del Sistema](docs/ARCHITECTURE.md)
- [Visión General del Proyecto](bitacora/VISION_GENERAL.md)
- [API Reference](docs/api/) (próximamente)
- [Guía de Contribución](CONTRIBUTING.md) (próximamente)

## 🤝 Contribuir

Este es un proyecto en desarrollo activo. Si quieres contribuir:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo desarrollo privado. Todos los derechos reservados.

## 👥 Equipo

- Roberto H. - Desarrollador Principal

## 🔗 Enlaces

- [Issues](https://github.com/RobeHGC/bot_provisional/issues)
- [Roadmap](https://github.com/RobeHGC/bot_provisional/projects) (próximamente)

---

**Estado del Proyecto**: 🚧 En desarrollo - Sprint 0 (Foundation & Setup)