import re
import copy
import json
from pathlib import Path
from collections import deque
from graphviz import Digraph

import os
import tempfile
import subprocess
from typing import List, Dict, Optional, Set, Tuple
from typing import List, Optional

class Clausula:
    def __init__(self, nombre, origen="<dynamic>:0", veracidad="",
                 profundidad=0, padre=None):
        self.nombre = nombre                       # p/2(args) …
        self.origen = origen                       # fichero:línea
        self.veracidad = veracidad                 # "", "verde", "rojo"
        self.profundidad = profundidad             # nivel
        self.padre = padre                         # Clausula | None
        self.valor = []                            # list[Clausula]
        self.choice_open = False                   # ¿dejé choice-point?

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
        d = {"nombre": self.nombre,
             "origen": self.origen,
             "veracidad": self.veracidad}
        if self.valor:
            d["valor"] = [h.to_dict() for h in self.valor]
        return d

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
        return (f"Clausula('{self.nombre}', nivel={self.profundidad}, "
                f"veracidad='{self.veracidad}', valor={len(self.valor)})")

# -------------  AJUSTA SOLO ESTA FUNCIÓN  ------------------------------------
def procesar_traza(traza_str):
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
                arbol_dict = ramas_de_pensamientos[-1].to_dict()
        
                # Determinar la carpeta basada en la veracidad del primer nodo
                target_dir = Path("solutions/pruebas/success")
                
                # Generar y guardar el gráfico
                dot = _create_thought_graph(arbol_dict)
                dot.render(str(target_dir / f'arbol_pensamiento_{conta}'), view=False, cleanup=True)
                conta += 1
                print(line_raw)
                if line_raw == "                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36":
                    print("llegue")
                
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
                        # print("node_found: ", node_to_redo_found)
                    for child in curr_search_node.valor:
                        if isinstance(child, Clausula): # Asegurarse de que el hijo es una Clausula
                            q.append(child)
                if node_to_redo_found == None:
                        print(last_found)
                        print(last_last_found)
                        print(contenido_str)

                        node_to_redo_found = last_found
                        node_to_redo_found.nombre = contenido_str
                        print("Solo se encontró un nodo con igual nombre, aridad y profundidad")
                
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
                            if clausula.nombre == nombre and (len(clausula.nombre.split('(')[1].split(',')) if '(' in clausula.nombre else 0) == aridad:
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
# ------------------------------------------------------------------------------

def _create_thought_graph(data, graph=None, parent_id=None, node_counter=[0]):
    """
    Recursively creates nodes and edges for the Graphviz diagram from the JSON data.
    """
    if graph is None:
        graph = Digraph(comment='Cadena de Pensamientos', format='png') # You can change 'png' to 'svg', 'jpg', etc.
        graph.attr(rankdir='TB') # Top to bottom layout
        graph.attr('node', shape='box', style='filled', fontname='Arial')

    current_node_id = f"node_{node_counter[0]}"
    node_counter[0] += 1

    name = data.get("nombre", "N/A")
    veracidad = data.get("veracidad", "")

    # Define node color based on 'veracidad'
    fill_color = "lightblue" # Default
    if veracidad == "verde":
        fill_color = "lightgreen"
    elif veracidad == "rojo":
        fill_color = "salmon"

    # Add the node to the graph
    graph.node(current_node_id, label="{}\\n({})".format(name.replace('\\', '\\\\'), veracidad), fillcolor=fill_color)

    # Add an edge from the parent node if it exists
    if parent_id:
        graph.edge(parent_id, current_node_id)

    # Recursively process children
    if "valor" in data and isinstance(data["valor"], list):
        for child in data["valor"]:
            _create_thought_graph(child, graph, current_node_id, node_counter)

    return graph

def create_prolog_program(clauses: List[str]) -> str:
    """Crea un programa Prolog a partir de una lista de HornClauses."""
    rules = "\n".join([clause for clause in clauses])
    # print(f"Programa Prolog: {rules}")
    return rules

def ejecutar_prolog_con_json(prolog_code, consulta):
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

# -------------------
# Example usage
# -------------------
if __name__ == "__main__":
    import textwrap
     # Crear el programa Prolog

    initial_clauses = [
"family(bellini).",
"family(cellini).",
"meaning(a, is_cellini(b)).",
"meaning(b, (is_cellini(b) ; (is_bellini(c), is_bellini(b)))).",
"meaning(c, is_bellini(c)).",
"meaning(d, is_bellini(c)).",
"is_bellini(Chest, Authors) :- member(author(Chest, bellini), Authors).",
"is_cellini(Chest, Authors) :- member(author(Chest, cellini), Authors).",
"prop_true(is_cellini(Chest), Authors) :- is_cellini(Chest, Authors).",
"prop_true(is_bellini(Chest), Authors) :- is_bellini(Chest, Authors).",
"prop_true(not(Proposition), Authors) :- \+ prop_true(Proposition, Authors).",
"prop_true((Prop1, Prop2), Authors) :- prop_true(Prop1, Authors), prop_true(Prop2, Authors).",
"prop_true((Prop1 ; Prop2), Authors) :- prop_true(Prop1, Authors) ; prop_true(Prop2, Authors).",
"check_chest(Chest, Author, Meaning, Authors) :- (Author = bellini, prop_true(Meaning, Authors)) ; (Author = cellini, prop_true(not(Meaning), Authors)).",
"find_solution(Authors) :- Authors = [author(a, AA), author(b, AB), author(c, AC), author(d, AD)], member(AA, [bellini, cellini]), member(AB, [bellini, cellini]), member(AC, [bellini, cellini]), member(AD, [bellini, cellini]), meaning(a, MeaningA), check_chest(a, AA, MeaningA, Authors), meaning(b, MeaningB), check_chest(b, AB, MeaningB, Authors), meaning(c, MeaningC), check_chest(c, AC, MeaningC, Authors), meaning(d, MeaningD), check_chest(d, AD, MeaningD, Authors)."]
    program_string = create_prolog_program(initial_clauses)
    
    consulta = f"find_solution(Authors)."

    # Ejecutar Prolog y obtener la traza
    dict_traza = ejecutar_prolog_con_json(program_string, consulta)
    raw_trace = dict_traza["traza"]
    print("--- Resultados ----")
    print(dict_traza["resultados"])
    print("--- Fin de resultados ----")
    raw_trace = "\n".join(raw_trace.split("\n")[1:-6]) if raw_trace else ""
    # print("--- Traza cruda de Prolog ---")
    # print(raw_trace)
    # print("--- Fin de traza cruda ---")
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
        ramas = procesar_traza(raw_trace)
        result["ramas"] = ramas
    except Exception as e:
        error_msg = f"Error en MISA-J: {str(e)}"
        print(f"ERROR: {error_msg}")
        result["ramas"] = []
        result["errors"] = "No se pudo procesar la traza."
        
        # # Crear directorios si no existen
        # solutions_dir = Path("solutions")

        # # Guardar el JSON
        # json_path = solutions_dir / f"ramas_de_pensamiento.json"
        # with open(json_path, 'w', encoding='utf-8') as f:
        #     # Convertir cada objeto Clausula a diccionario antes de guardar
        #     ramas_dict = [rama.to_dict() for rama in result["ramas"]]
        #     json.dump(ramas_dict, f, indent=2, ensure_ascii=False)

        # return result
