# dashboard20.md - Dashboard de Control con Gestión de Memoria Emocional

## 1. Funciones Principales del Dashboard

### 1.1 Visualización de Interacciones - Tarjetas Enriquecidas
```typescript
// Estructura de tarjeta de interacción
interface InteractionCard {
    userId: string;
    nickname: string;  // Editable
    avatar: string;    // Generado o personalizado
    currentSession: {
        startTime: Date;
        messageCount: number;
        emotionalState: {
            valence: number;    // -1 a 1
            arousal: number;    // 0 a 1
            dominance: number;  // 0 a 1
            trend: 'improving' | 'stable' | 'declining';
        };
        lastMessage: {
            content: string;
            timestamp: Date;
            hasImage: boolean;
        };
        pendingResponse: {
            content: string;
            confidence: number;
            requiresApproval: boolean;
            suggestedEdits?: string[];
        };
    };
    historicalMetrics: {
        totalInteractions: number;
        averageSessionLength: number;
        emotionalBaseline: EmotionalState;
        topTopics: string[];
    };
}
```

#### 1.1.1 Sistema de Nicknames y Personalización
- **Edición inline**: Click en el nombre para editar
- **Sugerencias automáticas**: Basadas en cómo el usuario se refiere a sí mismo
- **Avatar generation**: Emoji o imagen basada en personalidad detectada
- **Tags personalizados**: Etiquetas para categorizar usuarios
- **Notas privadas**: Campo para observaciones del operador

### 1.2 Aprobación de Mensajes con Contexto
```typescript
interface MessageApprovalPanel {
    // Vista de contexto completo
    contextWindow: Message[];  // Últimos N mensajes
    
    // Mensaje propuesto
    proposedMessage: {
        content: string;
        emotionalTone: EmotionalState;
        memoriesUsed: MemoryReference[];
        generationMetadata: {
            model: string;
            confidence: number;
            alternativeVersions: string[];
        };
    };
    
    // Controles de aprobación
    actions: {
        approve: () => void;
        edit: () => void;
        regenerate: () => void;
        reject: (reason: string) => void;
    };
    
    // Análisis de impacto
    impactAnalysis: {
        emotionalImpact: 'positive' | 'neutral' | 'negative';
        coherenceScore: number;
        riskFactors: string[];
    };
}
```

### 1.3 Editor de Mensajes Avanzado
```typescript
interface MessageEditor {
    // Editor principal
    content: string;
    
    // Herramientas de edición
    tools: {
        emotionalToneAdjuster: {
            targetValence: number;
            targetArousal: number;
            applySuggestions: () => void;
        };
        
        memoryInjector: {
            searchMemories: (query: string) => Memory[];
            injectMemory: (memory: Memory) => void;
        };
        
        styleAdapter: {
            formality: 'casual' | 'neutral' | 'formal';
            wordingStyle: 'concise' | 'descriptive' | 'playful';
            apply: () => void;
        };
    };
    
    // Vista previa en tiempo real
    preview: {
        bubbles: string[];  // Mensaje separado en globos
        estimatedTypingTime: number;
        emotionalImpact: EmotionalState;
    };
    
    // Validación
    validation: {
        coherenceCheck: boolean;
        lengthCheck: boolean;
        toneConsistency: boolean;
        warnings: string[];
    };
}
```

### 1.4 Sistema de Aprobación Inteligente
- **Auto-aprobación condicional**: Mensajes con confidence > 0.95
- **Aprobación por lotes**: Para conversaciones de bajo riesgo
- **Escalación automática**: Mensajes sensibles requieren supervisión
- **Historial de decisiones**: Track record de aprobaciones/rechazos

### 1.5 Control de Tiempo de Debouncing
```typescript
interface DebouncingControl {
    global: {
        defaultTime: number;  // 120s default
        range: [min: number, max: number];  // [30s, 300s]
    };
    
    perUser: {
        [userId: string]: {
            customTime: number;
            reason: string;  // "Usuario ansioso", "Conversación profunda"
            autoAdjust: boolean;
        };
    };
    
    rules: {
        emotionalUrgency: {
            enabled: boolean;
            highArousalReduction: number;  // -60s para arousal > 0.8
        };
        
        timeBasedAdjustment: {
            nightTimeIncrease: number;  // +30s entre 22:00-06:00
            weekendDecrease: number;    // -20s en weekends
        };
    };
}
```

