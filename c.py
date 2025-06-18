import re
import copy
import json
from pathlib import Path
from collections import deque
# from graphviz import Digraph

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
                # dot = _create_thought_graph(arbol_dict)
                # dot.render(str(target_dir / f'arbol_pensamiento_{conta}'), view=False, cleanup=True)
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

# def _create_thought_graph(data, graph=None, parent_id=None, node_counter=[0]):
#     """
#     Recursively creates nodes and edges for the Graphviz diagram from the JSON data.
#     """
#     if graph is None:
#         graph = Digraph(comment='Cadena de Pensamientos', format='png') # You can change 'png' to 'svg', 'jpg', etc.
#         graph.attr(rankdir='TB') # Top to bottom layout
#         graph.attr('node', shape='box', style='filled', fontname='Arial')

#     current_node_id = f"node_{node_counter[0]}"
#     node_counter[0] += 1

#     name = data.get("nombre", "N/A")
#     veracidad = data.get("veracidad", "")

#     # Define node color based on 'veracidad'
#     fill_color = "lightblue" # Default
#     if veracidad == "verde":
#         fill_color = "lightgreen"
#     elif veracidad == "rojo":
#         fill_color = "salmon"

#     # Add the node to the graph
#     graph.node(current_node_id, label="{}\\n({})".format(name.replace('\\', '\\\\'), veracidad), fillcolor=fill_color)

#     # Add an edge from the parent node if it exists
#     if parent_id:
#         graph.edge(parent_id, current_node_id)

#     # Recursively process children
#     if "valor" in data and isinstance(data["valor"], list):
#         for child in data["valor"]:
#             _create_thought_graph(child, graph, current_node_id, node_counter)

#     return graph

