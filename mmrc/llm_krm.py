from typing import Dict, List, Any, TypedDict
from mfsa.kr_store import KnowledgeRepresentationStore # Asumiendo accesibilidad
from mfsa.horn_clause import HornClause # Para validación y creación
from common.gemini_interface import ask_gemini, parse_gemini_json_response # Asumiendo accesibilidad
import json

class ProposedModification(TypedDict):
    action: str # "add", "delete", "modify"
    clause_str: str # La cláusula a añadir/eliminar, o la cláusula ORIGINAL a modificar
    # current_clause_category: Optional[str] # Para delete/modify, de dónde viene
    new_clause_str: str # Para modify, la nueva forma de la cláusula
    # new_clause_category: Optional[str] # Para add/modify, a dónde va
    justification: str # Justificación del LLM para esta acción

class LLMKRM:
    """LLM-KRM: Knowledge Refinement Modulator."""

    def __init__(self):
        pass

    def _format_kr_store_for_llm(self, kr_store: KnowledgeRepresentationStore) -> str:
        """Formatea el contenido del KR-Store de forma concisa para el LLM."""
        lines = ["Estado Actual del KR-Store:"]
        lines.append("  Axiomas Base:")
        if kr_store.base_axioms:
            for axiom in kr_store.base_axioms:
                lines.append(f"    - {str(axiom)} (ID: {axiom.id}, Origen: {axiom.source})")
        else:
            lines.append("    (Ninguno)")
        
        lines.append("  Cláusulas del Problema:")
        if kr_store.problem_clauses:
            for prob_c in kr_store.problem_clauses:
                lines.append(f"    - {str(prob_c)} (ID: {prob_c.id}, Origen: {prob_c.source})")
        else:
            lines.append("    (Ninguna)")

        lines.append("  Cláusulas Objetivo:")
        if kr_store.goal_clauses:
            for goal_c in kr_store.goal_clauses:
                lines.append(f"    - {str(goal_c)} (ID: {goal_c.id}, Origen: {goal_c.source})")
        else:
            lines.append("    (Ninguna)")
        return "\n".join(lines)

    def propose_knowledge_refinements(self, 
                                      sga_evaluation: Dict[str, Any], 
                                      kr_store: KnowledgeRepresentationStore,
                                      problem_description_nl: str,
                                      goal_clause_str: str
                                      ) -> List[ProposedModification]:
        """
        Propone modificaciones al KR-Store basadas en la evaluación de LLM-SGA.

        Args:
            sga_evaluation: El resultado del análisis de LLM-SGA.
            kr_store: El estado actual del Knowledge Representation Store.
            problem_description_nl: La descripción original del problema.
            goal_clause_str: La cláusula objetivo que se intentaba probar.

        Returns:
            Una lista de diccionarios, donde cada diccionario es una ProposedModification.
        """
        print("\n--- LLM-KRM: Iniciando Propuesta de Refinamientos de Conocimiento ---")

        formatted_sga_eval = json.dumps(sga_evaluation, indent=2, ensure_ascii=False)
        formatted_kr_store = self._format_kr_store_for_llm(kr_store)

        prompt = f"""
        Basado en una evaluación global (LLM-SGA) de un intento de inferencia, la descripción original del problema y el estado actual de la base de conocimiento (KR-Store), tu tarea es proponer MODIFICACIONES CONCRETAS al KR-Store.

        Descripción Original del Problema (Lenguaje Natural):
        {problem_description_nl}

        Cláusula Objetivo que se intentaba probar:
        {goal_clause_str}

        Evaluación Global del LLM-SGA:
        {formatted_sga_eval}

        Estado Actual del KR-Store:
        {formatted_kr_store}

        Instrucciones para proponer modificaciones:
        1.  **Acciones Válidas:** Para cada modificación, especifica una acción: "add" (añadir nueva cláusula), "delete" (eliminar cláusula existente), o "modify" (modificar una cláusula existente).
        2.  **Especificidad:** Las cláusulas deben ser sintácticamente válidas como Cláusulas de Horn (ej: `pred(X) :- cuerpo(X).` o `hecho(a).`).
        3.  **Justificación:** CADA propuesta de modificación DEBE ir acompañada de una justificación explícita que explique POR QUÉ esta modificación es necesaria o beneficiosa, basándose en el análisis SGA y el objetivo de resolver el problema.
        4.  **Contexto:** Considera la descripción original del problema para asegurar que las modificaciones sean coherentes con el dominio.
        5.  **Priorización (implícita):** Enfócate en los cambios que parezcan más impactantes para resolver el problema o corregir los fallos identificados por SGA.
        6.  **Evitar Redundancia:** No sugieras añadir cláusulas que ya existen o son semánticamente equivalentes a las existentes, a menos que la modificación sea para cambiar su categoría o fuente (lo cual es menos común para este LLM).

        Proporciona tus propuestas en el siguiente formato JSON (una lista de objetos, solo el JSON, sin texto introductorio o posterior):
        [
          {{
            "action": "add",
            "clause_str": "nuevo_hecho(detalle_importante).",
            "justification": "El análisis SGA indicó que faltaba información sobre 'detalle_importante', que es mencionado en el problema y necesario para la regla X."
          }},
          {{
            "action": "delete",
            "clause_str": "regla_problematica(A) :- cuerpo(A).",
            "justification": "SGA identificó esta regla como causante de derivaciones irrelevantes y no contribuye a la solución."
          }},
          {{
            "action": "modify",
            "clause_str": "regla_a_mejorar(X) :- condicion_actual(X).",
            "new_clause_str": "regla_a_mejorar(X) :- condicion_actual(X), nueva_condicion(X).",
            "justification": "SGA sugirió que esta regla es demasiado general. Añadir 'nueva_condicion(X)' la hace más específica y alineada con el objetivo, como se desprende de la necesidad de conectar X con Y."
          }}
        ]
        Si no hay modificaciones que proponer, devuelve una lista vacía [].
        Para las cláusulas en `clause_str` (para delete/modify), usa su representación de string exacta como aparece en el KR-Store si es posible (incluyendo su ID si lo ves relevante para identificarla, aunque el matching se hará por string). Para `clause_str` en "add" y `new_clause_str` en "modify", solo la cláusula lógica.
        """

        task_hint = f"krm_refine_{goal_clause_str[:15].replace(' ','_')}"
        response_text = ask_gemini(prompt, task_hint=task_hint)

        proposed_modifications: List[ProposedModification] = []
        try:
            raw_modifications = parse_gemini_json_response(response_text)
            if not isinstance(raw_modifications, list):
                raise ValueError("La respuesta del LLM no es una lista.")

            for mod_data in raw_modifications:
                if not isinstance(mod_data, dict): continue # Saltar si no es un diccionario
                action = mod_data.get("action")
                clause_str = mod_data.get("clause_str")
                justification = mod_data.get("justification")
                
                if not all([action, clause_str, justification]):
                    print(f"LLM-KRM Warning: Modificación incompleta ignorada: {mod_data}")
                    continue

                # Validación básica
                if action not in ["add", "delete", "modify"]:
                    print(f"LLM-KRM Warning: Acción desconocida '{action}' ignorada.")
                    continue
                
                try: # Validar la sintaxis de la cláusula a añadir/eliminar/original
                    HornClause.from_string(clause_str.split('(')[0] + '(dummyterm).') # Truco para parsear sin importar el contenido exacto
                    # HornClause.from_string(clause_str) # Asume que la string es parseable
                except ValueError as e:
                    print(f"LLM-KRM Warning: Cláusula original '{clause_str}' parece malformada ({e}), ignorando modificación: {mod_data}")
                    # continue # Podríamos ser más estrictos aquí

                modification: ProposedModification = {
                    "action": action,
                    "clause_str": clause_str,
                    "justification": justification
                }

                if action == "modify":
                    new_clause_str = mod_data.get("new_clause_str")
                    if not new_clause_str:
                        print(f"LLM-KRM Warning: Modificación de tipo 'modify' sin 'new_clause_str', ignorada: {mod_data}")
                        continue
                    try: # Validar la nueva cláusula para modify
                        HornClause.from_string(new_clause_str)
                    except ValueError as e:
                        print(f"LLM-KRM Warning: Nueva cláusula '{new_clause_str}' para modificar parece malformada ({e}), ignorando: {mod_data}")
                        continue
                    modification["new_clause_str"] = new_clause_str
                
                proposed_modifications.append(modification)

        except json.JSONDecodeError:
            print(f"LLM-KRM Error: La respuesta no fue un JSON válido.\nRespuesta: {response_text}")
        except ValueError as e:
             print(f"LLM-KRM Error: Problema con el contenido del JSON: {e}\nRespuesta: {response_text}")

        print(f"LLM-KRM: Propuestas de refinamiento generadas: {len(proposed_modifications)}")
        return proposed_modifications


