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
    
    def _ejecutar_prolog_con_traza_modificado(self, prolog_code, consulta):
        """
        Ejecuta un código Prolog en SWI-Prolog, captura y devuelve la traza de stderr.
        """

        enriq_trace = r"""
        :- set_prolog_flag(trace_file, true).
        :- leash(-all).

        user:prolog_trace_interception(Port, Frame, _PC, continue) :-
                (   prolog_frame_attribute(Frame, level, Lvl)
                ->  Indent is Lvl * 2
                ;   Indent = 0
                ),
                prolog_frame_attribute(Frame, goal,  Goal),
                (   prolog_frame_attribute(Frame, clause, ClRef),
                    clause_property(ClRef, file(File)),
                    clause_property(ClRef, line_count(Line))
                ->  true
                ;   File = '<dynamic>', Line = 0
                ),
                format(user_error,
                    '~N~*|~w: ~p @ ~w:~d~n',
                    [Indent, Port, Goal, File, Line]).
        """

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
            prolog_file_path_escaped = temp_prolog_file_name.replace("'", "''")
            
            # Modificado para imprimir excepciones a user_error (stderr)
            goal_prolog = (
                f"consult('{prolog_file_path_escaped}'), "          # carga el archivo
                f"trace, "                          # inicia la traza
                # Ejecuta la consulta, captura excepciones y continúa para ver la traza
                f"catch(({consulta[:-1]}, fail), "
                f"E, (format(user_error, "
                f"'~N### CAUGHT_EXCEPTION ###~n~w~n### END_EXCEPTION ###~n', [E]), fail)), "
                "halt."
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
        raw_trace = self._ejecutar_prolog_con_traza_modificado(program_string, consulta)
        raw_trace = "\n".join(raw_trace.split("\n")[1:-6])
        print("--- Traza cruda de Prolog ---")
        print(raw_trace)
        print("--- Fin de traza cruda ---")
        
        # Procesar la traza
        ramas = self._procesar_traza(raw_trace)
        
        # Crear directorios si no existen
        solutions_dir = Path("solutions")

        # Guardar el JSON
        json_path = solutions_dir / f"ramas_de_pensamiento.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            # Convertir cada objeto Clausula a diccionario antes de guardar
            ramas_dict = [rama.to_dict() for rama in ramas]
            json.dump(ramas_dict, f, indent=2, ensure_ascii=False)

        return ramas

if __name__ == "__main__":
    solver = PrologSolver()
    solver.solve(["contraseña(X, Y, Z) :- alfa(X), beta(Y), ganma(Z).","alfa(1).", "alfa(2).", "beta(1).", "ganma(Z) :- hola(Z).", "hola(1).", "hola(2)."], "contraseña(X,Y,Z).")