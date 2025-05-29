import os
import tempfile
import subprocess
from typing import List, Dict, Optional, Set, Tuple
from .llm_jem import LLMJEM
from .trace import InferenceTrace, InferenceStep, StepStatus

class PrologSolver:
    """
    Implementa un solver basado en Prolog para inferencia lógica con justificaciones.
    """

    def __init__(self, llm_jem: LLMJEM):
        self.llm_jem = llm_jem

    def _create_prolog_program(self, clauses: List[str]) -> str:
        """Crea un programa Prolog a partir de una lista de HornClauses."""
        rules = "\n".join([clause for clause in clauses])
        print(f"Programa Prolog: {rules}")
        return rules
    
    def _ejecutar_prolog_con_traza_modificado(self, prolog_code, consulta):
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
                f"catch(({consulta[:-1]}, fail), E, (format(user_error, '~N### CAUGHT_EXCEPTION ###~n~w~n### END_EXCEPTION ###~n', [E]), fail)), "
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

    def _parse_prolog_trace(self, raw_trace: str, trace: InferenceTrace, initial_clauses: List[str]):
        """
        Parsea la traza cruda de Prolog y construye el árbol de inferencia.
        """
        if not raw_trace:
            return
            
        lineas = raw_trace.split('\n')
        step_stack = []  # Stack para mantener la jerarquía de llamadas
        depth_to_step_id = {}  # Mapeo de profundidad a step_id
        
        for linea in lineas:
            if linea == lineas[0]:
                continue
            if "Fail: (10)" in linea:
                break
            linea = linea.strip()
            if not linea:
                continue
                
            # Extraer información de la línea de traza
            if any(keyword in linea for keyword in ["Call:", "Exit:", "Fail:", "Redo:"]):
                depth, predicate, status = self._parse_trace_line(linea)
                if depth is None or predicate is None:
                    continue
                
                # Determinar el padre basado en la profundidad
                parent_step_id = None
                if depth > 0:
                    # Buscar el padre en profundidades menores
                    for d in range(depth - 1, -1, -1):
                        if d in depth_to_step_id:
                            parent_step_id = depth_to_step_id[d]
                            break
                
                # Agregar el paso al árbol
                step_id = trace.add_step(
                    predicate=predicate,
                    status=status,
                    depth=depth,
                    parent_step_id=parent_step_id
                )
                
                # Actualizar el mapeo de profundidad
                depth_to_step_id[depth] = step_id
                
                # Agregar anotaciones específicas
                if status == StepStatus.SUCCEEDED:
                    # Verificar si es un hecho inicial
                    for clause in initial_clauses:
                        if not clause.body and str(clause).strip('.') in predicate:
                            trace.annotate_step(step_id, "source", "initial_fact")
                            trace.annotate_step(step_id, "clause", str(clause))
                            break
                    else:
                        # Es una derivación
                        trace.annotate_step(step_id, "source", "derived")
                        
                        # Intentar obtener justificación del LLM
                        premises = self._get_premises_for_step(step_id, trace)
                        if premises:
                            justification = self.llm_jem.get_justification(predicate, premises)
                            trace.steps[step_id].justification = justification

    def _parse_trace_line(self, linea: str) -> Tuple[Optional[int], Optional[str], Optional[StepStatus]]:
        """
        Parsea una línea de traza de Prolog y extrae profundidad, predicado y estado.
        """
        try:
            # Extraer profundidad del número entre paréntesis
            if "(" in linea and ")" in linea:
                depth_part = linea[linea.find("(") + 1:linea.find(")")]
                depth = int(depth_part) if depth_part.isdigit() else 0
            else:
                depth = 0
            
            # Determinar el estado
            if "Call:" in linea:
                status = StepStatus.CALLED
                predicate = linea.split("Call:")[1].strip()
            elif "Exit:" in linea:
                status = StepStatus.SUCCEEDED
                predicate = linea.split("Exit:")[1].strip()
            elif "Fail:" in linea:
                status = StepStatus.FAILED
                predicate = linea.split("Fail:")[1].strip()
            elif "Redo:" in linea:
                status = StepStatus.BACKTRACKED
                predicate = linea.split("Redo:")[1].strip()
            else:
                return None, None, None
            
            # Limpiar el predicado
            predicate = predicate.split(") ")[1].strip()
            
            return depth, predicate, status
            
        except Exception as e:
            print(f"Error parseando línea de traza: {linea} - {e}")
            return None, None, None

    def _get_premises_for_step(self, step_id: int, trace: InferenceTrace) -> List[str]:
        """
        Obtiene las premisas para un paso dado basándose en sus pasos hijo exitosos.
        """
        if step_id not in trace.steps:
            return []
        
        step = trace.steps[step_id]
        premises = []
        
        # Buscar pasos hijo que fueron exitosos
        for child_id in step.children_step_ids:
            if child_id in trace.steps:
                child_step = trace.steps[child_id]
                if child_step.status == StepStatus.SUCCEEDED:
                    premises.append(child_step.predicate)
        
        return premises

    def solve(self, initial_clauses: List[str], goal_clause_obj: Optional[str] = None, problem_name: str = "Problema") -> InferenceTrace:
        """
        Ejecuta el proceso de inferencia usando Prolog.

        Args:
            initial_clauses: Una lista de HornClauses (hechos y reglas).
            goal_clause_obj: La HornClause objetivo (opcional).
            problem_name: Nombre del problema para la traza.

        Returns:
            Una InferenceTrace con todos los pasos de derivación.
        """
        # Crear el programa Prolog
        program_string = self._create_prolog_program(initial_clauses)
        
        consulta = f"{goal_clause_obj}"

        # Ejecutar Prolog y obtener la traza
        raw_trace = self._ejecutar_prolog_con_traza_modificado(program_string, consulta)
        # raw_trace = "\n".join(raw_trace.split("\n")[1:-6])
        print("--- Traza cruda de Prolog ---")
        print(raw_trace)
        print("--- Fin de traza cruda ---")
        
        # # Crear la traza de inferencia
        # trace = InferenceTrace(goal_clause=str(goal_clause_obj) if goal_clause_obj else None)
        
        # # Parsear la traza de Prolog y construir el árbol
        # self._parse_prolog_trace(raw_trace, trace, initial_clauses)
        
        # # Extraer las cadenas de razonamiento
        # trace.extract_reasoning_chains()

        return raw_trace

if __name__ == "__main__":
    solver = PrologSolver(llm_jem=LLMJEM())
    solver.solve(["contraseña(X, Y, Z) :- alfa(X), beta(Y), ganma(Z).","alfa(1).", "alfa(2).", "beta(1).", "ganma(Z) :- hola(Z).", "hola(1).", "hola(2)."], "contraseña(X,Y,Z).")