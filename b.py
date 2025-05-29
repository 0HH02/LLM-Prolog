# from datasets import load_dataset
# dataset = load_dataset("michaelszx/StepGame")
# for example in dataset['test']:
#     story = example['story']
#     question = example['question']
#     true_label = example['label']
#     k = example['k_hop'] # Puedes usar k_hop para análisis granular
#     print(story)
#     print(question)
#     print(true_label)
#     print(k)
#     break

import re

class DerivationNode:
    def __init__(self, head_clause_instance, depth):
        self.head_clause_instance = head_clause_instance
        self.prolog_rule_str = "N/A (Fact, Built-in, or Undetermined)"
        self.body_clause_instances = []  # List of strings (final instantiated form from their own Exit)
        self.children_nodes = []  # List of DerivationNode objects
        self.depth = depth
        self.status = "Called"  # Called, Success, Fail, Redoing

    def __repr__(self, level=0):
        indent = "  " * level
        res = f"{indent}HEAD ({self.status}, Depth: {self.depth}): {self.head_clause_instance}\n"
        if self.prolog_rule_str != "N/A (Fact, Built-in, or Undetermined)" or self.status == "Success":
             res += f"{indent}RULE: {self.prolog_rule_str}\n"
        if self.body_clause_instances:
            res += f"{indent}BODY_INSTANCES (Derived from successful children):\n"
            for body_item in self.body_clause_instances:
                res += f"{indent}  - {body_item}\n"
        
        # Solo imprimir hijos si este nodo tuvo éxito y tiene hijos que llevaron a ese éxito.
        # O si queremos ver la estructura completa incluso de intentos.
        # Para este caso, nos enfocaremos en la estructura que llevó al éxito.
        if self.children_nodes and self.status in ["Success", "Called", "Redoing"]: # Mostrar hijos si el nodo es exitoso o aún está activo
            res += f"{indent}CHILD_DERIVATIONS ({len(self.children_nodes)}):\n"
            for child in self.children_nodes:
                res += child.__repr__(level + 1)
        elif not self.children_nodes and self.status == "Success" and not self.body_clause_instances and self.prolog_rule_str == "N/A (Fact, Built-in, or Undetermined)":
            # If it's a success, has no children, no explicit body instances, assume it's a fact that was called directly
            # or its rule implies no further traceable sub-goals.
             pass # No explicit children to print in detail beyond body_clause_instances
        return res

def get_predicate_signature_from_string(clause_str):
    """Extrae el functor y la aridad de una cadena de cláusula Prolog."""
    # Manejar unificaciones como predicados especiales
    if ('=' in clause_str or '\\=' in clause_str) and '(' not in clause_str and ')' not in clause_str:
        parts = re.split(r'(=|=\\=)', clause_str)
        if len(parts) == 3: # e.g. term1 = term2
             # Considerar '=' o '\=' como functor
            return parts[1], 2 # Functor es '=', aridad 2
    
    match = re.match(r"([a-zA-Z_0-9\\]+)(?:\((.*)\))?", clause_str)
    if not match:
        # Podría ser un átomo simple o una variable (aunque las variables no suelen ser cabezas de reglas)
        if re.match(r"^[a-z_][a-zA-Z_0-9]*$", clause_str): # Átomo simple
            return clause_str, 0
        return clause_str, 0 # Fallback genérico

    name = match.group(1)
    args_str = match.group(2)

    if args_str is None: # No arguments e.g. predicado
        arity = 0
    elif not args_str.strip(): # e.g. predicado()
        arity = 0
    else:
        # Contar argumentos basado en comas al nivel superior de paréntesis
        balance = 0
        commas = 0
        for char_idx, char in enumerate(args_str):
            if char == '(':
                balance += 1
            elif char == ')':
                balance -= 1
            elif char == ',' and balance == 0:
                commas += 1
        arity = commas + 1
    return name, arity


