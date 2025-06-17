// --- LÓGICA DE PROCESAMIENTO DE TRAZAS (Adaptada del código Python c.py) ---

class Clausula {
  constructor(
    nombre,
    origen = "<dynamic>:0",
    veracidad = "",
    profundidad = 0,
    padre = null
  ) {
    this.nombre = nombre;
    this.origen = origen;
    this.veracidad = veracidad; // "", "verde", "rojo"
    this.profundidad = profundidad;
    this.padre = padre;
    this.valor = []; // list[Clausula]
    this.id = Clausula.nextId++; // ID único para cada nodo
  }

  // Generador de ID para los nodos, crucial para vis.js
  static nextId = 0;

  toDict() {
    const d = {
      nombre: this.nombre,
      origen: this.origen,
      veracidad: this.veracidad,
      profundidad: this.profundidad,
    };
    if (this.valor.length > 0) {
      d.valor = this.valor.map((h) => h.toDict());
    }
    return d;
  }

  prettyPrint(indentLevel = 0) {
    const indent = "  ".repeat(indentLevel);
    const output = [];
    output.push(`${indent}{`);
    output.push(`${indent}  "nombre": "${this.nombre}",`);

    const veracidadLine = `${indent}  "veracidad": "${this.veracidad}"`;

    if (this.valor.length > 0) {
      output.push(veracidadLine + ",");
      output.push(`${indent}  "valor": [`);
      const childStrings = this.valor.map((child) =>
        child.prettyPrint(indentLevel + 2)
      );
      output.push(childStrings.join(",\n"));
      output.push(`${indent}  ]`);
    } else {
      output.push(veracidadLine);
    }

    output.push(`${indent}}`);
    return output.join("\n");
  }
}