#     sample_trace = textwrap.dedent("""
#                         call: catch((find_solution(_36),json_write_dict(user_output,json{authors:_36}),nl(user_output),fail;true),_84,(format(user_error,'~N### CAUGHT_EXCEPTION ###~n~w~n### END_EXCEPTION ###~n',[_84]),fail)) @ <dynamic>:0
#                         call: find_solution(_36) @ <dynamic>:0
#                           call: lists:member(_12612,[bellini,cellini]) @ <dynamic>:0
#                           exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: lists:member(_12624,[bellini,cellini]) @ <dynamic>:0
#                           exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: lists:member(_12636,[bellini,cellini]) @ <dynamic>:0
#                           exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: lists:member(_12648,[bellini,cellini]) @ <dynamic>:0
#                           exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: meaning(a,_13422) @ <dynamic>:0
#                           exit: meaning(a,is_cellini(b)) @ /tmp/tmpe46gq0i8.pl:18
#                           call: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                             call: bellini=bellini @ <dynamic>:0
#                             exit: bellini=bellini @ <dynamic>:0
#                             call: prop_true(is_cellini(b),[author(a,bellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                               call: is_cellini(b,[author(a,bellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 call: lists:member(author(b,cellini),[author(a,bellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 fail: lists:member(author(b,cellini),[author(a,bellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                               fail: is_cellini(b,[author(a,bellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                             fail: prop_true(is_cellini(b),[author(a,bellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                           redo(13): check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                             call: bellini=cellini @ <dynamic>:0
#                             fail: bellini=cellini @ <dynamic>:0
#                           fail: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                           redo(0): lists:member(_12648,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: meaning(a,_13494) @ <dynamic>:0
#                           exit: meaning(a,is_cellini(b)) @ /tmp/tmpe46gq0i8.pl:18
#                           call: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,bellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                             call: bellini=bellini @ <dynamic>:0
#                             exit: bellini=bellini @ <dynamic>:0
#                             call: prop_true(is_cellini(b),[author(a,bellini),author(b,bellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                               call: is_cellini(b,[author(a,bellini),author(b,bellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                                 call: lists:member(author(b,cellini),[author(a,bellini),author(b,bellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                                 fail: lists:member(author(b,cellini),[author(a,bellini),author(b,bellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                               fail: is_cellini(b,[author(a,bellini),author(b,bellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                             fail: prop_true(is_cellini(b),[author(a,bellini),author(b,bellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                           redo(13): check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,bellini),author(c,bellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                             call: bellini=cellini @ <dynamic>:0
#                             fail: bellini=cellini @ <dynamic>:0
#                           fail: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,bellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                           redo(0): lists:member(_12636,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: lists:member(_12648,[bellini,cellini]) @ <dynamic>:0
#                           exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: meaning(a,_13494) @ <dynamic>:0
#                           exit: meaning(a,is_cellini(b)) @ /tmp/tmpe46gq0i8.pl:18
#                           call: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,bellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                             call: bellini=bellini @ <dynamic>:0
#                             exit: bellini=bellini @ <dynamic>:0
#                             call: prop_true(is_cellini(b),[author(a,bellini),author(b,bellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                               call: is_cellini(b,[author(a,bellini),author(b,bellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                                 call: lists:member(author(b,cellini),[author(a,bellini),author(b,bellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                                 fail: lists:member(author(b,cellini),[author(a,bellini),author(b,bellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                               fail: is_cellini(b,[author(a,bellini),author(b,bellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                             fail: prop_true(is_cellini(b),[author(a,bellini),author(b,bellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                           redo(13): check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,bellini),author(c,cellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                             call: bellini=cellini @ <dynamic>:0
#                             fail: bellini=cellini @ <dynamic>:0
#                           fail: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,bellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                           redo(0): lists:member(_12648,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: meaning(a,_13566) @ <dynamic>:0
#                           exit: meaning(a,is_cellini(b)) @ /tmp/tmpe46gq0i8.pl:18
#                           call: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,bellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                             call: bellini=bellini @ <dynamic>:0
#                             exit: bellini=bellini @ <dynamic>:0
#                             call: prop_true(is_cellini(b),[author(a,bellini),author(b,bellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                               call: is_cellini(b,[author(a,bellini),author(b,bellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                                 call: lists:member(author(b,cellini),[author(a,bellini),author(b,bellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                                 fail: lists:member(author(b,cellini),[author(a,bellini),author(b,bellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                               fail: is_cellini(b,[author(a,bellini),author(b,bellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                             fail: prop_true(is_cellini(b),[author(a,bellini),author(b,bellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                           redo(13): check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,bellini),author(c,cellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                             call: bellini=cellini @ <dynamic>:0
#                             fail: bellini=cellini @ <dynamic>:0
#                           fail: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,bellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                           redo(0): lists:member(_12624,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: lists:member(_12636,[bellini,cellini]) @ <dynamic>:0
#                           exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: lists:member(_12648,[bellini,cellini]) @ <dynamic>:0
#                           exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: meaning(a,_13494) @ <dynamic>:0
#                           exit: meaning(a,is_cellini(b)) @ /tmp/tmpe46gq0i8.pl:18
#                           call: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                             call: bellini=bellini @ <dynamic>:0
#                             exit: bellini=bellini @ <dynamic>:0
#                             call: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                               call: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 call: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 exit: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                               exit: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:23
#                             exit: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:24
#                           exit: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                           call: meaning(b,_14176) @ <dynamic>:0
#                           exit: meaning(b,(is_cellini(b);is_bellini(c),is_bellini(b))) @ /tmp/tmpe46gq0i8.pl:19
#                           call: check_chest(b,cellini,(is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                             call: cellini=bellini @ <dynamic>:0
#                             fail: cellini=bellini @ <dynamic>:0
#                           redo(13): check_chest(b,cellini,(is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                             call: cellini=cellini @ <dynamic>:0
#                             exit: cellini=cellini @ <dynamic>:0
#                             call: prop_true(not((is_cellini(b);is_bellini(c),is_bellini(b))),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                               call: prop_true((is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 call: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                   call: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                     call: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                     exit: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                                   exit: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:23
#                                 exit: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:24
#                               exit: prop_true((is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:28
#                             fail: prop_true(not((is_cellini(b);is_bellini(c),is_bellini(b))),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                           fail: check_chest(b,cellini,(is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 redo(0): lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                                 fail: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                               fail: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                             fail: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                           redo(13): check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                             call: bellini=cellini @ <dynamic>:0
#                             fail: bellini=cellini @ <dynamic>:0
#                           fail: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                           redo(0): lists:member(_12648,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: meaning(a,_13566) @ <dynamic>:0
#                           exit: meaning(a,is_cellini(b)) @ /tmp/tmpe46gq0i8.pl:18
#                           call: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                             call: bellini=bellini @ <dynamic>:0
#                             exit: bellini=bellini @ <dynamic>:0
#                             call: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                               call: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                                 call: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                                 exit: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                               exit: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:23
#                             exit: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:24
#                           exit: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                           call: meaning(b,_14248) @ <dynamic>:0
#                           exit: meaning(b,(is_cellini(b);is_bellini(c),is_bellini(b))) @ /tmp/tmpe46gq0i8.pl:19
#                           call: check_chest(b,cellini,(is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                             call: cellini=bellini @ <dynamic>:0
#                             fail: cellini=bellini @ <dynamic>:0
#                           redo(13): check_chest(b,cellini,(is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                             call: cellini=cellini @ <dynamic>:0
#                             exit: cellini=cellini @ <dynamic>:0
#                             call: prop_true(not((is_cellini(b);is_bellini(c),is_bellini(b))),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                               call: prop_true((is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                                 call: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                                   call: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                                     call: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                                     exit: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                                   exit: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:23
#                                 exit: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:24
#                               exit: prop_true((is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:28
#                             fail: prop_true(not((is_cellini(b);is_bellini(c),is_bellini(b))),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                           fail: check_chest(b,cellini,(is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                                 redo(0): lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                                 fail: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                               fail: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                             fail: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                           redo(13): check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                             call: bellini=cellini @ <dynamic>:0
#                             fail: bellini=cellini @ <dynamic>:0
#                           fail: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,bellini),author(d,cellini)]) @ <dynamic>:0
#                           redo(0): lists:member(_12636,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: lists:member(_12648,[bellini,cellini]) @ <dynamic>:0
#                           exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: meaning(a,_13566) @ <dynamic>:0
#                           exit: meaning(a,is_cellini(b)) @ /tmp/tmpe46gq0i8.pl:18
#                           call: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                             call: bellini=bellini @ <dynamic>:0
#                             exit: bellini=bellini @ <dynamic>:0
#                             call: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                               call: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                                 call: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                                 exit: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                               exit: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:23
#                             exit: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:24
#                           exit: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                           call: meaning(b,_14248) @ <dynamic>:0
#                           exit: meaning(b,(is_cellini(b);is_bellini(c),is_bellini(b))) @ /tmp/tmpe46gq0i8.pl:19
#                           call: check_chest(b,cellini,(is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                             call: cellini=bellini @ <dynamic>:0
#                             fail: cellini=bellini @ <dynamic>:0
#                           redo(13): check_chest(b,cellini,(is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                             call: cellini=cellini @ <dynamic>:0
#                             exit: cellini=cellini @ <dynamic>:0
#                             call: prop_true(not((is_cellini(b);is_bellini(c),is_bellini(b))),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                               call: prop_true((is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                                 call: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                                   call: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                                     call: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                                     exit: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                                   exit: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:23
#                                 exit: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:24
#                               exit: prop_true((is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:28
#                             fail: prop_true(not((is_cellini(b);is_bellini(c),is_bellini(b))),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                           fail: check_chest(b,cellini,(is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                                 redo(0): lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                                 fail: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                               fail: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                             fail: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                           redo(13): check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                             call: bellini=cellini @ <dynamic>:0
#                             fail: bellini=cellini @ <dynamic>:0
#                           fail: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,bellini)]) @ <dynamic>:0
#                           redo(0): lists:member(_12648,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: meaning(a,_13638) @ <dynamic>:0
#                           exit: meaning(a,is_cellini(b)) @ /tmp/tmpe46gq0i8.pl:18
#                           call: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                             call: bellini=bellini @ <dynamic>:0
#                             exit: bellini=bellini @ <dynamic>:0
#                             call: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                               call: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                                 call: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                                 exit: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                               exit: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:23
#                             exit: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:24
#                           exit: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                           call: meaning(b,_14320) @ <dynamic>:0
#                           exit: meaning(b,(is_cellini(b);is_bellini(c),is_bellini(b))) @ /tmp/tmpe46gq0i8.pl:19
#                           call: check_chest(b,cellini,(is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                             call: cellini=bellini @ <dynamic>:0
#                             fail: cellini=bellini @ <dynamic>:0
#                           redo(13): check_chest(b,cellini,(is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                             call: cellini=cellini @ <dynamic>:0
#                             exit: cellini=cellini @ <dynamic>:0
#                             call: prop_true(not((is_cellini(b);is_bellini(c),is_bellini(b))),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                               call: prop_true((is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                                 call: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                                   call: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                                     call: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                                     exit: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                                   exit: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:23
#                                 exit: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:24
#                               exit: prop_true((is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:28
#                             fail: prop_true(not((is_cellini(b);is_bellini(c),is_bellini(b))),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                           fail: check_chest(b,cellini,(is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                                 redo(0): lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                                 fail: lists:member(author(b,cellini),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                               fail: is_cellini(b,[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                             fail: prop_true(is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                           redo(13): check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                             call: bellini=cellini @ <dynamic>:0
#                             fail: bellini=cellini @ <dynamic>:0
#                           fail: check_chest(a,bellini,is_cellini(b),[author(a,bellini),author(b,cellini),author(c,cellini),author(d,cellini)]) @ <dynamic>:0
#                           redo(0): lists:member(_12612,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: lists:member(_12624,[bellini,cellini]) @ <dynamic>:0
#                           exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: lists:member(_12636,[bellini,cellini]) @ <dynamic>:0
#                           exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: lists:member(_12648,[bellini,cellini]) @ <dynamic>:0
#                           exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                           call: meaning(a,_13494) @ <dynamic>:0
#                           exit: meaning(a,is_cellini(b)) @ /tmp/tmpe46gq0i8.pl:18
#                           call: check_chest(a,cellini,is_cellini(b),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                             call: cellini=bellini @ <dynamic>:0
#                             fail: cellini=bellini @ <dynamic>:0
#                           redo(13): check_chest(a,cellini,is_cellini(b),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                             call: cellini=cellini @ <dynamic>:0
#                             exit: cellini=cellini @ <dynamic>:0
#                             call: prop_true(not(is_cellini(b)),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                               call: prop_true(is_cellini(b),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 call: is_cellini(b,[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                   call: lists:member(author(b,cellini),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                   fail: lists:member(author(b,cellini),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 fail: is_cellini(b,[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                               fail: prop_true(is_cellini(b),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                             redo(16): prop_true(not(is_cellini(b)),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:26
#                             exit: prop_true(not(is_cellini(b)),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:26
#                           exit: check_chest(a,cellini,is_cellini(b),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                           call: meaning(b,_14078) @ <dynamic>:0
#                           exit: meaning(b,(is_cellini(b);is_bellini(c),is_bellini(b))) @ /tmp/tmpe46gq0i8.pl:19
#                           call: check_chest(b,bellini,(is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                             call: bellini=bellini @ <dynamic>:0
#                             exit: bellini=bellini @ <dynamic>:0
#                             call: prop_true((is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                               call: prop_true(is_cellini(b),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 call: is_cellini(b,[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                   call: lists:member(author(b,cellini),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                   fail: lists:member(author(b,cellini),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 fail: is_cellini(b,[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                               fail: prop_true(is_cellini(b),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                             redo(16): prop_true((is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:28
#                               call: prop_true((is_bellini(c),is_bellini(b)),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 call: prop_true(is_bellini(c),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                   call: is_bellini(c,[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                     call: lists:member(author(c,bellini),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                     exit: lists:member(author(c,bellini),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                                   exit: is_bellini(c,[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:22
#                                 exit: prop_true(is_bellini(c),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:25
#                                 call: prop_true(is_bellini(b),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                   call: is_bellini(b,[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                     call: lists:member(author(b,bellini),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                     exit: lists:member(author(b,bellini),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                                   exit: is_bellini(b,[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:22
#                                 exit: prop_true(is_bellini(b),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:25
#                               exit: prop_true((is_bellini(c),is_bellini(b)),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:27
#                             exit: prop_true((is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:28
#                           exit: check_chest(b,bellini,(is_cellini(b);is_bellini(c),is_bellini(b)),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                           call: meaning(c,_15414) @ <dynamic>:0
#                           exit: meaning(c,is_bellini(c)) @ /tmp/tmpe46gq0i8.pl:20
#                           call: check_chest(c,bellini,is_bellini(c),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                             call: bellini=bellini @ <dynamic>:0
#                             exit: bellini=bellini @ <dynamic>:0
#                             call: prop_true(is_bellini(c),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                               call: is_bellini(c,[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 call: lists:member(author(c,bellini),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 exit: lists:member(author(c,bellini),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                               exit: is_bellini(c,[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:22
#                             exit: prop_true(is_bellini(c),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:25
#                           exit: check_chest(c,bellini,is_bellini(c),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                           call: meaning(d,_16096) @ <dynamic>:0
#                           exit: meaning(d,is_bellini(c)) @ /tmp/tmpe46gq0i8.pl:21
#                           call: check_chest(d,bellini,is_bellini(c),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                             call: bellini=bellini @ <dynamic>:0
#                             exit: bellini=bellini @ <dynamic>:0
#                             call: prop_true(is_bellini(c),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                               call: is_bellini(c,[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 call: lists:member(author(c,bellini),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                 exit: lists:member(author(c,bellini),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
#                               exit: is_bellini(c,[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:22
#                             exit: prop_true(is_bellini(c),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:25
#                           exit: check_chest(d,bellini,is_bellini(c),[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:29
#                         exit: find_solution([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /tmp/tmpe46gq0i8.pl:30
#                         call: json:json_write_dict(user_output,json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]}) @ <dynamic>:0
#                           call: json:json_write_dict(user_output,json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},[]) @ <dynamic>:0
#                             call: json:make_json_write_state([],_16950,_16952) @ <dynamic>:0
#                               call: json:default_json_write_state(_17012) @ <dynamic>:0
#                               exit: json:default_json_write_state(json_write_state(0,2,8,72,false)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                               call: json:set_json_write_state_fields([],json_write_state(0,2,8,72,false),_16950,_16952) @ <dynamic>:0
#                               exit: json:set_json_write_state_fields([],json_write_state(0,2,8,72,false),json_write_state(0,2,8,72,false),[]) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                             exit: json:make_json_write_state([],json_write_state(0,2,8,72,false),[]) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                             call: json:make_json_dict_options([],_17342,_17364) @ <dynamic>:0
#                               call: json:default_json_dict_options(_17402) @ <dynamic>:0
#                               exit: json:default_json_dict_options(json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:131
#                               call: json:set_json_options_fields([],json_options(null,true,false,error,string,'',_17472),_17342,_17364) @ <dynamic>:0
#                               exit: json:set_json_options_fields([],json_options(null,true,false,error,string,'',_17472),json_options(null,true,false,error,string,'',_17472),[]) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:122
#                             exit: json:make_json_dict_options([],json_options(null,true,false,error,string,'',_17472),[]) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:1077
#                             call: json:json_write_term(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},user_output,json_write_state(0,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ <dynamic>:0
#                               call: var(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]}) @ <dynamic>:0
#                               fail: var(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]}) @ <dynamic>:0
#                             redo(0): json:json_write_term(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},user_output,json_write_state(0,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:610
#                               call: is_dict(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},_17872) @ <dynamic>:0
#                               exit: is_dict(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},json) @ <dynamic>:0
#                               call: json:json_pairs(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},_17974) @ <dynamic>:0
#                                 call: json:json_dict_pairs(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},_17974) @ <dynamic>:0
#                                 fail: json:json_dict_pairs(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},_17974) @ <dynamic>:0
#                               redo(0): json:json_pairs(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},_17974) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:693
#                                 call: dict_pairs(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},_18122,_17974) @ <dynamic>:0
#                                 exit: dict_pairs(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},json,[authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]]) @ <dynamic>:0
#                               exit: json:json_pairs(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},[authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]]) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:693
#                               call: nonvar(json) @ <dynamic>:0
#                               exit: nonvar(json) @ <dynamic>:0
#                               call: json:json_options_tag(json_options(null,true,false,error,string,'',_17472),_18382) @ <dynamic>:0
#                               exit: json:json_options_tag(json_options(null,true,false,error,string,'',_17472),'') @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:122
#                               call: ''\=='' @ <dynamic>:0
#                               fail: ''\=='' @ <dynamic>:0
#                             redo(44): json:json_write_term(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},user_output,json_write_state(0,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:610
#                               call: _18362=[authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]] @ <dynamic>:0
#                               exit: [authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]]=[authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]] @ <dynamic>:0
#                               call: json:json_write_object([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]],user_output,json_write_state(0,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ <dynamic>:0
#                                 call: json:space_if_not_at_left_margin(user_output,json_write_state(0,2,8,72,false)) @ <dynamic>:0
#                                   call: stream_pair(user_output,_18600,_18580) @ <dynamic>:0
#                                   exit: stream_pair(user_output,_18600,user_output) @ <dynamic>:0
#                                   call: line_position(user_output,_18686) @ <dynamic>:0
#                                   exit: line_position(user_output,0) @ <dynamic>:0
#                                   call: 0==0 @ <dynamic>:0
#                                   exit: 0==0 @ <dynamic>:0
#                                 exit: json:space_if_not_at_left_margin(user_output,json_write_state(0,2,8,72,false)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:789
#                                 call: write(user_output,'{') @ <dynamic>:0

