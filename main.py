from mfsa.mfsa_module import SemanticFormalizationAxiomatizationModule
from mfsa.kr_store import KnowledgeRepresentationStore
from ohi.ohi import HeuristicInferenceOrchestrator
from misa_j.cfcs import PrologSolver
# from mmrc.mmrc_module import MetaCognitionKnowledgeRefinementModule
from common.gemini_interface import ask_gemini
from checkpoints_utils import save_checkpoint, load_checkpoint, clear_all_checkpoints, clear_checkpoint

import json
import argparse
import sys
import os
from datetime import datetime
import contextlib
from datasets import load_dataset
import shutil

# --- CONFIGURACIÓN DEL FRAMEWORK ---
# Estos valores pueden ser sobrescritos por argumentos de línea de comandos
CONFIG = {
    "force_run_mfsa": False,      # Si True, siempre ejecuta MFSA ignorando checkpoint.
    "force_run_ohi": False,       # Si True, siempre ejecuta OHI ignorando checkpoint.
    "force_run_misa_j": False,    # <--- AÑADIDO para MISA-J/CFCS
    "force_run_mmrc": False,      # <--- AÑADIDO para MMRC
    "save_checkpoints": True,     # Si True, guarda checkpoints después de ejecutar módulos.
    "problem_indices_to_run": None, # Lista de índices de problemas a ejecutar, ej: [0, 2]. None para todos.
    "max_refinement_cycles": 3,    # <--- AÑADIDO: Número máximo de ciclos de refinamiento
    "log_to_file": True,          # <--- AÑADIDO: Si True, guarda la salida en un archivo
    "log_directory": "logs",      # <--- AÑADIDO: Directorio donde se guardarán los logs
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

def parse_arguments():
    """Parsea argumentos de línea de comandos para sobrescribir CONFIG."""
    parser = argparse.ArgumentParser(description="Framework de Razonamiento con Checkpoints.")
    parser.add_argument("--force-mfsa", action="store_true", help="Forzar ejecución de MFSA (ignorar checkpoint).")
    parser.add_argument("--force-ohi", action="store_true", help="Forzar ejecución de OHI (ignorar checkpoint).")
    parser.add_argument("--force-misa-j", action="store_true", help="Forzar ejecución de MISA-J/CFCS.")
    parser.add_argument("--force-mmrc", action="store_true", help="Forzar ejecución de MMRC.")
    parser.add_argument("--no-save", action="store_false", dest="save_checkpoints", help="Deshabilitar guardado de checkpoints.")
    parser.add_argument("--run-indices", type=str, help="Lista de índices de problemas a ejecutar, separados por coma (ej: 0,1,3).")
    parser.add_argument("--clear-all-cps", action="store_true", help="Eliminar todos los checkpoints al inicio.")
    parser.add_argument("--clear-cp", type=str, help="Eliminar checkpoint específico: 'module_name:problem_description_substring'.")
    parser.add_argument("--max-cycles", type=int, help="Número máximo de ciclos de refinamiento.")
    parser.add_argument("--no-log", action="store_false", dest="log_to_file", help="Deshabilitar guardado de logs en archivo.")
    parser.add_argument("--log-dir", type=str, help="Directorio donde guardar los logs.")

    args = parser.parse_args()

    if args.force_mfsa:
        CONFIG["force_run_mfsa"] = True
    if args.force_ohi:
        CONFIG["force_run_ohi"] = True
    if args.force_misa_j:
        CONFIG["force_run_misa_j"] = True
    if args.force_mmrc:
        CONFIG["force_run_mmrc"] = True
    if args.save_checkpoints is False:
        CONFIG["save_checkpoints"] = False
    if args.run_indices:
        try:
            CONFIG["problem_indices_to_run"] = [int(i.strip()) for i in args.run_indices.split(',')]
        except ValueError:
            print("Error: Índices de problema no válidos. Deben ser números separados por comas.")
            exit(1)
    if args.clear_all_cps:
        clear_all_checkpoints()
        print("INFO: Todos los checkpoints eliminados según argumento.")
    if args.clear_cp:
        try:
            module_name, problem_desc_substring = args.clear_cp.split(":",1)
            print(f"ADVERTENCIA: --clear-cp es experimental. Intenta limpiar para {module_name} con descripción similar a '{problem_desc_substring}'.")
            clear_checkpoint(module_name.strip(), problem_desc_substring.strip())
        except ValueError:
            print("Error: Formato incorrecto para --clear-cp. Usar 'module_name:problem_description_substring'.")
    if args.max_cycles is not None:
        CONFIG["max_refinement_cycles"] = args.max_cycles
    if args.log_to_file is False:
        CONFIG["log_to_file"] = False
    if args.log_dir:
        CONFIG["log_directory"] = args.log_dir

def clear_solutions():
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


def main():
    # Carga de problemas
    ds = load_dataset("yale-nlp/FOLIO")
    # mmrc_module = MetaCognitionKnowledgeRefinementModule()

    for index, problem_data in enumerate(ds['train']):
        if index < 4:
            continue
        problem_description = f"""
            Habían aparecido cuatro cofres, dos de oro y dos de plata; se sabía que constituían
            dos juegos, pero se habían mezclado y ahora no se sabía qué cofre de oro y qué cofre
            de plata formaban pareja. Me los enseñaron y pronto pude resolver el problema por lo
            que recibí unos excelentes honorarios. Pero además pude establecer también quién
            había hecho cada cofre, por lo que recibí un extra (que consistía, entre otras cosas, en
            una excelente caja de botellas de Chianti) y un beso de una de las florentinas más
            maravillosas que haya existido nunca
            He aquí los cuatro cofres:
            Cofre A (Oro)
            EL COFRE DE PLATA ES OBRA DE UN CELLINI
            Cofre B (Plata)
            EL COFRE DE PLATA O ES OBRA DE UN CELLINI O LOS DOS COFRES SON
            DE BELLINI
            Cofre C (Oro)
            EL COFRE DE ORO ES OBRA DE UN BELLINI
            Cofre D (Plata)
            EL COFRE DE ORO ES OBRA DE UN BELLINI Y POR LO MENOS UNO DE
            ESTOS COFRES ES OBRA DE UN HIJO O DE BELLINI O CELLINI
            Tenemos ahora un problema:
            ¿Quién hizo cada uno de los cofres?
            """
        problem_topic_hint = None

        if CONFIG["problem_indices_to_run"] is not None and index not in CONFIG["problem_indices_to_run"]:
            continue

        print("\n" + "="*70)
        print(f"PROCESANDO PROBLEMA {index + 1}: \"{problem_description[:80]}...\"")
        print("="*70)

        # --- Ciclo Iterativo de Razonamiento y Refinamiento ---
        current_kr_store = None
        thought_tree = None
        goal_clauses_mfsa = []
        goal_clause_str_for_llms = ""

        for cycle in range(CONFIG["max_refinement_cycles"]):
            print(f"\n--- CICLO DE REFINAMIENTO {cycle + 1} / {CONFIG['max_refinement_cycles']} ---")
            # --- Limpieza de soluciones anteriores ---
            # Limpiar archivos dentro de los directorios de soluciones
            clear_solutions()

            # --- 1. MFSA (Formalización Semántica y Axiomatización) ---
            if cycle == 0 or (CONFIG["force_run_mfsa"] and not current_kr_store):
                checkpoint_kr_store_name = "mfsa_kr_store"
                loaded_kr = None
                if not CONFIG["force_run_mfsa"]:
                    loaded_kr = load_checkpoint(checkpoint_kr_store_name, problem_description)
                
                if loaded_kr:
                    current_kr_store = loaded_kr
                    print("INFO: MFSA omitido, KR-Store cargado desde checkpoint.")
                else:
                    print("\n--- Ejecutando MFSA ---")
                    temp_kr_store = KnowledgeRepresentationStore()
                    mfsa_instance_problem = SemanticFormalizationAxiomatizationModule(temp_kr_store)
                    mfsa_instance_problem.formalize_problem(
                        problem_description, 
                        problem_topic_hint=problem_topic_hint
                    )
                    current_kr_store = temp_kr_store
                    if CONFIG["save_checkpoints"]:
                        save_checkpoint(current_kr_store, checkpoint_kr_store_name, problem_description)
            
            if not current_kr_store: 
                print(f"ERROR CRÍTICO: KR-Store no disponible para el problema {index + 1} en ciclo {cycle + 1}. Omitiendo problema.")
                break

            goal_clauses_mfsa = current_kr_store.get_clauses_by_category("goal_clause")
            if not goal_clauses_mfsa:
                print("\nAdvertencia: MFSA no generó cláusulas objetivo. No se puede continuar con este problema.")
                break
            goal_clause_str_for_llms = str(goal_clauses_mfsa[0]) # Usar la primera para los prompts
            print(f"\nINFO: Cláusula Objetivo Principal: {goal_clause_str_for_llms}")

            selected_clauses_by_ohi = current_kr_store.get_clauses_by_category("problem_clause")

            # --- 3. MISA-J (Motor de Inferencia Simbólica Asistido por Justificación) ---
            misa_j_solver = PrologSolver()
            checkpoint_misa_trace_name = f"misa_j_trace_cycle{cycle}"
            if not CONFIG["force_run_misa_j"]:
                thought_tree = load_checkpoint(checkpoint_misa_trace_name, problem_description)

            if thought_tree is None: # Si no se cargó o se fuerza
                print("\n--- Ejecutando MISA-J (CFCS) ---")
                thought_tree = misa_j_solver.solve(selected_clauses_by_ohi, goal_clauses_mfsa[0])
                if CONFIG["save_checkpoints"] and thought_tree:
                    save_checkpoint(thought_tree, checkpoint_misa_trace_name, problem_description)
            else:
                print("INFO: MISA-J omitido, traza cargada desde checkpoint.")
            break

        print("\n" + "="*70 + f"\nFIN DEL PROCESAMIENTO PARA PROBLEMA {index + 1}" + "\n" + "="*70)
        input("Presiona Enter para continuar con el siguiente problema...")
        break
    print("\nTODOS LOS PROBLEMAS CONFIGURADOS PROCESADOS.")



if __name__ == "__main__":
    parse_arguments() # Actualiza CONFIG basado en argumentos de línea de comandos
    
    # Configurar logging
    log_file = setup_logging()
    
    # Si se activó el logging a archivo, redirigir la salida
    if log_file:
        with redirect_output(log_file):
            main()  # Mover todo el código principal a una función main()
    else:
        main()  # Ejecutar sin redirección si no se activó el logging
