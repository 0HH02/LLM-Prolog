# checkpoint_utils.py
import pickle
import os
import re # Para sanitizar nombres de archivo

CHECKPOINT_DIR = "checkpoints" # Nombre de la carpeta para guardar los checkpoints

def _ensure_checkpoint_dir():
    """Asegura que el directorio de checkpoints exista."""
    if not os.path.exists(CHECKPOINT_DIR):
        try:
            os.makedirs(CHECKPOINT_DIR)
            print(f"Directorio de checkpoints creado: {CHECKPOINT_DIR}")
        except OSError as e:
            print(f"Error al crear el directorio de checkpoints {CHECKPOINT_DIR}: {e}")
            # Podrías lanzar una excepción aquí si el directorio es crucial

def _sanitize_filename(text: str, max_len: int = 50) -> str:
    """Convierte un texto en un nombre de archivo seguro y corto."""
    if not text:
        return "default_id"
    # Quitar caracteres no alfanuméricos (excepto guiones bajos y espacios que se reemplazarán)
    text = re.sub(r'[^\w\s-]', '', text)
    # Reemplazar espacios y guiones repetidos con un solo guión bajo
    text = re.sub(r'[-\s]+', '_', text).strip('_')
    return text[:max_len]

def get_checkpoint_filepath(module_name: str, problem_description: str) -> str:
    """Genera una ruta de archivo consistente para un checkpoint."""
    _ensure_checkpoint_dir()
    problem_identifier = _sanitize_filename(problem_description)
    filename = f"{module_name}_{problem_identifier}.pkl"
    return os.path.join(CHECKPOINT_DIR, filename)

def save_checkpoint(data: any, module_name: str, problem_description: str):
    """Guarda los datos de un módulo como un checkpoint."""
    filepath = get_checkpoint_filepath(module_name, problem_description)
    try:
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        print(f"INFO: Checkpoint guardado: {filepath}")
    except Exception as e:
        print(f"ERROR: No se pudo guardar el checkpoint en {filepath}: {e}")

def load_checkpoint(module_name: str, problem_description: str) -> any:
    """Carga los datos de un módulo desde un checkpoint, si existe."""
    filepath = get_checkpoint_filepath(module_name, problem_description)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            print(f"INFO: Checkpoint cargado: {filepath}")
            return data
        except Exception as e:
            print(f"ERROR: No se pudo cargar el checkpoint desde {filepath}: {e}. Se procederá sin checkpoint.")
            return None
    else:
        print(f"INFO: Checkpoint no encontrado: {filepath}. Se ejecutará el módulo correspondiente.")
        return None

def clear_checkpoint(module_name: str, problem_description: str):
    """Elimina un archivo de checkpoint específico."""
    filepath = get_checkpoint_filepath(module_name, problem_description)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"INFO: Checkpoint eliminado: {filepath}")
        except Exception as e:
            print(f"ERROR: No se pudo eliminar el checkpoint {filepath}: {e}")
    else:
        print(f"INFO: No se encontró checkpoint para eliminar: {filepath}")

def clear_all_checkpoints():
    """Elimina TODOS los archivos de checkpoint en el directorio de checkpoints."""
    _ensure_checkpoint_dir() # Asegura que el directorio exista para no fallar si está vacío
    if os.path.exists(CHECKPOINT_DIR):
        count = 0
        for filename in os.listdir(CHECKPOINT_DIR):
            if filename.endswith(".pkl"): # O cualquier extensión que uses
                filepath = os.path.join(CHECKPOINT_DIR, filename)
                try:
                    os.remove(filepath)
                    count +=1
                except Exception as e:
                    print(f"ERROR: No se pudo eliminar el archivo de checkpoint {filepath}: {e}")
        if count > 0 :
            print(f"INFO: Se eliminaron {count} archivos de checkpoint de '{CHECKPOINT_DIR}'.")
        else:
            print(f"INFO: No se encontraron checkpoints para eliminar en '{CHECKPOINT_DIR}'.")