#                                 exit: write(user_output,'{') @ <dynamic>:0
#                                 call: json:json_write_state_width(json_write_state(0,2,8,72,false),_19054) @ <dynamic>:0
#                                 exit: json:json_write_state_width(json_write_state(0,2,8,72,false),72) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                                 call: 72==0 @ <dynamic>:0
#                                 fail: 72==0 @ <dynamic>:0
#                               redo(31): json:json_write_object([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]],user_output,json_write_state(0,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:696
#                                 call: json:json_write_state_indent(json_write_state(0,2,8,72,false),_19254) @ <dynamic>:0
#                                 exit: json:json_write_state_indent(json_write_state(0,2,8,72,false),0) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                                 call: json:json_print_length(json([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]]),json_options(null,true,false,error,string,'',_17472),72,0,_19406) @ <dynamic>:0
#                                   call: var(json([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]])) @ <dynamic>:0
#                                   fail: var(json([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]])) @ <dynamic>:0
#                                 redo(0): json:json_print_length(json([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]]),json_options(null,true,false,error,string,'',_17472),72,0,_19406) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:811
#                                   call: _19528 is 0+2 @ <dynamic>:0
#                                   exit: 2 is 0+2 @ <dynamic>:0
#                                   call: 2=<72 @ <dynamic>:0
#                                   exit: 2=<72 @ <dynamic>:0
#                                   call: error:must_be(list,[authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]]) @ <dynamic>:0
#                                     call: error:has_type(list,[authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]]) @ <dynamic>:0
#                                       call: is_list([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]]) @ <dynamic>:0
#                                       exit: is_list([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]]) @ <dynamic>:0
#                                     exit: error:has_type(list,[authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]]) @ /usr/lib/swi-prolog/library/error.pl:387
#                                   exit: error:must_be(list,[authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]]) @ /usr/lib/swi-prolog/library/error.pl:253
#                                   call: json:pairs_print_length([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]],json_options(null,true,false,error,string,'',_17472),72,2,_19406) @ <dynamic>:0
#                                     call: json:pair_len(authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,2,_20132) @ <dynamic>:0
#                                       call: compound(authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                       exit: compound(authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                       call: json:pair_nv(authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],_20292,_20294) @ <dynamic>:0
#                                       exit: json:pair_nv(authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],authors,[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:888
#                                       call: json:string_len(authors,2,_20422) @ <dynamic>:0
#                                         call: atom(authors) @ <dynamic>:0
#                                         exit: atom(authors) @ <dynamic>:0
#                                         call: atom_length(authors,_20578) @ <dynamic>:0
#                                         exit: atom_length(authors,7) @ <dynamic>:0
#                                         call: _20422 is 2+7+2 @ <dynamic>:0
#                                         exit: 11 is 2+7+2 @ <dynamic>:0
#                                       exit: json:string_len(authors,2,11) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:902
#                                       call: _20866 is 11+2 @ <dynamic>:0
#                                       exit: 13 is 11+2 @ <dynamic>:0
#                                       call: 13=<72 @ <dynamic>:0
#                                       exit: 13=<72 @ <dynamic>:0
#                                       call: json:json_print_length([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,13,_20132) @ <dynamic>:0
#                                         call: var([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                         fail: var([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                       redo(0): json:json_print_length([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,13,_20132) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:817
#                                         call: is_dict([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                         fail: is_dict([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                       redo(0): json:json_print_length([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,13,_20132) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:824
#                                         call: is_list([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                         exit: is_list([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                         call: _21388 is 13+2 @ <dynamic>:0
#                                         exit: 15 is 13+2 @ <dynamic>:0
#                                         call: 15=<72 @ <dynamic>:0
#                                         exit: 15=<72 @ <dynamic>:0
#                                         call: json:array_print_length([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,15,_20132) @ <dynamic>:0
#                                           call: json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,15,_21652) @ <dynamic>:0
#                                             call: var(author(a,cellini)) @ <dynamic>:0
#                                             fail: var(author(a,cellini)) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,15,_21652) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:817
#                                             call: is_dict(author(a,cellini)) @ <dynamic>:0
#                                             fail: is_dict(author(a,cellini)) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,15,_21652) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:824
#                                             call: is_list(author(a,cellini)) @ <dynamic>:0
#                                             fail: is_list(author(a,cellini)) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,15,_21652) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:830
#                                             call: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                             fail: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,15,_21652) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:835
#                                             call: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                             fail: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,15,_21652) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:840
#                                             call: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                             fail: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,15,_21652) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:845
#                                             call: number(author(a,cellini)) @ <dynamic>:0
#                                             fail: number(author(a,cellini)) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,15,_21652) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:857
#                                             call: json:string_len(author(a,cellini),15,_21652) @ <dynamic>:0
#                                               call: atom(author(a,cellini)) @ <dynamic>:0
#                                               fail: atom(author(a,cellini)) @ <dynamic>:0
#                                             redo(0): json:string_len(author(a,cellini),15,_21652) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:907
#                                               call: string(author(a,cellini)) @ <dynamic>:0
#                                               fail: string(author(a,cellini)) @ <dynamic>:0
#                                             fail: json:string_len(author(a,cellini),15,_21652) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,15,_21652) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:861
#                                             call: write_length(author(a,cellini),_22340,[]) @ <dynamic>:0
#                                             exit: write_length(author(a,cellini),17,[]) @ <dynamic>:0
#                                             call: _21652 is 15+17+2 @ <dynamic>:0
#                                             exit: 34 is 15+17+2 @ <dynamic>:0
#                                             call: 34=<72 @ <dynamic>:0
#                                             exit: 34=<72 @ <dynamic>:0
#                                           exit: json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,15,34) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:861
#                                           call: [author(b,bellini),author(c,bellini),author(d,bellini)]==[] @ <dynamic>:0
#                                           fail: [author(b,bellini),author(c,bellini),author(d,bellini)]==[] @ <dynamic>:0
#                                         redo(29): json:array_print_length([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,15,_20132) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:893
#                                           call: _22814 is 34+2 @ <dynamic>:0
#                                           exit: 36 is 34+2 @ <dynamic>:0
#                                           call: 36=<72 @ <dynamic>:0
#                                           exit: 36=<72 @ <dynamic>:0
#                                           call: json:array_print_length([author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,36,_20132) @ <dynamic>:0
#                                             call: json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,36,_23078) @ <dynamic>:0
#                                               call: var(author(b,bellini)) @ <dynamic>:0
#                                               fail: var(author(b,bellini)) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,36,_23078) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:817
#                                               call: is_dict(author(b,bellini)) @ <dynamic>:0
#                                               fail: is_dict(author(b,bellini)) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,36,_23078) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:824
#                                               call: is_list(author(b,bellini)) @ <dynamic>:0
#                                               fail: is_list(author(b,bellini)) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,36,_23078) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:830
#                                               call: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(b,bellini)) @ <dynamic>:0
#                                               fail: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(b,bellini)) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,36,_23078) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:835
#                                               call: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(b,bellini)) @ <dynamic>:0
#                                               fail: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(b,bellini)) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,36,_23078) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:840
#                                               call: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(b,bellini)) @ <dynamic>:0
#                                               fail: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(b,bellini)) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,36,_23078) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:845
#                                               call: number(author(b,bellini)) @ <dynamic>:0
#                                               fail: number(author(b,bellini)) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,36,_23078) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:857
#                                               call: json:string_len(author(b,bellini),36,_23078) @ <dynamic>:0
#                                                 call: atom(author(b,bellini)) @ <dynamic>:0
#                                                 fail: atom(author(b,bellini)) @ <dynamic>:0
#                                               redo(0): json:string_len(author(b,bellini),36,_23078) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:907
#                                                 call: string(author(b,bellini)) @ <dynamic>:0
#                                                 fail: string(author(b,bellini)) @ <dynamic>:0
#                                               fail: json:string_len(author(b,bellini),36,_23078) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,36,_23078) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:861
#                                               call: write_length(author(b,bellini),_23766,[]) @ <dynamic>:0
#                                               exit: write_length(author(b,bellini),17,[]) @ <dynamic>:0
#                                               call: _23078 is 36+17+2 @ <dynamic>:0
#                                               exit: 55 is 36+17+2 @ <dynamic>:0
#                                               call: 55=<72 @ <dynamic>:0
#                                               exit: 55=<72 @ <dynamic>:0
#                                             exit: json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,36,55) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:861
#                                             call: [author(c,bellini),author(d,bellini)]==[] @ <dynamic>:0
#                                             fail: [author(c,bellini),author(d,bellini)]==[] @ <dynamic>:0
#                                           redo(29): json:array_print_length([author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,36,_20132) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:893
#                                             call: _24240 is 55+2 @ <dynamic>:0
#                                             exit: 57 is 55+2 @ <dynamic>:0
#                                             call: 57=<72 @ <dynamic>:0
#                                             exit: 57=<72 @ <dynamic>:0
#                                             call: json:array_print_length([author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,57,_20132) @ <dynamic>:0
#                                               call: json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,57,_24504) @ <dynamic>:0
#                                                 call: var(author(c,bellini)) @ <dynamic>:0
#                                                 fail: var(author(c,bellini)) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,57,_24504) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:817
#                                                 call: is_dict(author(c,bellini)) @ <dynamic>:0
#                                                 fail: is_dict(author(c,bellini)) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,57,_24504) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:824
#                                                 call: is_list(author(c,bellini)) @ <dynamic>:0
#                                                 fail: is_list(author(c,bellini)) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,57,_24504) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:830
#                                                 call: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(c,bellini)) @ <dynamic>:0
#                                                 fail: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(c,bellini)) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,57,_24504) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:835
#                                                 call: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(c,bellini)) @ <dynamic>:0
#                                                 fail: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(c,bellini)) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,57,_24504) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:840
#                                                 call: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(c,bellini)) @ <dynamic>:0
#                                                 fail: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(c,bellini)) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,57,_24504) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:845
#                                                 call: number(author(c,bellini)) @ <dynamic>:0
#                                                 fail: number(author(c,bellini)) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,57,_24504) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:857
#                                                 call: json:string_len(author(c,bellini),57,_24504) @ <dynamic>:0
#                                                   call: atom(author(c,bellini)) @ <dynamic>:0
#                                                   fail: atom(author(c,bellini)) @ <dynamic>:0
#                                                 redo(0): json:string_len(author(c,bellini),57,_24504) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:907
#                                                   call: string(author(c,bellini)) @ <dynamic>:0
#                                                   fail: string(author(c,bellini)) @ <dynamic>:0
#                                                 fail: json:string_len(author(c,bellini),57,_24504) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,57,_24504) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:861
#                                                 call: write_length(author(c,bellini),_25192,[]) @ <dynamic>:0
#                                                 exit: write_length(author(c,bellini),17,[]) @ <dynamic>:0
#                                                 call: _24504 is 57+17+2 @ <dynamic>:0
#                                                 exit: 76 is 57+17+2 @ <dynamic>:0
#                                                 call: 76=<72 @ <dynamic>:0
#                                                 fail: 76=<72 @ <dynamic>:0
#                                               fail: json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,57,_24504) @ <dynamic>:0
#                                             fail: json:array_print_length([author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,57,_20132) @ <dynamic>:0
#                                           fail: json:array_print_length([author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,36,_20132) @ <dynamic>:0
#                                         fail: json:array_print_length([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,15,_20132) @ <dynamic>:0
#                                       fail: json:json_print_length([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,13,_20132) @ <dynamic>:0
#                                     fail: json:pair_len(authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,2,_20132) @ <dynamic>:0
#                                   fail: json:pairs_print_length([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]],json_options(null,true,false,error,string,'',_17472),72,2,_19406) @ <dynamic>:0
#                                 fail: json:json_print_length(json([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]]),json_options(null,true,false,error,string,'',_17472),72,0,_19406) @ <dynamic>:0
#                               redo(84): json:json_write_object([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]],user_output,json_write_state(0,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:696
#                                 call: json:step_indent(json_write_state(0,2,8,72,false),_19130) @ <dynamic>:0
#                                   call: json:json_write_state_indent(json_write_state(0,2,8,72,false),_19188) @ <dynamic>:0
#                                   exit: json:json_write_state_indent(json_write_state(0,2,8,72,false),0) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                                   call: json:json_write_state_step(json_write_state(0,2,8,72,false),_19312) @ <dynamic>:0
#                                   exit: json:json_write_state_step(json_write_state(0,2,8,72,false),2) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                                   call: _19436 is 0+2 @ <dynamic>:0
#                                   exit: 2 is 0+2 @ <dynamic>:0
#                                   call: json:set_indent_of_json_write_state(2,json_write_state(0,2,8,72,false),_19130) @ <dynamic>:0
#                                     call: error:must_be(nonneg,2) @ <dynamic>:0
#                                       call: error:has_type(nonneg,2) @ <dynamic>:0
#                                         call: integer(2) @ <dynamic>:0
#                                         exit: integer(2) @ <dynamic>:0
#                                         call: 2>=0 @ <dynamic>:0
#                                         exit: 2>=0 @ <dynamic>:0
#                                       exit: error:has_type(nonneg,2) @ /usr/lib/swi-prolog/library/error.pl:379
#                                     exit: error:must_be(nonneg,2) @ /usr/lib/swi-prolog/library/error.pl:253
#                                   exit: json:set_indent_of_json_write_state(2,json_write_state(0,2,8,72,false),json_write_state(2,2,8,72,false)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                                 exit: json:step_indent(json_write_state(0,2,8,72,false),json_write_state(2,2,8,72,false)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:783
#                                 call: json:write_pairs_ver([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]],user_output,json_write_state(2,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ <dynamic>:0
#                                   call: json:indent(user_output,json_write_state(2,2,8,72,false)) @ <dynamic>:0
#                                     call: json:json_write_state_indent(json_write_state(2,2,8,72,false),_20304) @ <dynamic>:0
#                                     exit: json:json_write_state_indent(json_write_state(2,2,8,72,false),2) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                                     call: json:json_write_state_tab(json_write_state(2,2,8,72,false),_20428) @ <dynamic>:0
#                                     exit: json:json_write_state_tab(json_write_state(2,2,8,72,false),8) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                                     call: json:json_write_indent(user_output,2,8) @ <dynamic>:0

