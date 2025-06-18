def formalize_statement_promt(statement_nl, context_nl, premises):
    return f"""
        Traduce la siguiente declaración en lenguaje natural a una única cláusula de Horn formal.
        Omite detalles o datos que estén implicados en la resolución del problema porque la tarea final es solamente determinar la cláusula o afirmación que se quiere verificar.
        Formato de Cláusula de Horn:
        - Hechos: predicado(termino1, terminoConstant).
        - Reglas: cabeza(X, Y) :- cuerpo1(X, Z), cuerpo2(Z, Y).
        Usa variables en mayúsculas (ej: X, Y, Z) y constantes en minúsculas o como strings citados si es necesario.
        Cada regla debe tener una cabeza y un cuerpo. No puede haber cuerpo sin cabeza.
        Ten en cuenta que cada predicado debe vener con al menos un argumento, de lo contrario no ess un hecho válido.
        Dame la respuesta como una lista de strings, cada string es una cláusula de Horn.
        No utilices símbolos dentro de las cláusulas como comillas para enucniar nombres propios, esto tiene que parsear bien.

        Contexto del problema (si ayuda): "{context_nl}"

        Premisas sacadas hasta ahora: "{"\n".join(premises)}"

        EJEMPLOS:
        sentence: All people who regularly drink coffee are dependent on caffeine.
        reformulation: ∀x (DrinkRegularly(x, coffee) → IsDependentOn(x, caffeine))
        horn_clause: ["is_dependent_on(X, caffeine) :- drink_regularly(X, coffee)."]

        sentence: Sam is doing a project.
        reformulation: ∃x (Project(x) ∧ Do(sam, x))
        horn_clause: ["project(cs101_assignment).", "do(sam, cs101_assignment)."]


        sentence: No one who doesn't want to be addicted to caffeine is unaware that caffeine is a drug.
        reformulation: ∀x (¬WantToBeAddictedTo(x, caffeine) → ¬AwareThatDrug(x, caffeine))
        horn_clause: ["aware_that_drug(X, caffeine) :- \+ want_to_be_addicted_to(X, caffeine)."]


        sentence: If Sam does a project written in Python, he will not use a Mac.
        reformulation: ∀x (Project(x) ∧ WrittenIn(x, python) ∧ Do(sam, x) → ¬Use(sam, mac))
        horn_clause: ["\+ use(sam, mac) :- project(X), written_in(X, python), do(sam, X)."]
        
        sentence: All social media applications containing chat features are software.
        reformulation: ∀x (SocialMedia(x) ∧ Application(x) ∧ Contain(x, chatFeature) → Software(x))
        horn_clause: ["software(X) :- social_media(X), application(X), contain(X, chat_feature)."]

        
        Declaración a traducir: "{statement_nl}"
        
        horn_clause:
        """

def formalize_in_logic_statement_promt(statement_nl):
    return f"""
        Analiza la siguiente descripción del problema en lenguaje natural y reformula la sentencia en lógica de predicado para asegurar la comprensión.
        Solamente responde con la reformulación, no des explicaciones ni comentarios.
        Ten en cuenta que todo predicado debe tener argumentos.
            
        EJEMPLOS:
        sentence: All people who regularly drink coffee are dependent on caffeine.
        reformulation: ∀x (DrinkRegularly(x, coffee) → IsDependentOn(x, caffeine))

        sentence: Sam is doing a project.
        reformulation: ∃x (Project(x) ∧ Do(sam, x))

        sentence: No one who doesn't want to be addicted to caffeine is unaware that caffeine is a drug.
        reformulation: ∀x (¬WantToBeAddictedTo(x, caffeine) → ¬AwareThatDrug(x, caffeine))

        sentence: If Sam does a project written in Python, he will not use a Mac.
        reformulation: ∀x (Project(x) ∧ WrittenIn(x, python) ∧ Do(sam, x) → ¬Use(sam, mac))

        sentence: All social media applications containing chat features are software.
        reformulation: ∀x (SocialMedia(x) ∧ Application(x) ∧ Contain(x, chatFeature) → Software(x))

        sentence: {statement_nl}
        reformulation:
        """

