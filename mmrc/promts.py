from typing import List, Any
import json

def generate_successful_response_prompt(successful_branches_clausule: List[Any], problem_description: str, clauses: str, initial_LLM_analysis: str) -> str:
    return f"""
        Como experto en lógica y razonamiento, necesito que analices el siguiente problema y su solución:

        PROBLEMA ORIGINAL:
        {problem_description}

        CLAUSULAS USADAS:
        {clauses}

        RAMAS DE PENSAMIENTOS EXITOSAS:
        {json.dumps(successful_branches_clausule, indent=2, ensure_ascii=False)}

        ANÁLISIS INICIAL LLM:
        {initial_LLM_analysis}

        INSTRUCCIONES:
        1. Analiza las ramas de pensamientos que llevaron a una solución exitosa
        2. Formula una respuesta bien argumentada y clara al problema original
        3. Explica paso a paso cómo se llegó a esta solución
        4. Asegúrate de que la respuesta sea comprensible para alguien sin conocimientos técnicos de lógica formal

        Por favor, proporciona una respuesta estructurada que incluya:
        - La respuesta directa al problema
        - La justificación lógica paso a paso
        - Una explicación clara del razonamiento utilizado
        - Un resumen siendo contundente y breve con la pregunta que se te presentó al principio.
        """

def _analyze_failure_prompt(promising_branches_dict: List[Any], problem_description: str, clauses: str, solver_errors: List[str] = None, initial_LLM_analysis: str = None) -> str:
    return f"""
        Como experto en lógica y razonamiento, necesito que analices por qué no se pudo resolver el siguiente problema:

        PROBLEMA ORIGINAL:
        {problem_description}

        CLAUSULAS USADAS:
        {clauses}

        RAMAS DE PENSAMIENTO MÁS PROMETEDORAS:
        {json.dumps(promising_branches_dict, indent=2, ensure_ascii=False)}

        ANÁLISIS INICIAL LLM:
        {initial_LLM_analysis}

        CONTEXTO:
        El sistema de razonamiento lógico no pudo encontrar una solución exitosa. Todas las ramas de pensamiento terminaron sin éxito.
        {f"Además, se detectaron errores durante la ejecución del solver que pueden haber afectado el proceso de razonamiento." if solver_errors else ""}

        INSTRUCCIONES:
        1. Analiza las ramas de pensamiento que más se acercaron al éxito
        2. Identifica posibles errores en:
        - Las premisas del problema (¿faltan premisas importantes?)
        - Las premisas formuladas (¿hay premisas incorrectas o mal interpretadas?)
        - La lógica implementada (¿hay problemas en el razonamiento?)
        - Inconsistencias o contradicciones en las premisas
        {f"- Errores técnicos del solver que pudieron haber impedido una resolución exitosa" if solver_errors else ""}

        
        3. Proporciona sugerencias específicas para:
        - Premisas que podrían estar faltando
        - Premisas que podrían estar mal formuladas
        - Mejoras en la lógica de razonamiento
        - Resolución de inconsistencias
        {f"- Soluciones para los errores técnicos detectados" if solver_errors else ""}

        Por favor, proporciona un análisis estructurado que incluya:
        - Diagnóstico del problema principal
        - Análisis detallado de las ramas más prometedoras
        {f"- Análisis de los errores técnicos del solver" if solver_errors else ""}
        - Sugerencias específicas de mejora
        - Recomendaciones para futuras iteraciones
        4. Genera un programa de prolog:
        - Vuelve a escribir el programa pero corrige los errores anteriormente explicados.
        - Esto es sumamente importante: La corrección semántica y sintáctica del programa Prolog es crucial, ya que la verdad de tu hipótesis se deduce de la capacidad del programa para probarla. Asegúrate de que el código esté bien escrito y refleje lógicamente el problema y tu solución propuesta.
        - Para modelar implicaciones lógicas en Prolog de forma declarativa, usa la negación para expresar que no puede darse el caso de que el antecedente sea cierto y el consecuente falso.
        - Comenta el resultado esperado del programa pero nunca hables como si ya se hubiera ejecutado.
        """