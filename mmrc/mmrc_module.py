# from typing import Dict, List, Any, Optional

# from misa_j.trace import InferenceTrace
# from mfsa.kr_store import KnowledgeRepresentationStore
# from mfsa.horn_clause import HornClause # Para aplicar modificaciones
# from .llm_ara import LLMARA
# from .llm_sga import LLMSGA
# from .llm_krm import LLMKRM, ProposedModification

# class MetaCognitionKnowledgeRefinementModule:
#     """Orquesta los subcomponentes del MMRC: LLM-ARA, LLM-SGA, y LLM-KRM."""

#     def __init__(self):
#         self.ara = LLMARA()
#         self.sga = LLMSGA()
#         self.krm = LLMKRM()
#         # Podrías pasar instancias de LLM configuradas si fuera necesario

#     def analyze_and_refine(self, 
#                            inference_trace: InferenceTrace,
#                            kr_store: KnowledgeRepresentationStore,
#                            problem_description_nl: str,
#                            goal_clause_str: str # String de la cláusula objetivo original
#                            ) -> List[ProposedModification]: # Devuelve las propuestas de KRM
#         """
#         Ejecuta el ciclo completo de MMRC si la inferencia falló.

#         Args:
#             inference_trace: La traza del MISA-J.
#             kr_store: El almacén de conocimiento actual.
#             problem_description_nl: Descripción original del problema.
#             goal_clause_str: La cláusula objetivo que se intentaba probar.

#         Returns:
#             Una lista de ProposedModification del LLM-KRM, o una lista vacía si no hay propuestas
#             o si la solución ya fue encontrada por MISA-J.
#         """
#         if inference_trace.solution_found:
#             print("\n--- MMRC: Solución ya encontrada por MISA-J. No se requiere refinamiento en este ciclo. ---")
#             return []

#         print("\n--- MMRC: Iniciando Ciclo de Meta-cognición y Refinamiento del Conocimiento ---")

#         # 1. LLM-ARA: Análisis Abductivo del Fallo
#         ara_analysis = self.ara.analyze_inference_failure(
#             inference_trace, problem_description_nl, goal_clause_str
#         )
#         if not ara_analysis or not ara_analysis.get("summary") or "Error" in ara_analysis.get("summary",""):
#             print("MMRC Warning: LLM-ARA no produjo un análisis útil. Deteniendo refinamiento.")
#             return []

#         # 2. LLM-SGA: Síntesis y Evaluación Global
#         sga_evaluation = self.sga.assess_globally(
#             inference_trace, ara_analysis, problem_description_nl, goal_clause_str
#         )
#         if not sga_evaluation or not sga_evaluation.get("global_summary") or "Error" in sga_evaluation.get("global_summary",""):
#             print("MMRC Warning: LLM-SGA no produjo una evaluación útil. Deteniendo refinamiento.")
#             return []

#         # 3. LLM-KRM: Propuesta de Refinamientos de Conocimiento
#         proposed_modifications = self.krm.propose_knowledge_refinements(
#             sga_evaluation, kr_store, problem_description_nl, goal_clause_str
#         )
        
#         print(f"MMRC: Ciclo completado. {len(proposed_modifications)} modificaciones propuestas.")
#         return proposed_modifications

#     def apply_modifications_to_kr_store(self, 
#                                         kr_store: KnowledgeRepresentationStore, 
#                                         modifications: List[ProposedModification],
#                                         default_category_for_added: str = "base_axiom"):
#         """
#         Aplica las modificaciones propuestas por KRM al KR-Store.
#         NOTA: Esta es una implementación básica. Podrías querer más lógica para 
#         determinar la categoría de las cláusulas añadidas/modificadas, y un manejo
#         más robusto de la eliminación/modificación por ID si las cláusulas no son únicas por string.
#         """
#         if not modifications:
#             print("MMRC Apply: No hay modificaciones para aplicar.")
#             return

#         print(f"\n--- MMRC: Aplicando {len(modifications)} Modificaciones al KR-Store ---")
        
#         modified_count = 0
#         for mod in modifications:
#             action = mod["action"]
#             clause_str_original = mod["clause_str"]
#             justification = mod["justification"]
#             applied_this_mod = False

#             try:
#                 if action == "add":
#                     new_clause = HornClause.from_string(clause_str_original, source="mmrc_added", natural_lang_source=justification)
#                     # Decidir categoría: podrías tener una lógica más sofisticada o que el LLM la sugiera
#                     kr_store.add_clause(new_clause, default_category_for_added)
#                     print(f"  ADDED: {str(new_clause)} to {default_category_for_added} (Just.: {justification})")
#                     modified_count += 1
#                     applied_this_mod = True
                
