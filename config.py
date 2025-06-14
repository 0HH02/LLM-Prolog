import contextlib
import sys
import os
from datetime import datetime

CONFIG = {
    "force_run_mfsa": False,      # Si True, siempre ejecuta MFSA ignorando checkpoint.
    "force_run_misa_j": True,   # Si True, siempre ejecuta MISA-J/CFCS.
    "force_run_mmrc": True,     # Si True, siempre ejecuta MMRC.
    "force_run_ohi": True,      # Si True, siempre ejecuta OHI ignorando checkpoint.
    "save_checkpoints": True,    # Si True, guarda checkpoints después de ejecutar módulos.
    "max_refinement_cycles": 3,   # Número máximo de ciclos de refinamiento
    "log_to_file": True,         # Si True, guarda la salida en un archivo
    "log_directory": "logs",     # Directorio donde se guardarán los logs
}

@contextlib.contextmanager
def redirect_output(log_file):
    """Contexto para redirigir la salida estándar y de error a un archivo."""
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            sys.stdout = f
            sys.stderr = f
            yield
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr

def setup_logging():
    """Configura el sistema de logging."""
    if CONFIG["log_to_file"]:
        # Crear directorio de logs si no existe
        if not os.path.exists(CONFIG["log_directory"]):
            os.makedirs(CONFIG["log_directory"])
        
        # Crear nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"insight_run_{timestamp}.log"
        log_path = os.path.join(CONFIG["log_directory"], log_filename)
        
        print(f"Guardando log en: {log_path}")
        return log_path
    return None

def clear_solutions():
    """Limpia las soluciones anteriores."""
    solutions_dir = os.path.join(os.path.dirname(__file__), "solutions")
    success_dir = os.path.join(solutions_dir, "success")
    fails_dir = os.path.join(solutions_dir, "fails")
    
    # Crear directorios si no existen
    os.makedirs(success_dir, exist_ok=True)
    os.makedirs(fails_dir, exist_ok=True)
    
    # Eliminar archivos dentro de success
    for file in os.listdir(success_dir):
        file_path = os.path.join(success_dir, file)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    # Eliminar archivos dentro de fails
    for file in os.listdir(fails_dir):
        file_path = os.path.join(fails_dir, file)
        if os.path.isfile(file_path):
            os.remove(file_path)