#                                     exit: json:json_write_indent(user_output,2,8) @ <dynamic>:0
#                                   exit: json:indent(user_output,json_write_state(2,2,8,72,false)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:778
#                                   call: json:json_pair(authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],_20734,_20736) @ <dynamic>:0
#                                     call: var(authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                     fail: var(authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                   redo(0): json:json_pair(authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],_20734,_20736) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:749
#                                   exit: json:json_pair(authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],authors,[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:749
#                                   call: json:json_write_string(user_output,authors) @ <dynamic>:0

#                                   exit: json:json_write_string(user_output,authors) @ <dynamic>:0
#                                   call: write(user_output,:) @ <dynamic>:0

#                                   exit: write(user_output,:) @ <dynamic>:0
#                                   call: json:json_write_term([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],user_output,json_write_state(2,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ <dynamic>:0
#                                     call: var([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                     fail: var([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                   redo(0): json:json_write_term([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],user_output,json_write_state(2,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:610
#                                     call: is_dict([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],_21286) @ <dynamic>:0
#                                     fail: is_dict([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],_21286) @ <dynamic>:0
#                                   redo(0): json:json_write_term([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],user_output,json_write_state(2,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:621
#                                     call: is_list([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                     exit: is_list([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                     call: json:space_if_not_at_left_margin(user_output,json_write_state(2,2,8,72,false)) @ <dynamic>:0
#                                       call: stream_pair(user_output,_21534,_21514) @ <dynamic>:0
#                                       exit: stream_pair(user_output,_21534,user_output) @ <dynamic>:0
#                                       call: line_position(user_output,_21620) @ <dynamic>:0
#                                       exit: line_position(user_output,0) @ <dynamic>:0
#                                       call: 0==0 @ <dynamic>:0
#                                       exit: 0==0 @ <dynamic>:0
#                                     exit: json:space_if_not_at_left_margin(user_output,json_write_state(2,2,8,72,false)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:789
#                                     call: write(user_output,'[') @ <dynamic>:0

