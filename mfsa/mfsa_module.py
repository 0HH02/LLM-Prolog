from typing import List, Dict, Optional, Tuple
from common.gemini_interface import ask_gemini, ask_gemini_json # Asumiendo que la función ask_gemini está definida como antes
from .kr_store import KnowledgeRepresentationStore, PREDEFINED_AXIOM_MODULES
from common.horn_clause import verify_horn_clause_sintaxys
from mfsa.promts import initial_analysis_promt, formalize_statement_promt, extract_problem_clauses_promt, enrich_axioms_promt, formalize_in_logic_statement_promt

class SemanticFormalizationAxiomatizationModule:
    def __init__(self, kr_store: Optional[KnowledgeRepresentationStore] = None):
        self.kr_store = kr_store if kr_store else KnowledgeRepresentationStore()
        # Podrías tener modelos Gemini específicos o configuraciones aquí
        # self.kge_model = genai.GenerativeModel("gemini-pro-vision") # O el que sea

    def _llm_kge_initial_analysis(self, problem_description_nl: str) -> Tuple[str, str, str, List[str]]:
        """
        Paso 1 del LLM-KGE: Comprensión, reificación, identificación de objetivo y ambigüedades.
        Devuelve: (reformulación_llm, objetivo_nl, entidades_relaciones_str, ambiguedades_detectadas)
        """
        prompt = initial_analysis_promt(problem_description_nl)
        response = ask_gemini(prompt, f"initial_analysis_{problem_description_nl[:20].replace(' ','_').lower()}") # task_hint dinámico para mock

        return response

    def _llm_kge_request_disambiguation(self, ambiguities: List[str], problem_description_nl: str) -> str:
        """Solicita aclaraciones al usuario."""
        if not ambiguities:
            return problem_description_nl

        print("\n--- SOLICITUD DE DESAMBIGUACIÓN ---")
        print("El sistema ha detectado las siguientes ambigüedades o puntos que requieren aclaración:")
        for amb in ambiguities:
            print(f"- {amb}")
        
        user_clarification = input("Por favor, proporciona tus aclaraciones o escribe 'continuar' si no son relevantes: ")
        if user_clarification.lower() == 'continuar':
            return problem_description_nl
        return f"{problem_description_nl}\nAclaración del Usuario: {user_clarification}"

    def _llm_kge_formalize_statement(self, statement_nl: str, type_hint: str, context_nl: str = "") -> Optional[str]:
        """
        Pide al LLM que traduzca una única frase (objetivo, hecho, regla) a una cláusula de Horn.
        type_hint puede ser "objetivo", "hecho", "regla".
        """
        prompt = formalize_in_logic_statement_promt(statement_nl)

        formal_logic_statement = ask_gemini(prompt)

        prompt = formalize_statement_promt(formal_logic_statement, context_nl, "")

        formal_clause_str = ask_gemini_json(prompt)

        horn_clauses = []
        for clause in formal_clause_str:
            horn_clauses.append(verify_horn_clause_sintaxys(clause.strip()))
        return horn_clauses

    def _llm_kge_extract_problem_clauses(self, problem_description_nl: str, problem_reformulation: str) -> List[str]:
        """Extrae cláusulas (hechos y reglas) específicas del problema."""
        all_clauses = []

        problem_clauses_prompt = extract_problem_clauses_promt(problem_description_nl, problem_reformulation)
        
        response = ask_gemini_json(problem_clauses_prompt)
        
        facts = response["facts"]
        rules = response["rules"]

        for fact in facts:
            all_clauses.append(verify_horn_clause_sintaxys(fact.replace("//", "/")))

        for rule in rules:
            all_clauses.append(verify_horn_clause_sintaxys(rule.replace("//", "/")))

        objective = verify_horn_clause_sintaxys(response["objetive"][0].replace("//", "/"))

        return all_clauses, objective

    def _llm_kge_enrich_axioms(self, topic: str, existing_clauses: List[str], enable_ad_hoc_research: bool) -> List[str]:
        """Genera axiomas generales adicionales sobre un tema, opcionalmente con "investigación"."""
        existing_clauses_str = "\n".join([str(c) for c in existing_clauses[:10]]) # Mostrar solo algunos para no saturar el prompt
        
        research_instruction = ""
        if enable_ad_hoc_research:
            research_instruction = "Si es necesario, puedes simular una búsqueda de conocimiento general en la web sobre este tema para encontrar axiomas fundamentales y bien establecidos."

        prompt = enrich_axioms_promt(topic, research_instruction, existing_clauses_str)
        task_hint_suffix = "_web" if enable_ad_hoc_research else ""
        response = ask_gemini(prompt, f"enrich_axioms_{topic.lower().replace(' ','_')}{task_hint_suffix}")
        return self._parse_llm_clauses(response, "llm_generated_axiom", f"Topic: {topic}, Research: {enable_ad_hoc_research}")

    def formalize_problem(self, problem_description_nl: str, 
                          preselected_axiom_modules: Optional[List[str]] = None, 
                          enable_ad_hoc_research: bool = False,
                          problem_topic_hint: Optional[str] = None,
                          axiom_library_names: Optional[List[str]] = None) -> KnowledgeRepresentationStore:
        """
        Función principal del MFSA para traducir lenguaje natural a cláusulas formales.
        """
        self.kr_store.clear_all() # Empezar limpio para cada formalización
        print(f"\n--- Iniciando Formalización Semántica y Axiomatización (MFSA) ---")
        print(f"Descripción del Problema (NL): {problem_description_nl}")

        # Cargar bibliotecas de axiomas si se especifican
        if axiom_library_names:
            print(f"MFSA: Cargando bibliotecas de axiomas: {axiom_library_names}")
            for lib_name in axiom_library_names:
                self.kr_store.load_axiom_library(lib_name)

        # 1. LLM-KGE: Análisis inicial, identificación de objetivo NL, y detección de ambigüedades
        reformulation_llm = self._llm_kge_initial_analysis(problem_description_nl)

        # 2. LLM-KGE: Desambiguación con el usuario (si es necesario)
        # problem_description_final_nl = self._llm_kge_request_disambiguation(ambiguities, problem_description_nl)
        # if problem_description_final_nl != problem_description_nl: # Si hubo aclaración
        #     print(f"MFSA: Descripción del problema actualizada tras desambiguación.")
            # Opcional: Re-analizar si la aclaración fue sustancial
            # reformulation_llm, goal_nl, entities_relations_str, _ = self._llm_kge_initial_analysis(problem_description_final_nl)
            # Por simplicidad, asumimos que la aclaración se añade al contexto.

        # 4. LLM-KGE: Extraer Cláusulas Específicas del Problema
        problem_clauses_extracted, objective = self._llm_kge_extract_problem_clauses(problem_description_nl, reformulation_llm)
        for pc in problem_clauses_extracted:
            self.kr_store.add_clause(pc, "problem_clause")
        self.kr_store.add_clause(objective, "goal_clause")
        print(f"MFSA: Cláusulas del Problema Extraídas: {len(problem_clauses_extracted)}")

        # 5. Integrar Módulos Axiomáticos Predefinidos
        if preselected_axiom_modules:
            self._integrate_predefined_axioms(preselected_axiom_modules)

        # # 6. LLM-KGE: Enriquecer con Axiomas Generales / Ad-hoc Research
        # topic_for_axioms = problem_topic_hint if problem_topic_hint else "conocimiento general relevante al problema"
        # if not problem_topic_hint: # Intentar extraer un tema del análisis del LLM si no se da una pista
        #     # Podrías pedir al LLM que sugiera un tema basado en 'reformulation_llm'
        #     pass 
        
        # enriched_axioms = self._llm_kge_enrich_axioms(topic_for_axioms, self.kr_store.base_axioms, enable_ad_hoc_research)
        # for ax in enriched_axioms:
        #     self.kr_store.add_clause(ax, "base_axiom")
        # print(f"MFSA: Axiomas Generales Enriquecidos/Generados: {len(enriched_axioms)}")

        print(f"\n--- Cláusulas Extraídas ---")
        print("\nCláusulas Objetivo:")
        for clause in self.kr_store.get_clauses_by_category("goal_clause"):
            print(f"- {clause}")
            
        print("\nCláusulas del Problema:")
        for clause in self.kr_store.get_clauses_by_category("problem_clause"):
            print(f"- {clause}")
            
        print("\nAxiomas Base:")
        for clause in self.kr_store.get_clauses_by_category("base_axiom"):
            print(f"- {clause}")

        print(f"--- Formalización Completada ---")
        print(self.kr_store)
        return self.kr_store