function procesarTraza(trazaStr) {
  const ramasDePensamientos = [];
  const rangosDeLineas = []; // Nuevo: guardar el rango de líneas para cada árbol
  let root = new Clausula("root");
  let nodoActual = root;
  let inicioArbolActual = 0; // Índice donde inicia el árbol actual

  // Regex mejorada para capturar el formato completo
  const lineRegex =
    /^\s*(call|exit|fail|redo)(?:\(\d+\))?:\s*([^@]+?)\s*(?:@.*)?$/;

  const traza = trazaStr
    .trim()
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  traza.forEach((lineRaw, index) => {
    const match = lineRegex.exec(lineRaw);
    if (!match) {
      console.warn(`No se pudo parsear la línea: ${lineRaw}`);
      return;
    }

    const [, tipoLlamada, contenidoStr] = match;

    if (tipoLlamada === "call") {
      if (contenidoStr === "fail") return;

      const nuevaClausula = new Clausula(
        contenidoStr,
        "<dynamic>:0",
        "",
        nodoActual.profundidad + 1,
        nodoActual
      );
      nodoActual.valor.push(nuevaClausula);
      nodoActual = nuevaClausula;
    } else if (tipoLlamada === "exit") {
      const exitingNode = nodoActual;

      // Si el array valor está vacío, crear una cláusula resultado
      if (exitingNode.valor.length === 0) {
        const clausulaResultado = new Clausula(
          contenidoStr,
          "<dynamic>:0",
          "verde",
          exitingNode.profundidad + 1,
          exitingNode
        );
        exitingNode.valor.push(clausulaResultado);
      }
      exitingNode.veracidad = "verde";

      if (exitingNode.padre) {
        nodoActual = exitingNode.padre;
      }
    } else if (tipoLlamada === "fail") {
      if (contenidoStr === "fail") return;

      const failingNode = nodoActual;

      // Si el array valor está vacío, crear una cláusula resultado
      if (failingNode.valor.length === 0) {
        const clausulaResultado = new Clausula(
          contenidoStr,
          "<dynamic>:0",
          "rojo",
          failingNode.profundidad + 1,
          failingNode
        );
        failingNode.valor.push(clausulaResultado);
      }
      failingNode.veracidad = "rojo";

      if (failingNode.padre) {
        nodoActual = failingNode.padre;
      }
    } else if (tipoLlamada === "redo") {
      // Marcar nodos como rojos hasta llegar al padre
      while (nodoActual.padre) {
        nodoActual.veracidad = "rojo";
        nodoActual = nodoActual.padre;
      }

      // Hacer copia profunda del árbol y guardar el rango de líneas
      ramasDePensamientos.push(JSON.parse(JSON.stringify(root.toDict())));
      rangosDeLineas.push({
        inicio: inicioArbolActual,
        fin: index,
        redoLinea: index,
      });

      // Buscar el nodo a rehacer usando BFS
      const q = [root];
      let nodeToRedoFound = null;
      const visitedForBfs = new Set();
      let lastFound = null;
      let lastLastFound = null;

      while (q.length > 0) {
        const currSearchNode = q.shift();

        if (visitedForBfs.has(currSearchNode.id)) {
          continue;
        }
        visitedForBfs.add(currSearchNode.id);

        // Extraer nombre y aridad del nodo actual
        const currNombre = currSearchNode.nombre.split("(")[0].trim();
        const currAridadMatch = currSearchNode.nombre.match(/\((.*)\)/);
        const currAridad = currAridadMatch
          ? currAridadMatch[1].split(",").length
          : 0;

        // Extraer nombre y aridad del contenido
        const contNombre = contenidoStr.split("(")[0].trim();
        const contAridadMatch = contenidoStr.match(/\((.*)\)/);
        const contAridad = contAridadMatch
          ? contAridadMatch[1].split(",").length
          : 0;

        // Comparar nombre y aridad
        if (currNombre === contNombre && currAridad === contAridad) {
          lastLastFound = lastFound;
          lastFound = currSearchNode;
        }

        if (currSearchNode.nombre === contenidoStr) {
          nodeToRedoFound = currSearchNode;
        }

        if (currSearchNode.valor && Array.isArray(currSearchNode.valor)) {
          currSearchNode.valor.forEach((child) => {
            if (child && typeof child === "object") {
              q.push(child);
            }
          });
        }
      }

      if (!nodeToRedoFound) {
        if (lastFound) {
          nodeToRedoFound = lastFound;
          nodeToRedoFound.nombre = contenidoStr;
          console.log(
            "Solo se encontró un nodo con igual nombre, aridad y profundidad"
          );
        }
      }

      if (nodeToRedoFound) {
        // Lógica correcta de limpieza basada en c.py
        // No eliminar todo el árbol, solo los nodos que vinieron después del redo

        if (index + 1 < traza.length) {
          const nextClausule = traza[index + 1];
          const nextMatch = lineRegex.exec(nextClausule);
          if (nextMatch) {
            const nextContenido = nextMatch[2].trim();
            const nombre = nextContenido.split("(")[0].trim();
            const aridadMatch = nextContenido.match(/\((.*)\)/);
            const aridad = aridadMatch ? aridadMatch[1].split(",").length : 0;

            // Si hay hijos en el nodo del redo
            if (nodeToRedoFound.valor.length > 0) {
              let found = false;
              for (let i = 0; i < nodeToRedoFound.valor.length; i++) {
                const clausula = nodeToRedoFound.valor[i];
                const clausulaNombre = clausula.nombre.split("(")[0].trim();
                const clausulaAridadMatch = clausula.nombre.match(/\((.*)\)/);
                const clausulaAridad = clausulaAridadMatch
                  ? clausulaAridadMatch[1].split(",").length
                  : 0;

                // Si encontramos el nodo que coincide con la siguiente línea
                if (clausulaNombre === nombre && clausulaAridad === aridad) {
                  // Mantener solo hasta este índice (inclusive)
                  nodeToRedoFound.valor = nodeToRedoFound.valor.slice(0, i + 1);
                  found = true;
                  break;
                }
              }
              // Si no se encontró coincidencia, limpiar completamente
              if (!found) {
                nodeToRedoFound.valor = [];
              }
            }
          }
        }

        // Reiniciar el estado de veracidad del nodo del redo
        nodeToRedoFound.veracidad = "";
        nodoActual = nodeToRedoFound;

        // Limpiar hacia arriba en la jerarquía: mantener solo hasta el índice del nodo actual
        let current = nodeToRedoFound;
        while (current.padre) {
          const indice = current.padre.valor.indexOf(current);
          // Truncar el array de valor del padre hasta el índice encontrado (inclusive)
          current.padre.valor = current.padre.valor.slice(0, indice + 1);
          current = current.padre;
        }
      }

      // Reiniciar para el siguiente árbol
      inicioArbolActual = index + 1;
    }
  });

  // Añadir el estado final y su rango
  ramasDePensamientos.push(JSON.parse(JSON.stringify(root.toDict())));
  rangosDeLineas.push({
    inicio: inicioArbolActual,
    fin: traza.length - 1,
    redoLinea: null, // El último árbol no termina en redo
  });

  return {
    arboles: ramasDePensamientos,
    rangos: rangosDeLineas,
  };
}

