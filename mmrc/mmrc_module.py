from typing import List, Optional, Dict, Any
from common.gemini_interface import ask_gemini
import json
from pathlib import Path
from graphviz import Digraph



class MetaCognitionKnowledgeRefinementModule:
    """
    Módulo de Meta-cognición y Refinamiento del Conocimiento (MMRC)
    
    Analiza los resultados del árbol de pensamientos de MISA-J y:
    1. Si hay ramas exitosas: Formula una respuesta argumentada
    2. Si no hay éxitos: Analiza errores en premisas o lógica
    """
    
    def __init__(self):
        pass

    def _create_thought_graph(self, data, graph=None, parent_id=None, node_counter=[0]):
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
                self._create_thought_graph(child, graph, current_node_id, node_counter)

        return graph
    
    def analyze_thought_tree(self, thought_tree: List[Any], problem_description: str, clauses: List[str], solver_errors: List[str] = None) -> Dict[str, Any]:
        """
        Analiza el árbol de pensamientos y genera una respuesta o análisis de errores.
        
        Args:
            thought_tree: Lista de objetos Clausula que representan las ramas de pensamiento
            problem_description: Descripción original del problema
            clauses: Lista de cláusulas usadas en el problema
            solver_errors: Lista opcional de errores ocurridos durante la ejecución del solver
            
        Returns:
            Dict con el análisis y la respuesta generada
        """
        # Verificar si hay ramas exitosas

        successful_branches = self._find_successful_branches(thought_tree)
        
        if successful_branches:
            solutions_dir = Path("solutions")
            success_dir = solutions_dir / "success"
            fails_dir = solutions_dir / "fails"

            for i, arbol_pensamiento in enumerate(thought_tree):
                # Convertir el árbol a diccionario
                arbol_dict = arbol_pensamiento.to_dict()
                
                # Determinar la carpeta basada en la veracidad del primer nodo
                target_dir = success_dir if arbol_pensamiento.valor[0].veracidad == "verde" else fails_dir
                
                # Generar y guardar el gráfico
                dot = self._create_thought_graph(arbol_dict)
                dot.render(str(target_dir / f'arbol_pensamiento_{i}'), view=False, cleanup=True)
            return self._generate_successful_response(successful_branches, problem_description, clauses)
        else:
            return self._analyze_failure(thought_tree, problem_description, clauses, solver_errors)
    
    def _find_successful_branches(self, thought_tree: List[Any]) -> List[Any]:
        """
        Encuentra las ramas exitosas en el árbol de pensamientos.
        
        Args:
            thought_tree: Lista de objetos Clausula
            
        Returns:
            Lista de ramas exitosas (con veracidad "verde")
        """
        successful_branches = []
        for branch in thought_tree:
            if branch.valor[0].veracidad == "verde":
                successful_branches.append(branch)

        
        return successful_branches

    
    def _generate_successful_response(self, successful_branches_clausule: List[Any], problem_description: str, clauses: List[str]) -> Dict[str, Any]:
        """
        Genera una respuesta argumentada basada en las ramas exitosas.
        
        Args:
            successful_branches: Lista de ramas exitosas
            problem_description: Descripción original del problema
            
        Returns:
            Dict con la respuesta generada
        """
        successful_branches =[branch.to_dict() for branch in successful_branches_clausule]
        prompt = f"""
Como experto en lógica y razonamiento, necesito que analices el siguiente problema y su solución:

PROBLEMA ORIGINAL:
{problem_description}

CLAUSULAS USADAS:
{clauses}

RAMAS DE PENSAMIENTOS EXITOSAS:
{json.dumps(successful_branches, indent=2, ensure_ascii=False)}

INSTRUCCIONES:
1. Analiza las ramas de pensamientos que llevaron a una solución exitosa
2. Formula una respuesta bien argumentada y clara al problema original
3. Explica paso a paso cómo se llegó a esta solución
4. Asegúrate de que la respuesta sea comprensible para alguien sin conocimientos técnicos de lógica formal

Por favor, proporciona una respuesta estructurada que incluya:
- La respuesta directa al problema
- La justificación lógica paso a paso
- Una explicación clara del razonamiento utilizado
- Un resumen siendo contundente y breve con la pregunta que se te presentó al principio.
"""
        
        try:
            response = ask_gemini(prompt)
            return {
                "status": "success",
                "response": response,
                "successful_branches_count": len(successful_branches),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "successful_branches_count": len(successful_branches)
            }
    
    def _analyze_failure(self, thought_tree: List[Any], problem_description: str, clauses: List[str], solver_errors: List[str] = None) -> Dict[str, Any]:
        """
        Analiza por qué no se encontró una solución y sugiere mejoras.
        
        Args:
            thought_tree: Lista completa del árbol de pensamientos
            problem_description: Descripción original del problema
            clauses: Lista de cláusulas usadas en el problema
            solver_errors: Lista opcional de errores ocurridos durante la ejecución del solver
            
        Returns:
            Dict con el análisis de errores y sugerencias
        """
        # Encontrar las ramas con mayor potencial (más profundas o con más nodos verdes)
        promising_branches = self._find_most_promising_branches(thought_tree, max_branches=20)
        
        # Convertir las ramas más prometedoras a diccionarios
        promising_branches_dict = [branch.to_dict() for branch in promising_branches]
        
        # Agregar información de errores del solver si están disponibles
        solver_error_section = ""
        if solver_errors:
            solver_error_section = f"""
ERRORES DEL SOLVER DETECTADOS:
{chr(10).join(f"- {error}" for error in solver_errors)}
"""
        
        prompt = f"""
Como experto en lógica y razonamiento, necesito que analices por qué no se pudo resolver el siguiente problema:

PROBLEMA ORIGINAL:
{problem_description}

CLAUSULAS USADAS:
{clauses}
{solver_error_section}
RAMAS DE PENSAMIENTO MÁS PROMETEDORAS:
{json.dumps(promising_branches_dict, indent=2, ensure_ascii=False)}

CONTEXTO:
El sistema de razonamiento lógico no pudo encontrar una solución exitosa. Todas las ramas de pensamiento terminaron sin éxito.
{f"Además, se detectaron errores durante la ejecución del solver que pueden haber afectado el proceso de razonamiento." if solver_errors else ""}

INSTRUCCIONES:
1. Analiza las ramas de pensamiento que más se acercaron al éxito
2. Identifica posibles errores en:
   - Las premisas del problema (¿faltan premisas importantes?)
   - Las premisas formuladas (¿hay premisas incorrectas o mal interpretadas?)
   - La lógica implementada (¿hay problemas en el razonamiento?)
   - Inconsistencias o contradicciones en las premisas
   {f"- Errores técnicos del solver que pudieron haber impedido una resolución exitosa" if solver_errors else ""}

3. Proporciona sugerencias específicas para:
   - Premisas que podrían estar faltando
   - Premisas que podrían estar mal formuladas
   - Mejoras en la lógica de razonamiento
   - Resolución de inconsistencias
   {f"- Soluciones para los errores técnicos detectados" if solver_errors else ""}

Por favor, proporciona un análisis estructurado que incluya:
- Diagnóstico del problema principal
- Análisis detallado de las ramas más prometedoras
{f"- Análisis de los errores técnicos del solver" if solver_errors else ""}
- Sugerencias específicas de mejora
- Recomendaciones para futuras iteraciones
"""
        
        try:
            response = ask_gemini(prompt)
            return {
                "status": "failure_analysis",
                "analysis": response,
                "total_branches": len(thought_tree),
                "promising_branches_count": len(promising_branches),
                "promising_branches": promising_branches_dict
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "total_branches": len(thought_tree)
            }
    
    def _find_most_promising_branches(self, thought_tree: List[Any], max_branches: int = 1) -> List[Any]:
        """
        Encuentra las ramas más prometedoras (aquellas que llegaron más lejos o tuvieron más éxito parcial).
        
        Args:
            thought_tree: Lista completa del árbol de pensamientos
            max_branches: Número máximo de ramas a retornar
            
        Returns:
            Lista de las ramas más prometedoras
        """
        scored_branches = []
        
        for branch in thought_tree:
            score = self._calculate_branch_promise_score(branch)
            scored_branches.append((branch, score))
        
        # Ordenar por puntuación (mayor a menor)
        scored_branches.sort(key=lambda x: x[1], reverse=True)
        
        # Retornar las mejores ramas (hasta max_branches)
        return [branch for branch, _ in scored_branches[:max_branches]]
    
    def _calculate_branch_promise_score(self, branch: Any) -> float:
        """
        Calcula una puntuación que indica qué tan prometedora es una rama.
        
        Args:
            branch: Objeto Clausula que representa una rama
            
        Returns:
            Puntuación de la rama (mayor es mejor)
        """
        # Contar la profundidad de la rama
        depth = self._calculate_depth(branch)
        
        # Contar nodos con veracidad "verde"
        green_nodes = self._count_green_nodes(branch)
        
        return depth * green_nodes
    
    def _calculate_depth(self, node: Any) -> int:
        """
        Calcula la profundidad máxima de un nodo.
        
        Args:
            node: Objeto Clausula
            
        Returns:
            Profundidad máxima del árbol
        """
        if not hasattr(node, 'valor') or not node.valor:
            return 1
        
        max_child_depth = 0
        for child in node.valor:
            child_depth = self._calculate_depth(child)
            max_child_depth = max(max_child_depth, child_depth)
        
        return 1 + max_child_depth
    
    def _count_green_nodes(self, node: Any) -> int:
        """
        Cuenta los nodos con veracidad "verde" en un árbol.
        
        Args:
            node: Objeto Clausula
            
        Returns:
            Número de nodos verdes
        """
        count = 0
        
        if hasattr(node, 'veracidad') and node.veracidad == "verde":
            count += 1
        
        if hasattr(node, 'valor') and node.valor:
            for child in node.valor:
                count += self._count_green_nodes(child)
        
        return count