### 1.6 Control de Separación de Globos
```typescript
interface BubbleControl {
    global: {
        wordsPerBubble: number;  // Default: 20
        range: [5, 50];
    };
    
    smartSeparation: {
        enabled: boolean;
        rules: {
            respectSentences: boolean;
            emotionalBreaks: boolean;  // Separar por cambios emocionales
            topicalBreaks: boolean;    // Separar por cambios de tema
            maxBubbles: number;        // Límite máximo
        };
    };
    
    preview: {
        showRealTime: boolean;
        animateTyping: boolean;
    };
}
```

### 1.7 Monitor de Costos con Proyecciones
```typescript
interface CostMonitor {
    realTime: {
        tokensPerMessage: {
            input: number;
            output: number;
            embedding: number;
        };
        
        costPerMessage: {
            usd: number;
            breakdown: {
                llm: number;
                embedding: number;
                storage: number;
            };
        };
        
        accumulated: {
            daily: number;
            weekly: number;
            monthly: number;
            projection: {
                monthEnd: number;
                trend: 'increasing' | 'stable' | 'decreasing';
            };
        };
    };
    
    perUser: {
        [userId: string]: {
            totalTokens: number;
            totalCost: number;
            averagePerInteraction: number;
            rank: number;  // Posición en consumo
        };
    };
    
    optimization: {
        suggestions: string[];
        potentialSavings: number;
        implementOptimizations: () => void;
    };
}
```

### 1.8 Control de Context Window
```typescript
interface ContextWindowControl {
    global: {
        size: number;  // 20-100
        compressionEnabled: boolean;
        summarizationThreshold: number;
    };
    
    perUser: {
        [userId: string]: {
            customSize: number;
            retentionStrategy: 'emotional' | 'temporal' | 'balanced';
            importanceThreshold: number;
        };
    };
    
    visualization: {
        showMemoryMap: boolean;
        highlightImportant: boolean;
        previewCompression: () => string;
    };
}
```

### 1.9 Gestión de Datos para Fine-tuning
```typescript
interface DataManagement {
    collection: {
        filters: {
            dateRange: [Date, Date];
            users: string[];
            emotionalStates: EmotionalState[];
            minQuality: number;
            excludeEdited: boolean;
        };
        
        stats: {
            totalInteractions: number;
            uniqueUsers: number;
            averageQuality: number;
            dataSize: string;
        };
    };
    
    export: {
        formats: ['json', 'csv', 'parquet', 'huggingface'];
        
        schema: {
            includeMetadata: boolean;
            includeEmotions: boolean;
            includeMemories: boolean;
            anonymize: boolean;
        };
        
        process: () => Promise<DownloadLink>;
    };
    
    quality: {
        autoLabeling: boolean;
        manualReview: {
            queue: Interaction[];
            label: (quality: 1-5) => void;
        };
    };
}
```

## 2. Cambios sin Reiniciar (Hot Reload)
### 2.1 Sistema de Configuración Dinámica
```typescript
class ConfigurationManager {
    private watchers: Map<string, Function[]> = new Map();
    
    updateConfig(key: string, value: any) {
        // Validar cambio
        if (this.validateConfig(key, value)) {
            // Aplicar cambio
            this.applyConfig(key, value);
            
            // Notificar watchers
            this.notifyWatchers(key, value);
            
            // Persistir
            this.persistConfig(key, value);
            
            // Log
            this.logConfigChange(key, value);
        }
    }
    
    // Configuraciones hot-reloadable
    hotReloadConfigs = {
        'debounceTime': true,
        'contextWindowSize': true,
        'bubbleWordCount': true,
        'cacheThreshold': true,
        'ragThreshold': true,
        'emotionalWeights': true,
        'memoryConsolidation': true,
        'apiKeys': false,  // Requiere reinicio
        'databaseConnections': false
    };
}
```

