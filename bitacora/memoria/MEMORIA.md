1. MEMORIA CORTO PLAZO/MEMORIA DE CONTEXTO
    1.1 el supervisor siempre manda el contexto que guarda de redis para combinarlo con el prompt y el mensaje que recibe del userbot o del usuario
    1.2 Luego busca un caché hit mediante SEMANTIC Cache augmented generation 
    1.3 si no hay un cache hit, se usar RAG 
        1.4 se aplican tecnicas de graphrag / pathrag 
        1.5 se buscan las relaciones de neo4j 
        1.6 se inyecta en el prompt los recuerdos 
2. MEMORIA LARGO PLAZO/MEMORIA SEMANTICA, ESPACIAL Y EMOCIONAL. Nodos de dimensiones vectorizadas y relacionadas en neo4j 
    2.1 tiempo 
    2.2 emociones VAD 
        2.2.1 para lograrlo usamos un modelo Roberta VAD de hugging face (creo que sabes cual es) y asi logramos clasificar el VAD del usuario 
    2.3 lugar
    2.4 hechos 
    2.5 personas relacionadas 
