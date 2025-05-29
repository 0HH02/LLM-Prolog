import re
import copy

class Clausula:
    def __init__(self, nombre, valor=None, veracidad="", padre=None):
        self.nombre = nombre
        self.valor = valor if valor is not None else []  # array de Clausula
        self.veracidad = veracidad  # string
        self.padre = padre  # Clausula

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

    # Por cada linea en la traza:
    for line_raw in traza_str.strip().split('\n'):
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
                father = node_to_redo_found.padre
                # Encontrar el índice de la cláusula en el array del padre
                if father:
                    indice = father.valor.index(node_to_redo_found)
                    # Truncar el array de valor del padre hasta el índice encontrado
                    father.valor = father.valor[:indice + 1]

                # Limpiar el array de valor del nodo encontrado y reiniciar su veracidad
                node_to_redo_found.valor = [] 
                node_to_redo_found.veracidad = ""  # Reiniciar su estado de veracidad
                nodo_actual = node_to_redo_found
            else:
                # Este caso idealmente no debería ocurrir si la traza es consistente.
                # print(f"Advertencia: Objetivo de REDO '{contenido_str}' no encontrado en el estado actual del árbol.")
                pass

    ramas_de_pensamientos.append(copy.deepcopy(root))

    return ramas_de_pensamientos, root