## 3. Control de Thresholds Semánticos
### 3.1 CACHE HIT del Semantic CAG
```typescript
interface SemanticCacheControl {
    threshold: {
        current: number;  // 0.85 default
        range: [0.5, 0.99];
        
        adjustment: {
            mode: 'manual' | 'adaptive';
            
            adaptive: {
                targetHitRate: number;  // 0.3 = 30% hit rate
                adjustmentRate: number;  // 0.01 per iteration
                windowSize: number;     // Last 1000 queries
            };
        };
    };
    
    monitoring: {
        currentHitRate: number;
        recentHits: CacheHit[];
        
        visualization: {
            histogram: number[];
            heatmap: boolean;
        };
    };
    
    analysis: {
        missedOpportunities: Query[];  // Queries just below threshold
        falsePositives: Query[];       // Poor quality hits
        
        recommendations: {
            suggestedThreshold: number;
            estimatedImprovement: number;
        };
    };
}
```

### 3.2 Threshold del RAG
```typescript
interface RAGThresholdControl {
    similarity: {
        current: number;  // 0.7 default
        range: [0.3, 0.95];
        
        perCategory: {
            factual: number;     // Higher for facts
            emotional: number;   // Lower for emotions
            temporal: number;    // Medium for time-based
        };
    };
    
    spreading: {
        activationThreshold: number;  // 0.3
        decayFactor: number;         // 0.6
        maxHops: number;             // 3
        
        visualization: {
            showActivationGraph: boolean;
            animateSpread: boolean;
            nodeColorByActivation: boolean;
        };
    };
    
    performance: {
        averageNodesActivated: number;
        averagePathLength: number;
        timePerQuery: number;
        
        optimization: {
            pruneWeakPaths: boolean;
            cacheFrequentPaths: boolean;
            parallelizeSearch: boolean;
        };
    };
}
```

## 4. Visualizaciones Avanzadas del Dashboard

### 4.1 Vista de Red Emocional
```typescript
interface EmotionalNetworkView {
    // Grafo 3D de estados emocionales
    nodes: {
        users: UserNode[];
        emotions: EmotionNode[];
        memories: MemoryNode[];
    };
    
    edges: {
        interactions: Edge[];
        emotionalTransitions: Edge[];
        memoryActivations: Edge[];
    };
    
    controls: {
        timeRange: [Date, Date];
        filterByEmotion: EmotionalState[];
        animationSpeed: number;
        layout: 'force' | 'hierarchy' | 'circular';
    };
}
```

### 4.2 Timeline de Memorias
```typescript
interface MemoryTimeline {
    view: 'user' | 'global';
    
    events: {
        episodic: TimelineEvent[];
        semantic: TimelineEvent[];
        consolidations: ConsolidationEvent[];
    };
    
    filters: {
        emotionalIntensity: [min: number, max: number];
        memoryTypes: MemoryType[];
        searchQuery: string;
    };
    
    interactions: {
        hover: (event: TimelineEvent) => void;
        click: (event: TimelineEvent) => void;
        zoom: (range: [Date, Date]) => void;
    };
}
```

### 4.3 Análisis de Coherencia
```typescript
interface CoherenceAnalytics {
    overview: {
        totalDeclarations: number;
        coherenceRate: number;
        correctionsNeeded: number;
        autoResolved: number;
    };
    
    patterns: {
        commonInconsistencies: Pattern[];
        timeBasedErrors: Pattern[];
        emotionalConflicts: Pattern[];
    };
    
    userSpecific: {
        [userId: string]: {
            consistencyScore: number;
            problemAreas: string[];
            improvements: Trend;
        };
    };
}
```

## 5. Alertas y Notificaciones Inteligentes

### 5.1 Sistema de Alertas
```typescript
interface AlertSystem {
    types: {
        emotional: {
            criticalEmotionalState: boolean;  // User in distress
            emotionalVolatility: boolean;      // Rapid mood swings
            prolongedNegativeState: boolean;   // Extended sadness/anger
        };
        
        operational: {
            highLatency: boolean;
            cacheHitRateLow: boolean;
            memoryQuotaExceeded: boolean;
            costThresholdReached: boolean;
        };
        
        quality: {
            lowCoherenceScore: boolean;
            frequentCorrections: boolean;
            userComplaint: boolean;
        };
    };
    
    routing: {
        email: string[];
        slack: string;
        inApp: boolean;
        severity: 'info' | 'warning' | 'critical';
    };
}
```