def parse_prolog_rules(rules_str_list):
    """Parsea una lista de cadenas de reglas Prolog."""
    parsed_rules = {}  # "functor/arity": [ (rule_string, head_template_str, [(body_functor, body_arity)]) ]
    for rule_s in rules_str_list:
        rule_s = rule_s.strip()
        if not rule_s or rule_s.startswith('%'):
            continue

        head_part_str, body_part_str = rule_s.rstrip('.'), None
        if ":-" in rule_s:
            parts = rule_s.rstrip(".").split(":-", 1)
            head_part_str = parts[0].strip()
            body_part_str = parts[1].strip() if len(parts) > 1 else None
        
        head_functor, head_arity = get_predicate_signature_from_string(head_part_str)
        key = f"{head_functor}/{head_arity}"
        
        body_signatures = []
        if body_part_str:
            # Separar metas del cuerpo por coma, ignorando comas dentro de paréntesis
            raw_body_goals = re.split(r',(?![^\(]*\))', body_part_str)
            for goal_str_full in raw_body_goals:
                goal_str = goal_str_full.strip()
                if not goal_str: continue
                
                # Manejar negación como \+ predicado(...)
                is_negated = False
                if goal_str.startswith("\\+"):
                    is_negated = True
                    goal_str = goal_str[2:].strip() # Quitar \+
                    if goal_str.startswith("(") and goal_str.endswith(")"): # Quitar paréntesis externos si los hay
                        goal_str = goal_str[1:-1]
                
                bf, ba = get_predicate_signature_from_string(goal_str)
                body_signatures.append((bf, ba, is_negated)) # Store negation info

        if key not in parsed_rules:
            parsed_rules[key] = []
        parsed_rules[key].append((rule_s, head_part_str, body_signatures))
    return parsed_rules

def find_matching_rule(node, rules_db):
    """Intenta encontrar la regla de Prolog que coincide con un nodo derivado."""
    if not node.status == "Success":
        return "N/A (Not a successful derivation)"

    head_functor, head_arity = get_predicate_signature_from_string(node.head_clause_instance)
    key = f"{head_functor}/{head_arity}"

    if key not in rules_db:
        if not node.children_nodes: # Sin hijos y sin regla, podría ser un hecho o incorporado
            return f"{node.head_clause_instance}." # Representar como un hecho
        return "N/A (No rule found for this predicate signature)"

    candidate_rules = rules_db[key]
    
    # Obtener las signaturas de los hijos exitosos que forman el cuerpo
    # Esto asume que body_clause_instances ya ha sido poblado correctamente en el evento Exit
    successful_children_signatures = []
    for child_clause_str in node.body_clause_instances: # Usar body_clause_instances
        child_functor, child_arity = get_predicate_signature_from_string(child_clause_str)
        # Para la coincidencia de reglas, la negación se maneja por la estructura de la regla, no por el hijo.
        successful_children_signatures.append((child_functor, child_arity, False)) # is_negated=False para comparación directa

    for rule_str, head_template, body_templates_signatures in candidate_rules:
        if len(body_templates_signatures) == len(successful_children_signatures):
            match = True
            # Comparar las signaturas de las metas del cuerpo (ignorando la negación para la estructura)
            for (bf_rule, ba_rule, bn_rule), (bf_child, ba_child, _) in zip(body_templates_signatures, successful_children_signatures):
                if bf_rule != bf_child or ba_rule != ba_child:
                    match = False
                    break
            if match:
                return rule_str
    
    if not node.children_nodes and not node.body_clause_instances: # Sin hijos, sin cuerpo, probablemente un hecho
         for rule_str, _, body_templates_signatures in candidate_rules:
             if not body_templates_signatures : # Es un hecho en la BD de reglas
                 return rule_str
    
    return "N/A (Could not definitively match a rule)"


