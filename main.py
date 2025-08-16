from mfsa.mfsa_module import SemanticFormalizationAxiomatizationModule
from mfsa.kr_store import KnowledgeRepresentationStore
from ohi.ohi import HeuristicInferenceOrchestrator
from misa_j.cfcs import PrologSolver
from mmrc.mmrc_module import MetaCognitionKnowledgeRefinementModule
from checkpoints_utils import save_checkpoint, load_checkpoint
from config import CONFIG, redirect_output, setup_logging, clear_solutions
from llm_history import save_llm_history, load_latest_llm_history
from datetime import datetime

def run_main_with_problem(problem_description: str) -> str:
    """
    Ejecuta el sistema completo con un problema específico y devuelve la respuesta final.
    
    Args:
        problem_description: Descripción del problema a resolver
        
    Returns:
        str: Respuesta final del sistema
    """
    # Instanciación de módulos principales
    ohi = HeuristicInferenceOrchestrator()
    misa_j_solver = PrologSolver()
    mmrc_module = MetaCognitionKnowledgeRefinementModule()

    problem_topic_hint = None
    final_answer = "No se pudo encontrar una solución."

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
            history=history,
            ask_to_user=CONFIG["force_ask_to_user"]
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
            solver_result = misa_j_solver.solve(selected_clauses, goal_clauses_mfsa[0])
            thought_tree = solver_result["ramas"]
            solver_errors.append(solver_result["errors"])
            if CONFIG["save_checkpoints"] and solver_result:
                save_checkpoint(solver_result, checkpoint_misa_trace_name, problem_description)
            
        else:
            print("INFO: MISA-J omitido, traza cargada desde checkpoint.")
            solver_result = load_checkpoint(checkpoint_misa_trace_name, problem_description)
            thought_tree = solver_result["ramas"]
            solver_errors.append(solver_result["errors"])

        # Verificar si thought_tree es None o thought_tree.valor está vacío
        if not thought_tree:
            solver_errors.append("No se pudo generar un árbol de pensamiento válido")
        
        # --- 3. MMRC (Meta-cognición y Refinamiento del Conocimiento) ---
        print("\n--- Ejecutando MMRC ---")
        checkpoint_mmrc_name = f"mmrc_result_cycle{cycle}"
        mmrc_result = None

        if CONFIG["force_run_mmrc"]:
            mmrc_result = mmrc_module.analyze_thought_tree(solver_result, problem_description, selected_clauses, solver_errors, history)
            if CONFIG["save_checkpoints"] and mmrc_result:
                save_checkpoint(mmrc_result, checkpoint_mmrc_name, problem_description)
                
                # Guardar la respuesta en el historial
                if mmrc_result["response"]:
                    history['responses'].append(mmrc_result["response"])
                    history['timestamps'].append(datetime.now().isoformat())
                    history['cycle_count'] = cycle + 1
                    save_llm_history(history, problem_description)
        else:
            print("INFO: MMRC omitido, resultado cargado desde checkpoint.")
            mmrc_result = load_checkpoint(checkpoint_mmrc_name, problem_description)
            if not mmrc_result:
                print("No se encontró checkpoint para MMRC, ejecutando módulo...")
                mmrc_result = mmrc_module.analyze_thought_tree(solver_result, problem_description, selected_clauses, solver_errors, history)
                if CONFIG["save_checkpoints"] and mmrc_result:
                    save_checkpoint(mmrc_result, checkpoint_mmrc_name, problem_description)
                    
                    # Guardar la respuesta en el historial
                    if mmrc_result["response"]:
                        history['responses'].append(mmrc_result["response"])
                        history['timestamps'].append(datetime.now().isoformat())
                        history['cycle_count'] = cycle + 1
                        save_llm_history(history, problem_description)
        
        print("\n=== RESULTADO DEL ANÁLISIS MMRC ===")
        if mmrc_result["status"] == "success":
            print("✅ SE ENCONTRÓ UNA SOLUCIÓN EXITOSA")
            # Extraer la respuesta final
            if mmrc_result["response"]:
                final_answer = mmrc_result["response"]
            else:
                final_answer = "Se encontró una solución exitosa."
            break  # Salir del ciclo si se encontró solución
            
        elif mmrc_result["status"] == "failure_analysis":
            print("❌ NO SE ENCONTRÓ SOLUCIÓN - ANÁLISIS DE ERRORES")
            current_kr_store.update(problem_description, mmrc_result["response"])
            current_kr_store.print_all()
            final_answer = f"No se encontró solución después de {cycle + 1} ciclos de refinamiento."
    
    print("\nPROCESO COMPLETADO.")
    return final_answer