// --- LÓGICA DE LA INTERFAZ WEB ---

document.addEventListener("DOMContentLoaded", () => {
  // Contenedores y botones del DOM
  const treeContainer = document.getElementById("tree-container");
  const traceContainer = document.getElementById("trace-container");
  const nextBtn = document.getElementById("next-btn");
  const stepBtn = document.getElementById("step-btn");
  const fileInput = document.getElementById("file-input");
  const loadBtn = document.getElementById("load-btn");
  const resetBtn = document.getElementById("reset-btn");

  // Traza de ejemplo por defecto
  let currentTraceStr = `call: catch((solucion(_4650,_4652,_4654,_4656,_4658),fail),_4670,(format(user_error,'~N### CAUGHT_EXCEPTION ###~n~w~n### END_EXCEPTION ###~n',[_4670]),fail)) @ <dynamic>:0
                        call: solucion(_4650,_4652,_4654,_4656,_4658) @ <dynamic>:0
                          call: posibles_parejas(_7690) @ <dynamic>:0
                          exit: posibles_parejas([[(a,b),(c,d)],[(a,d),(c,b)]]) @ /tmp/tmpv4goqdt7.pl:27
                          call: lists:member(_4658,[[(a,b),(c,d)],[(a,d),(c,b)]]) @ <dynamic>:0
                          exit: lists:member([(a,b),(c,d)],[[(a,b),(c,d)],[(a,d),(c,b)]]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4650,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4652,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4654,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15386=[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]=[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15586,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15586),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16046,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16046),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16046),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16046),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16046,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16046,a),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((_16046,a),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(a,_16046,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15586),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15586),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15586,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15458=[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]=[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15658,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15658),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16118,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16118),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16118),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16118),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16118,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16118,a),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((_16118,a),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(a,_16118,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15658),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15658),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15658,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4654,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15458=[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]=[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15658,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15658),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16118,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16118),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16118),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16118),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16118,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16118,a),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((_16118,a),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(a,_16118,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15658),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15658),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15658,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15530=[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]=[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15730,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16190,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16190),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16190),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16190),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16190,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16190,a),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((_16190,a),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(a,_16190,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15730,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4652,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4654,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15458=[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]=[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15658,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15658),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16118,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16118),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:32
                            exit: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16726,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16726),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:33
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16726),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16726),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16726,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16118),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16118),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16118,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16118,a),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((_16118,a),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(a,_16118,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15658),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15658),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15658,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15530=[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]=[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15730,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16190,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16190),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:32
                            exit: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16798,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16798),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:33
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16798),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16798),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16798,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16190),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16190),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16190,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16190,a),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((_16190,a),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(a,_16190,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15730,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4654,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15530=[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]=[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15730,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16190,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16190),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:32
                            exit: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16798,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16798),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:33
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16798),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16798),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16798,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16190),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16190),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16190,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16190,a),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((_16190,a),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(a,_16190,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15730,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15602=[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]=[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15802,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15802),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16262,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16262),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:32
                            exit: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16870,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16870),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:33
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16870),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16870),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16870,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16262),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16262),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16262,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16262,a),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((_16262,a),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(a,_16262,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15802),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15802),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15802,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4650,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4652,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4654,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15458=[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]=[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15658,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15658),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16150,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16150),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16150),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16150),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16150,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16150,a),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((_16150,a),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(a,_16150,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(25): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                            exit: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16224,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16224),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              redo(16): inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:33
                                call: get_partner(b,_16752,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((b,_16752),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((b,_16752),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(b,_16752,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16752,b),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(b,a,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                call: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                                call: get_autor(a,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(a,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(a,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(a,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((_16752,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((_16752,b),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(b,_16752,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16224),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16224),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16224,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15658),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15658),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15658,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15530=[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]=[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15730,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15730),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16222,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16222),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16222),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16222),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16222,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16222,a),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((_16222,a),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(a,_16222,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(25): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                            exit: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16296,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16296),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              redo(16): inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:33
                                call: get_partner(b,_16824,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((b,_16824),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((b,_16824),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(b,_16824,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16824,b),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(b,a,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                call: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                                call: get_autor(a,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(a,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(a,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(a,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member((_16824,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((_16824,b),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(b,_16824,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16296),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16296),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16296,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15730),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15730),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15730,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4654,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15530=[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]=[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15730,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15730),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16222,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16222),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16222),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16222),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16222,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16222,a),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((_16222,a),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(a,_16222,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(25): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                            exit: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16296,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16296),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              redo(16): inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:33
                                call: get_partner(b,_16824,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((b,_16824),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((b,_16824),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(b,_16824,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16824,b),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(b,a,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                call: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                                call: get_autor(a,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(a,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(a,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(a,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((_16824,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((_16824,b),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(b,_16824,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16296),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16296),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16296,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15730),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15730),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15730,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15602=[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]=[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15802,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16294,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16294),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16294),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16294),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16294,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16294,a),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((_16294,a),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(a,_16294,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(25): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                            exit: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16368,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16368),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              redo(16): inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:33
                                call: get_partner(b,_16896,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((b,_16896),[(a,b),(c,d)]) @ <dynamic>:0
                                  fail: lists:member((b,_16896),[(a,b),(c,d)]) @ <dynamic>:0
                                redo(0): get_partner(b,_16896,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16896,b),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(b,a,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:30
                                call: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                                call: get_autor(a,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(a,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(a,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(a,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member((_16896,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((_16896,b),[(a,b),(c,d)]) @ <dynamic>:0
                                fail: get_partner(b,_16896,[(a,b),(c,d)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16368),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16368),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16368,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15802,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4652,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4654,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15530=[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]=[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15730,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15730),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16222,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16222),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:32
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15730),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15730),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15730,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15602=[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]=[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15802,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16294,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16294),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:32
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15802,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4654,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15602=[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]=[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15802,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16294,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16294),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:32
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15802,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15674=[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]=[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                            call: get_autor(a,_15874,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15874),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                                call: get_partner(a,_16366,[(a,b),(c,d)]) @ <dynamic>:0
                                  call: lists:member((a,_16366),[(a,b),(c,d)]) @ <dynamic>:0
                                  exit: lists:member((a,b),[(a,b),(c,d)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,b,[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ /tmp/tmpv4goqdt7.pl:32
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15874),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15874),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15874,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,b),(c,d)]) @ <dynamic>:0
                          redo(0): lists:member(_4658,[[(a,b),(c,d)],[(a,d),(c,b)]]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member([(a,d),(c,b)],[[(a,b),(c,d)],[(a,d),(c,b)]]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4650,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4652,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4654,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15458=[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]=[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15658,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15658),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16118,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16118),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(d,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16118),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16118),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16118,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16118,a),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((_16118,a),[(a,d),(c,b)]) @ <dynamic>:0
                                fail: get_partner(a,_16118,[(a,d),(c,b)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15658),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15658),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15658,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15530=[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]=[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15730,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16190,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16190),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(d,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:32
                            exit: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16798,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16798),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              redo(16): inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:33
                                call: get_partner(b,_17326,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((b,_17326),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((b,_17326),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(b,_17326,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_17326,b),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((c,b),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(b,c,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                call: get_autor(b,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                                call: get_autor(c,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(c,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(c,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(c,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:33
                            exit: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(c,_18244,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(c,_18244),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(c,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(c,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(c,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(c,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_autor(c,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(c,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(c,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(c,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(c,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:34
                            exit: (bellini=bellini)log_equiv inscripcion_verdadera_en(c,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(d,_19068,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(d,_19068),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(d,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(d,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(d,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(d,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(d,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(d,_19560,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((d,_19560),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((d,_19560),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(d,_19560,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_19560,d),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(d,a,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                call: get_autor(a,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(d,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:35
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(d,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(c,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(c,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(c,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(c,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(c,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(c,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(c,_18244),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(c,_18244),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(c,_18244,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(c,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(c,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(c,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(b,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(b,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(b,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16798),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16798),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16798,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16190),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16190),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16190,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16190,a),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((_16190,a),[(a,d),(c,b)]) @ <dynamic>:0
                                fail: get_partner(a,_16190,[(a,d),(c,b)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15730,[cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4654,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15530=[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]=[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15730,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16190,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16190),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(d,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16190),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16190),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16190,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16190,a),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((_16190,a),[(a,d),(c,b)]) @ <dynamic>:0
                                fail: get_partner(a,_16190,[(a,d),(c,b)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15730,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15602=[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]=[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15802,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15802),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16262,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16262),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(d,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:32
                            exit: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16870,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16870),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              redo(16): inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:33
                                call: get_partner(b,_17398,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((b,_17398),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((b,_17398),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(b,_17398,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_17398,b),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((c,b),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(b,c,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                call: get_autor(b,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                                call: get_autor(c,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(c,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(c,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(c,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(b,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(b,bellini),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                fail: get_autor(b,bellini,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16870),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16870),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16870,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16262),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16262),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16262,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16262,a),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((_16262,a),[(a,d),(c,b)]) @ <dynamic>:0
                                fail: get_partner(a,_16262,[(a,d),(c,b)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15802),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15802),[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15802,[cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4652,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4654,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15530=[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]=[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15730,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16190,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16190),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(d,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16190),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16190),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16190,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16190,a),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((_16190,a),[(a,d),(c,b)]) @ <dynamic>:0
                                fail: get_partner(a,_16190,[(a,d),(c,b)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15730),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15730,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15602=[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]=[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15802,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15802),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16262,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16262),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(d,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:32
                            exit: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16870,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16870),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:33
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16870),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16870),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16870,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16262),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16262),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16262,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16262,a),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((_16262,a),[(a,d),(c,b)]) @ <dynamic>:0
                                fail: get_partner(a,_16262,[(a,d),(c,b)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15802),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15802),[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15802,[cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4654,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15602=[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]=[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15802,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15802),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16262,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16262),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(d,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16262),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16262),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16262,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16262,a),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((_16262,a),[(a,d),(c,b)]) @ <dynamic>:0
                                fail: get_partner(a,_16262,[(a,d),(c,b)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15802),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15802),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15802,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15674=[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]=[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15874,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15874),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,bellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,bellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16334,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16334),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(d,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(d,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:32
                            exit: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16942,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16942),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:33
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16942),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16942),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16942,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16334),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16334),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16334,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16334,a),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((_16334,a),[(a,d),(c,b)]) @ <dynamic>:0
                                fail: get_partner(a,_16334,[(a,d),(c,b)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15874),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15874),[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15874,[cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,bellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4650,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4652,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4654,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15530=[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]=[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15730,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15730),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16222,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16222),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(d,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16222),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16222),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16222,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16222,a),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((_16222,a),[(a,d),(c,b)]) @ <dynamic>:0
                                fail: get_partner(a,_16222,[(a,d),(c,b)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(25): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            exit: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16296,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16296),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              redo(16): inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:33
                                call: get_partner(b,_16824,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((b,_16824),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((b,_16824),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(b,_16824,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16824,b),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((c,b),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(b,c,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                call: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                                call: get_autor(c,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(c,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(c,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(c,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:33
                            exit: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(c,_17742,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(c,_17742),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(c,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(c,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(c,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(c,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_autor(c,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(c,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(c,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(c,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(c,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:34
                            exit: (bellini=bellini)log_equiv inscripcion_verdadera_en(c,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(d,_18566,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(d,_18566),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(d,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(d,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(d,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(d,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(d,_19026,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((d,_19026),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((d,_19026),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(d,_19026,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_19026,d),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(d,a,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                call: get_autor(a,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(a,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(a,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(a,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((_19026,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((_19026,d),[(a,d),(c,b)]) @ <dynamic>:0
                                fail: get_partner(d,_19026,[(a,d),(c,b)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(d,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(d,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(d,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(c,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(c,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(c,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(c,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(c,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(c,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(c,_17742),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(c,_17742),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(c,_17742,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(c,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(c,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(c,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16296),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16296),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16296,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15730),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15730),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15730,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15602=[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]=[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15802,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16294,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16294),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(d,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:32
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15802,[cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4654,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15602=[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]=[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15802,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16294,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16294),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(d,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16294),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16294),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16294,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16294,a),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((_16294,a),[(a,d),(c,b)]) @ <dynamic>:0
                                fail: get_partner(a,_16294,[(a,d),(c,b)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(25): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            exit: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16368,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16368),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                              call: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(b,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              redo(16): inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:33
                                call: get_partner(b,_16896,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((b,_16896),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((b,_16896),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(b,_16896,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16896,b),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((c,b),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(b,c,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                call: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                                call: get_autor(c,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(c,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(c,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(c,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member(cofre(b,bellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(b,bellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(9): (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: bellini=bellini @ <dynamic>:0
                              exit: bellini=bellini @ <dynamic>:0
                            fail: (bellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16368),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16368),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16368,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15802,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15674=[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]=[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15874,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15874),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16366,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16366),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(d,cellini,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:32
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15874),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15874),[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15874,[cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,bellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4652,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4654,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15602=[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]=[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15802,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16294,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16294),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(d,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16294),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16294),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16294,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16294,a),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((_16294,a),[(a,d),(c,b)]) @ <dynamic>:0
                                fail: get_partner(a,_16294,[(a,d),(c,b)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(25): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            exit: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16368,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16368),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:33
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16368),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16368),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16368,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15802),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15802,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15674=[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]=[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15874,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15874),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16366,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16366),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(d,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:32
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15874),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15874),[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15874,[cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,bellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4654,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: lists:member(_4656,[bellini,cellini]) @ <dynamic>:0
                          exit: lists:member(bellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15674=[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]=[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15874,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15874),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16366,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16366),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  fail: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                fail: get_autor(d,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  redo(0): lists:member((a,_16366),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                  fail: lists:member((a,_16366),[(a,d),(c,b)]) @ <dynamic>:0
                                redo(0): get_partner(a,_16366,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:30
                                  call: lists:member((_16366,a),[(a,d),(c,b)]) @ <dynamic>:0
                                  fail: lists:member((_16366,a),[(a,d),(c,b)]) @ <dynamic>:0
                                fail: get_partner(a,_16366,[(a,d),(c,b)]) @ <dynamic>:0
                              fail: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            redo(25): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            exit: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                            call: get_autor(b,_16440,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              call: lists:member(cofre(b,_16440),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(b,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_autor(b,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(b,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(b,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:33
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(b,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(b,_16440),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(b,_16440),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(b,_16440,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15874),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15874),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15874,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,bellini)],[(a,d),(c,b)]) @ <dynamic>:0
                          redo(0): lists:member(_4656,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          exit: lists:member(cellini,[bellini,cellini]) @ /usr/lib/swi-prolog/library/lists.pl:121
                          call: _15746=[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          exit: [cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]=[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)] @ <dynamic>:0
                          call: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                            call: get_autor(a,_15946,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              call: lists:member(cofre(a,_15946),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                              exit: lists:member(cofre(a,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                            exit: get_autor(a,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                            call: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(9): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: cellini=bellini @ <dynamic>:0
                              fail: cellini=bellini @ <dynamic>:0
                            redo(17): (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:36
                              call: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                                call: get_partner(a,_16438,[(a,d),(c,b)]) @ <dynamic>:0
                                  call: lists:member((a,_16438),[(a,d),(c,b)]) @ <dynamic>:0
                                  exit: lists:member((a,d),[(a,d),(c,b)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_partner(a,d,[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:29
                                call: get_autor(d,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  call: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                                  exit: lists:member(cofre(d,cellini),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                                exit: get_autor(d,cellini,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /tmp/tmpv4goqdt7.pl:31
                              exit: inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ /tmp/tmpv4goqdt7.pl:32
                            fail: (cellini=bellini)log_equiv inscripcion_verdadera_en(a,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                              redo(0): lists:member(cofre(a,_15946),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ /usr/lib/swi-prolog/library/lists.pl:121
                              fail: lists:member(cofre(a,_15946),[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                            fail: get_autor(a,_15946,[cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)]) @ <dynamic>:0
                          fail: es_estado_consistente([cofre(a,cellini),cofre(b,cellini),cofre(c,cellini),cofre(d,cellini)],[(a,d),(c,b)]) @ <dynamic>:0
                        fail: solucion(_4650,_4652,_4654,_4656,_4658) @ <dynamic>:0`;

  let fullTraceLines = [];
  let completeTrees = [];
  let treeRanges = []; // Nuevo: rangos de líneas para cada árbol
  let currentTreeIndex = 0;
  let currentLineIndex = 0;
  let network = null;
  let stepByStepMode = false;

  // Función para cargar y mostrar la traza
  function loadTrace(traceStr) {
    currentTraceStr = traceStr;
    fullTraceLines = traceStr
      .trim()
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);

    traceContainer.innerHTML = fullTraceLines
      .map((line, index) => `<div data-line="${index}">${line}</div>`)
      .join("");

    // Reiniciar variables
    completeTrees = [];
    treeRanges = [];
    currentTreeIndex = 0;
    currentLineIndex = 0;
    stepByStepMode = false;

    // Habilitar botones
    nextBtn.disabled = false;
    stepBtn.disabled = false;

    console.log(`Traza cargada con ${fullTraceLines.length} líneas`);
  }

  // Función para dibujar/actualizar el árbol
  function drawTree(treeData) {
    const nodes = [];
    const edges = [];
    const levelInfo = new Map(); // Para rastrear cuántos nodos hay en cada nivel

    function traverse(node, parentId, level = 0) {
      const nodeId = `node_${nodes.length}`;

      // Rastrear información del nivel
      if (!levelInfo.has(level)) {
        levelInfo.set(level, 0);
      }
      levelInfo.set(level, levelInfo.get(level) + 1);

      nodes.push({
        id: nodeId,
        label: node.nombre,
        level: level, // Asignar nivel explícitamente
        color: {
          background:
            node.veracidad === "verde"
              ? "#90EE90"
              : node.veracidad === "rojo"
              ? "#FFB6C1"
              : "#ADD8E6",
          border: "#2B7CE9",
        },
        shape: "box",
        font: { size: 14 },
        margin: 15, // Aumentar margen interno
        widthConstraint: { minimum: 120, maximum: 300 }, // Controlar ancho
      });

      if (parentId !== null) {
        edges.push({ from: parentId, to: nodeId });
      }

      if (node.valor && Array.isArray(node.valor)) {
        node.valor.forEach((child) => traverse(child, nodeId, level + 1));
      }

      return nodeId;
    }

    const rootId = traverse(treeData, null);

    // Calcular espaciado dinámico basado en el número de nodos
    const maxNodesInLevel = Math.max(...Array.from(levelInfo.values()));
    const dynamicNodeSpacing = Math.max(150, maxNodesInLevel * 20); // Espaciado mínimo de 150
    const dynamicLevelSeparation = 180; // Separación vertical entre niveles

    const data = {
      nodes: new vis.DataSet(nodes),
      edges: new vis.DataSet(edges),
    };

    const options = {
      layout: {
        hierarchical: {
          direction: "UD", // Up-Down
          sortMethod: "directed",
          nodeSpacing: dynamicNodeSpacing, // Espaciado horizontal dinámico
          levelSeparation: dynamicLevelSeparation, // Separación vertical entre niveles
          treeSpacing: 200, // Espacio entre diferentes árboles
          blockShifting: true, // Permite mover bloques para evitar solapamiento
          edgeMinimization: true, // Minimiza cruces de aristas
          parentCentralization: true, // Centra padres sobre sus hijos
          shakeTowards: "leaves", // Optimiza hacia las hojas
        },
      },
      physics: {
        enabled: false, // Deshabilitado para layout fijo
      },
      nodes: {
        margin: 15,
        borderWidth: 2,
        borderWidthSelected: 3,
        font: {
          size: 12,
          face: "Arial",
          align: "center",
        },
        chosen: {
          node: function (values, id, selected, hovering) {
            values.borderWidth = 3;
          },
        },
      },
      edges: {
        arrows: {
          to: { enabled: true, scaleFactor: 1.2 },
        },
        smooth: {
          type: "cubicBezier",
          forceDirection: "vertical",
          roundness: 0.4,
        },
        width: 2,
        color: {
          color: "#2B7CE9",
          highlight: "#2B7CE9",
          hover: "#2B7CE9",
        },
      },
      interaction: {
        hover: true,
        selectConnectedEdges: false,
      },
    };

    if (network) {
      network.destroy();
    }
    network = new vis.Network(treeContainer, data, options);

    // Ajustar la vista para mostrar todo el árbol
    network.once("afterDrawing", function () {
      network.fit({
        nodes: nodes.map((n) => n.id),
        animation: {
          duration: 500,
          easingFunction: "easeInOutQuad",
        },
      });
    });
  }

  // Resalta la línea actual en el panel de traza
  function highlightTraceLine(index) {
    const divs = traceContainer.querySelectorAll("div");
    divs.forEach((div, i) => {
      div.classList.toggle("highlight", i === index);
    });
    if (divs[index]) {
      divs[index].scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  // --- Event Listeners ---

  // Cargar archivo
  loadBtn.addEventListener("click", () => {
    fileInput.click();
  });

  fileInput.addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        loadTrace(e.target.result);
        drawInitialTree();
      };
      reader.readAsText(file);
    }
  });

  // Reiniciar
  resetBtn.addEventListener("click", () => {
    loadTrace(currentTraceStr);
    drawInitialTree();
  });

  // Botón "Saltar al Siguiente Árbol"
  nextBtn.addEventListener("click", () => {
    if (!completeTrees.length) {
      const result = procesarTraza(currentTraceStr);
      completeTrees = result.arboles;
      treeRanges = result.rangos;
    }

    if (completeTrees.length > 0) {
      drawTree(completeTrees[currentTreeIndex]);

      // Actualizar currentLineIndex para que apunte al final del árbol actual
      if (treeRanges[currentTreeIndex]) {
        currentLineIndex = treeRanges[currentTreeIndex].fin + 1;
      }

      // Mostrar información del árbol actual
      const info = document.getElementById("tree-info");
      if (info) {
        const rangoActual = treeRanges[currentTreeIndex];
        const tipoFinalizacion =
          rangoActual && rangoActual.redoLinea !== null
            ? `(terminó en redo en línea ${rangoActual.redoLinea + 1})`
            : "(árbol final)";
        info.textContent = `Árbol ${currentTreeIndex + 1} de ${
          completeTrees.length
        } ${tipoFinalizacion}`;
      }

      currentTreeIndex = (currentTreeIndex + 1) % completeTrees.length;
      stepByStepMode = false;
      stepBtn.disabled = false;
    }
  });

  // Botón "Visualizar Línea por Línea"
  stepBtn.addEventListener("click", () => {
    // Si no se han cargado los árboles, cargarlos
    if (!completeTrees.length) {
      const result = procesarTraza(currentTraceStr);
      completeTrees = result.arboles;
      treeRanges = result.rangos;
    }

    // Determinar en qué árbol estamos basado en currentLineIndex
    let arbolActual = 0;
    for (let i = 0; i < treeRanges.length; i++) {
      if (
        currentLineIndex >= treeRanges[i].inicio &&
        currentLineIndex <= treeRanges[i].fin
      ) {
        arbolActual = i;
        break;
      }
      if (currentLineIndex < treeRanges[i].inicio) {
        arbolActual = i;
        currentLineIndex = treeRanges[i].inicio;
        break;
      }
    }

    // Si llegamos al final de todos los árboles
    if (currentLineIndex >= fullTraceLines.length) {
      alert("Fin de la traza.");
      currentLineIndex = 0;
      stepByStepMode = false;
      nextBtn.disabled = false;
      return;
    }

    stepByStepMode = true;
    nextBtn.disabled = true;

    // Determinar qué líneas procesar para el paso actual
    const rangoActual = treeRanges[arbolActual];
    const inicioRango = rangoActual.inicio;
    const finLinea = Math.min(currentLineIndex, rangoActual.fin);

    // Procesar solo las líneas hasta la línea actual dentro del rango del árbol
    const lineasParaProcesar = fullTraceLines.slice(inicioRango, finLinea + 1);
    const currentTrace = lineasParaProcesar.join("\n");

    try {
      if (currentTrace.trim()) {
        const result = procesarTraza(currentTrace);
        const treesForStep = result.arboles;
        const lastTree = treesForStep[treesForStep.length - 1];

        drawTree(lastTree);
        highlightTraceLine(currentLineIndex);

        // Mostrar información del paso actual
        const info = document.getElementById("tree-info");
        if (info) {
          info.textContent = `Árbol ${arbolActual + 1}: Procesando línea ${
            currentLineIndex + 1
          } de ${fullTraceLines.length} (rango: ${rangoActual.inicio + 1}-${
            rangoActual.fin + 1
          })`;
        }
      }

      // Avanzar al siguiente paso
      currentLineIndex++;

      // Si hemos llegado al final del árbol actual, saltar al siguiente
      if (
        currentLineIndex > rangoActual.fin &&
        arbolActual + 1 < treeRanges.length
      ) {
        currentLineIndex = treeRanges[arbolActual + 1].inicio;
      }
    } catch (error) {
      console.error("Error procesando traza:", error);
      alert("Error al procesar la traza en la línea " + (currentLineIndex + 1));
    }
  });

  // Función para dibujar el árbol inicial
  function drawInitialTree() {
    if (fullTraceLines.length > 0) {
      const result = procesarTraza(currentTraceStr);
      completeTrees = result.arboles;
      treeRanges = result.rangos;

      if (completeTrees.length > 0) {
        drawTree(completeTrees[0]);

        const info = document.getElementById("tree-info");
        if (info) {
          info.textContent = `Traza cargada. ${completeTrees.length} estados de árbol disponibles.`;
        }
      }
    }
  }

  // Inicialización
  loadTrace(currentTraceStr);
  drawInitialTree();
});