def build_derivation_tree(trace_str, rules_str_list):
    """Construye el árbol de derivación mostrando cada combinación de variables y aplicación de reglas."""
    parsed_rules = parse_prolog_rules(rules_str_list)
    trace_lines = trace_str.strip().split('\n')
    
    # Regex para parsear las líneas de la traza
    trace_pattern = re.compile(r"^\s*(Call|Exit|Fail|Redo):\s*\((\d+)\)\s*(.*)")

    # Diccionario para mapear depth -> lista de nodos activos en ese nivel
    active_nodes_by_depth = {}  # depth -> [DerivationNode]
    roots = []  # Lista de nodos raíz del árbol
    successful_trees = []  # Lista de árboles que fueron exitosos
    
    def is_builtin_predicate(clause_str):
        """Determina si una cláusula es un predicado built-in (=, \\=, >, <, etc.)"""
        builtin_ops = ['=', '\\\\=', '>', '<', '>=', '=<', 'is', '==', '\\\\==']
        for op in builtin_ops:
            if op in clause_str and '(' not in clause_str.split(op)[0]:
                return True
        return False
    
    def has_variables(clause_str):
        """Determina si una cláusula contiene variables (empiezan con _ o mayúscula)"""
        import re
        return bool(re.search(r'[_A-Z][a-zA-Z0-9_]*', clause_str))
    
    def extract_variables(clause_str):
        """Extrae todas las variables de una cláusula"""
        import re
        return re.findall(r'[_A-Z][a-zA-Z0-9_]*', clause_str)
    
    def get_variable_substitutions(original_clause, instantiated_clause):
        """Obtiene las sustituciones de variables entre dos cláusulas"""
        orig_vars = extract_variables(original_clause)
        if not orig_vars:
            return {}
        
        # Intentar mapear variables a sus valores
        substitutions = {}
        
        # Para operadores de unificación como X=valor
        if '=' in original_clause and '=' in instantiated_clause:
            orig_parts = original_clause.split('=')
            inst_parts = instantiated_clause.split('=')
            if len(orig_parts) == 2 and len(inst_parts) == 2:
                left_orig, right_orig = orig_parts[0].strip(), orig_parts[1].strip()
                left_inst, right_inst = inst_parts[0].strip(), inst_parts[1].strip()
                
                if left_orig in orig_vars and left_orig != left_inst:
                    substitutions[left_orig] = left_inst
                if right_orig in orig_vars and right_orig != right_inst:
                    substitutions[right_orig] = right_inst
        
        # Para predicados normales, intentar mapear por posición
        else:
            # Extraer el predicado y argumentos
            import re
            orig_match = re.match(r"([a-zA-Z_0-9\\\\]+)(?:\\((.*?)\\))?", original_clause)
            inst_match = re.match(r"([a-zA-Z_0-9\\\\]+)(?:\\((.*?)\\))?", instantiated_clause)
            
            if orig_match and inst_match:
                orig_groups = orig_match.groups()
                inst_groups = inst_match.groups()
                
                # Manejar casos donde puede haber 1 o 2 grupos
                orig_pred = orig_groups[0]
                inst_pred = inst_groups[0]
                
                orig_args = orig_groups[1] if len(orig_groups) > 1 and orig_groups[1] else None
                inst_args = inst_groups[1] if len(inst_groups) > 1 and inst_groups[1] else None
                
                if orig_pred == inst_pred and orig_args and inst_args:
                    # Dividir argumentos por comas (simplificado)
                    orig_arg_list = [arg.strip() for arg in orig_args.split(',')]
                    inst_arg_list = [arg.strip() for arg in inst_args.split(',')]
                    
                    if len(orig_arg_list) == len(inst_arg_list):
                        for orig_arg, inst_arg in zip(orig_arg_list, inst_arg_list):
                            if orig_arg in orig_vars and orig_arg != inst_arg:
                                substitutions[orig_arg] = inst_arg
        
        return substitutions
    
    def copy_tree(node):
        """Crea una copia profunda de un árbol de derivación"""
        new_node = DerivationNode(node.head_clause_instance, node.depth)
        new_node.prolog_rule_str = node.prolog_rule_str
        new_node.body_clause_instances = node.body_clause_instances.copy()
        new_node.status = node.status
        
        for child in node.children_nodes:
            new_node.children_nodes.append(copy_tree(child))
        
        return new_node
    
    def find_active_node_for_call(depth, clause_str):
        """Encuentra el nodo activo apropiado para una nueva llamada"""
        # Buscar en profundidades menores para encontrar el padre
        for parent_depth in range(depth - 1, 0, -1):
            if parent_depth in active_nodes_by_depth:
                for node in active_nodes_by_depth[parent_depth]:
                    if node.status in ["Called", "Redoing"]:
                        return node
        return None
    
    def find_matching_node_for_exit(depth, clause_str):
        """Encuentra el nodo que corresponde a un Exit"""
        if depth in active_nodes_by_depth:
            for node in active_nodes_by_depth[depth]:
                if node.status == "Called":
                    # Verificar si es el mismo predicado
                    orig_pred, _ = get_predicate_signature_from_string(node.head_clause_instance)
                    exit_pred, _ = get_predicate_signature_from_string(clause_str)
                    
                    if orig_pred == exit_pred:
                        return node
        return None

    for line_idx, line_content in enumerate(trace_lines):
        line_content = line_content.strip()
        match = trace_pattern.match(line_content)
        if not match:
            continue

        action, depth_str, clause_str = match.groups()
        depth = int(depth_str)
        clause_str = clause_str.strip()

        if action == "Call":
            # Crear un nuevo nodo para esta llamada
            node = DerivationNode(clause_str, depth)
            
            # Encontrar el padre apropiado
            parent = find_active_node_for_call(depth, clause_str)
            
            if parent:
                parent.children_nodes.append(node)
            else:
                # Es un nodo raíz
                roots.append(node)
            
            # Registrar este nodo como activo en su profundidad
            if depth not in active_nodes_by_depth:
                active_nodes_by_depth[depth] = []
            active_nodes_by_depth[depth].append(node)

        elif action == "Exit":
            # Buscar el nodo correspondiente a esta salida exitosa
            matching_node = find_matching_node_for_exit(depth, clause_str)
            
            if matching_node:
                # Marcar como exitoso
                matching_node.status = "Success"
                
                # Si hay sustituciones de variables, crear nodos hijos para mostrarlas
                if has_variables(matching_node.head_clause_instance):
                    substitutions = get_variable_substitutions(matching_node.head_clause_instance, clause_str)
                    
                    if substitutions:
                        # Crear un nodo hijo para cada sustitución significativa
                        for var, value in substitutions.items():
                            subst_clause = f"{var} = {value}"
                            subst_node = DerivationNode(subst_clause, depth + 0.1)
                            subst_node.status = "Success"
                            subst_node.prolog_rule_str = f"{subst_clause}."
                            matching_node.children_nodes.append(subst_node)
                        
                        # Crear un nodo final con la instanciación completa
                        final_node = DerivationNode(clause_str, depth + 0.2)
                        final_node.status = "Success"
                        if is_builtin_predicate(clause_str):
                            final_node.prolog_rule_str = f"{clause_str}."
                        else:
                            final_node.prolog_rule_str = find_matching_rule(final_node, parsed_rules)
                        matching_node.children_nodes.append(final_node)
                    else:
                        # No hay sustituciones obvias, actualizar directamente
                        matching_node.head_clause_instance = clause_str
                else:
                    # Sin variables, actualizar directamente
                    matching_node.head_clause_instance = clause_str
                
                # Determinar la regla Prolog correspondiente
                if is_builtin_predicate(clause_str):
                    matching_node.prolog_rule_str = f"{clause_str}."
                else:
                    matching_node.prolog_rule_str = find_matching_rule(matching_node, parsed_rules)
                
                # Si este es un nodo raíz exitoso, guardarlo
                if matching_node in roots and matching_node.status == "Success":
                    successful_tree = copy_tree(matching_node)
                    successful_trees.append(successful_tree)

        elif action == "Fail":
            # Buscar el nodo correspondiente a esta falla
            matching_node = None
            
            if depth in active_nodes_by_depth:
                for node in active_nodes_by_depth[depth]:
                    if node.status in ["Called", "Redoing", "Success"]:
                        orig_pred, _ = get_predicate_signature_from_string(node.head_clause_instance)
                        fail_pred, _ = get_predicate_signature_from_string(clause_str)
                        
                        if orig_pred == fail_pred:
                            matching_node = node
                            break
            
            if matching_node:
                # Si hay variables y la instanciación es diferente, crear nodo hijo para el fallo
                if has_variables(matching_node.head_clause_instance) and matching_node.head_clause_instance != clause_str:
                    fail_node = DerivationNode(clause_str, depth + 0.3)
                    fail_node.status = "Fail"
                    matching_node.children_nodes.append(fail_node)
                
                # Marcar el nodo como fallido
                matching_node.status = "Fail"

        elif action == "Redo":
            # Buscar el nodo correspondiente a este reintento
            matching_node = None
            
            if depth in active_nodes_by_depth:
                for node in active_nodes_by_depth[depth]:
                    orig_pred, _ = get_predicate_signature_from_string(node.head_clause_instance)
                    redo_pred, _ = get_predicate_signature_from_string(clause_str)
                    
                    if orig_pred == redo_pred:
                        matching_node = node
                        break
            
            if matching_node:
                matching_node.status = "Redoing"
    
    # Devolver los árboles exitosos o los que están actualmente exitosos
    if successful_trees:
        return successful_trees
    else:
        successful_roots = [node for node in roots if node.status == "Success"]
        return successful_roots

