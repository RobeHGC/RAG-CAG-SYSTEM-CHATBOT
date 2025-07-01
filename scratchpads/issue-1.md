# Plan de Acción para Issue #1 - Epic 1: Project Foundation & Setup

## 1. Diagnóstico

Este Epic corresponde al Sprint 0 del proyecto: preparar todo el entorno de desarrollo, diseño y configuración antes de escribir la primera línea de código de la aplicación. Según la VISION_GENERAL.md, estamos construyendo un chatbot de compañía con memoria persistente y coherencia verificada, que incluye:

- Un Userbot de Telegram
- Un Orquestador Central
- Sistema de Memoria (Redis + Neo4j)
- Agente Verificador de Coherencia
- Dashboard de Gestión
- Base de datos para fine-tuning

## 2. Análisis de Complejidad y Descomposición

Este Epic es demasiado grande para un solo PR. Se dividirá en las siguientes fases:

- **Fase 1:** Estructura básica del proyecto, configuración del entorno de desarrollo y documentación inicial
- **Fase 2:** Configuración de Docker y docker-compose para todos los servicios
- **Fase 3:** Configuración de bases de datos (PostgreSQL, Redis, Neo4j)
- **Fase 4:** Scripts de inicialización y herramientas de desarrollo
- **Fase 5:** Configuración de CI/CD y pre-commit hooks

Este plan se enfoca ÚNICAMENTE en la Fase 1.

## 3. Definition of Done (DoD) - para la Fase 1

- [x] Estructura de directorios del proyecto creada según la arquitectura definida
- [x] Archivo requirements.txt con dependencias básicas del proyecto
- [x] Archivo .env.example con todas las variables de entorno necesarias documentadas
- [x] README.md con instrucciones de instalación y configuración del entorno de desarrollo
- [x] Configuración básica de logging
- [x] Script de inicialización del entorno virtual
- [x] Documentación de la arquitectura en docs/ARCHITECTURE.md
- [x] Tests básicos de importación de módulos

## 4. Tareas de Implementación - Fase 1

### 4.1 Estructura de Directorios
- [x] **Crear estructura base del proyecto:**
  ```
  bot_provisional/
  ├── src/
  │   ├── __init__.py
  │   ├── userbot/
  │   │   └── __init__.py
  │   ├── orquestador/
  │   │   └── __init__.py
  │   ├── memoria/
  │   │   └── __init__.py
  │   ├── verificador/
  │   │   └── __init__.py
  │   ├── dashboard/
  │   │   └── __init__.py
  │   └── common/
  │       ├── __init__.py
  │       └── config.py
  ├── tests/
  │   ├── __init__.py
  │   └── test_imports.py
  ├── docs/
  │   └── ARCHITECTURE.md
  ├── scripts/
  │   └── setup_dev.sh
  └── config/
      └── logging.yaml
  ```

### 4.2 Archivos de Configuración Base
- [x] **Archivo:** `requirements.txt`
  - **Tarea:** Incluir dependencias básicas (telethon, fastapi, redis, neo4j, spacy, celery, etc.)

- [x] **Archivo:** `.env.example`
  - **Tarea:** Documentar todas las variables de entorno necesarias

- [x] **Archivo:** `README.md`
  - **Tarea:** Documentar instalación, configuración y primeros pasos

### 4.3 Configuración de Logging
- [x] **Archivo:** `config/logging.yaml`
  - **Tarea:** Configurar logging estructurado para todos los componentes

- [x] **Archivo:** `src/common/config.py`
  - **Tarea:** Crear clase de configuración que lea variables de entorno

### 4.4 Scripts de Desarrollo
- [x] **Archivo:** `scripts/setup_dev.sh`
  - **Tarea:** Script para crear entorno virtual e instalar dependencias

## 5. Tareas de Verificación - Fase 1

- [x] **Archivo:** `tests/test_imports.py`
  - **Tarea:** Verificar que todos los módulos se pueden importar correctamente

- [x] **Comando:** `python -m pytest tests/`
  - **Tarea:** Asegurar que los tests básicos pasen

## 6. Enlaces de Referencia

- GitHub Issue: https://github.com/RobeHGC/bot_provisional/issues/1
- Visión General del Proyecto: bitacora/VISION_GENERAL.md