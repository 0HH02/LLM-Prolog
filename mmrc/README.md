# Módulo 4: Meta-cognición y Refinamiento del Conocimiento (MMRC)

Este módulo es responsable de analizar los resultados del Motor de Inferencia Simbólica Asistido por Justificación (MISA-J), aprender de los éxitos y, especialmente, de los fracasos, para proponer modificaciones al Almacén de Representación del Conocimiento (KR-Store).

Su objetivo es permitir que el sistema INSIGhT refine iterativamente su base de conocimiento.

## Sub-componentes Neurales (LLM):

### 1. LLM-ARA (Abductive Reasoning & Analysis Unit)

- **Función:** Cuando MISA-J no alcanza la solución, LLM-ARA analiza la traza de inferencia comentada correspondiente.
- **Proceso:** Realiza un razonamiento abductivo para hipotetizar qué axiomas o supuestos adicionales hubieran sido necesarios, o cuáles podrían haber sido incorrectos, para alcanzar la solución por la vía explorada.

### 2. LLM-SGA (Synthesis & Global Assessment Unit)

- **Función:** Recibe el análisis del LLM-ARA y la traza completa de MISA-J.
- **Proceso:** Realiza una síntesis global, identificando patrones de fallo recurrentes, asunciones problemáticas comunes, o caminos inferenciales prometedores que fueron abandonados prematuramente. Puede emplear técnicas de clustering semántico sobre las justificaciones y análisis de fallos para identificar temas comunes.

### 3. LLM-KRM (Knowledge Refinement Modulator)

- **Función:** Basándose en las conclusiones del LLM-SGA y la descripción original del problema.
- **Proceso:** Propone adiciones, eliminaciones o modificaciones específicas al conjunto de cláusulas en el KR-Store. Cada propuesta de modificación debe ir acompañada de una justificación explícita generada por el LLM.

## Flujo dentro del MMRC (cuando MISA-J falla):

1.  La traza de inferencia completa de MISA-J se pasa al LLM-ARA.
2.  LLM-ARA genera un análisis abductivo (hipótesis sobre fallos/faltantes).
3.  El análisis de ARA y la traza original se pasan al LLM-SGA.
4.  LLM-SGA produce una evaluación sintética global.
5.  La evaluación de SGA, la descripción original del problema y el KR-Store actual se pasan al LLM-KRM.
6.  LLM-KRM genera una lista de propuestas de refinamiento del conocimiento (ej: añadir/eliminar/modificar cláusulas), cada una con su justificación.

Estas propuestas pueden ser luego aplicadas al KR-Store antes de iniciar un nuevo ciclo de razonamiento (volviendo al Orquestador Heurístico de Inferencia - OHI).
