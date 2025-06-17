import pickle
import os
from datetime import datetime

HISTORY_DIR = "checkpoints"  # Mismo directorio que otros checkpoints

def _ensure_history_dir():
    """Asegura que el directorio de historial exista."""
    if not os.path.exists(HISTORY_DIR):
        try:
            os.makedirs(HISTORY_DIR)
            print(f"Directorio de historial creado: {HISTORY_DIR}")
        except OSError as e:
            print(f"Error al crear el directorio de historial {HISTORY_DIR}: {e}")

def get_history_filepath(problem_description: str) -> str:
    """Genera una ruta de archivo para el historial."""
    _ensure_history_dir()
    # Crear un identificador único basado en la descripción del problema
    problem_identifier = problem_description[:50].replace(" ", "_").replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"llm_history_{problem_identifier}_{timestamp}.pkl"
    return os.path.join(HISTORY_DIR, filename)

def save_llm_history(history: dict, problem_description: str):
    """Guarda el historial de respuestas del LLM."""
    filepath = get_history_filepath(problem_description)
    try:
        with open(filepath, 'wb') as f:
            pickle.dump(history, f)
        print(f"INFO: Historial del LLM guardado: {filepath}")
    except Exception as e:
        print(f"ERROR: No se pudo guardar el historial del LLM en {filepath}: {e}")

def load_latest_llm_history(problem_description: str) -> dict:
    """Carga el historial más reciente para un problema específico."""
    _ensure_history_dir()
    prefix = f"llm_history_{problem_description[:50].replace(' ', '_').replace('/', '_')}"
    
    # Buscar el archivo más reciente que coincida con el prefijo
    matching_files = [f for f in os.listdir(HISTORY_DIR) if f.startswith(prefix) and f.endswith('.pkl')]
    if not matching_files:
        print(f"INFO: No se encontró historial previo para el problema.")
        return {}
    
    # Ordenar por fecha de modificación y tomar el más reciente
    latest_file = max(matching_files, key=lambda f: os.path.getmtime(os.path.join(HISTORY_DIR, f)))
    filepath = os.path.join(HISTORY_DIR, latest_file)
    
    try:
        with open(filepath, 'rb') as f:
            history = pickle.load(f)
        print(f"INFO: Historial del LLM cargado: {filepath}")
        return history
    except Exception as e:
        print(f"ERROR: No se pudo cargar el historial del LLM desde {filepath}: {e}")
        return {}

def clear_llm_history(problem_description: str = None):
    """Elimina archivos de historial.
    Si se proporciona problem_description, solo elimina el historial de ese problema.
    Si no, elimina todo el historial."""
    _ensure_history_dir()
    
    if problem_description:
        prefix = f"llm_history_{problem_description[:50].replace(' ', '_').replace('/', '_')}"
        files_to_delete = [f for f in os.listdir(HISTORY_DIR) if f.startswith(prefix) and f.endswith('.pkl')]
    else:
        files_to_delete = [f for f in os.listdir(HISTORY_DIR) if f.startswith('llm_history_') and f.endswith('.pkl')]
    
    count = 0
    for filename in files_to_delete:
        filepath = os.path.join(HISTORY_DIR, filename)
        try:
            os.remove(filepath)
            count += 1
        except Exception as e:
            print(f"ERROR: No se pudo eliminar el archivo de historial {filepath}: {e}")
    
    if count > 0:
        print(f"INFO: Se eliminaron {count} archivos de historial.")
    else:
        print("INFO: No se encontraron archivos de historial para eliminar.") 