## 6. Herramientas de Análisis y Debug

### 6.1 Inspector de Memorias
```typescript
interface MemoryInspector {
    search: {
        byUser: (userId: string) => Memory[];
        byEmotion: (emotion: EmotionalState) => Memory[];
        byKeyword: (keyword: string) => Memory[];
        byTimeRange: (start: Date, end: Date) => Memory[];
    };
    
    details: {
        showEmbedding: boolean;
        showRelationships: boolean;
        showActivationHistory: boolean;
        showConsolidationStatus: boolean;
    };
    
    actions: {
        editMemory: (id: string, updates: Partial<Memory>) => void;
        deleteMemory: (id: string, reason: string) => void;
        forceConsolidation: (memories: Memory[]) => void;
        recalculateImportance: (id: string) => void;
    };
}
```

### 6.2 Simulador de Conversaciones
```typescript
interface ConversationSimulator {
    scenarios: {
        predefined: Scenario[];
        custom: {
            create: () => Scenario;
            save: (scenario: Scenario) => void;
        };
    };
    
    execution: {
        speed: 'realtime' | 'fast' | 'instant';
        pauseOnError: boolean;
        logLevel: 'minimal' | 'normal' | 'verbose';
    };
    
    analysis: {
        compareResponses: boolean;
        measureLatency: boolean;
        trackMemoryUsage: boolean;
        emotionalCoherence: boolean;
    };
}
```

## 7. Gestión de Permisos y Roles

### 7.1 Control de Acceso
```typescript
interface AccessControl {
    roles: {
        admin: {
            fullAccess: boolean;
            configModification: boolean;
            dataExport: boolean;
            userDeletion: boolean;
        };
        
        supervisor: {
            messageApproval: boolean;
            configViewing: boolean;
            limitedExport: boolean;
            alertManagement: boolean;
        };
        
        analyst: {
            readOnlyAccess: boolean;
            reportGeneration: boolean;
            metricViewing: boolean;
        };
    };
    
    audit: {
        logAllActions: boolean;
        retentionDays: number;
        exportFormat: 'json' | 'csv';
    };
}
```

## 8. Integración con Herramientas Externas

### 8.1 Webhooks y APIs
```typescript
interface ExternalIntegrations {
    webhooks: {
        onMessageReceived: string;
        onMessageSent: string;
        onEmotionalAlert: string;
        onMemoryConsolidation: string;
    };
    
    apis: {
        metrics: '/api/v1/metrics';
        memories: '/api/v1/memories';
        conversations: '/api/v1/conversations';
        configuration: '/api/v1/config';
    };
    
    export: {
        prometheus: boolean;
        elasticsearch: boolean;
        datadog: boolean;
        customEndpoint: string;
    };
}
```

## 9. Performance y Optimización

### 9.1 Dashboard Performance
```typescript
interface PerformanceSettings {
    rendering: {
        virtualScrolling: boolean;
        lazyLoading: boolean;
        debounceUpdates: number;  // ms
        maxConcurrentCharts: number;
    };
    
    dataFetching: {
        cacheStrategy: 'aggressive' | 'moderate' | 'minimal';
        prefetchNext: boolean;
        compressionEnabled: boolean;
        paginationSize: number;
    };
    
    realtime: {
        websocketCompression: boolean;
        updateBatching: boolean;
        priorityQueuing: boolean;
    };
}
```

## 10. Configuración de Respaldo y Recuperación

### 10.1 Sistema de Backups
```typescript
interface BackupSystem {
    automatic: {
        enabled: boolean;
        frequency: 'hourly' | 'daily' | 'weekly';
        retention: {
            daily: number;    // Keep last N daily backups
            weekly: number;   // Keep last N weekly backups
            monthly: number;  // Keep last N monthly backups
        };
    };
    
    manual: {
        createBackup: () => Promise<BackupId>;
        restoreBackup: (id: BackupId) => Promise<void>;
        listBackups: () => Backup[];
    };
    
    scope: {
        includeMessages: boolean;
        includeMemories: boolean;
        includeConfiguration: boolean;
        includeMetrics: boolean;
    };
}
```