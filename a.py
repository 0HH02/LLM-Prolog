import os
import tempfile
import subprocess


def ejecutar_prolog_con_traza_modificado(prolog_code, consulta):
    """
    Ejecuta un código Prolog en SWI-Prolog, captura y devuelve la traza de stderr.
    """
    stdout_capture = ""
    stderr_capture = ""
    swipl_executable = "swipl" 
    temp_prolog_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.pl', delete=False)
    temp_prolog_file_name = temp_prolog_file.name
    try:
        temp_prolog_file.write(prolog_code)
        temp_prolog_file.close()
        prolog_file_path_escaped = temp_prolog_file_name.replace("'", "''")
        
        # Modificado para imprimir excepciones a user_error (stderr)
        goal_prolog = (
            f"set_prolog_flag(verbose_load, false), "
            f"consult('{prolog_file_path_escaped}'), "
            f"leash(-all), "
            f"trace, "
            # Captura la excepción, imprime info a user_error, luego falla para continuar la traza.
            f"catch(({consulta}, fail), E, (format(user_error, '~N### CAUGHT_EXCEPTION ###~n~w~n### END_EXCEPTION ###~n', [E]), fail)), "
            f"halt."
        )
        process = subprocess.Popen(
            [swipl_executable, "-q", "-g", goal_prolog, "-t", "halt"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8', errors='replace' 
        )
        # Aumentar el timeout para trazas largas
        stdout_capture, stderr_capture = process.communicate(timeout=60) 
    except subprocess.TimeoutExpired:
        process.kill()
        stdout_capture, stderr_capture = process.communicate()
        print("La ejecución de Prolog excedió el tiempo límite (Timeout).")
        stderr_capture += "\nERROR: Timeout during Prolog execution."
    except Exception as e:
        print(f"Error durante la ejecución de Prolog: {e}")
        stderr_capture += f"\nERROR: Python exception during Prolog call: {e}"
    finally:
        if os.path.exists(temp_prolog_file_name):
            os.remove(temp_prolog_file_name)

    if stdout_capture:
        print("--- Salida Estándar de Prolog (stdout) ---")
        print(stdout_capture) # Debería estar vacío o con pocos mensajes si todo va a user_error
    
    return stderr_capture


if __name__ == "__main__":
    # Tu código Prolog (el mismo que proporcionaste en la pregunta)
    # Se corrigió la advertencia de Python sobre \+
    codigo_prolog = f"""
% Hechos
animal(gato).
animal(perro).
animal(pez).

vive_en_agua(pez).
vive_en_tierra(gato).
vive_en_tierra(perro).

amigable(perro). 

% Regla
mascota_ideal(X) :-
    animal(X),
    vive_en_tierra(X),
    amigable(X).

% Hechos adicionales (para mostrar algo que funciona)
mascota_posible(X) :-
    animal(X),
    vive_en_tierra(X).
"""


    consulta_prolog = "mascota_ideal(X)"

    print(f">>> Ejecutando consulta: {consulta_prolog}")
    raw_trace = ejecutar_prolog_con_traza_modificado(codigo_prolog, consulta_prolog)
    
    if raw_trace:
        print(raw_trace)
    else:
        print("No se obtuvo traza para visualizar.")

    print("\n" + "="*50 + "\n")
    print("Ejecución de prueba finalizada. Revisa 'prolog_trace_graph.png'.")
