from typing import Dict, List, Any
from misa_j.trace import InferenceTrace # Asumiendo que está accesible
from common.gemini_interface import ask_gemini, parse_gemini_json_response # Asumiendo que está accesible
import json

class LLMARA:
    """LLM-ARA: Abductive Reasoning & Analysis Unit."""

    def __init__(self):
        # Podría inicializar un modelo Gemini específico si es necesario
        pass

    def analyze_inference_failure(self, 
                                  inference_trace: InferenceTrace, 
                                  problem_description_nl: str,
                                  goal_clause_str: str) -> Dict[str, Any]:
        """
        Analiza una traza de inferencia fallida para hipotetizar sobre las causas.

        Args:
            inference_trace: La traza completa del MISA-J que no condujo a la solución.
            problem_description_nl: La descripción original del problema en lenguaje natural.
            goal_clause_str: La cláusula objetivo que se intentaba probar.

        Returns:
            Un diccionario con el análisis, por ejemplo:
            {
                "summary": "El análisis sugiere que faltan axiomas sobre X o que la regla Y es incorrecta.",
                "hypothesized_missing_axioms": ["nuevo_axioma_1(Z).", "otro_axioma(A,B) :- condicion(A)."]
                "problematic_rules_identified": ["regla_existente_1(X) :- cuerpo(X)."],
                "reasoning_log": "[Log detallado del pensamiento del LLM ARA]"
            }
        """
        print("\n--- LLM-ARA: Iniciando Análisis Abductivo de Fallo de Inferencia ---")

        trace_summary_lines = []
        trace_summary_lines.append(f"Objetivo a probar: {goal_clause_str}")
        trace_summary_lines.append(f"Resultado: {'Solución encontrada' if inference_trace.solution_found else 'Solución NO encontrada'}")
        trace_summary_lines.append("\nPasos de Inferencia Realizados:")
        if not inference_trace.steps:
            trace_summary_lines.append("  No se ejecutaron pasos de inferencia (posiblemente no habían cláusulas iniciales o reglas aplicables).")
        else:
            for step in inference_trace.steps:
                trace_summary_lines.append(f"  - Paso {step.step_number}: {step.derived_clause}")
                trace_summary_lines.append(f"    Premisas: {', '.join(step.premises) if step.premises else 'Hecho Inicial'}")
                if step.justification:
                    trace_summary_lines.append(f"    Justificación LLM-JEM: {step.justification[:100]}...") # Acortar justificación larga
        
        formatted_trace = "\n".join(trace_summary_lines)

        prompt = f"""
        Se ha intentado resolver un problema lógico, pero no se ha alcanzado la cláusula objetivo.
        
        Descripción Original del Problema (Lenguaje Natural):
        {problem_description_nl}
        
        Cláusula Objetivo que se intentaba probar:
        {goal_clause_str}
        
        Traza de Inferencia Comentada del Intento Fallido (MISA-J):
        {formatted_trace}
        
        Tu tarea es realizar un razonamiento abductivo y un análisis profundo de este fallo. Considera lo siguiente:
        1.  ¿Qué axiomas o hechos cruciales podrían faltar en la base de conocimiento para que el objetivo SÍ se hubiera podido derivar por alguno de los caminos explorados o por uno nuevo razonable?
        2.  ¿Hay alguna regla existente que parezca incorrecta, demasiado restrictiva, o que haya llevado a un camino claramente erróneo según las justificaciones dadas por el LLM-JEM durante la inferencia?
        3.  ¿Hubo algún punto donde la inferencia se detuvo porque ninguna regla era aplicable, pero intuitivamente parecía que se debería poder avanzar? ¿Qué tipo de conocimiento faltaría ahí?
        4.  Si se exploraron múltiples ramas, ¿hay alguna que parezca más prometedora si se le añadiera algún conocimiento específico?
        5.  Si las cláusulas objetivos y las cláusulas derivadas tienen nombres coherentes y no hay problemas con la sitaxis, revisa que si dos cláusulas refieren a lo mismo estén escritas de manera idéntica.
        6.  Revisa que los nombres de entidades estén escritos de la misma manera. Si se están mecionando nombres propios deben coincidir en mayúsculas y minúsculas.
        
        Proporciona tu análisis en el siguiente formato JSON (solo el JSON, sin texto introductorio o posterior):
        {{ "summary": "[Tu resumen conciso del análisis y las principales hipótesis]",
           "hypothesized_missing_elements": ["[Ejemplo: axioma_faltante(X,Y) :- condicion(X). Comentario: Necesario para conectar A con B]", "[Ejemplo: hecho_faltante(detalle_especifico).]"],
           "problematic_rules_identified": ["[Ejemplo: regla_existente(A) :- cuerpo_problematico(A). Comentario: Esta regla es muy general y causa derivaciones irrelevantes.]"],
           "potential_inference_paths_to_reinforce": ["[Ejemplo: El camino que derivó '{{'clause_x'}}' parecía cercano. Podría reforzarse con un axioma sobre '{{'concept_y'}}'.]"],
           "reasoning_log": "[Describe brevemente tu cadena de pensamiento para llegar a estas conclusiones. Explica por qué crees que ciertos elementos faltan o son problemáticos.]"}}
        Asegúrate de que las cláusulas hipotéticas que sugieras sean sintácticamente válidas si son cláusulas de Horn.
        Si no tienes sugerencias para alguna categoría, usa una lista vacía [].
        """

        
        # task_hint para ayudar a los mocks si es necesario
        # Podría ser más específico basado en el goal_clause_str o el problema
        task_hint = f"ara_analysis_{goal_clause_str[:15].replace(' ','_')}"

        response_text = ask_gemini(prompt, task_hint=task_hint)
        
        try:
            # Asumimos que el LLM responde con un JSON válido como se le pidió
            analysis_result = parse_gemini_json_response(response_text)
            if analysis_result is None:
                raise json.JSONDecodeError("parse_gemini_json_response devolvió None", response_text, 0)
        except json.JSONDecodeError:
            print(f"LLM-ARA Error: La respuesta no fue un JSON válido.\nRespuesta: {response_text}")
            analysis_result = {
                "summary": "Error al parsear la respuesta del LLM-ARA.",
                "hypothesized_missing_elements": [],
                "problematic_rules_identified": [],
                "potential_inference_paths_to_reinforce": [],
                "reasoning_log": f"La respuesta del LLM no fue un JSON válido: {response_text}"
            }
        
        print(f"LLM-ARA: Análisis completado. Resumen: {analysis_result.get('summary', 'N/A')}")
        return analysis_result

