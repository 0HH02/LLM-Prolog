from common.gemini_interface import ask_gemini

class LLMJEM:
    """Simula la interacción con un LLM para obtener justificaciones."""

    def get_justification(self, derived_clause: str, context_clauses: list[str]) -> str:
        """
        Obtiene una justificación en lenguaje natural para una cláusula derivada,
        dado un contexto de cláusulas.

        Args:
            derived_clause (str): La cláusula que ha sido derivada.
            context_clauses (list[str]): Las cláusulas que se usaron para derivar la nueva cláusula.

        Returns:
            str: Una justificación en lenguaje natural (simulada).
        """
        
        context_str = "; ".join(context_clauses)
        prompt = (
            f"Dadas las siguientes premisas: [{context_str}], "
            f"se ha derivado la conclusión: '{derived_clause}'. "
            f"Por favor, proporciona una breve justificación en lenguaje natural para este paso de inferencia."
        )
        response = ask_gemini(prompt)
        return response