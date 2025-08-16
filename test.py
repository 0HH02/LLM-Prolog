#!/usr/bin/env python3
import json
import os
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys

# Importar las funciones necesarias
from main import run_main_with_problem  # Necesitaremos modificar main.py
from common.gemini_interface import ask_gemini_json
from test_checkpoints import TestCheckpointManager

def load_tests() -> List[Dict[str, Any]]:
    """Carga los tests desde tests/tests.json"""
    tests_file = Path("tests/tests.json")
    if not tests_file.exists():
        raise FileNotFoundError(f"El archivo {tests_file} no existe")
    
    with open(tests_file, 'r', encoding='utf-8') as f:
        tests = json.load(f)
    
    print(f"Cargados {len(tests)} tests desde {tests_file}")
    return tests

def evaluate_answer_with_gemini(problem_description: str, final_answer: str, expected_solution: str) -> Dict[str, Any]:
    """
    Evalúa si la respuesta final es correcta usando Gemini
    """
    prompt = f"""
Analiza si la respuesta final del modelo llegó a la misma conclusión que la solución esperada.

PROBLEMA:
{problem_description}

RESPUESTA DEL MODELO:
{final_answer}

SOLUCIÓN ESPERADA:
{expected_solution}

Por favor, evalúa si la respuesta del modelo es equivalente o llega a la misma conclusión lógica.
Considera que pueden usar palabras diferentes pero llegar a la misma conclusión lógica.

Devuelve ÚNICAMENTE un JSON con el siguiente formato:
{{
    "done": true/false
}}

Donde "done" es true si la respuesta del modelo es correcta/equivalente y false si no lo es.
"""
    
    try:
        #Configurar el squema de la respuesta
        config_schema = {
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "object",
                "properties": {
                    "done": {"type": "boolean"}
                },
                "required": ["done"]
            }
        }
        result = ask_gemini_json(prompt, "evaluacion_respuesta", config_schema)
        if result and "done" in result:
            return result
        else:
            print(f"Advertencia: Respuesta de Gemini no válida: {result}")
            return {"done": False}
    except Exception as e:
        print(f"Error al consultar Gemini: {e}")
        return {"done": False}

def run_test_suite(resume_from_checkpoint: bool = True, save_frequency: int = 1):
    """
    Ejecuta la suite completa de tests con soporte para checkpoints
    
    Args:
        resume_from_checkpoint: Si True, intentará cargar un checkpoint existente
        save_frequency: Frecuencia de guardado de checkpoints (cada N tests)
    """
    # Cargar tests
    tests = load_tests()
    results = []
    start_index = 0
    
    # Inicializar manager de checkpoints
    checkpoint_manager = TestCheckpointManager()
    
    # Intentar cargar checkpoint si se solicita
    if resume_from_checkpoint:
        checkpoint_data = checkpoint_manager.load_checkpoint(tests)
        if checkpoint_data:
            print(f"\n🔄 REANUDANDO DESDE CHECKPOINT")
            print(f"Progreso anterior: {checkpoint_data['completed_tests']}/{checkpoint_data['total_tests']} tests")
            
            results = checkpoint_data["results"]
            start_index = checkpoint_data["current_index"]
            
            response = input("¿Deseas continuar desde el checkpoint? (s/n): ").lower().strip()
            if response != 's':
                print("Iniciando desde el principio...")
                results = []
                start_index = 0
        else:
            print("No se encontró checkpoint previo. Iniciando desde el principio.")
    
    # Crear directorio de resultados si no existe
    solutions_dir = Path("solutions")
    solutions_dir.mkdir(exist_ok=True)
    tests_dir = solutions_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"INICIANDO SUITE DE TESTS - {len(tests)} tests totales")
    if start_index > 0:
        print(f"Reanudando desde test {start_index + 1}")
    print(f"{'='*70}")
    
    try:
        for index in range(start_index, len(tests)):
            test = tests[index]
            print(f"\n{'-'*50}")
            print(f"EJECUTANDO TEST {index + 1}/{len(tests)}")
            print(f"{'-'*50}")
            
            problem_description = test["problem_description"]
            expected_solution = test["solution"]
            
            print(f"Problema: {problem_description[:100]}...")
            
            try:
                # Ejecutar main.py con el problema
                print("Ejecutando sistema de razonamiento...")
                final_answer = run_main_with_problem(problem_description)
                
                print(f"Respuesta obtenida: {final_answer[:200]}...")
                
                # Evaluar con Gemini
                print("Evaluando respuesta con Gemini...")
                evaluation = evaluate_answer_with_gemini(
                    problem_description, 
                    final_answer, 
                    expected_solution
                )
                
                # Crear resultado
                result = {
                    "index": index,
                    "done": evaluation.get("done", False),
                    "final_answer": final_answer,
                    "problem_description": problem_description,
                    "expected_solution": expected_solution
                }
                
                results.append(result)
                
                status = "✅ CORRECTO" if result["done"] else "❌ INCORRECTO"
                print(f"Resultado: {status}")
                
            except Exception as e:
                print(f"❌ ERROR en test {index + 1}: {e}")
                result = {
                    "index": index,
                    "done": False,
                    "final_answer": f"ERROR: {str(e)}",
                    "problem_description": problem_description,
                    "expected_solution": expected_solution
                }
                results.append(result)
            
            # Guardar checkpoint cada N tests
            if (index + 1) % save_frequency == 0 or index == len(tests) - 1:
                print(f"\n💾 Guardando checkpoint... (Test {index + 1}/{len(tests)})")
                checkpoint_manager.save_checkpoint(
                    tests, 
                    results, 
                    index + 1,
                    {
                        "last_completed_test": index,
                        "test_name": test.get("name", f"Test_{index+1}")
                    }
                )
    
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Suite de tests interrumpida por el usuario en test {index + 1}")
        print("Guardando checkpoint antes de salir...")
        checkpoint_manager.save_checkpoint(
            tests, 
            results, 
            index,
            {"interrupted": True, "last_completed_test": len(results) - 1}
        )
        return results
    
    except Exception as e:
        print(f"\n❌ Error fatal en la suite de tests: {e}")
        print("Guardando checkpoint de emergencia...")
        checkpoint_manager.save_checkpoint(
            tests, 
            results, 
            index if 'index' in locals() else start_index,
            {"error": str(e), "emergency_save": True}
        )
        raise
    
    # Eliminar checkpoint exitoso al completar todos los tests
    if len(results) == len(tests):
        print("\n🗑️  Suite completada exitosamente. Eliminando checkpoint...")
        checkpoint_manager.delete_checkpoint(tests)
    
    # Guardar resultados
    results_file = tests_dir / "test_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Mostrar resumen
    print(f"\n{'='*70}")
    print(f"RESUMEN DE RESULTADOS")
    print(f"{'='*70}")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["done"])
    failed_tests = total_tests - passed_tests
    
    print(f"Total de tests: {total_tests}")
    print(f"Tests exitosos: {passed_tests}")
    print(f"Tests fallidos: {failed_tests}")
    print(f"Tasa de éxito: {(passed_tests/total_tests*100):.1f}%")
    
    print(f"\nResultados guardados en: {results_file}")
    
    # Mostrar detalles de tests fallidos
    failed_results = [r for r in results if not r["done"]]
    if failed_results:
        print(f"\nDETALLES DE TESTS FALLIDOS:")
        for result in failed_results:
            print(f"\nTest {result['index'] + 1}:")
            print(f"  Problema: {result['problem_description'][:100]}...")
            print(f"  Respuesta: {result['final_answer'][:150]}...")
    
    return results