#                                     exit: write(user_output,'[') @ <dynamic>:0
#                                     call: json:json_write_state_width(json_write_state(2,2,8,72,false),_21988) @ <dynamic>:0
#                                     exit: json:json_write_state_width(json_write_state(2,2,8,72,false),72) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                                     call: 72==0 @ <dynamic>:0
#                                     fail: 72==0 @ <dynamic>:0
#                                   redo(35): json:json_write_term([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],user_output,json_write_state(2,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:621
#                                     call: json:json_write_state_indent(json_write_state(2,2,8,72,false),_22188) @ <dynamic>:0
#                                     exit: json:json_write_state_indent(json_write_state(2,2,8,72,false),2) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                                     call: json:json_print_length([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,2,_22336) @ <dynamic>:0
#                                       call: var([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                       fail: var([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                     redo(0): json:json_print_length([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,2,_22336) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:817
#                                       call: is_dict([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                       fail: is_dict([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                     redo(0): json:json_print_length([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,2,_22336) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:824
#                                       call: is_list([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                       exit: is_list([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]) @ <dynamic>:0
#                                       call: _22632 is 2+2 @ <dynamic>:0
#                                       exit: 4 is 2+2 @ <dynamic>:0
#                                       call: 4=<72 @ <dynamic>:0
#                                       exit: 4=<72 @ <dynamic>:0
#                                       call: json:array_print_length([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,4,_22336) @ <dynamic>:0
#                                         call: json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,4,_22896) @ <dynamic>:0
#                                           call: var(author(a,cellini)) @ <dynamic>:0
#                                           fail: var(author(a,cellini)) @ <dynamic>:0
#                                         redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,4,_22896) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:817
#                                           call: is_dict(author(a,cellini)) @ <dynamic>:0
#                                           fail: is_dict(author(a,cellini)) @ <dynamic>:0
#                                         redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,4,_22896) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:824
#                                           call: is_list(author(a,cellini)) @ <dynamic>:0
#                                           fail: is_list(author(a,cellini)) @ <dynamic>:0
#                                         redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,4,_22896) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:830
#                                           call: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                           fail: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                         redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,4,_22896) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:835
#                                           call: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                           fail: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                         redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,4,_22896) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:840
#                                           call: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                           fail: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                         redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,4,_22896) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:845
#                                           call: number(author(a,cellini)) @ <dynamic>:0
#                                           fail: number(author(a,cellini)) @ <dynamic>:0
#                                         redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,4,_22896) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:857
#                                           call: json:string_len(author(a,cellini),4,_22896) @ <dynamic>:0
#                                             call: atom(author(a,cellini)) @ <dynamic>:0
#                                             fail: atom(author(a,cellini)) @ <dynamic>:0
#                                           redo(0): json:string_len(author(a,cellini),4,_22896) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:907
#                                             call: string(author(a,cellini)) @ <dynamic>:0
#                                             fail: string(author(a,cellini)) @ <dynamic>:0
#                                           fail: json:string_len(author(a,cellini),4,_22896) @ <dynamic>:0
#                                         redo(0): json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,4,_22896) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:861
#                                           call: write_length(author(a,cellini),_23584,[]) @ <dynamic>:0
#                                           exit: write_length(author(a,cellini),17,[]) @ <dynamic>:0
#                                           call: _22896 is 4+17+2 @ <dynamic>:0
#                                           exit: 23 is 4+17+2 @ <dynamic>:0
#                                           call: 23=<72 @ <dynamic>:0
#                                           exit: 23=<72 @ <dynamic>:0
#                                         exit: json:json_print_length(author(a,cellini),json_options(null,true,false,error,string,'',_17472),72,4,23) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:861
#                                         call: [author(b,bellini),author(c,bellini),author(d,bellini)]==[] @ <dynamic>:0
#                                         fail: [author(b,bellini),author(c,bellini),author(d,bellini)]==[] @ <dynamic>:0
#                                       redo(29): json:array_print_length([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,4,_22336) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:893
#                                         call: _24058 is 23+2 @ <dynamic>:0
#                                         exit: 25 is 23+2 @ <dynamic>:0
#                                         call: 25=<72 @ <dynamic>:0
#                                         exit: 25=<72 @ <dynamic>:0
#                                         call: json:array_print_length([author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,25,_22336) @ <dynamic>:0
#                                           call: json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,25,_24322) @ <dynamic>:0
#                                             call: var(author(b,bellini)) @ <dynamic>:0
#                                             fail: var(author(b,bellini)) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,25,_24322) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:817
#                                             call: is_dict(author(b,bellini)) @ <dynamic>:0
#                                             fail: is_dict(author(b,bellini)) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,25,_24322) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:824
#                                             call: is_list(author(b,bellini)) @ <dynamic>:0
#                                             fail: is_list(author(b,bellini)) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,25,_24322) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:830
#                                             call: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(b,bellini)) @ <dynamic>:0
#                                             fail: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(b,bellini)) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,25,_24322) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:835
#                                             call: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(b,bellini)) @ <dynamic>:0
#                                             fail: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(b,bellini)) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,25,_24322) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:840
#                                             call: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(b,bellini)) @ <dynamic>:0
#                                             fail: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(b,bellini)) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,25,_24322) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:845
#                                             call: number(author(b,bellini)) @ <dynamic>:0
#                                             fail: number(author(b,bellini)) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,25,_24322) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:857
#                                             call: json:string_len(author(b,bellini),25,_24322) @ <dynamic>:0
#                                               call: atom(author(b,bellini)) @ <dynamic>:0
#                                               fail: atom(author(b,bellini)) @ <dynamic>:0
#                                             redo(0): json:string_len(author(b,bellini),25,_24322) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:907
#                                               call: string(author(b,bellini)) @ <dynamic>:0
#                                               fail: string(author(b,bellini)) @ <dynamic>:0
#                                             fail: json:string_len(author(b,bellini),25,_24322) @ <dynamic>:0
#                                           redo(0): json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,25,_24322) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:861
#                                             call: write_length(author(b,bellini),_25010,[]) @ <dynamic>:0
#                                             exit: write_length(author(b,bellini),17,[]) @ <dynamic>:0
#                                             call: _24322 is 25+17+2 @ <dynamic>:0
#                                             exit: 44 is 25+17+2 @ <dynamic>:0
#                                             call: 44=<72 @ <dynamic>:0
#                                             exit: 44=<72 @ <dynamic>:0
#                                           exit: json:json_print_length(author(b,bellini),json_options(null,true,false,error,string,'',_17472),72,25,44) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:861
#                                           call: [author(c,bellini),author(d,bellini)]==[] @ <dynamic>:0
#                                           fail: [author(c,bellini),author(d,bellini)]==[] @ <dynamic>:0
#                                         redo(29): json:array_print_length([author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,25,_22336) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:893
#                                           call: _25484 is 44+2 @ <dynamic>:0
#                                           exit: 46 is 44+2 @ <dynamic>:0
#                                           call: 46=<72 @ <dynamic>:0
#                                           exit: 46=<72 @ <dynamic>:0
#                                           call: json:array_print_length([author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,46,_22336) @ <dynamic>:0
#                                             call: json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,46,_25748) @ <dynamic>:0
#                                               call: var(author(c,bellini)) @ <dynamic>:0
#                                               fail: var(author(c,bellini)) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,46,_25748) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:817
#                                               call: is_dict(author(c,bellini)) @ <dynamic>:0
#                                               fail: is_dict(author(c,bellini)) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,46,_25748) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:824
#                                               call: is_list(author(c,bellini)) @ <dynamic>:0
#                                               fail: is_list(author(c,bellini)) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,46,_25748) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:830
#                                               call: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(c,bellini)) @ <dynamic>:0
#                                               fail: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(c,bellini)) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,46,_25748) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:835
#                                               call: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(c,bellini)) @ <dynamic>:0
#                                               fail: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(c,bellini)) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,46,_25748) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:840
#                                               call: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(c,bellini)) @ <dynamic>:0
#                                               fail: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(c,bellini)) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,46,_25748) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:845
#                                               call: number(author(c,bellini)) @ <dynamic>:0
#                                               fail: number(author(c,bellini)) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,46,_25748) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:857
#                                               call: json:string_len(author(c,bellini),46,_25748) @ <dynamic>:0
#                                                 call: atom(author(c,bellini)) @ <dynamic>:0
#                                                 fail: atom(author(c,bellini)) @ <dynamic>:0
#                                               redo(0): json:string_len(author(c,bellini),46,_25748) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:907
#                                                 call: string(author(c,bellini)) @ <dynamic>:0
#                                                 fail: string(author(c,bellini)) @ <dynamic>:0
#                                               fail: json:string_len(author(c,bellini),46,_25748) @ <dynamic>:0
#                                             redo(0): json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,46,_25748) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:861
#                                               call: write_length(author(c,bellini),_26436,[]) @ <dynamic>:0
#                                               exit: write_length(author(c,bellini),17,[]) @ <dynamic>:0
#                                               call: _25748 is 46+17+2 @ <dynamic>:0
#                                               exit: 65 is 46+17+2 @ <dynamic>:0
#                                               call: 65=<72 @ <dynamic>:0
#                                               exit: 65=<72 @ <dynamic>:0
#                                             exit: json:json_print_length(author(c,bellini),json_options(null,true,false,error,string,'',_17472),72,46,65) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:861
#                                             call: [author(d,bellini)]==[] @ <dynamic>:0
#                                             fail: [author(d,bellini)]==[] @ <dynamic>:0
#                                           redo(29): json:array_print_length([author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,46,_22336) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:893
#                                             call: _26910 is 65+2 @ <dynamic>:0
#                                             exit: 67 is 65+2 @ <dynamic>:0
#                                             call: 67=<72 @ <dynamic>:0
#                                             exit: 67=<72 @ <dynamic>:0
#                                             call: json:array_print_length([author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,67,_22336) @ <dynamic>:0
#                                               call: json:json_print_length(author(d,bellini),json_options(null,true,false,error,string,'',_17472),72,67,_27174) @ <dynamic>:0
#                                                 call: var(author(d,bellini)) @ <dynamic>:0
#                                                 fail: var(author(d,bellini)) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(d,bellini),json_options(null,true,false,error,string,'',_17472),72,67,_27174) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:817
#                                                 call: is_dict(author(d,bellini)) @ <dynamic>:0
#                                                 fail: is_dict(author(d,bellini)) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(d,bellini),json_options(null,true,false,error,string,'',_17472),72,67,_27174) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:824
#                                                 call: is_list(author(d,bellini)) @ <dynamic>:0
#                                                 fail: is_list(author(d,bellini)) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(d,bellini),json_options(null,true,false,error,string,'',_17472),72,67,_27174) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:830
#                                                 call: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(d,bellini)) @ <dynamic>:0
#                                                 fail: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(d,bellini)) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(d,bellini),json_options(null,true,false,error,string,'',_17472),72,67,_27174) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:835
#                                                 call: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(d,bellini)) @ <dynamic>:0
#                                                 fail: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(d,bellini)) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(d,bellini),json_options(null,true,false,error,string,'',_17472),72,67,_27174) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:840
#                                                 call: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(d,bellini)) @ <dynamic>:0
#                                                 fail: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(d,bellini)) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(d,bellini),json_options(null,true,false,error,string,'',_17472),72,67,_27174) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:845
#                                                 call: number(author(d,bellini)) @ <dynamic>:0
#                                                 fail: number(author(d,bellini)) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(d,bellini),json_options(null,true,false,error,string,'',_17472),72,67,_27174) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:857
#                                                 call: json:string_len(author(d,bellini),67,_27174) @ <dynamic>:0
#                                                   call: atom(author(d,bellini)) @ <dynamic>:0
#                                                   fail: atom(author(d,bellini)) @ <dynamic>:0
#                                                 redo(0): json:string_len(author(d,bellini),67,_27174) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:907
#                                                   call: string(author(d,bellini)) @ <dynamic>:0
#                                                   fail: string(author(d,bellini)) @ <dynamic>:0
#                                                 fail: json:string_len(author(d,bellini),67,_27174) @ <dynamic>:0
#                                               redo(0): json:json_print_length(author(d,bellini),json_options(null,true,false,error,string,'',_17472),72,67,_27174) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:861
#                                                 call: write_length(author(d,bellini),_27862,[]) @ <dynamic>:0
#                                                 exit: write_length(author(d,bellini),17,[]) @ <dynamic>:0
#                                                 call: _27174 is 67+17+2 @ <dynamic>:0
#                                                 exit: 86 is 67+17+2 @ <dynamic>:0
#                                                 call: 86=<72 @ <dynamic>:0
#                                                 fail: 86=<72 @ <dynamic>:0
#                                               fail: json:json_print_length(author(d,bellini),json_options(null,true,false,error,string,'',_17472),72,67,_27174) @ <dynamic>:0
#                                             fail: json:array_print_length([author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,67,_22336) @ <dynamic>:0
#                                           fail: json:array_print_length([author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,46,_22336) @ <dynamic>:0
#                                         fail: json:array_print_length([author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,25,_22336) @ <dynamic>:0
#                                       fail: json:array_print_length([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,4,_22336) @ <dynamic>:0
#                                     fail: json:json_print_length([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],json_options(null,true,false,error,string,'',_17472),72,2,_22336) @ <dynamic>:0
#                                   redo(84): json:json_write_term([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],user_output,json_write_state(2,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:621
#                                     call: json:step_indent(json_write_state(2,2,8,72,false),_22064) @ <dynamic>:0
#                                       call: json:json_write_state_indent(json_write_state(2,2,8,72,false),_22122) @ <dynamic>:0
#                                       exit: json:json_write_state_indent(json_write_state(2,2,8,72,false),2) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                                       call: json:json_write_state_step(json_write_state(2,2,8,72,false),_22246) @ <dynamic>:0
#                                       exit: json:json_write_state_step(json_write_state(2,2,8,72,false),2) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                                       call: _22370 is 2+2 @ <dynamic>:0
#                                       exit: 4 is 2+2 @ <dynamic>:0
#                                       call: json:set_indent_of_json_write_state(4,json_write_state(2,2,8,72,false),_22064) @ <dynamic>:0
#                                         call: error:must_be(nonneg,4) @ <dynamic>:0
#                                           call: error:has_type(nonneg,4) @ <dynamic>:0
#                                             call: integer(4) @ <dynamic>:0
#                                             exit: integer(4) @ <dynamic>:0
#                                             call: 4>=0 @ <dynamic>:0
#                                             exit: 4>=0 @ <dynamic>:0
#                                           exit: error:has_type(nonneg,4) @ /usr/lib/swi-prolog/library/error.pl:379
#                                         exit: error:must_be(nonneg,4) @ /usr/lib/swi-prolog/library/error.pl:253
#                                       exit: json:set_indent_of_json_write_state(4,json_write_state(2,2,8,72,false),json_write_state(4,2,8,72,false)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                                     exit: json:step_indent(json_write_state(2,2,8,72,false),json_write_state(4,2,8,72,false)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:783
#                                     call: json:write_array_ver([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ <dynamic>:0
#                                       call: json:indent(user_output,json_write_state(4,2,8,72,false)) @ <dynamic>:0
#                                         call: json:json_write_state_indent(json_write_state(4,2,8,72,false),_23238) @ <dynamic>:0
#                                         exit: json:json_write_state_indent(json_write_state(4,2,8,72,false),4) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                                         call: json:json_write_state_tab(json_write_state(4,2,8,72,false),_23362) @ <dynamic>:0
#                                         exit: json:json_write_state_tab(json_write_state(4,2,8,72,false),8) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:589
#                                         call: json:json_write_indent(user_output,4,8) @ <dynamic>:0

