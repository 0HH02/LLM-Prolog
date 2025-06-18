import importlib.util
import os
from typing import List, Dict, Optional

from mfsa.promts import extract_problem_clauses_promt
from common.gemini_interface import ask_gemini_json

class KnowledgeRepresentationStore:
    def __init__(self):
        self.base_axioms: List[str] = []
        self.problem_clauses: List[str] = []
        self.goal_clauses: List[str] = [] # Podría ser una sola, pero lo dejamos como lista por flexibilidad
    
    def _llm_kge_extract_problem_clauses(self, problem_description_nl: str, problem_reformulation: str) -> List[str]:
        """Extrae cláusulas (hechos y reglas) específicas del problema."""
        all_clauses = []

        problem_clauses_prompt = extract_problem_clauses_promt(problem_description_nl, problem_reformulation)
        
        config = {
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "facts": {"type": "array", "items": {"type": "string"}},
                        "rules": {"type": "array", "items": {"type": "string"}},
                        "objetive": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["facts", "rules", "objetive"]
                }
            }
        response = ask_gemini_json(problem_clauses_prompt, config=config)
        
        facts = response["facts"]
        rules = response["rules"]

        for fact in facts:
            all_clauses.append(fact.replace("//", "/"))

        for rule in rules:
            all_clauses.append(rule.replace("//", "/"))

        objective = response["objetive"][0].replace("//", "/")

        return all_clauses, objective

    def update(self, problem_description: str, preview_response: str):
        self.clear_all()
        problem_clauses_extracted, objetive = self._llm_kge_extract_problem_clauses(problem_description, preview_response)
        for pc in problem_clauses_extracted:
            self.add_clause(pc, "problem_clause")
        self.add_clause(objetive, "goal_clause")
        print(f"MFSA: Cláusulas del Problema Extraídas: {len(problem_clauses_extracted)}")
        return problem_clauses_extracted, objetive

    def _get_target_list_by_category(self, category: str) -> Optional[List[str]]:
        """Helper interno para obtener la lista de cláusulas correcta por categoría."""
        if category == "base_axiom":
            return self.base_axioms
        elif category == "problem_clause":
            return self.problem_clauses
        elif category == "goal_clause":
            return self.goal_clauses
        print(f"KR-Store Warning: Categoría desconocida '{category}' en _get_target_list_by_category.")
        return None

    def add_clause(self, clause: str, category: str):
        """
        Añade una cláusula a la categoría especificada.
        Categorías: "base_axiom", "problem_clause", "goal_clause"
        """
        target_list = self._get_target_list_by_category(category)
        if target_list is None:
            # El warning ya se imprimió en _get_target_list_by_category
            # Opcionalmente, lanzar un error aquí si se prefiere un fallo duro
            print(f"KR-Store Error: No se pudo añadir cláusula a categoría desconocida '{category}'.")
            return

        if clause not in target_list: # Evitar duplicados exactos
            target_list.append(clause)
        else:
            print(f"Info KR-Store: Cláusula duplicada no añadida a {category}: {clause}")

    def get_all_clauses(self) -> List[str]:
        return self.base_axioms + self.problem_clauses + self.goal_clauses

    def get_clauses_by_category(self, category: str) -> List[str]:
        target_list = self._get_target_list_by_category(category)
        if target_list is not None:
            return list(target_list) # Devuelve una copia
        # raise ValueError(f"Categoría desconocida: {category}") # Opcional: Fallar duro
        return [] # Devolver lista vacía si la categoría es incorrecta después del warning

    def remove_clause_by_string(self, clause_str: str, category: str) -> bool:
        """Elimina la primera ocurrencia de una cláusula que coincida con el string dado en la categoría especificada."""
        target_list = self._get_target_list_by_category(category)
        if target_list is None:
            return False
        
        initial_len = len(target_list)
        # Es más seguro construir una nueva lista que modificarla mientras se itera
        # o encontrar el índice y usar pop, pero str() puede no ser único si no se incluyen IDs/fuentes.
        # Esta implementación simple busca por la representación de string exacta.
        new_list = [c for c in target_list if str(c) != clause_str]
        
        if len(new_list) < initial_len:
            if category == "base_axiom": self.base_axioms = new_list
            elif category == "problem_clause": self.problem_clauses = new_list
            elif category == "goal_clause": self.goal_clauses = new_list
            return True
        return False

    def get_clause_by_string(self, clause_str: str, category: str) -> Optional[str]:
        """Obtiene la primera ocurrencia de una cláusula que coincida con el string en la categoría especificada."""
        target_list = self._get_target_list_by_category(category)
        if target_list is not None:
            for c_obj in target_list:
                if str(c_obj) == clause_str:
                    return c_obj
        return None

    def clear_category(self, category: str):
        target_list = self._get_target_list_by_category(category)
        if target_list is not None:
            target_list.clear()
        else:
            # ValueError ya se maneja o se imprime warning en _get_target_list_by_category
            pass # No hacer nada si la categoría es inválida
    
    def clear_all(self):
        self.base_axioms.clear()
        self.problem_clauses.clear()
        self.goal_clauses.clear()

    def __str__(self):
        return (f"KR-Store:\n"
                f"  Axiomas Base: {len(self.base_axioms)}\n"
                f"  Cláusulas del Problema: {len(self.problem_clauses)}\n"
                f"  Cláusulas Objetivo: {len(self.goal_clauses)}")
    
    def print_all(self):
        print(f"\n--- Cláusulas Extraídas ---")
        print("\nCláusulas Objetivo:")
        for clause in self.get_clauses_by_category("goal_clause"):
            print(f"- {clause}")
            
        print("\nCláusulas del Problema:")
        for clause in self.get_clauses_by_category("problem_clause"):
            print(f"- {clause}")
            
        print("\nAxiomas Base:")
        for clause in self.get_clauses_by_category("base_axiom"):
            print(f"- {clause}")

        print(f"--- Formalización Completada ---")
        print(self)

    
# Ejemplo de módulos axiomáticos predefinidos (podrían estar en archivos JSON/YAML)
PREDEFINED_AXIOM_MODULES = {
    "logica_basica": [
        "implica(A, B) :- not(A), B.", # Esto no es Horn estándar, ejemplo de lo que el LLM podría generar
        "equivalente(A, B) :- implica(A, B), implica(B, A).",
        # Cláusulas de Horn reales serían más como:
        # "modus_ponens_aplicable(Conclusion, Premisa, Implicacion) :- es_verdad(Premisa), tiene_forma(Implicacion, Premisa, Conclusion)."
        # O, más directamente en lógica de objetos:
        "enfriar(X) :- poner_en_nevera(X)." # Ejemplo simple
    ],
    "relaciones_familiares": [
        "ancestro(X, Y) :- padre(X, Y).",
        "ancestro(X, Y) :- padre(X, Z), ancestro(Z, Y)."
    ]
}