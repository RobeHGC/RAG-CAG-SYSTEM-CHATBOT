# -----------------------------------------------------------------------------
# Metodología: Flujo de trabajo completo para analizar y resolver un issue de GitHub
# -----------------------------------------------------------------------------
description: End-to-end workflow to analyze & fix a GitHub issue
allowed-tools:
  - Bash(gh issue view:*)
  - Bash(gh issue list:*)
  - Bash(gh issue comment:*)
  - Bash(gh issue create:*) # <-- Herramienta nueva añadida
  - Bash(gh pr create:*)
  - Bash(git checkout:*)
  - Bash(git add:*)
  - Bash(git commit:*)
  - Bash(git push:*)
  - Bash(git grep:*)
  - Bash(grep:*)
  - Bash(pytest:*)
  - Edit
---

# =============================================================================
# FASE 1: COMPRENSIÓN Y PLANIFICACIÓN
# =============================================================================

# 1.1. Obtener Visión Global
!> Empezar por el contexto estratégico. Buscar la visión general del proyecto en la carpeta 'bitacora'.
- !`grep -r "VISION_GENERAL" bitacora/ || true`

# 1.2. Analizar el Issue de GitHub y su Jerarquía
!> Entender la tarea específica y su relación con el Epic padre.
- !`gh issue view $ARGUMENTS --json title,body,comments,labels`

# 1.3. Investigar Estado Actual del Proyecto
!> Analizar el código existente para entender qué se ha hecho ya y evitar duplicar trabajo.
- !`git grep -n "$ARGUMENTS" || true`

# 1.4. Crear un Plan de Acción Detallado
!> Usar 'think harder' para un análisis profundo. Si el issue es muy grande, proponer una descomposición en fases.
!think harder
!`EDIT -f scratchpads/issue-$ARGUMENTS.md << 'EOT'
# Plan de Acción para Issue #$ARGUMENTS

## 1. Diagnóstico
<!-- 
EJEMPLO: Bórralo y reemplázalo con el análisis real para este issue.
Describe aquí la causa raíz del problema o el objetivo de la nueva funcionalidad.
-->

## 2. Análisis de Complejidad y Descomposición (NUEVA SECCIÓN)
<!--
EJEMPLO: Si el issue es grande, úsalo. Si no, elimina esta sección.
Este issue es demasiado grande para un solo PR. Se tratará como un Epic y se dividirá en las siguientes fases. Este plan se enfoca ÚNICAMENTE en la Fase 1.
- **Fase 1:** Crear la estructura de base de datos y los endpoints API básicos. (Este plan)
- **Fase 2:** Desarrollar la interfaz de usuario en el Dashboard. (Se creará un nuevo issue para esto)
- **Fase 3:** Implementar las pruebas End-to-End. (Se creará un nuevo issue para esto)
-->

## 3. Definition of Done (DoD) - para la Fase Actual
<!--
EJEMPLO: Bórralo y reemplázalo con los criterios de éxito reales para la fase actual.
-->
- [ ] El código de la Fase 1 está implementado según las tareas.
- [ ] Se han creado y añadido nuevos tests que cubren la funcionalidad de la Fase 1.
- [ ] Toda la suite de tests pasa sin errores.
- [ ] El Pull Request ha sido aprobado por un revisor.

## 4. Tareas de Implementación - para la Fase Actual
<!--
EJEMPLO: Bórralo y reemplázalo con la lista de tareas real para la fase actual.
-->
- [ ] **Archivo:** `src/orquestador/main.py`
  - **Tarea:** En la función `handle_chat_request`, envolver la llamada a `llm_actor.generate()` en un bloque `try...except`.

## 5. Tareas de Verificación - para la Fase Actual
<!--
EJEMPLO: Bórralo y reemplázalo con las pruebas reales que se crearán para la fase actual.
-->
- [ ] **Archivo:** `tests/test_orquestador.py`
  - **Tarea:** Crear un nuevo test `test_chat_endpoint_handles_llm_timeout`.

## 6. Enlaces de Referencia
- GitHub Issue: [Link al issue #$ARGUMENTS en GitHub]
EOT`

# 1.5. Crear Issues para Fases Futuras (NUEVO PASO)
!> Si se ha propuesto una descomposición en el scratchpad, crear los issues para las fases futuras.
- !`# (Lógica condicional) Si el scratchpad contiene la sección "Descomposición"...`
- !`gh issue create --title "Fase 2 de Epic #$ARGUMENTS: Desarrollar la interfaz de usuario" --body "Este issue rastrea el trabajo de la Fase 2 del Epic #$ARGUMENTS." --label "epic-child"`
- !`gh issue create --title "Fase 3 de Epic #$ARGUMENTS: Implementar pruebas E2E" --body "Este issue rastrea el trabajo de la Fase 3 del Epic #$ARGUMENTS." --label "epic-child"`

# 1.6. Sincronizar Plan con el Epic Padre
!> Publicar el plan de acción de la FASE 1 y los enlaces a los nuevos issues en el Epic padre.
- !`# Identificar el número del issue padre (ej. de una etiqueta 'epic:123'). Asignarlo a la variable $PARENT_ISSUE_NUMBER.`
- !`gh issue comment $PARENT_ISSUE_NUMBER --body-file scratchpads/issue-$ARGUMENTS.md`

# =============================================================================
# FASE 2: EJECUCIÓN DEL CÓDIGO (para la Fase 1)
# =============================================================================

# 2.1. Preparar el Entorno de Desarrollo
!`git checkout -b issue/$ARGUMENTS`

# 2.2. Implementar las Tareas del Plan
!> Implementar cada sub-tarea del scratchpad para la FASE ACTUAL.
!`# (Ejemplo) EDIT src/orquestador/main.py`
!`git add -A && git commit -m "feat(Fase 1): Añadir manejo de errores para #$ARGUMENTS"`

# =============================================================================
# FASE 3: VERIFICACIÓN RIGUROSA (para la Fase 1)
# =============================================================================

# 3.1. Crear/Actualizar Pruebas
!> Ninguna nueva funcionalidad se sube sin un test que compruebe que funciona.
!`# (Ejemplo) EDIT tests/test_orquestador.py`
!`git add -A && git commit -m "test(Fase 1): Añadir test para el manejo de timeouts en #$ARGUMENTS"`

# 3.2. Ejecutar Pruebas de Regresión Completa
!> Ejecutar toda la suite de tests. Iterar hasta que todo esté en verde.
!`pytest -q`

# =============================================================================
# FASE 4: DESPLIEGUE Y CIERRE (para la Fase 1)
# =============================================================================

# 4.1. Crear un Pull Request para Revisión
!> Subir la rama y abrir un PR en modo borrador (draft) para la revisión humana.
!`git push --set-upstream origin issue/$ARGUMENTS`
!`gh pr create --title "Solución para Fase 1 de Issue #$ARGUMENTS: (Título del Issue)" --body "Este PR resuelve la FASE 1 del issue #$ARGUMENTS. El plan de acción detallado se encuentra en el scratchpad adjunto. @revisores" --draft`

# 4.2. Esperar Aprobación y Cerrar
!> Cuando el PR sea aprobado y fusionado, el trabajo de esta fase está completo. El issue original (Epic) permanecerá abierto hasta que todas las fases se completen.