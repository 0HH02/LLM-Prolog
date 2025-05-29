#!/usr/bin/env python3

from b import build_derivation_tree, visualizar_arbol_derivacion_con_variables, reglas_completas_usuario

# Traza simplificada para probar el visualizador
test_trace = """
   Call: (12) problema_tweedle(_1, _2, _3, _4, _5)
   Call: (13) _1=tweedledum
   Exit: (13) tweedledum=tweedledum
   Call: (13) _2=tweedledee
   Exit: (13) tweedledee=tweedledee
   Call: (13) tweedledum\=tweedledee
   Exit: (13) tweedledum\=tweedledee
   Call: (13) _3=lion
   Exit: (13) lion=lion
   Call: (13) _4=unicorn
   Exit: (13) unicorn=unicorn
   Call: (13) lion\=unicorn
   Exit: (13) lion\=unicorn
   Call: (13) dia(_5)
   Exit: (13) dia(jueves)
   Call: (13) reclama_identidad(persona1, _100)
   Exit: (13) reclama_identidad(persona1, tweedledum)
   Exit: (12) problema_tweedle(tweedledum, tweedledee, lion, unicorn, jueves)
"""

print("=== Probando nuevo visualizador ===")
arboles = build_derivation_tree(test_trace, reglas_completas_usuario)

print(f"Número de árboles exitosos: {len(arboles)}")

if arboles:
    print("Generando visualización...")
    grafo = visualizar_arbol_derivacion_con_variables(arboles)
    
    try:
        grafo.render('test_arbol_variables', view=False, format='png')
        print("✅ Grafo guardado como test_arbol_variables.png")
        print("El grafo muestra:")
        print("  🔍 Nodos con variables (rectangulares, azules)")
        print("  ✓ Nodos de instanciación (elípticos, verdes)")
        print("  ⬢ Nodos de hechos (hexagonales)")
        print("  → Aristas sólidas para relaciones padre-hijo")
        print("  ⇢ Aristas punteadas para instanciaciones")
    except Exception as e:
        print(f"❌ Error al renderizar el grafo: {e}")
else:
    print("❌ No se encontraron árboles exitosos") 