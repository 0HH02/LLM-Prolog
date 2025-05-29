# axiom_libraries/example_axioms.py

# Cada string en esta lista debe ser una cláusula de Horn válida.
# Estas cláusulas podrán ser cargadas directamente en el KR-Store.

AXIOM_CLAUSES = [
    "not(not(verdadero(A))) :- verdadero(A).",
    "implica(verdadero(A), verdadero(B)) :- not(verdadero(A)) ; verdadero(B).",
    "equivalente(A, B) :- implica(A, B), implica(B, A).",
    "not(not(verdadero(A))) :- verdadero(A).",
    "not(A) :- implica(A, falso(X)).",
    
]

# Metadatos opcionales sobre esta biblioteca de axiomas
METADATA = {
    "name": "logica_base",
    "description": "Una colección de axiomas de ejemplo que cubren las leyes de la lógica proposicional.",
    "version": "0.1.0",
    "author": "Sistema INSIGhT"
}

# Podrías también tener funciones que generen cláusulas si son muy numerosas o siguen un patrón:
# def generar_axiomas_matematicos_basicos():
#   axiomas = []
#   for i in range(10):
#       axiomas.append(f"numero({i}).")
#       axiomas.append(f"sucesor({i+1}, {i}).")
#   return axiomas
#
# AXIOM_CLAUSES.extend(generar_axiomas_matematicos_basicos()) 