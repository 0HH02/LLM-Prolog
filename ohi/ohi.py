from typing import List, Dict, Any, Optional
from mfsa.kr_store import KnowledgeRepresentationStore
from common.gemini_interface import ask_gemini


class HeuristicInferenceOrchestrator:
    def __init__(self):
        """
        Orquestador Heurístico de Inferencia (OHI).
        Su función principal es seleccionar un subconjunto estratégico de cláusulas.
        """
        # En el futuro, aquí podría haber modelos de políticas aprendidas, etc.
        # Por ahora, la "política" la implementa el LLM a través de prompts.
        pass

    def _format_clauses_for_llm(self, clauses: List[str]) -> str:
        """Formatea una lista de cláusulas para incluir en el prompt del LLM."""
        if not clauses:
            return "Ninguna."
        
        # Usar el ID de la cláusula para una referencia unívoca
        return "\n".join([f"ID: {cl.id} | {str(cl)} (Fuente: {cl.source})" for cl in clauses])

    def _format_inference_history_for_llm(self, inference_history: Optional[List[Dict[str, Any]]]) -> str:
        """
        Formatea el historial de inferencias para el LLM.
        inference_history es una lista de dicts, donde cada dict puede contener:
        - 'path_summary': str
        - 'reason': str (razón del fallo)
        - 'llm_analysis': str (análisis del LLM sobre ese fallo)
        - 'overall_review': str (si es un resumen global)
        """
        if not inference_history:
            return "No hay historial de inferencias previas."

        formatted_history = ["Resumen de Intentos de Inferencia Previos y Análisis:"]
        for i, entry in enumerate(inference_history):
            if entry.get('overall_review'):
                formatted_history.append(f"\nAnálisis Global Previo:\n{entry['overall_review']}")
                if entry.get('suggestions'):
                     formatted_history.append(f"Sugerencias Previas: {entry['suggestions']}")
            else:
                path_summary = entry.get('path_summary', 'Desconocido')
                reason = entry.get('reason', 'Desconocida')
                llm_analysis = entry.get('llm_analysis', 'No disponible')
                formatted_history.append(
                    f"\nIntento Fallido {i+1}:\n"
                    f"  Camino (resumen): {path_summary}\n"
                    f"  Razón del bloqueo: {reason}\n"
                    f"  Análisis del LLM sobre este camino: {llm_analysis}"
                )
        return "\n".join(formatted_history)

    def _parse_llm_selection(self, llm_response: str, all_available_clauses: List[str]) -> List[str]:
        """
        Parsea la respuesta del LLM para extraer las cláusulas seleccionadas.
        Espera que el LLM devuelva IDs de cláusulas o su contenido exacto.
        La forma más robusta es que el LLM devuelva los IDs.
        """
        selected_clauses: List[str] = []
        selected_identifiers = set() # Para IDs o contenido, y evitar duplicados

        # Primero, intenta extraer por ID si el LLM lo proporciona
        for line in llm_response.splitlines():
            line = line.strip()
            if line.startswith("ID:"):
                try:
                    # Ej: "ID: uuid-123 | mortal(X) :- humano(X). ..."
                    # o "ID: uuid-123"
                    clause_id = line.split("ID:")[1].split("|")[0].strip()
                    if clause_id:
                        selected_identifiers.add(clause_id)
                except IndexError:
                    print(f"OHI Warning: Línea malformada para extracción de ID: {line}")

        # Si no se encontraron IDs, o como fallback, intenta por contenido (menos robusto)
        if not selected_identifiers and "SELECCIONADAS:" in llm_response: # Adaptar al formato de respuesta del mock/LLM
            content_block = llm_response.split("SELECCIONADAS:")[1]
            for line in content_block.splitlines():
                line = line.split("/*")[0].strip() # Quitar comentarios
                if line:
                    selected_identifiers.add(line)
        elif not selected_identifiers: # Si no hay IDs ni bloque "SELECCIONADAS:", tomar cada linea como posible contenido
             for line in llm_response.splitlines():
                line = line.split("/*")[0].strip() # Quitar comentarios
                if line:
                    selected_identifiers.add(line)


        # Mapear identificadores (IDs o contenido) a objetos str
        clauses_by_id = {c.id: c for c in all_available_clauses}
        clauses_by_content = {str(c): c for c in all_available_clauses} # str(c) da la forma "pred(a)."

        for identifier in selected_identifiers:
            clause_obj = clauses_by_id.get(identifier)
            if not clause_obj: # Si no es un ID, intenta por contenido
                clause_obj = clauses_by_content.get(identifier)
            
            if clause_obj and clause_obj not in selected_clauses:
                selected_clauses.append(clause_obj)
            elif not clause_obj:
                print(f"OHI Warning: El LLM seleccionó un identificador/contenido de cláusula no encontrado: '{identifier}'")
        
        if not selected_clauses and selected_identifiers:
             print(f"OHI Warning: Se identificaron {len(selected_identifiers)} posibles selecciones pero no se mapearon a cláusulas existentes.")
        elif not selected_identifiers:
            print("OHI Info: El LLM no pareció seleccionar ninguna cláusula específica o el formato de respuesta no fue reconocido.")


        return selected_clauses

    def select_clauses(self, 
                       kr_store: KnowledgeRepresentationStore, 
                       inference_history: Optional[List[Dict[str, Any]]] = None,
                       max_clauses_to_select: int = 10
                       ) -> List[str]:
        """
        LLM-PSU: Policy Selection Unit.
        Selecciona un subconjunto de cláusulas relevantes.

        Args:
            kr_store: El almacén de conocimiento con todas las cláusulas.
            inference_history: Historial de análisis de inferencias previas.
            max_clauses_to_select: Un límite sugerido para el LLM.

        Returns:
            Una lista de objetos str seleccionados.
        """
        print("\n--- OHI: Iniciando Selección Heurística de Cláusulas ---")

        goal_clauses = kr_store.get_clauses_by_category("goal_clause")
        if not goal_clauses:
            print("OHI Error: No hay cláusula objetivo definida en el KR-Store. No se puede seleccionar.")
            return []
        
        # Asumimos una cláusula objetivo principal por ahora para el prompt
        # En un sistema más complejo, podría manejar múltiples objetivos.
        main_goal_clause_str = str(goal_clauses[0]) if goal_clauses else "Ninguno"

        all_available_clauses = kr_store.get_all_clauses()
        # Excluir las cláusulas objetivo de la selección de premisas, ya que son lo que intentamos probar.
        clauses_for_selection = [c for c in all_available_clauses if c not in goal_clauses]

        if not clauses_for_selection:
            print("OHI Info: No hay cláusulas disponibles (axiomas o del problema) para seleccionar.")
            return []

        formatted_clauses = self._format_clauses_for_llm(clauses_for_selection)
        formatted_history = self._format_inference_history_for_llm(inference_history)

        prompt = f"""
        Tu tarea es actuar como una Unidad de Selección de Políticas (Policy Selection Unit).
        Debes seleccionar un subconjunto estratégico de cláusulas para intentar probar un objetivo.

        Objetivo Principal a Probar: {main_goal_clause_str}

        Cláusulas Disponibles (Axiomas y Hechos del Problema):
        {formatted_clauses}

        Historial de Intentos de Inferencia Anteriores (si existe):
        {formatted_history}

        Instrucciones para la Selección:
        1. Enfócate en cláusulas que parezcan directamente relevantes para alcanzar el Objetivo Principal.
        2. Considera el historial: Si ciertos caminos fallaron por falta de cláusulas específicas, y esas cláusulas (o similares) están ahora disponibles, podrían ser buenas candidatas.
        3. Evita cláusulas que consistentemente llevaron a análisis negativos en el historial, a menos que tengas una nueva razón para incluirlas.
        4. El objetivo es reducir el espacio de búsqueda.
        5. Si crees que faltan cláusulas cruciales o ninguna de las disponibles es útil, puedes indicarlo.

        Formato de Respuesta Esperado:
        Lista las cláusulas seleccionadas. Es preferible que uses los IDs de las cláusulas si puedes identificarlos en la lista de arriba.
        Si no usas IDs, escribe el contenido exacto de la cláusula.
        Puedes añadir una justificación breve para tu selección general o para cláusulas específicas si es importante.
        Ejemplo de formato de respuesta si usas IDs:
        SELECCIONADAS:
        ID: [ID_de_la_clausula_1]
        ID: [ID_de_la_clausula_2]
        /* Justificación general: Estas cláusulas conectan directamente los términos del objetivo. */

        Tu Selección:
        """

        # Crear un task_hint más específico para los mocks
        # Esto ayuda si tienes diferentes estados del problema de Sócrates, por ejemplo.
        history_tag = "_with_history" if inference_history else "_initial"
        goal_tag = main_goal_clause_str.split('(')[0] # ej: "mortal" de "mortal(socrates)."
        task_hint = f"select_clauses_{goal_tag}{history_tag}"

        llm_response_text = ask_gemini(prompt, task_hint=task_hint)

        selected_clauses = self._parse_llm_selection(llm_response_text, clauses_for_selection)

        print(f"OHI: El LLM-PSU ha seleccionado {len(selected_clauses)} cláusulas:")
        for sc in selected_clauses:
            print(f"  - {str(sc)} (ID: {sc.id})")
        
        if not selected_clauses and llm_response_text: # Si el LLM respondió pero no pudimos parsear nada útil
            if "ninguna de las disponibles es útil" in llm_response_text.lower() or "faltan cláusulas cruciales" in llm_response_text.lower():
                print("OHI Info: El LLM indicó que las cláusulas actuales podrían no ser suficientes o faltan elementos clave.")
            # Podrías devolver un código especial o una lista vacía con una advertencia.

        return selected_clauses