from typing import List, Dict, Any, Optional
from mfsa.kr_store import KnowledgeRepresentationStore
from common.gemini_interface import ask_gemini, ask_gemini_json
from ohi.promts import extract_clauses_from_prolog_promt, generate_refined_analysis_promt
import re


class HeuristicInferenceOrchestrator:
    """
    Orquestador Heurístico de Inferencia (OHI) v1.1
    
    Responsable de refinar el conocimiento cuando no se encuentran soluciones exitosas,
    usando el análisis del MMRC para proponer nuevas cláusulas y mejorar la representación
    del conocimiento.
    """
    
    def __init__(self):
        pass
    
    def refine_knowledge(self, 
                        mmrc_analysis: Dict[str, Any], 
                        problem_description: str, 
                        current_clauses: List[str]) -> KnowledgeRepresentationStore:
        """
        Refina el conocimiento basándose en el análisis de fallas del MMRC.
        
        Args:
            mmrc_analysis: Resultado del análisis del MMRC
            problem_description: Descripción original del problema
            current_clauses: Cláusulas actuales que no lograron resolver el problema
            current_kr_store: KR Store actual
            
        Returns:
            Nuevo KR Store con cláusulas refinadas
        """
        
        # Paso 1: Generar nuevo análisis del problema considerando el feedback del MMRC
        refined_analysis = self._generate_refined_analysis(
            mmrc_analysis, problem_description, current_clauses
        )

        # Paso 3: Extraer nuevas cláusulas del código Prolog propuesto
        new_clauses, objetive = self._extract_clauses_from_prolog(refined_analysis)
        
        new_kr_store = KnowledgeRepresentationStore()
        for pc in new_clauses:
            new_kr_store.add_clause(pc, "problem_clause")
        new_kr_store.add_clause(objetive, "goal_clause")

        print(f"\n--- Cláusulas Extraídas ---")
        print("\nCláusulas Objetivo:")
        for clause in new_kr_store.get_clauses_by_category("goal_clause"):
            print(f"- {clause}")
            
        print("\nCláusulas del Problema:")
        for clause in new_kr_store.get_clauses_by_category("problem_clause"):
            print(f"- {clause}")

        print(f"--- Formalización Completada ---")
        print(new_kr_store)
        
        return new_kr_store
    
    def _generate_refined_analysis(self, 
                                  mmrc_analysis: Dict[str, Any], 
                                  problem_description: str, 
                                  current_clauses: List[str]) -> str:
        """
        Genera un nuevo análisis del problema considerando el feedback del MMRC.
        """
        prompt = generate_refined_analysis_promt(problem_description, current_clauses, mmrc_analysis)
        
        try:
            response = ask_gemini(prompt)
            print("OHI: Análisis refinado generado exitosamente.")
            return response
        except Exception as e:
            print(f"OHI Error: Falló la generación del análisis refinado: {e}")
            return "Error en el análisis refinado."
    
    def _extract_clauses_from_prolog(self, prolog_code: str) -> List[str]:
        """
        Extrae cláusulas individuales del código Prolog generado.
        """
        prompt = extract_clauses_from_prolog_promt(prolog_code)
        all_clauses = []

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
        response = ask_gemini_json(prompt, config=config)
        facts = response["facts"]
        rules = response["rules"]

        for fact in facts:
            all_clauses.append(fact.replace("//", "/"))

        for rule in rules:
            all_clauses.append(rule.replace("//", "/"))

        objective = response["objetive"][0].replace("//", "/")
        
        return all_clauses, objective