# ---- Ejemplo de Uso ----
# (La traza y las reglas son muy largas para incluirlas directamente aquí,
#  se cargarían desde variables o archivos como en el ejemplo de la pregunta)

# Ejemplo de traza (muy abreviado para demostración)
ejemplo_traza_corta = """
   Call: (12) problema_tweedle(_1, _2, _3, _4, _5)
   Call: (13) _1=tweedledum
   Exit: (13) tweedledum=tweedledum
   Call: (13) _2=tweedledee
   Exit: (13) tweedledee=tweedledee
   Call: (13) tweedledum\=tweedledee
   Exit: (13) tweedledum\=tweedledee
   Call: (13) _3=lion
   Exit: (13) lion=lion
   Call: (13) _4=unicorn
   Exit: (13) unicorn=unicorn
   Call: (13) lion\=unicorn
   Exit: (13) lion\=unicorn
   Call: (13) dia(_5)
   Exit: (13) dia(jueves)
   Call: (13) reclama_identidad(persona1, _100)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, jueves)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(lion, jueves)
   Exit: (14) dice_verdad(lion, jueves)
   Exit: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, jueves)
   Call: (13) reclama_identidad(persona2, _200)
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
   Fail: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, jueves)
   Redo: (13) dia(_5)
   Exit: (13) dia(domingo)
   Call: (13) reclama_identidad(persona1, _300)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Call: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, domingo)
   Call: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (15) tweedledum=tweedledum
   Exit: (15) tweedledum=tweedledum
   Exit: (14) afirmacion_es_verdadera(persona1, tweedledum, tweedledum)
   Call: (14) dice_verdad(lion, domingo)
   Exit: (14) dice_verdad(lion, domingo)
   Exit: (13) es_consistente_enunciado(persona1, tweedledum, lion, tweedledum, domingo)
   Call: (13) reclama_identidad(persona2, _400)
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
"""

