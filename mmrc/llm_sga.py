from typing import Dict, List, Any
from misa_j.trace import InferenceTrace # Asumiendo que está accesible
from common.gemini_interface import ask_gemini, parse_gemini_json_response # Asumiendo que está accesible
import json # Para formatear el análisis ARA para el prompt

class LLMSGA:
    """LLM-SGA: Synthesis & Global Assessment Unit."""

    def __init__(self):
        pass

    def assess_globally(self, 
                        inference_trace: InferenceTrace, 
                        ara_analysis: Dict[str, Any],
                        problem_description_nl: str,
                        goal_clause_str: str) -> Dict[str, Any]:
        """
        Realiza una síntesis global basada en la traza de MISA-J y el análisis de LLM-ARA.

        Args:
            inference_trace: La traza completa del MISA-J.
            ara_analysis: El resultado del análisis del LLM-ARA.
            problem_description_nl: La descripción original del problema.
            goal_clause_str: La cláusula objetivo que se intentaba probar.

        Returns:
            Un diccionario con la evaluación global, por ejemplo:
            {
                "global_summary": "El problema principal parece ser la falta de conexión entre conceptoA y conceptoB...",
                "recurring_failure_patterns": ["Siempre que se intenta usar regla_X, falta el hecho_Y."],
                "problematic_assumptions_identified": ["Se asumió Z, pero la traza no lo soporta."],
                "promising_paths_to_explore_further": ["El camino que usó regla_A y hecho_B parecía prometedor."],
                "overall_confidence_in_knowledge_base": "Media (faltan algunos axiomas clave)",
                "reasoning_log": "[Log del pensamiento del LLM SGA]"
            }
        """
        print("\n--- LLM-SGA: Iniciando Síntesis y Evaluación Global ---")

        trace_summary_lines = []
        trace_summary_lines.append(f"Objetivo a probar: {goal_clause_str}")
        trace_summary_lines.append(f"Resultado de MISA-J: {'Solución encontrada' if inference_trace.solution_found else 'Solución NO encontrada'}")
        trace_summary_lines.append("\nPasos de Inferencia Realizados por MISA-J:")
        if not inference_trace.steps:
            trace_summary_lines.append("  No se ejecutaron pasos de inferencia.")
        else:
            for step in inference_trace.steps:
                trace_summary_lines.append(f"    Premisas: {', '.join(step.premises) if step.premises else 'Hecho Inicial'}")
                if step.justification:
                    trace_summary_lines.append(f"    Justificación LLM-JEM: {step.justification[:100]}...")
        formatted_misa_trace = "\n".join(trace_summary_lines)
        
        formatted_ara_analysis = json.dumps(ara_analysis, indent=2, ensure_ascii=False)

        prompt = f"""
        Se ha realizado un intento de inferencia (MISA-J) y un análisis abductivo posterior (LLM-ARA).
        Tu tarea es realizar una SÍNTESIS GLOBAL y una EVALUACIÓN del estado actual del conocimiento y del proceso de razonamiento.

        Descripción Original del Problema (Lenguaje Natural):
        {problem_description_nl}

        Cláusula Objetivo que se intentaba probar:
        {goal_clause_str}

        Traza de Inferencia Comentada del MISA-J:
        {formatted_misa_trace}

        Análisis Abductivo del LLM-ARA (sobre el fallo si ocurrió):
        {formatted_ara_analysis}

        Instrucciones para tu Síntesis Global:
        1.  **Resumen Global:** ¿Cuál es tu evaluación general del intento de resolver el problema? ¿Cuáles son los puntos más críticos o las observaciones más importantes que surgen al ver toda la información junta?
        2.  **Patrones de Fallo Recurrentes:** ¿Identificas patrones en cómo o por qué fallaron ciertos caminos de inferencia (si MISA-J falló)? Por ejemplo, ¿se repite la falta de un tipo específico de información? ¿Hay reglas que consistentemente no encuentran las premisas necesarias?
        3.  **Asunciones Problemáticas Comunes:** ¿Hay asunciones implícitas en las reglas o en el conocimiento que parezcan problemáticas o no soportadas, a la luz del análisis completo?
        4.  **Caminos Prometedores Abandonados:** Si MISA-J falló, ¿hubo caminos que parecían prometedores pero que se abandonaron prematuramente (quizás por una pequeña pieza de información faltante que ARA ya identificó)?
        5.  **Confianza General en la Base de Conocimiento:** ¿Qué tan completa y correcta parece la base de conocimiento actual para este tipo de problema? (Baja, Media, Alta, y una breve justificación).
        
        Proporciona tu análisis en el siguiente formato JSON (solo el JSON, sin texto introductorio o posterior):
        {{ "global_summary": "[Tu evaluación general y observaciones clave]",
           "recurring_failure_patterns": ["[Ejemplo: La conexión entre '{{'concepto_A'}}' y '{{'concepto_B'}}' es consistentemente débil o ausente.]"],
           "problematic_assumptions_identified": ["[Ejemplo: Se asume que si '{{'X ocurre'}}', entonces '{{'Y siempre sigue'}}', pero el contexto del problema sugiere excepciones.]"],
           "promising_paths_to_explore_further_or_reinforce": ["[Ejemplo: La derivación de '{{'clause_alpha'}}' usando '{{'rule_beta'}}' fue un buen paso. Si se pudiera establecer '{{'missing_fact_gamma'}}', podría llevar a la solución.]"],
           "overall_confidence_in_knowledge_base": "[Baja/Media/Alta] - [Justificación breve]",
           "reasoning_log": "[Describe brevemente tu cadena de pensamiento para esta síntesis global.]"}}
        Si no tienes sugerencias para alguna categoría, usa una lista vacía [].
        """

        task_hint = f"sga_assessment_{goal_clause_str[:15].replace(' ','_')}"
        response_text = ask_gemini(prompt, task_hint=task_hint)

        try:
            sga_result = parse_gemini_json_response(response_text)
        except json.JSONDecodeError:
            print(f"LLM-SGA Error: La respuesta no fue un JSON válido.\nRespuesta: {response_text}")
            sga_result = {
                "global_summary": "Error al parsear la respuesta del LLM-SGA.",
                "recurring_failure_patterns": [],
                "problematic_assumptions_identified": [],
                "promising_paths_to_explore_further_or_reinforce": [],
                "overall_confidence_in_knowledge_base": "Indeterminada",
                "reasoning_log": f"La respuesta del LLM no fue un JSON válido: {response_text}"
            }
        
        print(f"LLM-SGA: Síntesis completada. Resumen: {sga_result.get('global_summary', 'N/A')}")
        return sga_result

