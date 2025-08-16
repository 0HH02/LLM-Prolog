import os
import tempfile
import subprocess
import re
import copy
from typing import List, Dict, Optional, Set, Tuple
import json
from pathlib import Path
from collections import deque
from typing import List, Optional

class Clausula:
    def __init__(self, nombre, valor=None, veracidad="", profundidad = 0, padre=None):
        self.nombre = nombre
        self.valor = valor if valor is not None else []  # array de Clausula
        self.veracidad = veracidad  # string
        self.profundidad = profundidad
        self.padre = padre  # Clausula

    def __eq__(self, other):
        if not isinstance(other, Clausula):
            return False
        self_nombre = self.nombre.split('(')[0].strip()
        self_aridad = len(self.nombre.split('(')[1].split(',')) if '(' in self.nombre else 0

        # Extraer nombre y aridad del contenido
        other_nombre = other.nombre.split('(')[0].strip()
        other_aridad = len(other.nombre.split('(')[1].split(',')) if '(' in other.nombre else 0
        return (self_nombre == other_nombre and self_aridad == other_aridad and self.veracidad == other.veracidad and len(self.valor) == len(other.valor))

    def to_dict(self):
        output_dict = {
            "nombre": self.nombre,
            "veracidad": self.veracidad
        }

        if self.valor:  # Si hay nodos hijos
            # Llama recursivamente 'to_dict' en cada hijo
            output_dict["valor"] = [child.to_dict() for child in self.valor]

        return output_dict

    def pretty_print(self, indent_level=0):
        indent = "  " * indent_level
        output = []
        output.append(f"{indent}{{")
        output.append(f"{indent}  \"nombre\": \"{self.nombre}\",")
        
        # La línea de veracidad no lleva coma si no hay 'valor' o si 'valor' está vacío.
        veracidad_line = f"{indent}  \"veracidad\": \"{self.veracidad}\""

        if self.valor:
            output.append(veracidad_line + ",") # Añadir coma si 'valor' sigue
            output.append(f"{indent}  \"valor\": [")
            child_strings = []
            for i, child in enumerate(self.valor):
                child_strings.append(child.pretty_print(indent_level + 2))
            output.append(",\n".join(child_strings)) # Los hijos se unen con ',\n'
            output.append(f"{indent}  ]")
        else:
            output.append(veracidad_line) # Sin coma si 'valor' no sigue o está vacío.

        output.append(f"{indent}}}")
        return "\n".join(output)

    def __repr__(self):
        # Representación útil para depuración, no para la salida final solicitada.
        padre_nombre = self.padre.nombre if self.padre else "None"
        return (f"Clausula(nombre='{self.nombre}', veracidad='{self.veracidad}', "
                f"num_hijos={len(self.valor)}, padre='{padre_nombre}')")