ejemplo_reglas = [
    "afirmacion_es_verdadera(Persona, IdentidadReal, IdentidadReclamada) :- IdentidadReal = IdentidadReclamada.",
    "afirmacion_es_falsa(Persona, IdentidadReal, IdentidadReclamada) :- \\+ afirmacion_es_verdadera(Persona, IdentidadReal, IdentidadReclamada).",
    "es_consistente_enunciado(Persona, IdentidadReal, TipoPersona, IdentidadReclamada, Dia) :- afirmacion_es_verdadera(Persona, IdentidadReal, IdentidadReclamada), dice_verdad(TipoPersona, Dia).",
    "es_consistente_enunciado(Persona, IdentidadReal, TipoPersona, IdentidadReclamada, Dia) :- afirmacion_es_falsa(Persona, IdentidadReal, IdentidadReclamada), miente(TipoPersona, Dia).",
    "problema_tweedle(Identidad1, Identidad2, Tipo1, Tipo2, DiaEncuentro) :- (Identidad1 = tweedledum, Identidad2 = tweedledee ; Identidad1 = tweedledee, Identidad2 = tweedledum), Identidad1 \\= Identidad2, (Tipo1 = lion, Tipo2 = unicorn ; Tipo1 = unicorn, Tipo2 = lion), Tipo1 \\= Tipo2, dia(DiaEncuentro), reclama_identidad(persona1, Reclama1), es_consistente_enunciado(persona1, Identidad1, Tipo1, Reclama1, DiaEncuentro), reclama_identidad(persona2, Reclama2), es_consistente_enunciado(persona2, Identidad2, Tipo2, Reclama2, DiaEncuentro).",
    "dice_verdad(lion, jueves).", # Hecho para test
    "dice_verdad(lion, domingo).", # Hecho para test
    "dice_verdad(unicorn, domingo).", # Hecho para test
    "dia(jueves).", # Hecho para test
    "dia(domingo).", # Hecho para test
    "reclama_identidad(persona1, tweedledum).", # Hecho para test
    "reclama_identidad(persona2, tweedledee).", # Hecho para test
    "miente(Tipo, Dia) :- \\+ dice_verdad(Tipo, Dia)." # Regla adicional para test
]