# Ejemplo de uso:
if __name__ == '__main__':
    # 1. Simular una KR-Store
    kr = KnowledgeRepresentationStore()
    kr.add_clause(HornClause.from_string("alarma_suena(casa) :- detecta_intruso(casa)."), "base_axiom")
    kr.add_clause(HornClause.from_string("alarma_suena(casa) :- fallo_electrico(casa)."), "base_axiom")
    kr.add_clause(HornClause.from_string("vecinos_llaman(casa) :- alarma_suena(casa)."), "base_axiom")
    kr.add_clause(HornClause.from_string("vecinos_llaman(casa)."), "problem_clause")
    kr.add_clause(HornClause.from_string("not fallo_electrico(casa)."), "problem_clause")
    kr.add_clause(HornClause.from_string("detecta_intruso(casa)."), "goal_clause")

    # 2. Simular una evaluación de SGA
    simulated_sga_eval = {
        "global_summary": "El sistema no pudo concluir detecta_intruso(casa) directamente. Parece que la regla para inferir la ausencia de fallo eléctrico (not fallo_electrico) y la llamada de los vecinos están presentes, pero no hay una regla clara que combine estos para deducir un intruso bajo la premisa de que la alarma suena por intruso O fallo.",
        "recurring_failure_patterns": ["No se pudo aplicar una regla directa tipo modus tollens para el caso del intruso."],
        "problematic_assumptions_identified": [],
        "promising_paths_to_explore_further_or_reinforce": ["El conocimiento de `alarma_suena(casa)` y `not fallo_electrico(casa)` está disponible."],
        "overall_confidence_in_knowledge_base": "Media - Falta una regla de inferencia clave para este problema específico.",
        "reasoning_log": "SGA: El problema es un caso clásico de inferencia por descarte. Si A o B causan C, y C ocurre, y sabemos que B no ocurrió, entonces A debe haber ocurrido."
    }
    problem_desc_krm = "La alarma de la casa suena si detecta un intruso o si hay un fallo en el sistema eléctrico. Los vecinos llamaron porque la alarma estaba sonando. Más tarde, la compañía eléctrica confirmó que no hubo ningún fallo en el sistema en toda la zona. ¿Qué se puede concluir sobre la causa de que sonara la alarma?"
    goal_krm = "detecta_intruso(casa)."

    print("--- KR-Store Inicial (Para KRM) ---")
    print(LLMKRM()._format_kr_store_for_llm(kr)) # Mostrar cómo lo ve el LLM
    print("\n--- Evaluación SGA (Input para KRM) ---")
    print(json.dumps(simulated_sga_eval, indent=2, ensure_ascii=False))

    # 3. Ejecutar LLM-KRM
    krm_modulator = LLMKRM()
    modifications = krm_modulator.propose_knowledge_refinements(
        simulated_sga_eval, 
        kr, 
        problem_desc_krm,
        goal_krm
    )

    print("\n--- Propuestas de Refinamiento de LLM-KRM ---")
    print(json.dumps(modifications, indent=2, ensure_ascii=False))

    # Aquí, en un sistema real, aplicarías estas modificaciones al kr_store
    # ej. kr_store.remove_clause(HornClause.from_string(mod["clause_str"]))
    # ej. kr_store.add_clause(HornClause.from_string(mod["clause_str"]), "base_axiom") 