class PrologSolver:
    """
    Implementa un solver basado en Prolog para inferencia lógica con justificaciones.
    """

    def _create_prolog_program(self, clauses: List[str]) -> str:
        """Crea un programa Prolog a partir de una lista de HornClauses."""
        rules = "\n".join([clause for clause in clauses])
        print(f"Programa Prolog: {rules}")
        return rules
    
    def ejecutar_prolog_con_json(self, prolog_code, consulta):
        """
        Ejecuta un código Prolog usando forall/2 para mayor robustez y devuelve
        un diccionario con los resultados y la traza.
        """
        enriq_trace = r"""
        :- use_module(library(http/json)).
        :- set_prolog_flag(trace_file, true).
        :- leash(-all).
        user:prolog_trace_interception(Port, Frame, _PC, continue) :-
            ( prolog_frame_attribute(Frame, level, Lvl) -> Indent is Lvl * 2 ; Indent = 0 ),
            prolog_frame_attribute(Frame, goal,  Goal),
            ( prolog_frame_attribute(Frame, clause, ClRef),
            clause_property(ClRef, file(File)),
            clause_property(ClRef, line_count(Line))
            -> true
            ; File = '<dynamic>', Line = 0
            ),
            format(user_error, '~N~*|~w: ~p @ ~w:~d~n', [Indent, Port, Goal, File, Line]).
        """

        var_names = sorted(list(set(re.findall(r'\b([A-Z_][a-zA-Z0-9_]*)\b', consulta))))
        
        # Se elimina el punto final de la consulta si existe
        if consulta.endswith('.'):
            consulta_limpia = consulta[:-1]
        else:
            consulta_limpia = consulta

        goal_logic = ""
        if var_names:
            # Usar format para generar JSON simple en lugar de json_write_dict
            var_format_parts = []
            for v in var_names:
                var_format_parts.append(f'\\"{v.lower()}\\":\\"~w\\"')
            
            format_string = "{" + ",".join(var_format_parts) + "}"
            var_args = ",".join([v for v in var_names])
            
            json_action = f"format(user_output, '{format_string}~n', [{var_args}]), flush_output(user_output)"
            
            # ### CAMBIO CLAVE: Usar forall/2 ###
            # forall((generador_de_soluciones), (accion_a_realizar)). Los paréntesis son importantes.
            goal_logic = f"forall(({consulta_limpia}), ({json_action}))"
        else:
            # Para consultas sin variables, el comportamiento es encontrar una solución o ninguna.
            # (Si_exito -> Entonces_imprime_true ; Si_no_exito -> no hagas nada)
            json_action_no_vars = "format(user_output, '{\\\"solution\\\":true}~n', []), flush_output(user_output)"
            goal_logic = f"(({consulta_limpia}) -> {json_action_no_vars} ; true)"

        # Envolvemos la lógica principal en un catch para capturar errores de Prolog.
        final_goal_logic = f"catch(({goal_logic}), E, (format(user_error, '~N### CAUGHT_PROLOG_EXCEPTION ###~n~w~n### END_EXCEPTION ###~n', [E]), fail))"

        stdout_capture = ""
        stderr_capture = ""
        swipl_executable = "swipl"
        temp_prolog_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.pl', delete=False)
        temp_prolog_file_name = temp_prolog_file.name
        
        try:
            temp_prolog_file.write(enriq_trace)
            temp_prolog_file.write('\n')
            temp_prolog_file.write(prolog_code)
            temp_prolog_file.close()
            prolog_file_path_escaped = temp_prolog_file.name.replace("'", "''")
            
            final_goal = (
                f"consult('{prolog_file_path_escaped}'), "
                f"trace, "
                f"{final_goal_logic}"
            )

            # DEBUG: Imprime la meta final para poder probarla manualmente.
            print("--- DEBUG: Meta de Prolog a ejecutar ---")
            print(final_goal)
            print("-----------------------------------------")

            process = subprocess.Popen(
                [swipl_executable, "-q", "-g", final_goal, "-t", "halt"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8', errors='replace'
            )
            stdout_capture, stderr_capture = process.communicate(timeout=60)
            
            lista_resultados = []
            if stdout_capture:
                # Intentar parsear el JSON completo primero
                try:
                    # Si todo el stdout es un JSON válido
                    parsed_json = json.loads(stdout_capture.strip())
                    if isinstance(parsed_json, list):
                        lista_resultados.extend(parsed_json)
                    else:
                        lista_resultados.append(parsed_json)
                except json.JSONDecodeError:
                    # Si no, procesar línea por línea y concatenar si es necesario
                    json_buffer = ""
                    for line in stdout_capture.strip().split('\n'):
                        line = line.strip()
                        if line:
                            json_buffer += line
                            try:
                                # Intentar parsear el buffer completo
                                parsed = json.loads(json_buffer)
                                lista_resultados.append(parsed)
                                json_buffer = ""  # Limpiar buffer después de éxito
                            except json.JSONDecodeError:
                                # Continuar acumulando en el buffer
                                continue
                    
                    # Si queda algo en el buffer al final, intentar parsearlo
                    if json_buffer:
                        try:
                            parsed = json.loads(json_buffer)
                            lista_resultados.append(parsed)
                        except json.JSONDecodeError:
                            print(f"Advertencia: No se pudo decodificar el JSON final: {json_buffer}")
            
            output_dict = {
                "resultados": lista_resultados,
                "traza": stderr_capture.strip(),
                "errors": ""
            }

        except subprocess.TimeoutExpired:
            process.kill()
            stdout_capture, stderr_capture = process.communicate()
            output_dict = { "resultados": [], "traza": stderr_capture, "errors": "ERROR: Timeout." }
        except Exception as e:
            output_dict = { "resultados": [], "traza": "", "errors": f"ERROR: Python exception: {e}" }
        finally:
            if os.path.exists(temp_prolog_file_name):
                os.remove(temp_prolog_file_name)

        return output_dict
    
    def _procesar_traza(self, traza_str):
        # Inicializamos un array de Clausulas llamado ramas_de_pensamientos
        ramas_de_pensamientos = []
        # Inicializamos una variable llamada root con la Clausula root con el nombre root, array vacío, valor = "" y padre = None
        root = Clausula(nombre="root", veracidad="", padre=None)
        # Inicializamos una variable llamada nodo_actual que será igual a root
        nodo_actual = root

        # Regex para parsear: Tipo, Nivel (ignorado por ahora), Contenido
        line_regex = re.compile(r'^\s*(call|exit|fail|redo)(?:\(\d+\))?:\s*([^@]+?)\s*(?:@.*)?$')
        
        traza = traza_str.strip().split('\n')
        # Por cada linea en la traza:
        conta = 0
        for index, line_raw in enumerate(traza):
            line = line_raw.strip()
            if not line:
                continue

            # Parseala para determinar el contenido de la linea y desestrúcturalo en nombre, aridad y tipo de llamada.
            match = line_regex.match(line)
            if not match:
                # print(f"Advertencia: No se pudo parsear la línea: {line}")
                continue

            tipo_llamada, contenido_str = match.groups()
            # 'nombre' y 'aridad' se infieren del 'contenido_str' según el contexto.


            if tipo_llamada == "call":
                # Si la linea es de tipo Call, si el contenido es fail salta la linea
                if contenido_str == "fail":
                    continue
                # si no crea una Clausula con nombre = al contenido y padre = nodo_actual, esta será el nuevo nodo_actual
                nueva_clausula = Clausula(nombre=contenido_str, padre=nodo_actual)
                nodo_actual.valor.append(nueva_clausula)
                nodo_actual = nueva_clausula
            
            elif tipo_llamada == "exit":
                # El nodo_actual es el que fue llamado y ahora está saliendo (Exit)
                exiting_node = nodo_actual
                
                # Si el array valor está vacío crea una Cláusula con el nombre = al contenido, veracidad = "verde" y agrégalo al array de cláusulas de valor del nodo_actual.
                if not exiting_node.valor: 
                    clausula_resultado = Clausula(nombre=contenido_str, veracidad="verde", padre=exiting_node)
                    exiting_node.valor.append(clausula_resultado)
                exiting_node.veracidad = "verde"
                
                # Nodo_actual será nodo_actual.padre (para ambos casos de Exit)
                if exiting_node.padre:
                    nodo_actual = exiting_node.padre
                
            elif tipo_llamada == "fail":
                # si el contenido es fail salta la linea
                if contenido_str == "fail":
                    continue
                
                failing_node = nodo_actual # El nodo que fue llamado y ahora está fallando (Fail)
                
                # si no si el array valor está vacío crea una Cláusula con el nombre = al contenido, veracidad = "rojo" y agrégalo al array de cláusulas de valor del nodo_actual.
                if not failing_node.valor:
                    clausula_resultado = Clausula(nombre=contenido_str, veracidad="rojo", padre=failing_node)
                    failing_node.valor.append(clausula_resultado)

                failing_node.veracidad = "rojo"
                
                # y el nodo_actual será nodo_actual.padre (para ambos casos de Fail)
                if failing_node.padre:
                    nodo_actual = failing_node.padre

            elif tipo_llamada == "redo":
                # Hacemos una copia del arbol almacenado en root y la guardamos en el array de ramas_de_pensamientos.
                while nodo_actual.padre:
                    nodo_actual.veracidad = "rojo"
                    nodo_actual = nodo_actual.padre
                ramas_de_pensamientos.append(copy.deepcopy(root))
                
                # Luego bajamos por el arbol desde root hasta encontrar una de las cláusulas 
                # ... con nombre igual al contenido de la linea
                # (contenido_str es, por ej., "hola(_4668)")
                
                q = [root] # Cola para búsqueda BFS para encontrar el nodo
                node_to_redo_found = None
                # Usamos un set para evitar ciclos en la búsqueda si la estructura del árbol fuera inesperada,
                # aunque con padres no debería haber ciclos descendentes.
                visited_for_bfs = set() 

                last_last_found = None
                last_found = None

                while q:
                    curr_search_node = q.pop(0)
                    
                    if id(curr_search_node) in visited_for_bfs: # Comprobar por id del objeto
                        continue
                    visited_for_bfs.add(id(curr_search_node))

                    # Extraer nombre y aridad del nodo actual
                    curr_nombre = curr_search_node.nombre.split('(')[0].strip()
                    curr_aridad = len(curr_search_node.nombre.split('(')[1].split(',')) if '(' in curr_search_node.nombre else 0

                    # Extraer nombre y aridad del contenido
                    cont_nombre = contenido_str.split('(')[0].strip()
                    cont_aridad = len(contenido_str.split('(')[1].split(',')) if '(' in contenido_str else 0

                    # Comparar nombre y aridad
                    if curr_nombre == cont_nombre and curr_aridad == cont_aridad:
                        last_last_found = last_found
                        last_found = curr_search_node

                    if curr_search_node.nombre == contenido_str:
                        node_to_redo_found = curr_search_node
                    for child in curr_search_node.valor:
                        if isinstance(child, Clausula): # Asegurarse de que el hijo es una Clausula
                            q.append(child)
                if node_to_redo_found == None:
                        node_to_redo_found = last_found
                        node_to_redo_found.nombre = contenido_str
                
                if node_to_redo_found != None:
                    #ELIMINAR ESTO DESPUES DE LA PRUEBAs
                    if index + 1 == len(traza):
                        break
                    next_clausule = traza[index + 1]
                    next_contenido = line_regex.match(next_clausule).group(2).strip()
                    nombre = next_contenido.split('(')[0].strip()
                    aridad = len(next_contenido.split('(')[1].split(',')) if '(' in next_contenido else 0
                    if node_to_redo_found.valor != []:
                        for index, clausula in enumerate(node_to_redo_found.valor):
                            if clausula.nombre == nombre and len(clausula.nombre.split('(')[1].split(',')) if '(' in clausula.nombre else 0 == aridad:
                                node_to_redo_found.valor = node_to_redo_found.valor[:index + 1]
                                break
                        else:
                            # Limpiar el array de valor del nodo encontrado y reiniciar su veracidad
                            node_to_redo_found.valor = [] 
                    node_to_redo_found.veracidad = ""  # Reiniciar su estado de veracidad
                    nodo_actual = node_to_redo_found
                    current = node_to_redo_found
                    while current.padre:

                        indice = 0
                        for son in current.padre.valor:
                            if son.nombre == current.nombre:
                                break
                            indice += 1
                        # Truncar el array de valor del padre hasta el índice encontrado
                        current.padre.valor = current.padre.valor[:indice + 1]
                        current = current.padre
                        
                else:
                    # Este caso idealmente no debería ocurrir si la traza es consistente.
                    # print(f"Advertencia: Objetivo de REDO '{contenido_str}' no encontrado en el estado actual del árbol.")
                    pass

        ramas_de_pensamientos.append(copy.deepcopy(root))

        return ramas_de_pensamientos


    def solve(self, initial_clauses: List[str], goal_clause_obj: Optional[str] = None, problem_name: str = "Problema") -> List[Clausula]:
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
        dict_traza = self.ejecutar_prolog_con_json(program_string, consulta)
        raw_trace = dict_traza["traza"]
        print("--- Resultados ----")
        print(dict_traza["resultados"])
        print("--- Fin de resultados ----")
        raw_trace = "\n".join(raw_trace.split("\n")[1:-6]) if raw_trace else ""
        print("--- Traza cruda de Prolog ---")
        print(raw_trace)
        print("--- Fin de traza cruda ---")
        print("--- Errores ---")
        print(dict_traza["errors"])
        print("--- Fin de errores ---")
        

        result = {
            "status": "success" if dict_traza["resultados"] else "failed",
            "resultados": dict_traza["resultados"],
            "ramas": [],
            "errors": dict_traza["errors"]
        }
        # Procesar la traza
        try:
            ramas = self._procesar_traza(raw_trace)
            result["ramas"] = ramas
        except Exception as e:
            error_msg = f"Error en MISA-J: {str(e)}"
            print(f"ERROR: {error_msg}")
            result["ramas"] = []
            result["errors"] = "No se pudo procesar la traza."
        
        # Crear directorios si no existen
        solutions_dir = Path("solutions")

        # Guardar el JSON
        json_path = solutions_dir / f"ramas_de_pensamiento.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            # Convertir cada objeto Clausula a diccionario antes de guardar
            ramas_dict = [rama.to_dict() for rama in result["ramas"]]
            json.dump(ramas_dict, f, indent=2, ensure_ascii=False)

        return result

if __name__ == "__main__":
    solver = PrologSolver()
    result = solver.solve([
    "cofre(oro).", "cofre(plata).", "cofre(plomo).", "verdadera(enunciado_oro, UbicacionRetrato) :- UbicacionRetrato = oro.","verdadera(enunciado_plata, UbicacionRetrato) :- UbicacionRetrato \= plata.", "verdadera(enunciado_plomo, UbicacionRetrato) :- UbicacionRetrato \= oro.","regla_a_lo_sumo_uno_verdadero(UbicacionRetrato) :- findall(Enunciado, verdadera(Enunciado, UbicacionRetrato), EnunciadosVerdaderos), length(EnunciadosVerdaderos, NumeroVerdaderos), NumeroVerdaderos =< 1.","solucion(CofreDelRetrato) :- cofre(CofreDelRetrato), regla_a_lo_sumo_uno_verdadero(CofreDelRetrato)."
  ], "solucion(Cofre).")
    print(result)