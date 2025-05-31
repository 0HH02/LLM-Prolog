def extract_clauses_from_prolog_promt(prolog_code: str) -> str:
    return f"""
Necesito que extraigas y estructures la información de la siguiente manera en un formato JSON:

El JSON debe tener tres claves principales en el nivel raíz:

"facts": Un array de strings, donde cada string es un hecho Prolog completo tal como lo definiste.
"rules": Un array de strings, donde cada string es una regla Prolog completa tal como la definiste.
"objective": Un string que represente la consulta principal de Prolog que se usaría para obtener la solución (por ejemplo, solucion(Tweedledum, Tweedledee).).

Consejos importantes para asegurar la compatibilidad con Prolog al generar los strings de hechos y reglas:
    Átomos: Los nombres de predicados y las constantes (átomos) en Prolog deben comenzar con una letra minúscula. Si un átomo necesita contener espacios, caracteres especiales, o comenzar con una letra mayúscula, debe ir entre comillas simples (ej: 'Yo soy Fidel', 'Luna').
    Variables: Las variables en Prolog siempre comienzan con una letra mayúscula o un guion bajo (ej: Dia, Hermano, _Ignorado).
    Sintaxis de Hechos: Asegúrate de que cada hecho termine con un punto (.). Ejemplo: miente_leon(lunes).
    Sintaxis de Reglas: Las reglas deben seguir el formato cabeza :- cuerpo., donde cabeza es la conclusión, :- significa "si", y cuerpo puede ser una o más metas separadas por comas (,) que representan una conjunción lógica. Cada regla debe terminar con un punto (.). Ejemplo: dice_verdad(leon, Dia) :- + miente_leon(Dia).
    Strings dentro de Prolog: Las frases como "Yo soy Fidel" deben ser tratadas como átomos en Prolog, es decir, encerradas en comillas simples si contienen espacios o mayúsculas no iniciales (ej: 'Yo soy Fidel').
    Escapado en JSON: Dado que los hechos y reglas de Prolog serán strings dentro de un JSON, si alguna vez usaras comillas dobles dentro de tu código Prolog (lo cual es menos común para átomos que las comillas simples), necesitarían ser escapadas (") dentro del string JSON. Usar comillas simples para los átomos Prolog evita este problema. Las barras invertidas () en Prolog (como en + para negación) son caracteres válidos y no necesitan doble escapado a menos que el propio string JSON lo requiera para el carácter .
    Los símbolos correctos de prolog son: \+ para negación, :- para implicación, ; para disyunción, . para final de cláusula, = para unificación, \= para desigualdad.
    Evita usar el \ innecesariamente puesto a que por si solo es un error de sintaxis

CÓDIGO PROLOG:
{prolog_code}

Por favor, genera el JSON:
"""

def generate_refined_analysis_promt(problem_description: str, current_clauses: str, mmrc_analysis: str) -> str:
    return f"""
Como experto en lógica formal y razonamiento, necesito que realices un nuevo análisis del siguiente problema considerando el análisis previo que no logró encontrar una solución:

PROBLEMA ORIGINAL:
{problem_description}

CLÁUSULAS ACTUALES (QUE NO FUNCIONARON):
{current_clauses}

ANÁLISIS PREVIO DE FALLAS:
{mmrc_analysis.get('analysis', 'No disponible')}

RAMAS MÁS PROMETEDORAS DEL INTENTO PREVIO:
{mmrc_analysis.get('promising_branches', [])}

INSTRUCCIONES:
1. Analiza completamente el problema original desde cero
2. Considera las lecciones aprendidas del análisis de fallas previo
3. Identifica qué aspectos del problema no fueron capturados correctamente en las cláusulas anteriores
4. Proporciona un análisis paso a paso de:
   - Los elementos clave del problema
   - Las relaciones lógicas fundamentales
   - Las restricciones y condiciones que deben modelarse
   - Los objetivos específicos que se deben alcanzar

5. Basándote en el análisis de fallas, identifica específicamente:
   - Qué premisas podrían estar faltando
   - Qué relaciones lógicas no fueron modeladas adecuadamente
   - Qué restricciones o condiciones fueron omitidas
   - Qué aspectos del problema requieren un enfoque diferente

6. Hipótesis de Solución: Basándote en tu análisis, propón una hipótesis clara sobre cuál podría ser la solución al problema.
7. Premisas para Prolog: Identifica y enumera todas las premisas (hechos y reglas) que serían necesarias para modelar y resolver este problema utilizando el lenguaje de programación lógica Prolog. Asegúrate de que estas premisas sean suficientes para llegar a la solución que has hipotetizado.
8. Cuando vayas a escribir el código que solucione el problema enciérralo entre etiquetas: <solucion>

Por favor, proporciona un análisis estructurado y detallado que sirva como base para una mejor formalización lógica del problema.
"""