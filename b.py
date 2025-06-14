import tempfile
import subprocess
import os


def _ejecutar_prolog_con_traza_modificado(prolog_code, consulta):
    """
    Ejecuta un código Prolog en SWI-Prolog, captura y devuelve la traza de stderr.
    """

    enriq_trace = r"""
    :- set_prolog_flag(trace_file, true).
    :- leash(-all).

    user:prolog_trace_interception(Port, Frame, _PC, continue) :-
            (   prolog_frame_attribute(Frame, level, Lvl)
            ->  Indent is Lvl * 2
            ;   Indent = 0
            ),
            prolog_frame_attribute(Frame, goal,  Goal),
            (   prolog_frame_attribute(Frame, clause, ClRef),
                clause_property(ClRef, file(File)),
                clause_property(ClRef, line_count(Line))
            ->  true
            ;   File = '<dynamic>', Line = 0
            ),
            format(user_error,
                '~N~*|~w: ~p @ ~w:~d~n',
                [Indent, Port, Goal, File, Line]).
    """

    stdout_capture = ""
    stderr_capture = ""
    swipl_executable = "swipl" 
    temp_prolog_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.pl', delete=False)
    temp_prolog_file_name = temp_prolog_file.name
    try:
        temp_prolog_file.write(enriq_trace)
        temp_prolog_file.write('\n') 
        temp_prolog_file.write(prolog_code)
        temp_prolog_file.close()
        prolog_file_path_escaped = temp_prolog_file_name.replace("'", "''")
        
        # Modificado para imprimir excepciones a user_error (stderr)
        goal_prolog = (
            f"consult('{prolog_file_path_escaped}'), "          # carga el archivo
            f"trace, "                          # inicia la traza
            # Ejecuta la consulta, captura excepciones y continúa para ver la traza
            f"catch(({consulta[:-1]}, fail), "
            f"E, (format(user_error, "
            f"'~N### CAUGHT_EXCEPTION ###~n~w~n### END_EXCEPTION ###~n', [E]), fail)), "
            "halt."
        )
        process = subprocess.Popen(
            [swipl_executable, "-q", "-g", goal_prolog, "-t", "halt"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8', errors='replace' 
        )
        # Aumentar el timeout para trazas largas
        stdout_capture, stderr_capture = process.communicate(timeout=60) 
    except subprocess.TimeoutExpired:
        process.kill()
        stdout_capture, stderr_capture = process.communicate()
        print("La ejecución de Prolog excedió el tiempo límite (Timeout).")
        stderr_capture += "\nERROR: Timeout during Prolog execution."
    except Exception as e:
        print(f"Error durante la ejecución de Prolog: {e}")
        stderr_capture += f"\nERROR: Python exception during Prolog call: {e}"
    finally:
        if os.path.exists(temp_prolog_file_name):
            os.remove(temp_prolog_file_name)

    if stdout_capture:
        print("--- Salida Estándar de Prolog (stdout) ---")
        print(stdout_capture) # Debería estar vacío o con pocos mensajes si todo va a user_error
    
    return stderr_capture


prolog_code = """
    es_maker(bellini).
    es_maker(cellini).
    regla_maker_cumplida(Maker, TruthValue) :- (Maker == bellini, TruthValue == true) ; (Maker == cellini, TruthValue == false).
    get_literal_truth(es_obra_term(a, M), MA, _, _, _, (M == MA)).
    get_literal_truth(es_obra_term(b, M), _, MB, _, _, (M == MB)).
    get_literal_truth(es_obra_term(c, M), _, _, MC, _, (M == MC)).
    get_literal_truth(es_obra_term(d, M), _, _, _, MD, (M == MD)).
    get_term_truth(Literal, MA,MB,MC,MD, TruthValue) :- get_literal_truth(Literal, MA,MB,MC,MD, Evaluation), evaluate_bool(Evaluation, TruthValue).
    get_term_truth((S1 ; S2), MA,MB,MC,MD, TruthValue) :- get_term_truth(S1, MA,MB,MC,MD, Res1), get_term_truth(S2, MA,MB,MC,MD, Res2), evaluate_bool((Res1 ; Res2), TruthValue).
    get_term_truth((S1 , S2), MA,MB,MC,MD, TruthValue) :- get_term_truth(S1, MA,MB,MC,MD, Res1), get_term_truth(S2, MA,MB,MC,MD, Res2), evaluate_bool((Res1 , Res2), TruthValue).
    evaluate_bool(true, true).
    evaluate_bool(false, false).
    evaluate_bool((V1 == V2), true) :- V1 == V2.
    evaluate_bool((V1 == V2), false) :- V1 \\== V2.
    evaluate_bool((R1 ; R2), true) :- evaluate_bool(R1, true) ; evaluate_bool(R2, true).
    evaluate_bool((R1 ; R2), false) :- evaluate_bool(R1, false), evaluate_bool(R2, false).
    evaluate_bool((R1 , R2), true) :- evaluate_bool(R1, true), evaluate_bool(R2, true).
    evaluate_bool((R1 , R2), false) :- evaluate_bool(R1, false) ; evaluate_bool(R2, false).
    inscripcion(a, PartnerA, es_obra_term(PartnerA, cellini)).
    inscripcion(b, PartnerB, (es_obra_term(b, cellini) ; (es_obra_term(b, bellini), es_obra_term(PartnerB, bellini)))).
    inscripcion(c, PartnerC, es_obra_term(c, bellini)).
    inscripcion(d, PartnerD, es_obra_term(PartnerD, bellini)).
    check_cofre(Cofre, Maker, Partner, MA, MB, MC, MD) :- inscripcion(Cofre, Partner, InscTerm), get_term_truth(InscTerm, MA, MB, MC, MD, InscTruth), regla_maker_cumplida(Maker, InscTruth).
    pairing(pairing1_ab_cd, b, a, d, c).
    pairing(pairing2_ad_cb, d, c, b, a).
    solucion(MA, MB, MC, MD, PairingName) :- es_maker(MA), es_maker(MB), es_maker(MC), es_maker(MD), pairing(PairingName, Pa, Pb, Pc, Pd), check_cofre(a, MA, Pa, MA, MB, MC, MD), check_cofre(b, MB, Pb, MA, MB, MC, MD), check_cofre(c, MC, Pc, MA, MB, MC, MD), check_cofre(d, MD, Pd, MA, MB, MC, MD).
    """

consulta = "solucion(MA, MB, MC, MD, PairingName)."

print(_ejecutar_prolog_con_traza_modificado(prolog_code, consulta))