#                                         exit: json:json_write_indent(user_output,4,8) @ <dynamic>:0
#                                       exit: json:indent(user_output,json_write_state(4,2,8,72,false)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:778
#                                       call: json:json_write_term(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ <dynamic>:0
#                                         call: var(author(a,cellini)) @ <dynamic>:0
#                                         fail: var(author(a,cellini)) @ <dynamic>:0
#                                       redo(0): json:json_write_term(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:610
#                                         call: is_dict(author(a,cellini),_23804) @ <dynamic>:0
#                                         fail: is_dict(author(a,cellini),_23804) @ <dynamic>:0
#                                       redo(0): json:json_write_term(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:621
#                                         call: is_list(author(a,cellini)) @ <dynamic>:0
#                                         fail: is_list(author(a,cellini)) @ <dynamic>:0
#                                       redo(0): json:json_write_term(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:641
#                                         call: json:json_write_hook(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ <dynamic>:0
#                                         fail: json:json_write_hook(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ <dynamic>:0
#                                       redo(0): json:json_write_term(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:644
#                                         call: number(author(a,cellini)) @ <dynamic>:0
#                                         fail: number(author(a,cellini)) @ <dynamic>:0
#                                       redo(0): json:json_write_term(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:654
#                                         call: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                         fail: json:json_options_true(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                       redo(0): json:json_write_term(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:658
#                                         call: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                         fail: json:json_options_false(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                       redo(0): json:json_write_term(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:662
#                                         call: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                         fail: json:json_options_null(json_options(null,true,false,error,string,'',_17472),author(a,cellini)) @ <dynamic>:0
#                                       redo(0): json:json_write_term(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:675
#                                         call: atom(author(a,cellini)) @ <dynamic>:0
#                                         fail: atom(author(a,cellini)) @ <dynamic>:0
#                                       redo(0): json:json_write_term(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:679
#                                         call: string(author(a,cellini)) @ <dynamic>:0
#                                         fail: string(author(a,cellini)) @ <dynamic>:0
#                                       redo(0): json:json_write_term(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:683
#                                         call: json:json_write_state_serialize_unknown(json_write_state(4,2,8,72,false),true) @ <dynamic>:0
#                                         fail: json:json_write_state_serialize_unknown(json_write_state(4,2,8,72,false),true) @ <dynamic>:0
#                                       redo(33): json:json_write_term(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:683
#                                         call: error:type_error(json_term,author(a,cellini)) @ <dynamic>:0
#                                         exception(error(type_error(json_term,author(a,cellini)),_24638)): error:type_error(json_term,author(a,cellini)) @ /usr/lib/swi-prolog/library/error.pl:96
#                                       exception(error(type_error(json_term,author(a,cellini)),_24638)): json:json_write_term(author(a,cellini),user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:683
#                                     exception(error(type_error(json_term,author(a,cellini)),_24638)): json:write_array_ver([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],user_output,json_write_state(4,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:768
#                                   exception(error(type_error(json_term,author(a,cellini)),_24638)): json:json_write_term([author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)],user_output,json_write_state(2,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:621
#                                 exception(error(type_error(json_term,author(a,cellini)),_24638)): json:write_pairs_ver([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]],user_output,json_write_state(2,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:731
#                               exception(error(type_error(json_term,author(a,cellini)),_24638)): json:json_write_object([authors-[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]],user_output,json_write_state(0,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:696
#                             exception(error(type_error(json_term,author(a,cellini)),_24638)): json:json_write_term(json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},user_output,json_write_state(0,2,8,72,false),json_options(null,true,false,error,string,'',_17472)) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:610
#                           exception(error(type_error(json_term,author(a,cellini)),_24638)): json:json_write_dict(user_output,json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]},[]) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:1071
#                         exception(error(type_error(json_term,author(a,cellini)),_24638)): json:json_write_dict(user_output,json{authors:[author(a,cellini),author(b,bellini),author(c,bellini),author(d,bellini)]}) @ /usr/lib/swi-prolog/library/ext/http/http/json.pl:1068
#                         call: format(user_error,'~N### CAUGHT_EXCEPTION ###~n~w~n### END_EXCEPTION ###~n',[error(type_error(json_term,author(a,cellini)),_160)]) @ <dynamic>:0
# ### CAUGHT_EXCEPTION ###
# error(type_error(json_term,author(a,cellini)),_160)
# ### END_EXCEPTION ###
#                         exit: format(user_error,'~N### CAUGHT_EXCEPTION ###~n~w~n### END_EXCEPTION ###~n',[error(type_error(json_term,author(a,cellini)),_160)]) @ <dynamic>:0

# """)

#     clauses = procesar_traza(sample_trace)