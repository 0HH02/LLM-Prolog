from typing import List, Dict, Optional, Tuple
from common.gemini_interface import ask_gemini, ask_gemini_json # Asumiendo que la función ask_gemini está definida como antes
from .kr_store import KnowledgeRepresentationStore
from mfsa.promts import initial_analysis_promt, enrich_axioms_promt, nl_to_prolog_promt
from datetime import datetime

class SemanticFormalizationAxiomatizationModule:
    def __init__(self, kr_store: Optional[KnowledgeRepresentationStore] = None):
        self.kr_store = kr_store if kr_store else KnowledgeRepresentationStore()
        # Podrías tener modelos Gemini específicos o configuraciones aquí
        # self.kge_model = genai.GenerativeModel("gemini-pro-vision") # O el que sea

    def _llm_kge_initial_analysis(self, problem_description_nl: str, ask_to_user: bool = False) -> Tuple[str, str, str, List[str]]:
        """
        Paso 1 del LLM-KGE: Comprensión, reificación, identificación de objetivo y ambigüedades.
        Devuelve: (reformulación_llm, objetivo_nl, entidades_relaciones_str, ambiguedades_detectadas)
        """
        config = {
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "general_description": {"type": "string"},
                        "objetive": {"type": "string"},
                        "premises": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["general_description", "objetive", "premises"]
                }
            }
        prompt = initial_analysis_promt(problem_description_nl)
        response = ask_gemini_json(prompt, f"initial_analysis_{problem_description_nl[:20].replace(' ','_').lower()}", config=config) # task_hint dinámico para mock
        
        print("===Premisas encontradas===")
        for premise in response["premises"]:
            print(premise)
        
        if ask_to_user:
            user_clariuser_clarificationfication = input("Estas son las premisas que he encontrado. Si crees que me he saltado algunas puedes comentármelas si no presiona enter para continuar")
        else:
            user_clarification = ""
        print("Continuando...")
        
        all_premises = "\n".join(response["premises"]) + "\nAclaración del Usuario: " + user_clarification


        config = {
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "preview_analysis": {"type": "string"},
                        "hypothetical_solution": {"type": "string"},
                        "output_desired": {"type": "string"},
                        "prolog_code": {"type": "string"},
                    },
                    "required": ["preview_analysis", "hypothetical_solution", "output_desired", "prolog_code"]}
                }
        prompt = nl_to_prolog_promt(problem_description_nl, all_premises, response["general_description"])
        response = ask_gemini_json(prompt, f"nl_to_prolog_{problem_description_nl[:20].replace(' ','_').lower()}", config=config)
        return response["prolog_code"]

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

    def formalize_problem(self, problem_description_nl: str, history: Dict[str, any] = None,
                          preselected_axiom_modules: Optional[List[str]] = None, 
                          axiom_library_names: Optional[List[str]] = None, ask_to_user: bool = False) -> Dict:
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
        initial_LLM_analysis = self._llm_kge_initial_analysis(problem_description_nl, ask_to_user=ask_to_user)

        # 4. LLM-KGE: Extraer Cláusulas Específicas del Problema
        problem_clauses_extracted, objective = self.kr_store.update(problem_description_nl, initial_LLM_analysis)

        # 5. Integrar Módulos Axiomáticos Predefinidos
        if preselected_axiom_modules:
            self._integrate_predefined_axioms(preselected_axiom_modules)

        self.kr_store.print_all()
        
        if history is not None:
            history["responses"].append({
                'module': 'MFSA',
                'content': initial_LLM_analysis,
                'problem_clauses': problem_clauses_extracted,
                'objective': objective
            })
            history['timestamps'].append(datetime.now().isoformat())
            history['cycle_count'] = 0  # MFSA es pre-ciclos

        return {
            "kr_store": self.kr_store,
            "response": initial_LLM_analysis,
            "problem_clauses": problem_clauses_extracted,
            "objective": objective
        }