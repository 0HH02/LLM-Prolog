from typing import List, Optional, Dict, Any
from common.gemini_interface import ask_gemini
from mmrc.promts import generate_successful_response_prompt, _analyze_failure_prompt

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
    
    def analyze_thought_tree(self, solver_result: List[Any], problem_description: str, clauses: List[str], solver_errors: List[str] = None, history: Dict[str, Any] = None) -> Dict[str, Any]:
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

        thought_tree = solver_result["ramas"]
        if thought_tree == [] or thought_tree == "":
            if solver_result["status"] == "success":
                return self._generate_successful_response(solver_result["resultados"], problem_description, clauses, history)
            else:
                return self._analyze_failure(thought_tree, problem_description, clauses, solver_errors, history)
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
            return self._generate_successful_response(successful_branches, problem_description, clauses, history)
        else:
            return self._analyze_failure(thought_tree, problem_description, clauses, solver_errors, history)
    
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
            if "catch(" in branch.valor[0].nombre:
                if branch.valor[0].valor[0].veracidad == "verde":
                    successful_branches.append(branch)
            else:
                if branch.valor[0].veracidad == "verde":
                    successful_branches.append(branch)

        
        return successful_branches

    
    def _generate_successful_response(self, successful_branches_clausule: List[Any], problem_description: str, clauses: List[str], history: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Genera una respuesta argumentada basada en las ramas exitosas.
        
        Args:
            successful_branches: Lista de ramas exitosas
            problem_description: Descripción original del problema
            
        Returns:
            Dict con la respuesta generada
        """
        try:
            successful_branches =[branch.to_dict() for branch in successful_branches_clausule]
        except AttributeError:
            print("Error al convertir las ramas exitosas a diccionarios")
            successful_branches = successful_branches_clausule
        prompt = generate_successful_response_prompt(successful_branches, problem_description, clauses, history["responses"][-1]["content"])
        
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
    
    def _analyze_failure(self, thought_tree: List[Any], problem_description: str, clauses: List[str], solver_errors: List[str] = None, history: Dict[str, Any] = None) -> Dict[str, Any]:
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
        
        prompt = _analyze_failure_prompt(promising_branches_dict, problem_description, clauses, solver_errors)
        
        try:
            response = ask_gemini(prompt)
            
            return {
                "status": "failure_analysis",
                "response": response,
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