# Ejemplo de uso (requiere Mocks o una API de Gemini configurada)
if __name__ == '__main__':
    from misa_j.trace import InferenceStep # Para construir un ejemplo de traza
    # Simular una traza de inferencia fallida
    failed_trace = InferenceTrace(goal_clause="detectado(intruso).", solution_found=False)
    failed_trace.add_step(
        derived_clause="alarma(sonando).",
        premises=["vecinos(llamaron)."],
        justification="Los vecinos llamaron porque la alarma sonaba, lo que implica que la alarma estaba sonando.",
    )
    failed_trace.add_step(
        derived_clause="not fallo_electrico.",
        premises=["compania_electrica(confirmo_no_fallo)."],
        justification="La compañía eléctrica confirmó la ausencia de fallos, por lo que se concluye que no hubo fallo eléctrico.",
    )
    # Supongamos que MISA-J se detuvo aquí sin alcanzar 'detectado(intruso)'.

    problem_desc_example = "La alarma de la casa suena si detecta un intruso o si hay un fallo en el sistema eléctrico. Los vecinos llamaron porque la alarma estaba sonando. Más tarde, la compañía eléctrica confirmó que no hubo ningún fallo en el sistema en toda la zona. ¿Qué se puede concluir sobre la causa de que sonara la alarma?"
    goal_example = "detectado(intruso)."

    ara_analyzer = LLMARA()
    analysis = ara_analyzer.analyze_inference_failure(failed_trace, problem_desc_example, goal_example)

    print("\n--- Resultado del Análisis de LLM-ARA ---")
    import json
    print(json.dumps(analysis, indent=2, ensure_ascii=False)) 