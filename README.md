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

- Python 3.10 o superior
- PostgreSQL 14+
- Redis 7+
- Neo4j 5+
- Docker y Docker Compose (opcional pero recomendado)

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

#### Opción A: Con Docker (recomendado)

```bash
# Próximamente en Fase 2
docker-compose up -d
```

#### Opción B: Instalación manual

- **PostgreSQL**: Instalar y crear la base de datos `bot_provisional`
- **Redis**: Instalar y ejecutar con configuración por defecto
- **Neo4j**: Instalar y configurar con las credenciales del `.env`

## 🏃 Ejecutar el Proyecto

### Userbot de Telegram

```bash
python -m src.userbot
```

### Dashboard de Gestión

```bash
python -m src.dashboard
# Acceder en: http://localhost:8000
```

### Orquestador Central

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