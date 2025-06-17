# Visualizador de Árbol de Trazas Prolog

Esta interfaz web permite visualizar y analizar trazas de ejecución de Prolog de manera interactiva, mostrando cómo se construye el árbol de pensamientos durante el proceso de backtracking.

## Características

- **Visualización en tiempo real**: Observa cómo se construye el árbol línea por línea
- **Navegación entre estados**: Explora diferentes estados del árbol durante el proceso de `redo`
- **Carga de archivos**: Importa trazas desde archivos de texto
- **Interfaz intuitiva**: Colores diferenciados para éxito (verde), fallo (rojo) y nodos en proceso (azul)

## Cómo usar

### 1. Cargar una traza

Puedes cargar una traza de dos maneras:

- **Usar la traza de ejemplo**: La interfaz viene con una traza de ejemplo cargada por defecto
- **Cargar archivo**: Haz clic en "📁 Cargar Archivo" para seleccionar un archivo de traza (.txt, .log, .pl)

### 2. Modos de visualización

#### Modo Paso a Paso (▶️ Paso a Paso)

- Procesa la traza línea por línea
- Muestra cómo se va construyendo el árbol gradualmente
- Resalta la línea actual en el panel de traza
- Ideal para entender el flujo de ejecución detallado

#### Modo Navegación entre Árboles (⏭️ Siguiente Árbol)

- Muestra los diferentes estados completos del árbol
- Cada estado representa un momento de `redo` en la ejecución
- Útil para comparar diferentes intentos de solución

### 3. Interpretación de colores

- **Verde**: Nodos que han tenido éxito (`exit`)
- **Rojo**: Nodos que han fallado (`fail`)
- **Azul**: Nodos en proceso o sin estado definido

### 4. Formato de traza esperado

La interfaz procesa trazas de Prolog con el siguiente formato:

```
call: predicado(argumentos) @ archivo:linea
exit: predicado(argumentos) @ archivo:linea
fail: predicado(argumentos) @ archivo:linea
redo: predicado(argumentos) @ archivo:linea
```

## Ejemplo de traza

Se incluye un archivo `ejemplo_traza.txt` con una traza real de Prolog que demuestra:

- Llamadas a predicados
- Éxitos y fallos
- Procesos de backtracking (`redo`)
- Predicados complejos como `forall` y negación (`\+`)

## Archivos del proyecto

- `index.html`: Estructura principal de la interfaz
- `script.js`: Lógica de procesamiento y visualización
- `style.css`: Estilos y diseño responsivo
- `ejemplo_traza.txt`: Archivo de ejemplo para pruebas
- `README.md`: Este archivo de documentación

## Compatibilidad

- Compatible con navegadores modernos que soporten ES6+
- Utiliza la librería vis-network para la visualización de grafos
- Diseño responsivo que se adapta a diferentes tamaños de pantalla

## Uso con el código Python

Esta interfaz web implementa el mismo algoritmo que el archivo `c.py`, permitiendo:

- Procesar las mismas trazas que el código Python
- Visualizar los mismos árboles de pensamiento
- Entender mejor el proceso de backtracking de Prolog

Para obtener trazas compatibles desde Prolog, puedes usar:

```prolog
trace, tu_consulta, notrace.
```

O capturar la salida de tu programa Prolog en un archivo de texto.