def main():
    """
    Función principal con argumentos de línea de comandos
    """
    parser = argparse.ArgumentParser(description="Suite de tests con sistema de checkpoints")
    parser.add_argument("--no-checkpoint", action="store_true", 
                       help="No usar checkpoints (iniciar desde el principio)")
    parser.add_argument("--save-frequency", type=int, default=1,
                       help="Frecuencia de guardado de checkpoints (cada N tests)")
    parser.add_argument("--list-checkpoints", action="store_true",
                       help="Listar checkpoints disponibles")
    parser.add_argument("--cleanup-checkpoints", type=int, metavar="DAYS",
                       help="Limpiar checkpoints más antiguos que N días")
    parser.add_argument("--delete-checkpoints", action="store_true",
                       help="Eliminar todos los checkpoints de tests")
    
    args = parser.parse_args()
    
    checkpoint_manager = TestCheckpointManager()
    
    # Operaciones de gestión de checkpoints
    if args.list_checkpoints:
        print("📋 CHECKPOINTS DISPONIBLES:")
        checkpoints = checkpoint_manager.list_checkpoints()
        if not checkpoints:
            print("No hay checkpoints disponibles.")
        else:
            for cp in checkpoints:
                print(f"  • {cp['suite_id'][:8]}... - {cp['timestamp']} - "
                      f"{cp['completed_tests']}/{cp['total_tests']} tests "
                      f"({cp['progress_percent']:.1f}%)")
        return
    
    if args.cleanup_checkpoints:
        print(f"🧹 Limpiando checkpoints más antiguos que {args.cleanup_checkpoints} días...")
        deleted = checkpoint_manager.cleanup_old_checkpoints(args.cleanup_checkpoints)
        print(f"Eliminados {deleted} checkpoints antiguos.")
        return
    
    if args.delete_checkpoints:
        # Eliminar todos los checkpoints
        import shutil
        if checkpoint_manager.checkpoint_dir.exists():
            response = input("⚠️  ¿Estás seguro de eliminar TODOS los checkpoints? (s/n): ")
            if response.lower().strip() == 's':
                shutil.rmtree(checkpoint_manager.checkpoint_dir)
                print("🗑️  Todos los checkpoints eliminados.")
            else:
                print("Operación cancelada.")
        else:
            print("No hay checkpoints para eliminar.")
        return
    
    # Ejecutar suite de tests
    print("Iniciando suite de tests...")
    try:
        results = run_test_suite(
            resume_from_checkpoint=not args.no_checkpoint,
            save_frequency=args.save_frequency
        )
        print("\nSuite de tests completada.")
    except KeyboardInterrupt:
        print("\n\nSuite de tests interrumpida por el usuario.")
        sys.exit(1)

if __name__ == "__main__":
    # Comentar la ejecución anterior y usar la nueva función main
    main()
    
    # Código original comentado:
    # print("Iniciando suite de tests...")
    # try:
    #     results = run_test_suite()
    #     print("\nSuite de tests completada.")
    # except KeyboardInterrupt:
    #     print("\n\nSuite de tests interrumpida por el usuario.")
    #     sys.exit(1)
    # # except Exception as e:
    # #     print(f"\nError fatal en la suite de tests: {e}")
    # #     sys.exit(1) 