# -------------------
# Example usage
# -------------------
if __name__ == "__main__":
    import textwrap

    sample_trace = textwrap.dedent("""
                        call: catch((solution_finder(_36,_38,_40,_42,_44,_46,_48,_50),fail),_62,(format(user_error,'~N### CAUGHT_EXCEPTION ###~n~w~n### END_EXCEPTION ###~n',[_62]),fail)) @ <dynamic>:0
                        call: solution_finder(_36,_38,_40,_42,_44,_46,_48,_50) @ <dynamic>:0
                          call: possible_maker(_36) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: possible_maker(_38) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: possible_maker(_40) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: possible_maker(_42) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(bellini,bellini,bellini,bellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,bellini,bellini,bellini,bellini,_4372) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4540=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,bellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,bellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,bellini,bellini,bellini,bellini,_4372) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4622=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(36): statement_content_true(a,a,b,c,d,bellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(45): statement_content_true(a,a,b,c,d,bellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,b,c,d,bellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,bellini,bellini,bellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,bellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,bellini,bellini,bellini,bellini,_4372) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,bellini,bellini,bellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(bellini,bellini,bellini,bellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,bellini,bellini,bellini,bellini,_4442) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4610=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,bellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,bellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,bellini,bellini,bellini,bellini,_4442) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4692=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,bellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(45): statement_content_true(a,a,d,c,b,bellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,d,c,b,bellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,bellini,bellini,bellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,bellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,bellini,bellini,bellini,bellini,_4442) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,bellini,bellini,bellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_42) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(bellini,bellini,bellini,cellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,bellini,bellini,bellini,cellini,_4436) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4604=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,bellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,bellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,bellini,bellini,bellini,cellini,_4436) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4686=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(36): statement_content_true(a,a,b,c,d,bellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(45): statement_content_true(a,a,b,c,d,bellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,b,c,d,bellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,bellini,bellini,cellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,bellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,bellini,bellini,bellini,cellini,_4436) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,bellini,bellini,cellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(bellini,bellini,bellini,cellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,bellini,bellini,bellini,cellini,_4506) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4674=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,bellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,d,c,b,bellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: true==true @ <dynamic>:0
                            exit: true==true @ <dynamic>:0
                            call: statement_content_true(b,a,d,c,b,bellini,bellini,bellini,cellini,_5334) @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,bellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5584=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(30): statement_content_true(b,a,d,c,b,bellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(43): statement_content_true(b,a,d,c,b,bellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: c=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            exit: statement_content_true(b,a,d,c,b,bellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: true==true @ <dynamic>:0
                            exit: true==true @ <dynamic>:0
                            call: statement_content_true(c,a,d,c,b,bellini,bellini,bellini,cellini,_6426) @ <dynamic>:0
                            exit: statement_content_true(c,a,d,c,b,bellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:29
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: true==true @ <dynamic>:0
                            exit: true==true @ <dynamic>:0
                            call: statement_content_true(d,a,d,c,b,bellini,bellini,bellini,cellini,_6770) @ <dynamic>:0
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: _6938=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            exit: statement_content_true(d,a,d,c,b,bellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:31
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(135): is_consistent_scenario(bellini,bellini,bellini,cellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(33): statement_content_true(d,a,d,c,b,bellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:31
                              call: a=c @ <dynamic>:0
                              fail: a=c @ <dynamic>:0
                            redo(17): statement_content_true(d,a,d,c,b,bellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:31
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(0): statement_content_true(d,a,d,c,b,bellini,bellini,bellini,cellini,_6770) @ /tmp/tmpd794ti5a.pl:32
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: _7020=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            fail: statement_content_true(d,a,d,c,b,bellini,bellini,bellini,cellini,_6770) @ <dynamic>:0
                          redo(100): is_consistent_scenario(bellini,bellini,bellini,cellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(0): statement_content_true(c,a,d,c,b,bellini,bellini,bellini,cellini,_6426) @ /tmp/tmpd794ti5a.pl:30
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: statement_content_true(c,a,d,c,b,bellini,bellini,bellini,cellini,_6426) @ <dynamic>:0
                          redo(65): is_consistent_scenario(bellini,bellini,bellini,cellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(0): statement_content_true(b,a,d,c,b,bellini,bellini,bellini,cellini,_5334) @ /tmp/tmpd794ti5a.pl:28
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,bellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5666=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(b,a,d,c,b,bellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(46): statement_content_true(b,a,d,c,b,bellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: c=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: statement_content_true(b,a,d,c,b,bellini,bellini,bellini,cellini,_5334) @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,bellini,bellini,cellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,bellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,bellini,bellini,bellini,cellini,_4506) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4756=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,bellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,bellini,bellini,bellini,cellini,_4506) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,bellini,bellini,cellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_40) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: possible_maker(_42) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(bellini,bellini,cellini,bellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,bellini,bellini,cellini,bellini,_4436) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4604=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,bellini,bellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,bellini,bellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,bellini,bellini,cellini,bellini,_4436) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4686=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(36): statement_content_true(a,a,b,c,d,bellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(45): statement_content_true(a,a,b,c,d,bellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,b,c,d,bellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,bellini,cellini,bellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,bellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,bellini,bellini,cellini,bellini,_4436) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,bellini,cellini,bellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(bellini,bellini,cellini,bellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,bellini,bellini,cellini,bellini,_4506) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4674=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,bellini,bellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,bellini,bellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,bellini,bellini,cellini,bellini,_4506) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4756=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,bellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(45): statement_content_true(a,a,d,c,b,bellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,d,c,b,bellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,bellini,cellini,bellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,bellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,bellini,bellini,cellini,bellini,_4506) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,bellini,cellini,bellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_42) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(bellini,bellini,cellini,cellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,bellini,bellini,cellini,cellini,_4500) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4668=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,bellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,bellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,bellini,bellini,cellini,cellini,_4500) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4750=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(36): statement_content_true(a,a,b,c,d,bellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(45): statement_content_true(a,a,b,c,d,bellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,b,c,d,bellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,bellini,cellini,cellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,bellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,bellini,bellini,cellini,cellini,_4500) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,bellini,cellini,cellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(bellini,bellini,cellini,cellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,bellini,bellini,cellini,cellini,_4570) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4738=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,bellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,d,c,b,bellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: true==true @ <dynamic>:0
                            exit: true==true @ <dynamic>:0
                            call: statement_content_true(b,a,d,c,b,bellini,bellini,cellini,cellini,_5398) @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,bellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5648=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(30): statement_content_true(b,a,d,c,b,bellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(43): statement_content_true(b,a,d,c,b,bellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: c=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(0): statement_content_true(b,a,d,c,b,bellini,bellini,cellini,cellini,_5398) @ /tmp/tmpd794ti5a.pl:28
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,bellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5730=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(b,a,d,c,b,bellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(46): statement_content_true(b,a,d,c,b,bellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: c=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(55): statement_content_true(b,a,d,c,b,bellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                            exit: statement_content_true(b,a,d,c,b,bellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(65): is_consistent_scenario(bellini,bellini,cellini,cellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,bellini,cellini,cellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,bellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,bellini,bellini,cellini,cellini,_4570) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4820=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,bellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,bellini,bellini,cellini,cellini,_4570) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,bellini,cellini,cellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_38) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: possible_maker(_40) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: possible_maker(_42) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(bellini,cellini,bellini,bellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,bellini,cellini,bellini,bellini,_4436) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4604=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,b,c,d,bellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: true==true @ <dynamic>:0
                            exit: true==true @ <dynamic>:0
                            call: statement_content_true(b,a,b,c,d,bellini,cellini,bellini,bellini,_5182) @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5350=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(b,a,b,c,d,bellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(65): is_consistent_scenario(bellini,cellini,bellini,bellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(30): statement_content_true(b,a,b,c,d,bellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): statement_content_true(b,a,b,c,d,bellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(0): statement_content_true(b,a,b,c,d,bellini,cellini,bellini,bellini,_5182) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5432=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            fail: statement_content_true(b,a,b,c,d,bellini,cellini,bellini,bellini,_5182) @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,cellini,bellini,bellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,bellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,bellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,bellini,cellini,bellini,bellini,_4436) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4686=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,bellini,cellini,bellini,bellini,_4436) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,cellini,bellini,bellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(bellini,cellini,bellini,bellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,bellini,cellini,bellini,bellini,_4506) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4674=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,bellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,bellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,bellini,cellini,bellini,bellini,_4506) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4756=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,bellini,cellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(45): statement_content_true(a,a,d,c,b,bellini,cellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,d,c,b,bellini,cellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,cellini,bellini,bellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,bellini,cellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,bellini,cellini,bellini,bellini,_4506) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,cellini,bellini,bellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_42) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(bellini,cellini,bellini,cellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,bellini,cellini,bellini,cellini,_4500) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4668=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,b,c,d,bellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: true==true @ <dynamic>:0
                            exit: true==true @ <dynamic>:0
                            call: statement_content_true(b,a,b,c,d,bellini,cellini,bellini,cellini,_5246) @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5414=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(b,a,b,c,d,bellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(65): is_consistent_scenario(bellini,cellini,bellini,cellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(30): statement_content_true(b,a,b,c,d,bellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): statement_content_true(b,a,b,c,d,bellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(0): statement_content_true(b,a,b,c,d,bellini,cellini,bellini,cellini,_5246) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5496=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            fail: statement_content_true(b,a,b,c,d,bellini,cellini,bellini,cellini,_5246) @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,cellini,bellini,cellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,bellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,bellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,bellini,cellini,bellini,cellini,_4500) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4750=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,bellini,cellini,bellini,cellini,_4500) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,cellini,bellini,cellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(bellini,cellini,bellini,cellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,bellini,cellini,bellini,cellini,_4570) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4738=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,bellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,d,c,b,bellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: true==true @ <dynamic>:0
                            exit: true==true @ <dynamic>:0
                            call: statement_content_true(b,a,d,c,b,bellini,cellini,bellini,cellini,_5398) @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,bellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5648=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(b,a,d,c,b,bellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(65): is_consistent_scenario(bellini,cellini,bellini,cellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(30): statement_content_true(b,a,d,c,b,bellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(0): statement_content_true(b,a,d,c,b,bellini,cellini,bellini,cellini,_5398) @ /tmp/tmpd794ti5a.pl:28
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,bellini,cellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5730=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            fail: statement_content_true(b,a,d,c,b,bellini,cellini,bellini,cellini,_5398) @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,cellini,bellini,cellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,bellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,bellini,cellini,bellini,cellini,_4570) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4820=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,bellini,cellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,bellini,cellini,bellini,cellini,_4570) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,cellini,bellini,cellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_40) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: possible_maker(_42) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(bellini,cellini,cellini,bellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,bellini,cellini,cellini,bellini,_4500) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4668=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,b,c,d,bellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: true==true @ <dynamic>:0
                            exit: true==true @ <dynamic>:0
                            call: statement_content_true(b,a,b,c,d,bellini,cellini,cellini,bellini,_5246) @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5414=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(b,a,b,c,d,bellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(65): is_consistent_scenario(bellini,cellini,cellini,bellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(30): statement_content_true(b,a,b,c,d,bellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): statement_content_true(b,a,b,c,d,bellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(0): statement_content_true(b,a,b,c,d,bellini,cellini,cellini,bellini,_5246) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5496=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            fail: statement_content_true(b,a,b,c,d,bellini,cellini,cellini,bellini,_5246) @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,cellini,cellini,bellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,bellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,bellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,bellini,cellini,cellini,bellini,_4500) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4750=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,bellini,cellini,cellini,bellini,_4500) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,cellini,cellini,bellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(bellini,cellini,cellini,bellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,bellini,cellini,cellini,bellini,_4570) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4738=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,bellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,bellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,bellini,cellini,cellini,bellini,_4570) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4820=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,bellini,cellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(45): statement_content_true(a,a,d,c,b,bellini,cellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,d,c,b,bellini,cellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,cellini,cellini,bellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,bellini,cellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,bellini,cellini,cellini,bellini,_4570) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,cellini,cellini,bellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_42) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(bellini,cellini,cellini,cellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,bellini,cellini,cellini,cellini,_4564) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4732=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,b,c,d,bellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: true==true @ <dynamic>:0
                            exit: true==true @ <dynamic>:0
                            call: statement_content_true(b,a,b,c,d,bellini,cellini,cellini,cellini,_5310) @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5478=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(b,a,b,c,d,bellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(65): is_consistent_scenario(bellini,cellini,cellini,cellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(30): statement_content_true(b,a,b,c,d,bellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): statement_content_true(b,a,b,c,d,bellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(0): statement_content_true(b,a,b,c,d,bellini,cellini,cellini,cellini,_5310) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5560=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            fail: statement_content_true(b,a,b,c,d,bellini,cellini,cellini,cellini,_5310) @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,cellini,cellini,cellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,bellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,bellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,bellini,cellini,cellini,cellini,_4564) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4814=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,bellini,cellini,cellini,cellini,_4564) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,cellini,cellini,cellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(bellini,cellini,cellini,cellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,bellini,cellini,cellini,cellini,_4634) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4802=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,bellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,d,c,b,bellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: true==true @ <dynamic>:0
                            exit: true==true @ <dynamic>:0
                            call: statement_content_true(b,a,d,c,b,bellini,cellini,cellini,cellini,_5462) @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,bellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5712=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(b,a,d,c,b,bellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(65): is_consistent_scenario(bellini,cellini,cellini,cellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(30): statement_content_true(b,a,d,c,b,bellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(0): statement_content_true(b,a,d,c,b,bellini,cellini,cellini,cellini,_5462) @ /tmp/tmpd794ti5a.pl:28
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,bellini,cellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5794=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            fail: statement_content_true(b,a,d,c,b,bellini,cellini,cellini,cellini,_5462) @ <dynamic>:0
                          redo(30): is_consistent_scenario(bellini,cellini,cellini,cellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,bellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,bellini,cellini,cellini,cellini,_4634) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4884=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,bellini,cellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,bellini,cellini,cellini,cellini,_4634) @ <dynamic>:0
                          fail: is_consistent_scenario(bellini,cellini,cellini,cellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_36) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: possible_maker(_38) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: possible_maker(_40) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: possible_maker(_42) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(cellini,bellini,bellini,bellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,cellini,bellini,bellini,bellini,_4436) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4604=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,cellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,cellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,cellini,bellini,bellini,bellini,_4436) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4686=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(36): statement_content_true(a,a,b,c,d,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(45): statement_content_true(a,a,b,c,d,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,b,c,d,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,bellini,bellini,bellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: false==false @ <dynamic>:0
                            exit: false==false @ <dynamic>:0
                            call: statement_content_true(b,a,b,c,d,cellini,bellini,bellini,bellini,_5224) @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5392=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(30): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(43): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: a=c @ <dynamic>:0
                              fail: a=c @ <dynamic>:0
                            redo(17): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(0): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,bellini,_5224) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5474=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(46): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: a=c @ <dynamic>:0
                              fail: a=c @ <dynamic>:0
                            redo(55): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                            exit: statement_content_true(b,a,b,c,d,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(65): is_consistent_scenario(cellini,bellini,bellini,bellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            fail: statement_content_true(b,a,b,c,d,cellini,bellini,bellini,bellini,_5224) @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,cellini,bellini,bellini,bellini,_4436) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,bellini,bellini,bellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(cellini,bellini,bellini,bellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,cellini,bellini,bellini,bellini,_4506) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4674=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,cellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,cellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,cellini,bellini,bellini,bellini,_4506) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4756=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(45): statement_content_true(a,a,d,c,b,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,d,c,b,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,bellini,bellini,bellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: false==false @ <dynamic>:0
                            exit: false==false @ <dynamic>:0
                            call: statement_content_true(b,a,d,c,b,cellini,bellini,bellini,bellini,_5294) @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,cellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5544=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(30): statement_content_true(b,a,d,c,b,cellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(43): statement_content_true(b,a,d,c,b,cellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: c=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            exit: statement_content_true(b,a,d,c,b,cellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: true==true @ <dynamic>:0
                            exit: true==true @ <dynamic>:0
                            call: statement_content_true(c,a,d,c,b,cellini,bellini,bellini,bellini,_6386) @ <dynamic>:0
                            exit: statement_content_true(c,a,d,c,b,cellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:29
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: true==true @ <dynamic>:0
                            exit: true==true @ <dynamic>:0
                            call: statement_content_true(d,a,d,c,b,cellini,bellini,bellini,bellini,_6730) @ <dynamic>:0
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: _6898=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(33): statement_content_true(d,a,d,c,b,cellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:31
                              call: a=c @ <dynamic>:0
                              fail: a=c @ <dynamic>:0
                            redo(17): statement_content_true(d,a,d,c,b,cellini,bellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:31
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(0): statement_content_true(d,a,d,c,b,cellini,bellini,bellini,bellini,_6730) @ /tmp/tmpd794ti5a.pl:32
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: _6980=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(36): statement_content_true(d,a,d,c,b,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:32
                              call: a=c @ <dynamic>:0
                              fail: a=c @ <dynamic>:0
                            redo(45): statement_content_true(d,a,d,c,b,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:32
                            exit: statement_content_true(d,a,d,c,b,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:32
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(135): is_consistent_scenario(cellini,bellini,bellini,bellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(d,a,d,c,b,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:32
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            fail: statement_content_true(d,a,d,c,b,cellini,bellini,bellini,bellini,_6730) @ <dynamic>:0
                          redo(100): is_consistent_scenario(cellini,bellini,bellini,bellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(0): statement_content_true(c,a,d,c,b,cellini,bellini,bellini,bellini,_6386) @ /tmp/tmpd794ti5a.pl:30
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: statement_content_true(c,a,d,c,b,cellini,bellini,bellini,bellini,_6386) @ <dynamic>:0
                          redo(65): is_consistent_scenario(cellini,bellini,bellini,bellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(0): statement_content_true(b,a,d,c,b,cellini,bellini,bellini,bellini,_5294) @ /tmp/tmpd794ti5a.pl:28
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5626=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(b,a,d,c,b,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(46): statement_content_true(b,a,d,c,b,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: c=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: statement_content_true(b,a,d,c,b,cellini,bellini,bellini,bellini,_5294) @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,cellini,bellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,cellini,bellini,bellini,bellini,_4506) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,bellini,bellini,bellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_42) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(cellini,bellini,bellini,cellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,cellini,bellini,bellini,cellini,_4500) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4668=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,cellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,cellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,cellini,bellini,bellini,cellini,_4500) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4750=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(36): statement_content_true(a,a,b,c,d,cellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(45): statement_content_true(a,a,b,c,d,cellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,b,c,d,cellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,bellini,bellini,cellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: false==false @ <dynamic>:0
                            exit: false==false @ <dynamic>:0
                            call: statement_content_true(b,a,b,c,d,cellini,bellini,bellini,cellini,_5288) @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5456=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(30): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(43): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: a=c @ <dynamic>:0
                              fail: a=c @ <dynamic>:0
                            redo(17): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(0): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,cellini,_5288) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5538=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(46): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: a=c @ <dynamic>:0
                              fail: a=c @ <dynamic>:0
                            redo(55): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                            exit: statement_content_true(b,a,b,c,d,cellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(65): is_consistent_scenario(cellini,bellini,bellini,cellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(b,a,b,c,d,cellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            fail: statement_content_true(b,a,b,c,d,cellini,bellini,bellini,cellini,_5288) @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,cellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,cellini,bellini,bellini,cellini,_4500) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,bellini,bellini,cellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(cellini,bellini,bellini,cellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,cellini,bellini,bellini,cellini,_4570) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4738=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,cellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,d,c,b,cellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,bellini,bellini,cellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,cellini,bellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,cellini,bellini,bellini,cellini,_4570) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4820=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,cellini,bellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,cellini,bellini,bellini,cellini,_4570) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,bellini,bellini,cellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_40) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: possible_maker(_42) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(cellini,bellini,cellini,bellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,cellini,bellini,cellini,bellini,_4500) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4668=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,cellini,bellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,cellini,bellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,cellini,bellini,cellini,bellini,_4500) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4750=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(36): statement_content_true(a,a,b,c,d,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(45): statement_content_true(a,a,b,c,d,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,b,c,d,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,bellini,cellini,bellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: false==false @ <dynamic>:0
                            exit: false==false @ <dynamic>:0
                            call: statement_content_true(b,a,b,c,d,cellini,bellini,cellini,bellini,_5288) @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5456=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(30): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(43): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: a=c @ <dynamic>:0
                              fail: a=c @ <dynamic>:0
                            redo(17): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(0): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,bellini,_5288) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5538=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(46): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: a=c @ <dynamic>:0
                              fail: a=c @ <dynamic>:0
                            redo(55): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                            exit: statement_content_true(b,a,b,c,d,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(65): is_consistent_scenario(cellini,bellini,cellini,bellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            fail: statement_content_true(b,a,b,c,d,cellini,bellini,cellini,bellini,_5288) @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,cellini,bellini,cellini,bellini,_4500) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,bellini,cellini,bellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(cellini,bellini,cellini,bellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,cellini,bellini,cellini,bellini,_4570) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4738=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,cellini,bellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,cellini,bellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,cellini,bellini,cellini,bellini,_4570) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4820=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(45): statement_content_true(a,a,d,c,b,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,d,c,b,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,bellini,cellini,bellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: false==false @ <dynamic>:0
                            exit: false==false @ <dynamic>:0
                            call: statement_content_true(b,a,d,c,b,cellini,bellini,cellini,bellini,_5358) @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,cellini,bellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5608=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(30): statement_content_true(b,a,d,c,b,cellini,bellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(43): statement_content_true(b,a,d,c,b,cellini,bellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: c=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(0): statement_content_true(b,a,d,c,b,cellini,bellini,cellini,bellini,_5358) @ /tmp/tmpd794ti5a.pl:28
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5690=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(b,a,d,c,b,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(46): statement_content_true(b,a,d,c,b,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: c=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(55): statement_content_true(b,a,d,c,b,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                            exit: statement_content_true(b,a,d,c,b,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(65): is_consistent_scenario(cellini,bellini,cellini,bellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,cellini,bellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,cellini,bellini,cellini,bellini,_4570) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,bellini,cellini,bellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_42) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(cellini,bellini,cellini,cellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,cellini,bellini,cellini,cellini,_4564) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4732=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,cellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,cellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,cellini,bellini,cellini,cellini,_4564) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4814=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(36): statement_content_true(a,a,b,c,d,cellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(45): statement_content_true(a,a,b,c,d,cellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,b,c,d,cellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,bellini,cellini,cellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: false==false @ <dynamic>:0
                            exit: false==false @ <dynamic>:0
                            call: statement_content_true(b,a,b,c,d,cellini,bellini,cellini,cellini,_5352) @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5520=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(30): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(43): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: a=c @ <dynamic>:0
                              fail: a=c @ <dynamic>:0
                            redo(17): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(0): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,cellini,_5352) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5602=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(33): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(46): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: a=c @ <dynamic>:0
                              fail: a=c @ <dynamic>:0
                            redo(55): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                            exit: statement_content_true(b,a,b,c,d,cellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                            call: bellini==bellini @ <dynamic>:0
                            exit: bellini==bellini @ <dynamic>:0
                            call: false==true @ <dynamic>:0
                            fail: false==true @ <dynamic>:0
                          redo(65): is_consistent_scenario(cellini,bellini,cellini,cellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: bellini==cellini @ <dynamic>:0
                            fail: bellini==cellini @ <dynamic>:0
                            redo(17): statement_content_true(b,a,b,c,d,cellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            fail: statement_content_true(b,a,b,c,d,cellini,bellini,cellini,cellini,_5352) @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,cellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,cellini,bellini,cellini,cellini,_4564) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,bellini,cellini,cellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(cellini,bellini,cellini,cellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,cellini,bellini,cellini,cellini,_4634) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4802=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,cellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,d,c,b,cellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,bellini,cellini,cellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,cellini,bellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,cellini,bellini,cellini,cellini,_4634) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4884=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,cellini,bellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,cellini,bellini,cellini,cellini,_4634) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,bellini,cellini,cellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_38) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: possible_maker(_40) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: possible_maker(_42) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(cellini,cellini,bellini,bellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,cellini,cellini,bellini,bellini,_4500) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4668=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,b,c,d,cellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,cellini,bellini,bellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,cellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,cellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,cellini,cellini,bellini,bellini,_4500) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4750=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,cellini,cellini,bellini,bellini,_4500) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,cellini,bellini,bellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(cellini,cellini,bellini,bellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,cellini,cellini,bellini,bellini,_4570) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4738=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,cellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,cellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,cellini,cellini,bellini,bellini,_4570) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4820=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,cellini,cellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(45): statement_content_true(a,a,d,c,b,cellini,cellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,d,c,b,cellini,cellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,cellini,bellini,bellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: false==false @ <dynamic>:0
                            exit: false==false @ <dynamic>:0
                            call: statement_content_true(b,a,d,c,b,cellini,cellini,bellini,bellini,_5358) @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,cellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5608=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(b,a,d,c,b,cellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(65): is_consistent_scenario(cellini,cellini,bellini,bellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(30): statement_content_true(b,a,d,c,b,cellini,cellini,bellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(0): statement_content_true(b,a,d,c,b,cellini,cellini,bellini,bellini,_5358) @ /tmp/tmpd794ti5a.pl:28
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,cellini,cellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5690=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            fail: statement_content_true(b,a,d,c,b,cellini,cellini,bellini,bellini,_5358) @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,cellini,cellini,bellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,cellini,cellini,bellini,bellini,_4570) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,cellini,bellini,bellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_42) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(cellini,cellini,bellini,cellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,cellini,cellini,bellini,cellini,_4564) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4732=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,b,c,d,cellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,cellini,bellini,cellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,cellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,cellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,cellini,cellini,bellini,cellini,_4564) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4814=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,cellini,cellini,bellini,cellini,_4564) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,cellini,bellini,cellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(cellini,cellini,bellini,cellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,cellini,cellini,bellini,cellini,_4634) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4802=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,cellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,d,c,b,cellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,cellini,bellini,cellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,cellini,cellini,bellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,cellini,cellini,bellini,cellini,_4634) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4884=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,cellini,cellini,bellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,cellini,cellini,bellini,cellini,_4634) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,cellini,bellini,cellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_40) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: possible_maker(_42) @ <dynamic>:0
                          exit: possible_maker(bellini) @ /tmp/tmpd794ti5a.pl:21
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(cellini,cellini,cellini,bellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,cellini,cellini,cellini,bellini,_4564) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4732=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,b,c,d,cellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,cellini,cellini,bellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,cellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,cellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,cellini,cellini,cellini,bellini,_4564) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4814=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,cellini,cellini,cellini,bellini,_4564) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,cellini,cellini,bellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(cellini,cellini,cellini,bellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,cellini,cellini,cellini,bellini,_4634) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4802=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,cellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,cellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,cellini,cellini,cellini,bellini,_4634) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4884=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,cellini,cellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: bellini=cellini @ <dynamic>:0
                              fail: bellini=cellini @ <dynamic>:0
                            redo(45): statement_content_true(a,a,d,c,b,cellini,cellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            exit: statement_content_true(a,a,d,c,b,cellini,cellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,cellini,cellini,bellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: false==false @ <dynamic>:0
                            exit: false==false @ <dynamic>:0
                            call: statement_content_true(b,a,d,c,b,cellini,cellini,cellini,bellini,_5422) @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,cellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5672=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(b,a,d,c,b,cellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(65): is_consistent_scenario(cellini,cellini,cellini,bellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(30): statement_content_true(b,a,d,c,b,cellini,cellini,cellini,bellini,true) @ /tmp/tmpd794ti5a.pl:27
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(0): statement_content_true(b,a,d,c,b,cellini,cellini,cellini,bellini,_5422) @ /tmp/tmpd794ti5a.pl:28
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(17): statement_content_true(b,a,d,c,b,cellini,cellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:28
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: _5754=c @ <dynamic>:0
                              exit: c=c @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            fail: statement_content_true(b,a,d,c,b,cellini,cellini,cellini,bellini,_5422) @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,cellini,cellini,cellini,bellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,cellini,cellini,cellini,bellini,_4634) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,cellini,cellini,bellini,a,d,c,b) @ <dynamic>:0
                          redo(0): possible_maker(_42) @ /tmp/tmpd794ti5a.pl:22
                          exit: possible_maker(cellini) @ /tmp/tmpd794ti5a.pl:22
                          call: pairing_v2(_44,_46,_48,_50) @ <dynamic>:0
                          exit: pairing_v2(a,b,c,d) @ /tmp/tmpd794ti5a.pl:23
                          call: is_consistent_scenario(cellini,cellini,cellini,cellini,a,b,c,d) @ <dynamic>:0
                            call: statement_content_true(a,a,b,c,d,cellini,cellini,cellini,cellini,_4628) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4796=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,b,c,d,cellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,cellini,cellini,cellini,a,b,c,d) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(33): statement_content_true(a,a,b,c,d,cellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: b=d @ <dynamic>:0
                              fail: b=d @ <dynamic>:0
                            redo(17): statement_content_true(a,a,b,c,d,cellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,b,c,d,cellini,cellini,cellini,cellini,_4628) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4878=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: b=b @ <dynamic>:0
                              exit: b=b @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,b,c,d,cellini,cellini,cellini,cellini,_4628) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,cellini,cellini,cellini,a,b,c,d) @ <dynamic>:0
                          redo(0): pairing_v2(_44,_46,_48,_50) @ /tmp/tmpd794ti5a.pl:24
                          exit: pairing_v2(a,d,c,b) @ /tmp/tmpd794ti5a.pl:24
                          call: is_consistent_scenario(cellini,cellini,cellini,cellini,a,d,c,b) @ <dynamic>:0
                            call: statement_content_true(a,a,d,c,b,cellini,cellini,cellini,cellini,_4698) @ <dynamic>:0
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4866=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(33): statement_content_true(a,a,d,c,b,cellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                            exit: statement_content_true(a,a,d,c,b,cellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                            call: cellini==bellini @ <dynamic>:0
                            fail: cellini==bellini @ <dynamic>:0
                          redo(30): is_consistent_scenario(cellini,cellini,cellini,cellini,a,d,c,b) @ /tmp/tmpd794ti5a.pl:33
                            call: cellini==cellini @ <dynamic>:0
                            exit: cellini==cellini @ <dynamic>:0
                            call: true==false @ <dynamic>:0
                            fail: true==false @ <dynamic>:0
                            redo(17): statement_content_true(a,a,d,c,b,cellini,cellini,cellini,cellini,true) @ /tmp/tmpd794ti5a.pl:25
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            redo(0): statement_content_true(a,a,d,c,b,cellini,cellini,cellini,cellini,_4698) @ /tmp/tmpd794ti5a.pl:26
                              call: a=a @ <dynamic>:0
                              exit: a=a @ <dynamic>:0
                              call: _4948=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: d=b @ <dynamic>:0
                              fail: d=b @ <dynamic>:0
                            redo(36): statement_content_true(a,a,d,c,b,cellini,cellini,cellini,cellini,false) @ /tmp/tmpd794ti5a.pl:26
                              call: d=d @ <dynamic>:0
                              exit: d=d @ <dynamic>:0
                              call: cellini=cellini @ <dynamic>:0
                              exit: cellini=cellini @ <dynamic>:0
                              call: c=a @ <dynamic>:0
                              fail: c=a @ <dynamic>:0
                            fail: statement_content_true(a,a,d,c,b,cellini,cellini,cellini,cellini,_4698) @ <dynamic>:0
                          fail: is_consistent_scenario(cellini,cellini,cellini,cellini,a,d,c,b) @ <dynamic>:0
                        fail: solution_finder(_36,_38,_40,_42,_44,_46,_48,_50) @ <dynamic>:0

""")

    clauses = procesar_traza(sample_trace)