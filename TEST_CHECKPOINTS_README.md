# Sistema de Checkpoints para Tests

Este sistema permite ejecutar suites de tests largas de manera robusta, con la capacidad de guardar y reanudar el progreso automáticamente.

## Características

- **Guardado automático**: Los checkpoints se guardan automáticamente cada N tests (configurable)
- **Reanudación inteligente**: Al reiniciar, detecta automáticamente si hay un checkpoint previo
- **Manejo de interrupciones**: Si se interrumpe la ejecución (Ctrl+C), guarda el progreso antes de salir
- **Gestión de checkpoints**: Herramientas para listar, limpiar y eliminar checkpoints
- **Identificación única**: Cada suite de tests tiene un ID único basado en su contenido

## Uso Básico

### Ejecutar tests con checkpoints (por defecto)

```bash
python test.py
```

### Ejecutar sin checkpoints (desde el principio siempre)

```bash
python test.py --no-checkpoint
```

### Configurar frecuencia de guardado

```bash
# Guardar checkpoint cada 5 tests
python test.py --save-frequency 5
```

## Gestión de Checkpoints

### Listar checkpoints disponibles

```bash
python test.py --list-checkpoints
```

### Limpiar checkpoints antiguos

```bash
# Eliminar checkpoints más antiguos que 7 días
python test.py --cleanup-checkpoints 7
```

### Eliminar todos los checkpoints

```bash
python test.py --delete-checkpoints
```

## Funcionamiento Interno

### Estructura de un Checkpoint

Los checkpoints se guardan en `checkpoints/tests/` con el formato:

```json
{
  "suite_id": "abc123def456",
  "timestamp": "2024-01-15T10:30:00",
  "total_tests": 10,
  "completed_tests": 7,
  "current_index": 7,
  "tests": [...],
  "results": [...],
  "metadata": {
    "last_completed_test": 6,
    "test_name": "Test_7"
  }
}
```

### Identificación de Suites

Cada suite de tests se identifica por un hash MD5 de los `problem_description` de todos los tests. Esto significa que:

- Si cambias el contenido de los tests, se creará un nuevo checkpoint
- Si ejecutas la misma suite, usará el checkpoint existente
- Diferentes suites no interfieren entre sí

### Manejo de Errores

- **Interrupción del usuario (Ctrl+C)**: Guarda checkpoint y termina limpiamente
- **Errores fatales**: Guarda checkpoint de emergencia antes de fallar
- **Finalización exitosa**: Elimina automáticamente el checkpoint

## Ejemplos de Uso

### Ejemplo 1: Suite larga con checkpoints frecuentes

```bash
# Para suites de 100+ tests, guardar cada 10 tests
python test.py --save-frequency 10
```

### Ejemplo 2: Reanudar después de interrupción

```bash
# Primera ejecución (interrumpida en test 45)
python test.py
# [Ctrl+C en el test 45]

# Segunda ejecución (continúa desde test 45)
python test.py
# "¿Deseas continuar desde el checkpoint? (s/n): s"
```

### Ejemplo 3: Gestión de checkpoints

```bash
# Ver qué checkpoints tienes
python test.py --list-checkpoints

# Salida:
# 📋 CHECKPOINTS DISPONIBLES:
#   • abc123de... - 2024-01-15T10:30:00 - 45/100 tests (45.0%)
#   • def456ab... - 2024-01-14T15:20:00 - 23/50 tests (46.0%)

# Limpiar checkpoints antiguos
python test.py --cleanup-checkpoints 3
```

## Archivos Generados

- `checkpoints/tests/test_suite_<id>.json`: Checkpoint activo
- `checkpoints/tests/test_suite_<id>.json.backup`: Backup del checkpoint anterior
- `solutions/tests/test_results.json`: Resultados finales (como siempre)

## Integración con el Sistema Existente

El sistema de checkpoints es completamente compatible con el sistema de tests existente:

- No cambia el formato de `tests/tests.json`
- No modifica `test_results.json`
- Se puede activar/desactivar sin afectar la funcionalidad

## Recomendaciones

1. **Para suites cortas (< 10 tests)**: Usar frecuencia 1 (por defecto)
2. **Para suites medianas (10-50 tests)**: Usar frecuencia 5
3. **Para suites largas (50+ tests)**: Usar frecuencia 10
4. **Limpieza regular**: Ejecutar `--cleanup-checkpoints 7` semanalmente
5. **Debugging**: Usar `--no-checkpoint` cuando necesites ejecutar desde el principio siempre