#                 elif action == "delete":
#                     # La eliminación es más compleja si las cláusulas no son únicas o si necesitas
#                     # encontrarla por ID. Esta es una eliminación simple basada en string.
#                     # Necesitaríamos una función en KRStore para eliminar por string o ID.
#                     # Por ahora, buscaremos en todas las categorías.
#                     categories_to_search = ["base_axiom", "problem_clause", "goal_clause"]
#                     found_and_deleted = False
#                     for category in categories_to_search:
#                         if kr_store.remove_clause_by_string(clause_str_original, category):
#                             print(f"  DELETED: '{clause_str_original}' from {category} (Just.: {justification})")
#                             modified_count += 1
#                             found_and_deleted = True
#                             applied_this_mod = True
#                             break # Eliminada, no buscar más
#                     if not found_and_deleted:
#                         print(f"  DELETE FAILED: Cláusula '{clause_str_original}' no encontrada para eliminar.")

#                 elif action == "modify":
#                     new_clause_str = mod.get("new_clause_str")
#                     if not new_clause_str:
#                         print(f"  MODIFY FAILED: No se proporcionó 'new_clause_str' para '{clause_str_original}'.")
#                         continue

#                     # Similar a delete, encontrar la original y luego añadir la nueva.
#                     # Esto también necesita una función robusta en KRStore.
#                     deleted_for_modify = False
#                     original_category_temp = default_category_for_added # Placeholder
                    
#                     categories_to_search_modify = ["base_axiom", "problem_clause", "goal_clause"]
#                     for category_m in categories_to_search_modify:
#                         # Guardamos la categoría original para añadir la modificada en el mismo sitio (o decidir una nueva)
#                         temp_clause_to_check = kr_store.get_clause_by_string(clause_str_original, category_m)
#                         if temp_clause_to_check:
#                              original_category_temp = category_m # Asignar la categoría real donde se encontró
#                              if kr_store.remove_clause_by_string(clause_str_original, category_m):
#                                 deleted_for_modify = True
#                                 break
                    
#                     if deleted_for_modify:
#                         modified_clause = HornClause.from_string(new_clause_str, source="mmrc_modified", natural_lang_source=justification)
#                         kr_store.add_clause(modified_clause, original_category_temp) # Añadir a la misma categoría que la original
#                         print(f"  MODIFIED: '{clause_str_original}' to '{str(modified_clause)}' in {original_category_temp} (Just.: {justification})")
#                         modified_count += 1
#                         applied_this_mod = True
#                     else:
#                         print(f"  MODIFY FAILED: Cláusula original '{clause_str_original}' no encontrada para modificar.")
                
#                 if not applied_this_mod and action in ["delete", "modify"]:
#                     print(f"  NOTA: La modificación [{action} '{clause_str_original}'] no se pudo aplicar como se esperaba.")

#             except ValueError as e:
#                 print(f"  ERROR al aplicar modificación ({action} '{clause_str_original}'): {e}. Modificación ignorada.")
#             except Exception as e_gen:
#                 print(f"  ERROR GENERAL al aplicar modificación ({action} '{clause_str_original}'): {e_gen}. Modificación ignorada.")

#         if modified_count > 0:
#             print(f"MMRC Apply: {modified_count} modificaciones aplicadas exitosamente al KR-Store.")
#         else:
#             print("MMRC Apply: Ninguna modificación fue finalmente aplicada (podría ser debido a fallos o cláusulas no encontradas).")

# # Ejemplo de cómo podrías querer extender KRStore para esto:
# # En mfsa/kr_store.py:
# # def remove_clause_by_string(self, clause_str: str, category: str) -> bool:
# #     target_list = self._get_target_list_by_category(category)
# #     initial_len = len(target_list)
# #     # Iterar y eliminar. Cuidado con modificar lista mientras se itera.
# #     # clause_obj_to_remove = None
# #     # for c_obj in target_list:
# #     #    if str(c_obj) == clause_str:
# #     #        clause_obj_to_remove = c_obj
# #     #        break
# #     # if clause_obj_to_remove:
# #     #    target_list.remove(clause_obj_to_remove)
# #     #    return True
# #     # return False
# #     # O más simple pero menos eficiente para listas largas:
# #     new_list = [c for c in target_list if str(c) != clause_str]
# #     if len(new_list) < initial_len:
# #         if category == "base_axiom": self.base_axioms = new_list
# #         elif category == "problem_clause": self.problem_clauses = new_list
# #         elif category == "goal_clause": self.goal_clauses = new_list
# #         return True
# #     return False

# # def get_clause_by_string(self, clause_str: str, category: str) -> Optional[HornClause]:
# #    target_list = self._get_target_list_by_category(category)
# #    for c_obj in target_list:
# #        if str(c_obj) == clause_str:
# #            return c_obj
# #    return None

# # def _get_target_list_by_category(self, category:str) -> List[HornClause]: ... (helper para obtener la lista correcta) 