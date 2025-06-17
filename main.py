from mfsa.mfsa_module import SemanticFormalizationAxiomatizationModule
from mfsa.kr_store import KnowledgeRepresentationStore
from ohi.ohi import HeuristicInferenceOrchestrator
from misa_j.cfcs import PrologSolver
from mmrc.mmrc_module import MetaCognitionKnowledgeRefinementModule
from checkpoints_utils import save_checkpoint, load_checkpoint
from config import CONFIG, redirect_output, setup_logging, clear_solutions
from llm_history import save_llm_history, load_latest_llm_history
from datetime import datetime

def main():
    # Instanciación de módulos principales
    ohi = HeuristicInferenceOrchestrator()
    misa_j_solver = PrologSolver()
    mmrc_module = MetaCognitionKnowledgeRefinementModule()


    problem_description = f"""
    Recordamos que Bellini siempre ponía a sus cofres inscripciones verdaderas, mientras que Cellini siempre les ponía inscripciones falsas.En algunos museos podemos ver parejas de cofres —uno de oro y otro de plata— que en un principio se hicieron y se vendieron como juego. La verdad es que la familia Bellini y la Cellini eran íntimas y que a veces colaboraban en algunas de estas parejas; aunque cada cofre lo hiciera siempre una sola persona, dentro de la pareja un cofre podía hacerlo uno y el otro otro diferente. Ambas familias se divertían muchísimo haciendo estas parejas de manera que la inteligente posteridad pudiera adivinar —o adivinar parcialmente— quiénes habían sido los autores.  Habían aparecido cuatro cofres, dos de oro y dos de plata; se sabía que constituían dos juegos, pero se habían mezclado y ahora no se sabía qué cofre de oro y qué cofre de plata formaban pareja. Me los enseñaron y pronto pude resolver el problema por lo que recibí unos excelentes honorarios. Pero además pude establecer también quién había hecho cada cofre, por lo que recibí un extra (que consistía, entre otras cosas, en una excelente caja de botellas de Chianti) y un beso de una de las florentinas más maravillosas que haya existido nunca He aquí los cuatro cofres:
    Cofre A (Oro)
    EL COFRE DE PLATA ES OBRA DE UN CELLINI
    Cofre B (Plata)
    EL COFRE DE PLATA O ES OBRA DE UN CELLINI O LOS DOS COFRES SON
    DE BELLINI
    Cofre C (Oro)
    EL COFRE DE ORO ES OBRA DE UN BELLINI
    Cofre D (Plata)
    EL COFRE DE ORO ES OBRA DE UN BELLINI Y POR LO MENOS UNO DE
    ESTOS COFRES ES OBRA DE UN HIJO O DE BELLINI O CELLINI

    Tenemos ahora un problema:
    ¿Quién hizo cada uno de los cofres?
    """
    problem_topic_hint = None

    print("\n" + "="*70)
    print(f"PROCESANDO PROBLEMA: \"{problem_description[:80]}...\"")
    print("="*70)

    current_kr_store = None
    thought_tree = None
    goal_clauses_mfsa = []
    
    # Cargar historial previo o inicializar uno nuevo
    history = load_latest_llm_history(problem_description)
    if not history:
        history = {
            'responses': [],
            'timestamps': [],
            'cycle_count': 0
        }

    # --- 1. MFSA (Formalización Semántica y Axiomatización) ---
    checkpoint_kr_store_name = "mfsa_kr_store"
    loaded_kr = None
    if not CONFIG["force_run_mfsa"]:
        loaded_kr = load_checkpoint(checkpoint_kr_store_name, problem_description)
        history = load_latest_llm_history(problem_description)
    
    if loaded_kr:
        current_kr_store = loaded_kr
        print("INFO: MFSA omitido, KR-Store cargado desde checkpoint.")
    else:
        print("\n--- Ejecutando MFSA ---")
        temp_kr_store = KnowledgeRepresentationStore()
        mfsa_instance_problem = SemanticFormalizationAxiomatizationModule(temp_kr_store)
        mfsa_result = mfsa_instance_problem.formalize_problem(
            problem_description, 
            history=history
        )
        current_kr_store = mfsa_result["kr_store"]
            
        # Guardar la respuesta del MFSA en el historial
        if mfsa_result["response"]:
            history['responses'].append({
                'module': 'MFSA',
                'content': mfsa_result["response"],
                'problem_clauses': mfsa_result["problem_clauses"],
                'objective': mfsa_result["objective"]
            })
            history['timestamps'].append(datetime.now().isoformat())
            history['cycle_count'] = 0  # MFSA es pre-ciclos
        
        if CONFIG["save_checkpoints"]:
            save_checkpoint(current_kr_store, checkpoint_kr_store_name, problem_description)
            save_llm_history(history, problem_description)
    
    for cycle in range(CONFIG["max_refinement_cycles"]):
        print(f"\n--- CICLO DE REFINAMIENTO {cycle + 1} / {CONFIG['max_refinement_cycles']} ---")

        # --- Limpieza de soluciones anteriores ---
        clear_solutions()

        goal_clauses_mfsa = current_kr_store.get_clauses_by_category("goal_clause")
        selected_clauses = current_kr_store.get_clauses_by_category("problem_clause")
        
        # --- 2. MISA-J (Motor de Inferencia Simbólica Asistido por Justificación) ---
        checkpoint_misa_trace_name = f"misa_j_trace_cycle{cycle}"
        solver_errors = []  # Lista para capturar errores del solver
        thought_tree = {}
        if CONFIG["force_run_misa_j"]:
            print("\n--- Ejecutando MISA-J (CFCS) ---")
            try:
                thought_tree = misa_j_solver.solve(selected_clauses, goal_clauses_mfsa[0])
                if CONFIG["save_checkpoints"] and thought_tree:
                    save_checkpoint(thought_tree, checkpoint_misa_trace_name, problem_description)
            except RecursionError as e:
                error_msg = f"Error de recursión infinita en MISA-J: {str(e)}"
                print(f"ERROR: {error_msg}")
                solver_errors.append(error_msg)
                thought_tree = None
            except Exception as e:
                error_msg = f"Error en MISA-J: {str(e)}"
                print(f"ERROR: {error_msg}")
                solver_errors.append(error_msg)
                thought_tree = None
        else:
            print("INFO: MISA-J omitido, traza cargada desde checkpoint.")
            thought_tree = load_checkpoint(checkpoint_misa_trace_name, problem_description)

        # Verificar si thought_tree es None o thought_tree.valor está vacío
        if thought_tree is None:
            solver_errors.append("No se pudo generar un árbol de pensamiento válido")
            # Crear un árbol de pensamiento vacío para pasar a MMRC
            thought_tree = []
        
        # --- 3. MMRC (Meta-cognición y Refinamiento del Conocimiento) ---
        print("\n--- Ejecutando MMRC ---")
        checkpoint_mmrc_name = f"mmrc_result_cycle{cycle}"
        mmrc_result = None

        if CONFIG["force_run_mmrc"]:
            mmrc_result = mmrc_module.analyze_thought_tree(thought_tree, problem_description, selected_clauses, solver_errors, history)
            if CONFIG["save_checkpoints"] and mmrc_result:
                save_checkpoint(mmrc_result, checkpoint_mmrc_name, problem_description)
                
                # Guardar la respuesta en el historial
                if mmrc_result.get("response"):
                    history['responses'].append(mmrc_result["response"])
                    history['timestamps'].append(datetime.now().isoformat())
                    history['cycle_count'] = cycle + 1
                    save_llm_history(history, problem_description)
        else:
            print("INFO: MMRC omitido, resultado cargado desde checkpoint.")
            mmrc_result = load_checkpoint(checkpoint_mmrc_name, problem_description)
            if not mmrc_result:
                print("No se encontró checkpoint para MMRC, ejecutando módulo...")
                mmrc_result = mmrc_module.analyze_thought_tree(thought_tree, problem_description, selected_clauses, solver_errors, history)
                if CONFIG["save_checkpoints"] and mmrc_result:
                    save_checkpoint(mmrc_result, checkpoint_mmrc_name, problem_description)
                    
                    # Guardar la respuesta en el historial
                    if mmrc_result.get("response"):
                        history['responses'].append(mmrc_result["response"])
                        history['timestamps'].append(datetime.now().isoformat())
                        history['cycle_count'] = cycle + 1
                        save_llm_history(history, problem_description)
        
        print("\n=== RESULTADO DEL ANÁLISIS MMRC ===")
        if mmrc_result["status"] == "success":
            print("✅ SE ENCONTRÓ UNA SOLUCIÓN EXITOSA")
            break  # Salir del ciclo si se encontró solución
            
        elif mmrc_result["status"] == "failure_analysis":
            print("❌ NO SE ENCONTRÓ SOLUCIÓN - ANÁLISIS DE ERRORES")
            current_kr_store.update(problem_description, mmrc_result["analysis"])
            current_kr_store.print_all()
            
            # # --- 4. OHI (Orquestación Heurística de Inferencia) ---
            # print("\n--- Ejecutando OHI (Refinamiento del Conocimiento) ---")
            # checkpoint_ohi_name = f"ohi_result_cycle{cycle}"
            # refined_kr_store = None

            # if CONFIG["force_run_ohi"]:
            #     # Convertir cláusulas HornClause a strings para OHI
            #     current_clauses_str = [str(clause) for clause in selected_clauses]
                
            #     # Refinar el conocimiento usando el análisis del MMRC
            #     refined_kr_store = ohi.refine_knowledge(
            #         mmrc_result, 
            #         problem_description, 
            #         current_clauses_str
            #     )
            #     if CONFIG["save_checkpoints"] and refined_kr_store:
            #         save_checkpoint(refined_kr_store, checkpoint_ohi_name, problem_description)
            # else:
            #     print("INFO: OHI omitido, resultado cargado desde checkpoint.")
            #     refined_kr_store = load_checkpoint(checkpoint_ohi_name, problem_description)
            #     if not refined_kr_store:
            #         print("No se encontró checkpoint para OHI, ejecutando módulo...")
            #         current_clauses_str = [str(clause) for clause in selected_clauses]
            #         refined_kr_store = ohi.refine_knowledge(
            #             mmrc_result,
            #             problem_description,
            #             current_clauses_str
            #         )
            #         if CONFIG["save_checkpoints"] and refined_kr_store:
            #             save_checkpoint(refined_kr_store, checkpoint_ohi_name, problem_description)
            
            # # Actualizar el KR Store actual con el refinado
            # if refined_kr_store:
            #     current_kr_store = refined_kr_store
            #     print("OHI: Conocimiento refinado. Continuando con el siguiente ciclo...")
            # else:
            #     print("ADVERTENCIA: OHI no pudo refinar el conocimiento. Usando KR Store anterior.")
        
    print("\nTODOS LOS PROBLEMAS CONFIGURADOS PROCESADOS.")

if __name__ == "__main__":
    # Configurar logging
    log_file = setup_logging()
    
    # Si se activó el logging a archivo, redirigir la salida
    if log_file:
        with redirect_output(log_file):
            main()  # Mover todo el código principal a una función main()
    else:
        main()  # Ejecutar sin redirección si no se activó el logging
