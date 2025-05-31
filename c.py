import re
import copy

class Clausula:
    def __init__(self, nombre, valor=None, veracidad="", padre=None):
        self.nombre = nombre
        self.valor = valor if valor is not None else []  # array de Clausula
        self.veracidad = veracidad  # string
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

def procesar_traza(traza_str):
    # Inicializamos un array de Clausulas llamado ramas_de_pensamientos
    ramas_de_pensamientos = []
    # Inicializamos una variable llamada root con la Clausula root con el nombre root, array vacío, valor = "" y padre = None
    root = Clausula(nombre="root", veracidad="", padre=None)
    # Inicializamos una variable llamada nodo_actual que será igual a root
    nodo_actual = root

    # Regex para parsear: Tipo, Nivel (ignorado por ahora), Contenido
    line_regex = re.compile(r"^\s*(Call|Exit|Fail|Redo):\s*\(\d+\)\s*(.*)$")

    traza = traza_str.strip().split('\n')
    # Por cada linea en la traza:
    for index, line_raw in enumerate(traza):
        line = line_raw.strip()
        if not line:
            continue

        # Parseala para determinar el contenido de la linea y desestrúcturalo en nombre, aridad y tipo de llamada.
        match = line_regex.match(line)
        if not match:
            # print(f"Advertencia: No se pudo parsear la línea: {line}")
            continue

        tipo_llamada, contenido_str = match.group(1), match.group(2).strip()
        # 'nombre' y 'aridad' se infieren del 'contenido_str' según el contexto.

        if tipo_llamada == "Call":
            # Si la linea es de tipo Call, si el contenido es fail salta la linea
            if contenido_str == "fail":
                continue
            # si no crea una Clausula con nombre = al contenido y padre = nodo_actual, esta será el nuevo nodo_actual
            nueva_clausula = Clausula(nombre=contenido_str, padre=nodo_actual)
            nodo_actual.valor.append(nueva_clausula)
            nodo_actual = nueva_clausula
        
        elif tipo_llamada == "Exit":
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
            
        elif tipo_llamada == "Fail":
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

        elif tipo_llamada == "Redo":
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
                    node_to_redo_found = curr_search_node
                    break
                for child in curr_search_node.valor:
                    if isinstance(child, Clausula): # Asegurarse de que el hijo es una Clausula
                         q.append(child)
            
            if node_to_redo_found:
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

                    indice = current.padre.valor.index(current)
                    # Truncar el array de valor del padre hasta el índice encontrado
                    current.padre.valor = current.padre.valor[:indice + 1]
                    current = current.padre
                    
            else:
                # Este caso idealmente no debería ocurrir si la traza es consistente.
                # print(f"Advertencia: Objetivo de REDO '{contenido_str}' no encontrado en el estado actual del árbol.")
                pass

    ramas_de_pensamientos.append(copy.deepcopy(root))

    return ramas_de_pensamientos, root

# Procesar la traza
ramas, arbol_final = procesar_traza(traza_ejemplo)

# Imprimir cada Clausula en ramas_de_pensamientos
print("--- Ramas de Pensamientos Generadas ---")
if not ramas:
    print("No se generaron ramas de pensamientos (no hubo Redos o la traza fue corta).")
for i, arbol_pensamiento in enumerate(ramas):
    print(f"--- Inicio Rama de Pensamiento {i+1} ---")
    print(arbol_pensamiento.pretty_print())
    print(f"--- Fin Rama de Pensamiento {i+1} ---\n")


import json
from graphviz import Digraph

def create_thought_graph(data, graph=None, parent_id=None, node_counter=[0]):
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
    graph.node(current_node_id, label=f"{name.replace("\\", "\\\\")}\\n({veracidad})", fillcolor=fill_color)

    # Add an edge from the parent node if it exists
    if parent_id:
        graph.edge(parent_id, current_node_id)

    # Recursively process children
    if "valor" in data and isinstance(data["valor"], list):
        for child in data["valor"]:
            create_thought_graph(child, graph, current_node_id, node_counter)

    return graph


for i, arbol_pensamiento in enumerate(ramas):
    if arbol_pensamiento.valor[0].veracidad == "verde":    
        dot = create_thought_graph(arbol_pensamiento.to_dict())

        # Render the graph to a file (e.g., PNG)
        # The .render() method saves the file and returns its path
        output_file = dot.render(f'cadena_pensamientos{i}', view=False, cleanup=True)
        print(f"Gráfico generado en: {output_file}")