def initial_analysis_promt(problem_description_nl):
    return f"""
        Hola, necesito tu ayuda para analizar y resolver un problema de lógica de manera sistemática. Por favor, sigue los siguientes pasos:

        1. Entendimiento del Problema: 
        - Responde a las siguientes preguntas. ¿De qué trata? ¿Quiénes son los personajes? ¿Cuáles son los objetos o variables?

        2. Identificar y Aislar la Pregunta
        - Encuentra la pregunta principal que debes responder y sepárala del resto del texto.

        3. Busca las Afirmaciones
        - Busca cada frase que declare un hecho. Pregúntate: "¿Esta oración me está dando una pieza de información sólida e incuestionable?"
        - Cada afirmación debe ser una ley inmutable dentro del mundo del problema.
        - Las premisas a menudo vienen en frases complejas. Tu trabajo es traducirlas a un lenguaje lógico y simple.
            Frase original: "sEl coche rojo, que fue comprado después que el coche de Juan, no pertenece a María."
            Premisas extraídas y simplificadas:
            Hay un coche rojo.
            El coche rojo se compró después del coche de Juan.
            El coche rojo no es de María.
        - Ciertas palabras suelen introducir premisas, mientras que otras suelen introducir conclusiones.
            Típicas de PREMISAS: Dado que..., Sabiendo que..., Se asume que..., Es un hecho que..., Porque..., Puesto que...
            Típicas de CONCLUSIONES (¡No son premisas!): Por lo tanto..., En consecuencia..., Así que..., Se deduce que..., Se concluye que...
        - El Principio del "Mundo Cerrado": La única información que existe es la que te dan las premisas. Si no se menciona, no existe o no se puede asumir. Si el problema habla de perros y gatos, no puedes asumir que también hay un loro solo porque sería interesante. ¡No agregues información!
        - Maneja las Negaciones y las Condicionales: Presta especial atención a las frases negativas y a las que usan "si..., entonces...". Son premisas muy poderosas.
            "Ana no tiene el sombrero azul." es una premisa tan fuerte como "Ana tiene el sombrero rojo".
            "Si llueve, entonces la calle se moja." es una sola premisa (una regla condicional). No la separes. Establece una relación directa entre dos eventos.
        - Entre paréntesis haz anotaciones referentes al contenido de cada premisa cuando hagan referencias a otros objetos o a sí misma con el objetivo de esclarecer la intensionalidad de cada premisa.

        A continuación, te presento el problema de lógica:
        {problem_description_nl}
        """

def nl_to_prolog_promt(problem_description_nl, premises, preview_analysis):
    return f"""
        Como experto en lógica tienes que solucionar el siguiente problema:
        {problem_description_nl}

        Análisis previo:
        {preview_analysis}

        A continuación, te presento las premisas que usarás:
        {premises}

        Para ello sigue estas instrucciones:
        1. Análisis e Inferencia Preliminar:
        - Basándote en la información organizada, realiza inferencias lógicas paso a paso. Elimina posibilidades o deduce nuevos hechos. Si es aplicable, actualiza tu representación de la información con cada nueva inferencia hasta que se clarifiquen las relaciones.
        
        2. Hipótesis de Solución:
        - A partir de tu análisis e inferencias, propón una hipótesis clara sobre cuál es la solución al problema de lógica.
        
        3. Comprobación Formal con Prolog:
        - Transforma cada premisa en una o más sentencias de prolog, de forma que cada una esté asociada con alguna sentencia.
        - Intenta que las sentencias de prolog sean lo más parecida a la premisa que modela.
        - Cada cláusula y cada palabra conectiva ("y", "o", "si") debe ser representada con total fidelidad en tu código, sin simplificaciones ni interpretaciones que alteren su significado estricto.
        - Vas a crear un programa en Prolog (hechos y reglas) basado en tu hipótesis de solución y las pistas originales. Este programa debe ser capaz de demostrar la validez de tu hipótesis a través de consultas.
        - Identifica y codifica primero las reglas globales que rigen el comportamiento de todos los agentes del sistema, pues estas definen el marco en el que se deben evaluar sus acciones individuales.
        - Modela cada pieza de evidencia o declaración de forma atómica y fiel a su descripción original, evitando crear relaciones o dependencias artificiales entre componentes que el problema no vincula explícitamente.
        - Garantiza una correspondencia precisa entre las entidades del problema y las variables de tu código, validando que el contexto de cada regla solo afecte a las variables que le conciernen directamente.
        - Esto es sumamente importante: La corrección semántica y sintáctica del programa Prolog es crucial, ya que la verdad de tu hipótesis se deduce de la capacidad del programa para probarla. Asegúrate de que el código esté bien escrito y refleje lógicamente el problema y tu solución propuesta.
        - Para modelar implicaciones lógicas en Prolog de forma declarativa, usa la negación para expresar que no puede darse el caso de que el antecedente sea cierto y el consecuente falso.
        - Comenta el resultado esperado del programa pero nunca hables como si ya se hubiera ejecutado.
        """

def extract_problem_clauses_promt(problem_description_nl, problem_reformulation):
    return f"""
        Hola, basándote en tu respuesta anterior sobre el problema de lógica, necesito que extraigas y estructures la información de la siguiente manera en un formato JSON:

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

        Problema original:
            {problem_description_nl}

        Por favor, procesa la siguiente respuesta tuya y genera el JSON:
        Tu respuesta: 
            {problem_reformulation}
        """

def enrich_axioms_promt(topic, research_instruction, existing_clauses_str):
    return f"""
        Se necesita un conjunto de axiomas generales (expresados como cláusulas de Horn) sobre el tema: "{topic}".
        Estos axiomas deben ser fundamentales, generalmente aceptados y relevantes para el razonamiento lógico dentro de este dominio.
        {research_instruction}
        Evita redundancias con los siguientes axiomas ya existentes (si los hay):
        {existing_clauses_str if existing_clauses_str else "Ninguno."}

        Proporciona los nuevos axiomas, uno por línea. Formato:
        predicado(termino1, X).
        cabeza(X) :- cuerpo(X, Y).

        Nuevos Axiomas Generales sobre "{topic}":
        """