def main_original():
    # Instanciación de módulos principales
    ohi = HeuristicInferenceOrchestrator()
    misa_j_solver = PrologSolver()
    mmrc_module = MetaCognitionKnowledgeRefinementModule()


    problem_description = f"""
        Una cierta isla G está habitada exclusivamente por caballeros que dicen siempre
        la verdad y escuderos que mienten siempre. Por añadidura, algunos de los caballeros
        reciben el nombre de «caballeros establecidos» (estos son caballeros que en un cierto
        sentido se han demostrado a sí mismos), y ciertos escuderos reciben el nombre de
        «escuderos establecidos». Ahora bien, los habitantes de esta isla han formado varios
        clubs. Es posible que un habitante pueda pertenecer a más de un club. Dados
        cualquier habitante X y cualquier club C, o bien X afirma que es un miembro de C o
        bien afirma que no es un miembro de C.
        Está dado que se cumplen las cuatro condiciones siguientes, E1, E2, C, G.
        E1: El conjunto de todos los caballeros establecidos forma un club.
        E2: El conjunto de todos los escuderos establecidos forma un club.
        C (La Condición de Complementación): Dado cualquier club C, el conjunto
        de todos los habitantes de la isla que no son miembros de C forman un club de
        su exclusividad. (Este club es denominado el complemento de C y es denotado
        por C’.)
        G (La Condición Gödeliana): Dado cualquier club C, hay al menos un
        habitante de la isla que afirma que es un miembro de C. (Naturalmente su
        afirmación pudiera ser falsa: podría ser un escudero.)
        Existe al menos un caballero no establecido en la isla.
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
            history=history,
            ask_to_user=CONFIG["force_ask_to_user"]
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
            solver_result = misa_j_solver.solve(selected_clauses, goal_clauses_mfsa[0])
            thought_tree = solver_result["ramas"]
            solver_errors.append(solver_result["errors"])
            if CONFIG["save_checkpoints"] and solver_result:
                save_checkpoint(solver_result, checkpoint_misa_trace_name, problem_description)
            
        else:
            print("INFO: MISA-J omitido, traza cargada desde checkpoint.")
            solver_result = load_checkpoint(checkpoint_misa_trace_name, problem_description)
            thought_tree = solver_result["ramas"]
            solver_errors.append(solver_result["errors"])

        # Verificar si thought_tree es None o thought_tree.valor está vacío
        if not thought_tree:
            solver_errors.append("No se pudo generar un árbol de pensamiento válido")
        
        # --- 3. MMRC (Meta-cognición y Refinamiento del Conocimiento) ---
        print("\n--- Ejecutando MMRC ---")
        checkpoint_mmrc_name = f"mmrc_result_cycle{cycle}"
        mmrc_result = None

        if CONFIG["force_run_mmrc"]:
            mmrc_result = mmrc_module.analyze_thought_tree(solver_result, problem_description, selected_clauses, solver_errors, history)
            if CONFIG["save_checkpoints"] and mmrc_result:
                save_checkpoint(mmrc_result, checkpoint_mmrc_name, problem_description)
                
                # Guardar la respuesta en el historial
                if mmrc_result["response"]:
                    history['responses'].append(mmrc_result["response"])
                    history['timestamps'].append(datetime.now().isoformat())
                    history['cycle_count'] = cycle + 1
                    save_llm_history(history, problem_description)
        else:
            print("INFO: MMRC omitido, resultado cargado desde checkpoint.")
            mmrc_result = load_checkpoint(checkpoint_mmrc_name, problem_description)
            if not mmrc_result:
                print("No se encontró checkpoint para MMRC, ejecutando módulo...")
                mmrc_result = mmrc_module.analyze_thought_tree(solver_result, problem_description, selected_clauses, solver_errors, history)
                if CONFIG["save_checkpoints"] and mmrc_result:
                    save_checkpoint(mmrc_result, checkpoint_mmrc_name, problem_description)
                    
                    # Guardar la respuesta en el historial
                    if mmrc_result["response"]:
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
    
    # Extraer respuesta final
    final_answer = "No se pudo encontrar una solución."
    if 'mmrc_result' in locals() and mmrc_result and mmrc_result["status"] == "success":
        if mmrc_result.get("response"):
            final_answer = mmrc_result["response"].get("content", "Solución encontrada pero sin contenido específico.")
        else:
            final_answer = "Se encontró una solución exitosa."
    
    return final_answer

def main():
    """Función main simplificada que usa el problema por defecto"""
    problem_description = f"""
        Una cierta isla G está habitada exclusivamente por caballeros que dicen siempre
        la verdad y escuderos que mienten siempre. Por añadidura, algunos de los caballeros
        reciben el nombre de «caballeros establecidos» (estos son caballeros que en un cierto
        sentido se han demostrado a sí mismos), y ciertos escuderos reciben el nombre de
        «escuderos establecidos». Ahora bien, los habitantes de esta isla han formado varios
        clubs. Es posible que un habitante pueda pertenecer a más de un club. Dados
        cualquier habitante X y cualquier club C, o bien X afirma que es un miembro de C o
        bien afirma que no es un miembro de C.
        Está dado que se cumplen las cuatro condiciones siguientes, E1, E2, C, G.
        E1: El conjunto de todos los caballeros establecidos forma un club.
        E2: El conjunto de todos los escuderos establecidos forma un club.
        C (La Condición de Complementación): Dado cualquier club C, el conjunto
        de todos los habitantes de la isla que no son miembros de C forman un club de
        su exclusividad. (Este club es denominado el complemento de C y es denotado
        por C'.)
        G (La Condición Gödeliana): Dado cualquier club C, hay al menos un
        habitante de la isla que afirma que es un miembro de C. (Naturalmente su
        afirmación pudiera ser falsa: podría ser un escudero.)
        Existe al menos un caballero no establecido en la isla.
    """
    
    # Usar la nueva función
    final_answer = run_main_with_problem(problem_description)
    print(f"\nRESPUESTA FINAL: {final_answer}")
    return final_answer

if __name__ == "__main__":
    # Configurar logging
    log_file = setup_logging()
    
    # Si se activó el logging a archivo, redirigir la salida
    if log_file:
        with redirect_output(log_file):
            main()  # Usar la nueva función main simplificada
    else:
        main()  # Ejecutar sin redirección si no se activó el logging
