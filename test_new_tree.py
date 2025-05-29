#!/usr/bin/env python3

from b import build_derivation_tree, reglas_completas_usuario

# Traza simplificada para probar la nueva funcionalidad
test_trace = """
   Call: (12) problema_tweedle(_1, _2, _3, _4, _5)
   Call: (13) _1=tweedledum
   Exit: (13) tweedledum=tweedledum
   Call: (13) _2=tweedledee
   Exit: (13) tweedledee=tweedledee
   Call: (13) dia(_5)
   Exit: (13) dia(jueves)
   Call: (13) reclama_identidad(persona1, _100)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Exit: (12) problema_tweedle(tweedledum, tweedledee, lion, unicorn, jueves)
"""

print("=== Probando nueva implementación de build_derivation_tree ===")
arboles = build_derivation_tree(test_trace, reglas_completas_usuario)

print(f"Número de árboles exitosos: {len(arboles)}")

if arboles:
    arbol = arboles[0]
    print(f"\nNodo raíz: {arbol.head_clause_instance}")
    print(f"Estado: {arbol.status}")
    print(f"Número de hijos directos: {len(arbol.children_nodes)}")
    
    def mostrar_estructura(nodo, nivel=0):
        indent = "  " * nivel
        print(f"{indent}- {nodo.head_clause_instance} ({nodo.status}) [depth: {nodo.depth}]")
        for hijo in nodo.children_nodes:
            mostrar_estructura(hijo, nivel + 1)
    
    print("\n=== Estructura del árbol ===")
    mostrar_estructura(arbol)
else:
    print("No se encontraron árboles exitosos") 