# Traza proporcionada
traza_ejemplo = """
   Call: (12) problema_tweedle(_4664, _4666, _4668, _4670, _4672)
   Call: (13) _4664=tweedledum
   Exit: (13) tweedledum=tweedledum
   Call: (13) _4666=tweedledee
   Exit: (13) tweedledee=tweedledee
   Call: (13) tweedledum\=tweedledee
   Exit: (13) tweedledum\=tweedledee
   Call: (13) _4668=lion
   Exit: (13) lion=lion
   Call: (13) _4670=unicorn
   Exit: (13) unicorn=unicorn
   Call: (13) lion\=unicorn
   Exit: (13) lion\=unicorn
   Call: (13) dia(_4672)
   Exit: (13) dia(lunes)
   Call: (13) reclama_identidad(persona1, _26300)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, lunes)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(lion, lunes)
   Fail: (14) dice_verdad(lion, lunes)
   Redo: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, lunes)
   Call: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (16) tweedledum=tweedledum
   Exit: (16) tweedledum=tweedledum
   Exit: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Fail: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, lunes)
   Redo: (13) dia(_4672)
   Exit: (13) dia(martes)
   Call: (13) reclama_identidad(persona1, _37982)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, martes)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(lion, martes)
   Fail: (14) dice_verdad(lion, martes)
   Redo: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, martes)
   Call: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (16) tweedledum=tweedledum
   Exit: (16) tweedledum=tweedledum
   Exit: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Fail: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, martes)
   Redo: (13) dia(_4672)
   Exit: (13) dia(miercoles)
   Call: (13) reclama_identidad(persona1, _49664)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, miercoles)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(lion, miercoles)
   Fail: (14) dice_verdad(lion, miercoles)
   Redo: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, miercoles)
   Call: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (16) tweedledum=tweedledum
   Exit: (16) tweedledum=tweedledum
   Exit: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Fail: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, miercoles)
   Redo: (13) dia(_4672)
   Exit: (13) dia(jueves)
   Call: (13) reclama_identidad(persona1, _61346)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, jueves)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(lion, jueves)
   Exit: (14) dice_verdad(lion, jueves)
   Exit: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, jueves)
   Call: (13) reclama_identidad(persona2, _2446)
   Exit: (13) reclama_identidad(persona2, tweedledee)
   Call: (13) es_consistente_enunciado(persona2, tweedledee, unicorn, tweedledee, jueves)
   Call: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (15) tweedledee=tweedledee
   Exit: (15) tweedledee=tweedledee
   Exit: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (14) dice_verdad(unicorn, jueves)
   Fail: (14) dice_verdad(unicorn, jueves)
   Redo: (13) es_consistente_enunciado(persona2, tweedledee, unicorn, tweedledee, jueves)
   Call: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Call: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (16) tweedledee=tweedledee
   Exit: (16) tweedledee=tweedledee
   Exit: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Fail: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Fail: (13) es_consistente_enunciado(persona2, tweedledee, unicorn, tweedledee, jueves)
   Redo: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, jueves)
   Call: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (16) tweedledum=tweedledum
   Exit: (16) tweedledum=tweedledum
   Exit: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Fail: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, jueves)
   Redo: (13) dia(_58)
   Exit: (13) dia(viernes)
   Call: (13) reclama_identidad(persona1, _19064)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, viernes)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(lion, viernes)
   Exit: (14) dice_verdad(lion, viernes)
   Exit: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, viernes)
   Call: (13) reclama_identidad(persona2, _25218)
   Exit: (13) reclama_identidad(persona2, tweedledee)
   Call: (13) es_consistente_enunciado(persona2, tweedledee, unicorn, tweedledee, viernes)
   Call: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (15) tweedledee=tweedledee
   Exit: (15) tweedledee=tweedledee
   Exit: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (14) dice_verdad(unicorn, viernes)
   Fail: (14) dice_verdad(unicorn, viernes)
   Redo: (13) es_consistente_enunciado(persona2, tweedledee, unicorn, tweedledee, viernes)
   Call: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Call: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (16) tweedledee=tweedledee
   Exit: (16) tweedledee=tweedledee
   Exit: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Fail: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Fail: (13) es_consistente_enunciado(persona2, tweedledee, unicorn, tweedledee, viernes)
   Redo: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, viernes)
   Call: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (16) tweedledum=tweedledum
   Exit: (16) tweedledum=tweedledum
   Exit: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Fail: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, viernes)
   Redo: (13) dia(_58)
   Exit: (13) dia(sabado)
   Call: (13) reclama_identidad(persona1, _41836)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, sabado)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(lion, sabado)
   Exit: (14) dice_verdad(lion, sabado)
   Exit: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, sabado)
   Call: (13) reclama_identidad(persona2, _47990)
   Exit: (13) reclama_identidad(persona2, tweedledee)
   Call: (13) es_consistente_enunciado(persona2, tweedledee, unicorn, tweedledee, sabado)
   Call: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (15) tweedledee=tweedledee
   Exit: (15) tweedledee=tweedledee
   Exit: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (14) dice_verdad(unicorn, sabado)
   Fail: (14) dice_verdad(unicorn, sabado)
   Redo: (13) es_consistente_enunciado(persona2, tweedledee, unicorn, tweedledee, sabado)
   Call: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Call: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (16) tweedledee=tweedledee
   Exit: (16) tweedledee=tweedledee
   Exit: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Fail: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Fail: (13) es_consistente_enunciado(persona2, tweedledee, unicorn, tweedledee, sabado)
   Redo: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, sabado)
   Call: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (16) tweedledum=tweedledum
   Exit: (16) tweedledum=tweedledum
   Exit: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Fail: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, sabado)
   Redo: (13) dia(_58)
   Exit: (13) dia(domingo)
   Call: (13) reclama_identidad(persona1, _64608)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, domingo)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(lion, domingo)
   Exit: (14) dice_verdad(lion, domingo)
   Exit: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, domingo)
   Call: (13) reclama_identidad(persona2, _5668)
   Exit: (13) reclama_identidad(persona2, tweedledee)
   Call: (13) es_consistente_enunciado(persona2, tweedledee, unicorn, tweedledee, domingo)
   Call: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (15) tweedledee=tweedledee
   Exit: (15) tweedledee=tweedledee
   Exit: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (14) dice_verdad(unicorn, domingo)
   Exit: (14) dice_verdad(unicorn, domingo)
   Exit: (13) es_consistente_enunciado(persona2, tweedledee, unicorn, tweedledee, domingo)
   Exit: (12) problema_tweedle(tweedledum, tweedledee, lion, unicorn, domingo)
    Call: (12) fail
    Fail: (12) fail
   Redo: (13) es_consistente_enunciado(persona2, tweedledee, unicorn, tweedledee, domingo)
   Call: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Call: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (16) tweedledee=tweedledee
   Exit: (16) tweedledee=tweedledee
   Exit: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Fail: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Fail: (13) es_consistente_enunciado(persona2, tweedledee, unicorn, tweedledee, domingo)
   Redo: (14) dice_verdad(lion, domingo)
   Fail: (14) dice_verdad(lion, domingo)
   Redo: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, domingo)
   Call: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (16) tweedledum=tweedledum
   Exit: (16) tweedledum=tweedledum
   Exit: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Fail: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, domingo)
   Redo: (12) problema_tweedle(tweedledum, tweedledee, _54, _56, _58)
   Call: (13) _54=unicorn
   Exit: (13) unicorn=unicorn
   Call: (13) _56=lion
   Exit: (13) lion=lion
   Call: (13) unicorn\=lion
   Exit: (13) unicorn\=lion
   Call: (13) dia(_58)
   Exit: (13) dia(lunes)
   Call: (13) reclama_identidad(persona1, _30254)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, lunes)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(unicorn, lunes)
   Exit: (14) dice_verdad(unicorn, lunes)
   Exit: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, lunes)
   Call: (13) reclama_identidad(persona2, _36408)
   Exit: (13) reclama_identidad(persona2, tweedledee)
   Call: (13) es_consistente_enunciado(persona2, tweedledee, lion, tweedledee, lunes)
   Call: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (15) tweedledee=tweedledee
   Exit: (15) tweedledee=tweedledee
   Exit: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (14) dice_verdad(lion, lunes)
   Fail: (14) dice_verdad(lion, lunes)
   Redo: (13) es_consistente_enunciado(persona2, tweedledee, lion, tweedledee, lunes)
   Call: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Call: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (16) tweedledee=tweedledee
   Exit: (16) tweedledee=tweedledee
   Exit: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Fail: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Fail: (13) es_consistente_enunciado(persona2, tweedledee, lion, tweedledee, lunes)
   Redo: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, lunes)
   Call: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (16) tweedledum=tweedledum
   Exit: (16) tweedledum=tweedledum
   Exit: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Fail: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, lunes)
   Redo: (13) dia(_58)
   Exit: (13) dia(martes)
   Call: (13) reclama_identidad(persona1, _53026)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, martes)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(unicorn, martes)
   Exit: (14) dice_verdad(unicorn, martes)
   Exit: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, martes)
   Call: (13) reclama_identidad(persona2, _59180)
   Exit: (13) reclama_identidad(persona2, tweedledee)
   Call: (13) es_consistente_enunciado(persona2, tweedledee, lion, tweedledee, martes)
   Call: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (15) tweedledee=tweedledee
   Exit: (15) tweedledee=tweedledee
   Exit: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (14) dice_verdad(lion, martes)
   Fail: (14) dice_verdad(lion, martes)
   Redo: (13) es_consistente_enunciado(persona2, tweedledee, lion, tweedledee, martes)
   Call: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Call: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (16) tweedledee=tweedledee
   Exit: (16) tweedledee=tweedledee
   Exit: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Fail: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Fail: (13) es_consistente_enunciado(persona2, tweedledee, lion, tweedledee, martes)
   Redo: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, martes)
   Call: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (16) tweedledum=tweedledum
   Exit: (16) tweedledum=tweedledum
   Exit: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Fail: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, martes)
   Redo: (13) dia(_58)
   Exit: (13) dia(miercoles)
   Call: (13) reclama_identidad(persona1, _10616)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, miercoles)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(unicorn, miercoles)
   Exit: (14) dice_verdad(unicorn, miercoles)
   Exit: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, miercoles)
   Call: (13) reclama_identidad(persona2, _16770)
   Exit: (13) reclama_identidad(persona2, tweedledee)
   Call: (13) es_consistente_enunciado(persona2, tweedledee, lion, tweedledee, miercoles)
   Call: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (15) tweedledee=tweedledee
   Exit: (15) tweedledee=tweedledee
   Exit: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (14) dice_verdad(lion, miercoles)
   Fail: (14) dice_verdad(lion, miercoles)
   Redo: (13) es_consistente_enunciado(persona2, tweedledee, lion, tweedledee, miercoles)
   Call: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Call: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (16) tweedledee=tweedledee
   Exit: (16) tweedledee=tweedledee
   Exit: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Fail: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Fail: (13) es_consistente_enunciado(persona2, tweedledee, lion, tweedledee, miercoles)
   Redo: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, miercoles)
   Call: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (16) tweedledum=tweedledum
   Exit: (16) tweedledum=tweedledum
   Exit: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Fail: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, miercoles)
   Redo: (13) dia(_58)
   Exit: (13) dia(jueves)
   Call: (13) reclama_identidad(persona1, _33388)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, jueves)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(unicorn, jueves)
   Fail: (14) dice_verdad(unicorn, jueves)
   Redo: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, jueves)
   Call: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (16) tweedledum=tweedledum
   Exit: (16) tweedledum=tweedledum
   Exit: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Fail: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, jueves)
   Redo: (13) dia(_58)
   Exit: (13) dia(viernes)
   Call: (13) reclama_identidad(persona1, _45070)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, viernes)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(unicorn, viernes)
   Fail: (14) dice_verdad(unicorn, viernes)
   Redo: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, viernes)
   Call: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (16) tweedledum=tweedledum
   Exit: (16) tweedledum=tweedledum
   Exit: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Fail: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, viernes)
   Redo: (13) dia(_58)
   Exit: (13) dia(sabado)
   Call: (13) reclama_identidad(persona1, _56752)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, sabado)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(unicorn, sabado)
   Fail: (14) dice_verdad(unicorn, sabado)
   Redo: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, sabado)
   Call: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (16) tweedledum=tweedledum
   Exit: (16) tweedledum=tweedledum
   Exit: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Fail: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, sabado)
   Redo: (13) dia(_58)
   Exit: (13) dia(domingo)
   Call: (13) reclama_identidad(persona1, _3222)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, domingo)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(unicorn, domingo)
   Exit: (14) dice_verdad(unicorn, domingo)
   Exit: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, domingo)
   Call: (13) reclama_identidad(persona2, _9376)
   Exit: (13) reclama_identidad(persona2, tweedledee)
   Call: (13) es_consistente_enunciado(persona2, tweedledee, lion, tweedledee, domingo)
   Call: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (15) tweedledee=tweedledee
   Exit: (15) tweedledee=tweedledee
   Exit: (14) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (14) dice_verdad(lion, domingo)
   Exit: (14) dice_verdad(lion, domingo)
   Exit: (13) es_consistente_enunciado(persona2, tweedledee, lion, tweedledee, domingo)
   Exit: (12) problema_tweedle(tweedledum, tweedledee, unicorn, lion, domingo)
    Call: (12) fail
    Fail: (12) fail
   Redo: (14) dice_verdad(lion, domingo)
   Fail: (14) dice_verdad(lion, domingo)
   Redo: (13) es_consistente_enunciado(persona2, tweedledee, lion, tweedledee, domingo)
   Call: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Call: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Call: (16) tweedledee=tweedledee
   Exit: (16) tweedledee=tweedledee
   Exit: (15) afirmacion_es_verdadera(persona2, tweedledee, tweedledee)
   Fail: (14) afirmacion_es_falsa(persona2, tweedledee, tweedledee)
   Fail: (13) es_consistente_enunciado(persona2, tweedledee, lion, tweedledee, domingo)
   Redo: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, domingo)
   Call: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (16) tweedledum=tweedledum
   Exit: (16) tweedledum=tweedledum
   Exit: (15) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Fail: (14) afirmacion_es_falsa(persona1, tweedledum, tweedledum)
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, unicorn, tweedledum, domingo)
   Redo: (12) problema_tweedle(_50, _52, _54, _56, _58)
   Call: (13) _50=tweedledee
   Exit: (13) tweedledee=tweedledee
   Call: (13) _52=tweedledum
   Exit: (13) tweedledum=tweedledum
   Call: (13) tweedledee\=tweedledum
   Exit: (13) tweedledee\=tweedledum
   Call: (13) _54=lion
   Exit: (13) lion=lion
   Call: (13) _56=unicorn
   Exit: (13) unicorn=unicorn
   Call: (13) lion\=unicorn
   Exit: (13) lion\=unicorn
   Call: (13) dia(_58)
   Exit: (13) dia(lunes)
   Call: (13) reclama_identidad(persona1, _37634)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, lunes)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (15) tweedledee=tweedledum
   Fail: (15) tweedledee=tweedledum
   Fail: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, lunes)
   Call: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (16) tweedledee=tweedledum
   Fail: (16) tweedledee=tweedledum
   Fail: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Exit: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (14) miente(lion, lunes)
   Exit: (14) miente(lion, lunes)
   Exit: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, lunes)
   Call: (13) reclama_identidad(persona2, _48716)
   Exit: (13) reclama_identidad(persona2, tweedledee)
   Call: (13) es_consistente_enunciado(persona2, tweedledum, unicorn, tweedledee, lunes)
   Call: (14) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Call: (15) tweedledum=tweedledee
   Fail: (15) tweedledum=tweedledee
   Fail: (14) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Redo: (13) es_consistente_enunciado(persona2, tweedledum, unicorn, tweedledee, lunes)
   Call: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Call: (15) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Call: (16) tweedledum=tweedledee
   Fail: (16) tweedledum=tweedledee
   Fail: (15) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Redo: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Exit: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Call: (14) miente(unicorn, lunes)
   Fail: (14) miente(unicorn, lunes)
   Fail: (13) es_consistente_enunciado(persona2, tweedledum, unicorn, tweedledee, lunes)
   Redo: (13) dia(_58)
   Exit: (13) dia(martes)
   Call: (13) reclama_identidad(persona1, _61014)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, martes)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (15) tweedledee=tweedledum
   Fail: (15) tweedledee=tweedledum
   Fail: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, martes)
   Call: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (16) tweedledee=tweedledum
   Fail: (16) tweedledee=tweedledum
   Fail: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Exit: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (14) miente(lion, martes)
   Exit: (14) miente(lion, martes)
   Exit: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, martes)
   Call: (13) reclama_identidad(persona2, _6926)
   Exit: (13) reclama_identidad(persona2, tweedledee)
   Call: (13) es_consistente_enunciado(persona2, tweedledum, unicorn, tweedledee, martes)
   Call: (14) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Call: (15) tweedledum=tweedledee
   Fail: (15) tweedledum=tweedledee
   Fail: (14) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Redo: (13) es_consistente_enunciado(persona2, tweedledum, unicorn, tweedledee, martes)
   Call: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Call: (15) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Call: (16) tweedledum=tweedledee
   Fail: (16) tweedledum=tweedledee
   Fail: (15) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Redo: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Exit: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Call: (14) miente(unicorn, martes)
   Fail: (14) miente(unicorn, martes)
   Fail: (13) es_consistente_enunciado(persona2, tweedledum, unicorn, tweedledee, martes)
   Redo: (13) dia(_58)
   Exit: (13) dia(miercoles)
   Call: (13) reclama_identidad(persona1, _19224)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, miercoles)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (15) tweedledee=tweedledum
   Fail: (15) tweedledee=tweedledum
   Fail: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, miercoles)
   Call: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (16) tweedledee=tweedledum
   Fail: (16) tweedledee=tweedledum
   Fail: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Exit: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (14) miente(lion, miercoles)
   Exit: (14) miente(lion, miercoles)
   Exit: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, miercoles)
   Call: (13) reclama_identidad(persona2, _30306)
   Exit: (13) reclama_identidad(persona2, tweedledee)
   Call: (13) es_consistente_enunciado(persona2, tweedledum, unicorn, tweedledee, miercoles)
   Call: (14) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Call: (15) tweedledum=tweedledee
   Fail: (15) tweedledum=tweedledee
   Fail: (14) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Redo: (13) es_consistente_enunciado(persona2, tweedledum, unicorn, tweedledee, miercoles)
   Call: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Call: (15) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Call: (16) tweedledum=tweedledee
   Fail: (16) tweedledum=tweedledee
   Fail: (15) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Redo: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Exit: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Call: (14) miente(unicorn, miercoles)
   Fail: (14) miente(unicorn, miercoles)
   Fail: (13) es_consistente_enunciado(persona2, tweedledum, unicorn, tweedledee, miercoles)
   Redo: (13) dia(_58)
   Exit: (13) dia(jueves)
   Call: (13) reclama_identidad(persona1, _42604)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, jueves)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (15) tweedledee=tweedledum
   Fail: (15) tweedledee=tweedledum
   Fail: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, jueves)
   Call: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (16) tweedledee=tweedledum
   Fail: (16) tweedledee=tweedledum
   Fail: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Exit: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (14) miente(lion, jueves)
   Fail: (14) miente(lion, jueves)
   Fail: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, jueves)
   Redo: (13) dia(_58)
   Exit: (13) dia(viernes)
   Call: (13) reclama_identidad(persona1, _54902)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, viernes)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (15) tweedledee=tweedledum
   Fail: (15) tweedledee=tweedledum
   Fail: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, viernes)
   Call: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (16) tweedledee=tweedledum
   Fail: (16) tweedledee=tweedledum
   Fail: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Exit: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (14) miente(lion, viernes)
   Fail: (14) miente(lion, viernes)
   Fail: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, viernes)
   Redo: (13) dia(_58)
   Exit: (13) dia(sabado)
   Call: (13) reclama_identidad(persona1, _1990)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, sabado)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (15) tweedledee=tweedledum
   Fail: (15) tweedledee=tweedledum
   Fail: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, sabado)
   Call: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (16) tweedledee=tweedledum
   Fail: (16) tweedledee=tweedledum
   Fail: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Exit: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (14) miente(lion, sabado)
   Fail: (14) miente(lion, sabado)
   Fail: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, sabado)
   Redo: (13) dia(_58)
   Exit: (13) dia(domingo)
   Call: (13) reclama_identidad(persona1, _14288)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, domingo)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (15) tweedledee=tweedledum
   Fail: (15) tweedledee=tweedledum
   Fail: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, domingo)
   Call: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (16) tweedledee=tweedledum
   Fail: (16) tweedledee=tweedledum
   Fail: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Exit: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (14) miente(lion, domingo)
   Fail: (14) miente(lion, domingo)
   Fail: (13) es_consistente_enunciado(persona1, tweedledee, lion, tweedledum, domingo)
   Redo: (12) problema_tweedle(tweedledee, tweedledum, _54, _56, _58)
   Call: (13) _54=unicorn
   Exit: (13) unicorn=unicorn
   Call: (13) _56=lion
   Exit: (13) lion=lion
   Call: (13) unicorn\=lion
   Exit: (13) unicorn\=lion
   Call: (13) dia(_58)
   Exit: (13) dia(lunes)
   Call: (13) reclama_identidad(persona1, _30882)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, lunes)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (15) tweedledee=tweedledum
   Fail: (15) tweedledee=tweedledum
   Fail: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, lunes)
   Call: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (16) tweedledee=tweedledum
   Fail: (16) tweedledee=tweedledum
   Fail: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Exit: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (14) miente(unicorn, lunes)
   Fail: (14) miente(unicorn, lunes)
   Fail: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, lunes)
   Redo: (13) dia(_58)
   Exit: (13) dia(martes)
   Call: (13) reclama_identidad(persona1, _43180)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, martes)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (15) tweedledee=tweedledum
   Fail: (15) tweedledee=tweedledum
   Fail: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, martes)
   Call: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (16) tweedledee=tweedledum
   Fail: (16) tweedledee=tweedledum
   Fail: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Exit: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (14) miente(unicorn, martes)
   Fail: (14) miente(unicorn, martes)
   Fail: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, martes)
   Redo: (13) dia(_58)
   Exit: (13) dia(miercoles)
   Call: (13) reclama_identidad(persona1, _55478)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, miercoles)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (15) tweedledee=tweedledum
   Fail: (15) tweedledee=tweedledum
   Fail: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, miercoles)
   Call: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (16) tweedledee=tweedledum
   Fail: (16) tweedledee=tweedledum
   Fail: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Exit: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (14) miente(unicorn, miercoles)
   Fail: (14) miente(unicorn, miercoles)
   Fail: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, miercoles)
   Redo: (13) dia(_58)
   Exit: (13) dia(jueves)
   Call: (13) reclama_identidad(persona1, _2602)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, jueves)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (15) tweedledee=tweedledum
   Fail: (15) tweedledee=tweedledum
   Fail: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, jueves)
   Call: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (16) tweedledee=tweedledum
   Fail: (16) tweedledee=tweedledum
   Fail: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Exit: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (14) miente(unicorn, jueves)
   Exit: (14) miente(unicorn, jueves)
   Exit: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, jueves)
   Call: (13) reclama_identidad(persona2, _13684)
   Exit: (13) reclama_identidad(persona2, tweedledee)
   Call: (13) es_consistente_enunciado(persona2, tweedledum, lion, tweedledee, jueves)
   Call: (14) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Call: (15) tweedledum=tweedledee
   Fail: (15) tweedledum=tweedledee
   Fail: (14) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Redo: (13) es_consistente_enunciado(persona2, tweedledum, lion, tweedledee, jueves)
   Call: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Call: (15) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Call: (16) tweedledum=tweedledee
   Fail: (16) tweedledum=tweedledee
   Fail: (15) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Redo: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Exit: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Call: (14) miente(lion, jueves)
   Fail: (14) miente(lion, jueves)
   Fail: (13) es_consistente_enunciado(persona2, tweedledum, lion, tweedledee, jueves)
   Redo: (13) dia(_58)
   Exit: (13) dia(viernes)
   Call: (13) reclama_identidad(persona1, _25982)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, viernes)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (15) tweedledee=tweedledum
   Fail: (15) tweedledee=tweedledum
   Fail: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, viernes)
   Call: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (16) tweedledee=tweedledum
   Fail: (16) tweedledee=tweedledum
   Fail: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Exit: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (14) miente(unicorn, viernes)
   Exit: (14) miente(unicorn, viernes)
   Exit: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, viernes)
   Call: (13) reclama_identidad(persona2, _37064)
   Exit: (13) reclama_identidad(persona2, tweedledee)
   Call: (13) es_consistente_enunciado(persona2, tweedledum, lion, tweedledee, viernes)
   Call: (14) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Call: (15) tweedledum=tweedledee
   Fail: (15) tweedledum=tweedledee
   Fail: (14) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Redo: (13) es_consistente_enunciado(persona2, tweedledum, lion, tweedledee, viernes)
   Call: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Call: (15) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Call: (16) tweedledum=tweedledee
   Fail: (16) tweedledum=tweedledee
   Fail: (15) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Redo: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Exit: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Call: (14) miente(lion, viernes)
   Fail: (14) miente(lion, viernes)
   Fail: (13) es_consistente_enunciado(persona2, tweedledum, lion, tweedledee, viernes)
   Redo: (13) dia(_58)
   Exit: (13) dia(sabado)
   Call: (13) reclama_identidad(persona1, _49362)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, sabado)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (15) tweedledee=tweedledum
   Fail: (15) tweedledee=tweedledum
   Fail: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, sabado)
   Call: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (16) tweedledee=tweedledum
   Fail: (16) tweedledee=tweedledum
   Fail: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Exit: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (14) miente(unicorn, sabado)
   Exit: (14) miente(unicorn, sabado)
   Exit: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, sabado)
   Call: (13) reclama_identidad(persona2, _60444)
   Exit: (13) reclama_identidad(persona2, tweedledee)
   Call: (13) es_consistente_enunciado(persona2, tweedledum, lion, tweedledee, sabado)
   Call: (14) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Call: (15) tweedledum=tweedledee
   Fail: (15) tweedledum=tweedledee
   Fail: (14) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Redo: (13) es_consistente_enunciado(persona2, tweedledum, lion, tweedledee, sabado)
   Call: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Call: (15) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Call: (16) tweedledum=tweedledee
   Fail: (16) tweedledum=tweedledee
   Fail: (15) afirmacion_es_verdadera(persona2, tweedledum, tweedledee)
   Redo: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Exit: (14) afirmacion_es_falsa(persona2, tweedledum, tweedledee)
   Call: (14) miente(lion, sabado)
   Fail: (14) miente(lion, sabado)
   Fail: (13) es_consistente_enunciado(persona2, tweedledum, lion, tweedledee, sabado)
   Redo: (13) dia(_58)
   Exit: (13) dia(domingo)
   Call: (13) reclama_identidad(persona1, _7520)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, domingo)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (15) tweedledee=tweedledum
   Fail: (15) tweedledee=tweedledum
   Fail: (14) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, domingo)
   Call: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Call: (16) tweedledee=tweedledum
   Fail: (16) tweedledee=tweedledum
   Fail: (15) afirmacion_es_verdadera(persona1, tweedledee, tweedledum)
   Redo: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Exit: (14) afirmacion_es_falsa(persona1, tweedledee, tweedledum)
   Call: (14) miente(unicorn, domingo)
   Fail: (14) miente(unicorn, domingo)
   Fail: (13) es_consistente_enunciado(persona1, tweedledee, unicorn, tweedledum, domingo)
   Fail: (12) problema_tweedle(_50, _52, _54, _56, _58)
"""

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
    graph.node(current_node_id, label=f"{name}\\n({veracidad})", fillcolor=fill_color)

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