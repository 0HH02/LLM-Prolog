# Visualizador de Árbol SLD - Versión 1.1

Este proyecto implementa un visualizador de árboles SLD (Selective Linear Definite) para trazas de Prolog, permitiendo analizar y visualizar el proceso de resolución de consultas Prolog.

## Arquitectura

### Componentes Principales

1. **Clase Clausula**

   - Representa un nodo en el árbol SLD
   - Atributos:
     - `nombre`: String que representa el predicado y sus argumentos
     - `valor`: Array de Clausulas (hijos)
     - `veracidad`: Estado del nodo ("verde" para éxito, "rojo" para fallo)
     - `padre`: Referencia al nodo padre

2. **Procesador de Traza**
   - Función `procesar_traza(traza_str)`
   - Responsabilidades:
     - Parsear la traza de Prolog
     - Construir el árbol SLD
     - Manejar eventos (Call, Exit, Fail, Redo)
     - Generar ramas de pensamiento

### Flujo de Datos

1. **Entrada**

   - Traza de Prolog en formato texto
   - Cada línea sigue el patrón: `Tipo: (Nivel) Contenido`

2. **Procesamiento**

   - Parseo de líneas usando expresiones regulares
   - Construcción del árbol SLD
   - Manejo de eventos:
     - Call: Crea nuevo nodo
     - Exit: Marca nodo como exitoso
     - Fail: Marca nodo como fallido
     - Redo: Genera nueva rama

3. **Salida**
   - Árbol SLD en formato JSON
   - Ramas de pensamiento generadas
   - Visualización del estado final

## Notas de Implementación

### Manejo de Eventos

1. **Call**

   - Crea nueva cláusula
   - La añade como hijo del nodo actual
   - Actualiza nodo actual

2. **Exit**

   - Marca nodo como exitoso (verde)
   - Añade resultado al array de valor
   - Retrocede al padre

3. **Fail**

   - Marca nodo como fallido (rojo)
   - Añade resultado al array de valor
   - Retrocede al padre

4. **Redo**
   - Guarda copia del árbol actual
   - Encuentra nodo a rehacer
   - Trunca árbol hasta ese punto
   - Reinicia estado del nodo

### Consideraciones Técnicas

- Uso de expresiones regulares para parseo robusto
- Manejo de memoria eficiente con referencias a padres
- Copias profundas para preservar estado en ramas
- Búsqueda BFS para encontrar nodos en redo

## Uso

```python
# Ejemplo de uso
traza = """
    Call: (12) contraseña(_4664, _4666, _4668)
    Call: (13) alfa(_4664)
    Exit: (13) alfa(1)
    ...
"""

ramas, arbol_final = procesar_traza(traza)
```

## Mejoras Futuras

1. Visualización gráfica del árbol
2. Soporte para más tipos de eventos Prolog
3. Análisis de rendimiento
4. Exportación a diferentes formatos
5. Integración con IDEs de Prolog