# Usar la traza y reglas completas proporcionadas por el usuario
trace_completa_usuario = """
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
reglas_completas_usuario = [
"afirmacion_es_verdadera(Persona, IdentidadReal, IdentidadReclamada) :- IdentidadReal = IdentidadReclamada.",
"afirmacion_es_falsa(Persona, IdentidadReal, IdentidadReclamada) :- \\+ afirmacion_es_verdadera(Persona, IdentidadReal, IdentidadReclamada).",
"es_consistente_enunciado(Persona, IdentidadReal, TipoPersona, IdentidadReclamada, Dia) :- afirmacion_es_verdadera(Persona, IdentidadReal, IdentidadReclamada), dice_verdad(TipoPersona, Dia).",
"es_consistente_enunciado(Persona, IdentidadReal, TipoPersona, IdentidadReclamada, Dia) :- afirmacion_es_falsa(Persona, IdentidadReal, IdentidadReclamada), miente(TipoPersona, Dia).",
"problema_tweedle(Identidad1, Identidad2, Tipo1, Tipo2, DiaEncuentro) :- (Identidad1 = tweedledum, Identidad2 = tweedledee ; Identidad1 = tweedledee, Identidad2 = tweedledum), Identidad1 \\= Identidad2, (Tipo1 = lion, Tipo2 = unicorn ; Tipo1 = unicorn, Tipo2 = lion), Tipo1 \\= Tipo2, dia(DiaEncuentro), reclama_identidad(persona1, Reclama1), es_consistente_enunciado(persona1, Identidad1, Tipo1, Reclama1, DiaEncuentro), reclama_identidad(persona2, Reclama2), es_consistente_enunciado(persona2, Identidad2, Tipo2, Reclama2, DiaEncuentro).",
"dice_verdad(lion, jueves).", # Hecho para test
"dice_verdad(lion, domingo).", # Hecho para test
"dice_verdad(unicorn, domingo).", # Hecho para test
"dia(jueves).", # Hecho para test
"dia(domingo).", # Hecho para test
"reclama_identidad(persona1, tweedledum).", # Hecho para test
"reclama_identidad(persona2, tweedledee).", # Hecho para test
"miente(Tipo, Dia) :- \\+ dice_verdad(Tipo, Dia)." # Regla adicional para test
]

trace = f"""
Call: (12) mortal(_4664)
Call: (13) humano(_4664)
Exit: (13) humano(socrates)
Exit: (12) mortal(socrates)
Call: (12) fail
Fail: (12) fail"""

reglas = [
    "mortal(X) :- humano(X).",
    "humano(socrates)."
]


print("\n\n--- Árbol de Derivación (Traza Completa del Usuario) ---")
arboles_exitosos_completo = build_derivation_tree(trace, reglas)
for arbol_raiz in arboles_exitosos_completo:
    print(arbol_raiz)


import graphviz

def _agregar_nodos_y_aristas_grafo_modificado(deriv_node, dot_graph, parent_node_id_str=None, visited_node_ids=None):
    """
    Función auxiliar recursiva para añadir nodos y aristas al objeto Digraph.
    Etiquetas muestran reglas/hechos completos. Nodos fallidos en rojo.
    """
    if visited_node_ids is None:
        visited_node_ids = set()

    current_node_id_str = str(id(deriv_node))

    if current_node_id_str in visited_node_ids:
        if parent_node_id_str:
            dot_graph.edge(parent_node_id_str, current_node_id_str)
        return

    node_label = _determinar_etiqueta_nodo_mejorado(deriv_node)
    
    node_attrs = {'label': node_label}
    if deriv_node.status == "Fail":
        node_attrs['color'] = "red"
        node_attrs['style'] = "filled"
        node_attrs['fillcolor'] = "lightpink"
    elif deriv_node.status == "Redoing":
        node_attrs['color'] = "orange"
        node_attrs['style'] = "filled"
        node_attrs['fillcolor'] = "lightyellow"
    elif deriv_node.status == "Success":
        node_attrs['color'] = "green"
        node_attrs['style'] = "filled"
        node_attrs['fillcolor'] = "lightgreen"
    # 'Called' status will use default node attributes

    dot_graph.node(current_node_id_str, **node_attrs)
    visited_node_ids.add(current_node_id_str)

    if parent_node_id_str:
        dot_graph.edge(parent_node_id_str, current_node_id_str)

    # Solo expandir hijos si el nodo actual no falló.
    # Si queremos ver la estructura de búsqueda completa incluso para fallos,
    # se podría quitar la condición `deriv_node.status != "Fail"`.
    # Pero para un árbol de "cómo se intentó/logró", los hijos de un fallo no son tan relevantes.
    if deriv_node.status != "Fail":
        for child_deriv_node in deriv_node.children_nodes:
            _agregar_nodos_y_aristas_grafo_modificado(child_deriv_node, dot_graph, current_node_id_str, visited_node_ids)


# Nuevas funciones de visualización mejoradas
def _determinar_etiqueta_nodo_mejorado(deriv_node):
    """Determina la etiqueta para el nodo del grafo, adaptado para mostrar variables e instanciaciones."""
    
    def has_variables(clause_str):
        """Determina si una cláusula contiene variables (empiezan con _ o mayúscula)"""
        import re
        return bool(re.search(r'[_A-Z][a-zA-Z0-9_]*', clause_str))
    
    def is_instantiation_node(deriv_node):
        """Determina si es un nodo de instanciación (depth fraccionario)"""
        return isinstance(deriv_node.depth, float)
    
    # Para nodos de instanciación, mostrar la instanciación específica
    if is_instantiation_node(deriv_node):
        if deriv_node.status == "Success":
            if deriv_node.prolog_rule_str and not deriv_node.prolog_rule_str.startswith("N/A"):
                return f"✓ {deriv_node.head_clause_instance}"
            else:
                return f"✓ {deriv_node.head_clause_instance}"
        elif deriv_node.status == "Fail":
            return f"✗ {deriv_node.head_clause_instance}"
        else:
            return f"? {deriv_node.head_clause_instance}"
    
    # Para nodos con variables (nodos originales)
    if has_variables(deriv_node.head_clause_instance):
        if deriv_node.status == "Success":
            return f"🔍 {deriv_node.head_clause_instance}"
        elif deriv_node.status == "Fail":
            return f"❌ {deriv_node.head_clause_instance}"
        elif deriv_node.status == "Redoing":
            return f"🔄 {deriv_node.head_clause_instance}"
        else:
            return f"📞 {deriv_node.head_clause_instance}"
    
    # Para nodos sin variables (hechos directos)
    if deriv_node.status == "Success":
        if deriv_node.prolog_rule_str and not deriv_node.prolog_rule_str.startswith("N/A"):
            return deriv_node.prolog_rule_str
        else:
            if not deriv_node.children_nodes:  # Es una hoja
                if deriv_node.head_clause_instance.endswith('.'):
                    return deriv_node.head_clause_instance
                else:
                    return f"{deriv_node.head_clause_instance}."
            else:
                return deriv_node.head_clause_instance
    elif deriv_node.status in ["Fail", "Redoing", "Called"]:
        return deriv_node.head_clause_instance
    else:
        return deriv_node.head_clause_instance

def _agregar_nodos_y_aristas_grafo_mejorado(deriv_node, dot_graph, parent_node_id_str=None, visited_node_ids=None):
    """
    Función auxiliar recursiva para añadir nodos y aristas al objeto Digraph.
    Adaptada para manejar nodos con variables e instanciaciones.
    """
    if visited_node_ids is None:
        visited_node_ids = set()

    current_node_id_str = str(id(deriv_node))

    if current_node_id_str in visited_node_ids:
        if parent_node_id_str:
            dot_graph.edge(parent_node_id_str, current_node_id_str)
        return

    node_label = _determinar_etiqueta_nodo_mejorado(deriv_node)
    
    def has_variables(clause_str):
        import re
        return bool(re.search(r'[_A-Z][a-zA-Z0-9_]*', clause_str))
    
    def is_instantiation_node(deriv_node):
        return isinstance(deriv_node.depth, float)
    
    # Determinar atributos del nodo basado en tipo y estado
    node_attrs = {'label': node_label}
    
    if is_instantiation_node(deriv_node):
        # Nodos de instanciación - formas más pequeñas
        node_attrs['shape'] = 'ellipse'
        if deriv_node.status == "Success":
            node_attrs['color'] = "darkgreen"
            node_attrs['style'] = "filled"
            node_attrs['fillcolor'] = "lightgreen"
        elif deriv_node.status == "Fail":
            node_attrs['color'] = "darkred"
            node_attrs['style'] = "filled"
            node_attrs['fillcolor'] = "lightpink"
        else:
            node_attrs['color'] = "gray"
            node_attrs['style'] = "filled"
            node_attrs['fillcolor'] = "lightgray"
    elif has_variables(deriv_node.head_clause_instance):
        # Nodos con variables - formas rectangulares
        node_attrs['shape'] = 'box'
        if deriv_node.status == "Success":
            node_attrs['color'] = "blue"
            node_attrs['style'] = "filled"
            node_attrs['fillcolor'] = "lightblue"
        elif deriv_node.status == "Fail":
            node_attrs['color'] = "red"
            node_attrs['style'] = "filled"
            node_attrs['fillcolor'] = "mistyrose"
        elif deriv_node.status == "Redoing":
            node_attrs['color'] = "orange"
            node_attrs['style'] = "filled"
            node_attrs['fillcolor'] = "lightyellow"
        else:  # Called
            node_attrs['color'] = "purple"
            node_attrs['style'] = "filled"
            node_attrs['fillcolor'] = "lavender"
    else:
        # Nodos sin variables (hechos) - formas hexagonales
        node_attrs['shape'] = 'hexagon'
        if deriv_node.status == "Success":
            node_attrs['color'] = "green"
            node_attrs['style'] = "filled"
            node_attrs['fillcolor'] = "lightgreen"
        elif deriv_node.status == "Fail":
            node_attrs['color'] = "red"
            node_attrs['style'] = "filled"
            node_attrs['fillcolor'] = "lightpink"
        else:
            node_attrs['color'] = "gray"
            node_attrs['style'] = "filled"
            node_attrs['fillcolor'] = "lightgray"

    dot_graph.node(current_node_id_str, **node_attrs)
    visited_node_ids.add(current_node_id_str)

    if parent_node_id_str:
        # Diferentes estilos de aristas según el tipo de relación
        edge_attrs = {}
        if is_instantiation_node(deriv_node):
            edge_attrs['style'] = 'dashed'
            edge_attrs['color'] = 'blue'
            edge_attrs['label'] = 'instancia'
        else:
            edge_attrs['style'] = 'solid'
            edge_attrs['color'] = 'black'
        
        dot_graph.edge(parent_node_id_str, current_node_id_str, **edge_attrs)

    # Expandir todos los hijos para mostrar la estructura completa
    for child_deriv_node in deriv_node.children_nodes:
        _agregar_nodos_y_aristas_grafo_mejorado(child_deriv_node, dot_graph, current_node_id_str, visited_node_ids)

def visualizar_arbol_derivacion_con_variables(arbol_nodos_raiz, nombre_grafo="ArbolDerivacionConVariables"):
    """
    Crea un objeto graphviz.Digraph que muestra claramente variables e instanciaciones.
    
    Args:
        arbol_nodos_raiz: Un solo objeto DerivationNode raíz o una lista de ellos.
        nombre_grafo: Nombre para el grafo generado.
        
    Returns:
        Un objeto graphviz.Digraph.
    """
    if not isinstance(arbol_nodos_raiz, list):
        arbol_nodos_raiz = [arbol_nodos_raiz]

    dot = graphviz.Digraph(name=nombre_grafo, comment='Árbol de Derivación con Variables e Instanciaciones')
    dot.attr(rankdir='TB')
    dot.attr('graph', splines='ortho', nodesep='0.5', ranksep='0.8')
    dot.attr('node', fontname='Arial', fontsize='10')
    dot.attr('edge', fontname='Arial', fontsize='8')

    visited_node_ids_global = set()

    for raiz_node in arbol_nodos_raiz:
        if raiz_node:
            _agregar_nodos_y_aristas_grafo_mejorado(raiz_node, dot, visited_node_ids=visited_node_ids_global)
            
    return dot

grafo_visual = visualizar_arbol_derivacion_con_variables(arboles_exitosos_completo) 
try:
    grafo_visual.render('arbol_derivacion_prolog', view=False, format='png')
    print("Grafo guardado como arbol_derivacion_prolog.png")
    print("El grafo muestra:")
    print("  🔍 Nodos con variables (rectangulares, azules)")
    print("  ✓ Nodos de instanciación (elípticos, verdes)")
    print("  ⬢ Nodos de hechos (hexagonales)")
    print("  → Aristas sólidas para relaciones padre-hijo")
    print("  ⇢ Aristas punteadas para instanciaciones")
except Exception as e:
    print(f"Error al renderizar el grafo: {e}")
    print("Asegúrate de que Graphviz esté instalado y en el PATH del sistema.")