# Ejemplo de uso:
if __name__ == '__main__':
    from misa_j.trace import InferenceStep
    from mmrc.llm_ara import LLMARA # Necesitamos ARA para el input de SGA

    # 1. Simular una traza de MISA-J fallida (la misma que en el ejemplo de ARA)
    failed_trace_sga = InferenceTrace(goal_clause="detectado(intruso).", solution_found=False)
    failed_trace_sga.add_step(
        derived_clause="alarma(sonando).",
        premises=["vecinos(llamaron)."],
        justification="Los vecinos llamaron porque la alarma sonaba...",
    )
    failed_trace_sga.add_step(
        derived_clause="not fallo_electrico.",
        premises=["compania_electrica(confirmo_no_fallo)."],
        justification="La compañía eléctrica confirmó la ausencia de fallos...",
    )
    problem_desc_sga = "La alarma de la casa suena si detecta un intruso o si hay un fallo en el sistema eléctrico. Los vecinos llamaron porque la alarma estaba sonando. Más tarde, la compañía eléctrica confirmó que no hubo ningún fallo en el sistema en toda la zona. ¿Qué se puede concluir sobre la causa de que sonara la alarma?"
    goal_sga = "detectado(intruso)."

    # 2. Obtener análisis de LLM-ARA (simulado o real)
    simulated_ara_analysis = {
        "summary": "El análisis ARA sugiere que falta una regla que conecte 'alarma(sonando)' y 'not fallo_electrico' con 'detectado(intruso)'.",
        "hypothesized_missing_elements": ["detectado(intruso) :- alarma(sonando), not fallo_electrico. /* Comentario: Esta es la regla modus tollens implícita en el problema. */"],
        "problematic_rules_identified": [],
        "potential_inference_paths_to_reinforce": ["El camino actual llegó hasta alarma(sonando) y not fallo_electrico. Reforzar con la regla hipotética mencionada."],
        "reasoning_log": "ARA: Dado que la alarma suena por intruso O fallo, y no hubo fallo, se infiere intruso."
    }
    print("\n--- Análisis ARA Simulado (Input para SGA) ---")
    print(json.dumps(simulated_ara_analysis, indent=2, ensure_ascii=False))

    # 3. Ejecutar LLM-SGA
    sga_assessor = LLMSGA()
    sga_evaluation = sga_assessor.assess_globally(
        failed_trace_sga, 
        simulated_ara_analysis, 
        problem_desc_sga,
        goal_sga
    )

    print("\n--- Resultado de la Evaluación Global de LLM-SGA ---")
    print(json.dumps(sga_evaluation, indent=2, ensure_ascii=False)) 