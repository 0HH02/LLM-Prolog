from typing import List, Optional, Any, Dict, Set
from dataclasses import dataclass, field
from enum import Enum

class StepStatus(Enum):
    """Estados posibles de un paso de inferencia."""
    CALLED = "called"      # El predicado fue llamado
    SUCCEEDED = "succeeded" # El predicado tuvo éxito
    FAILED = "failed"      # El predicado falló
    BACKTRACKED = "backtracked"  # Se hizo backtracking

@dataclass
class InferenceStep:
    """Representa un único paso en el proceso de inferencia."""
    step_id: int
    predicate: str
    status: StepStatus
    depth: int
    parent_step_id: Optional[int] = None
    children_step_ids: List[int] = field(default_factory=list)
    premises: List[str] = field(default_factory=list)
    justification: Optional[str] = None
    annotations: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[float] = None

    def add_annotation(self, key: str, value: Any):
        """Añade una anotación al paso."""
        self.annotations[key] = value

    def get_annotation(self, key: str, default=None):
        """Obtiene una anotación del paso."""
        return self.annotations.get(key, default)

    def __str__(self) -> str:
        status_str = f"[{self.status.value.upper()}]"
        depth_str = "  " * self.depth
        parent_str = f" (parent: {self.parent_step_id})" if self.parent_step_id else ""
        annotations_str = f" {self.annotations}" if self.annotations else ""
        return f"{depth_str}Step {self.step_id}: {self.predicate} {status_str}{parent_str}{annotations_str}"

@dataclass
class ReasoningChain:
    """Representa una cadena completa de razonamiento desde la raíz hasta una hoja."""
    chain_id: int
    steps: List[InferenceStep]
    is_successful: bool
    goal_achieved: bool = False
    annotations: Dict[str, Any] = field(default_factory=dict)

    def add_annotation(self, key: str, value: Any):
        """Añade una anotación a la cadena."""
        self.annotations[key] = value

    def get_successful_steps(self) -> List[InferenceStep]:
        """Retorna solo los pasos exitosos de la cadena."""
        return [step for step in self.steps if step.status == StepStatus.SUCCEEDED]

    def get_failed_steps(self) -> List[InferenceStep]:
        """Retorna solo los pasos fallidos de la cadena."""
        return [step for step in self.steps if step.status == StepStatus.FAILED]

    def __str__(self) -> str:
        status = "EXITOSA" if self.is_successful else "FALLIDA"
        goal_str = " [OBJETIVO ALCANZADO]" if self.goal_achieved else ""
        return f"Cadena {self.chain_id} ({status}){goal_str}: {len(self.steps)} pasos"

@dataclass
class InferenceTrace:
    """Almacena el árbol completo de inferencia con todas las cadenas de razonamiento."""
    steps: Dict[int, InferenceStep] = field(default_factory=dict)
    reasoning_chains: List[ReasoningChain] = field(default_factory=list)
    goal_clause: Optional[str] = None
    solution_found: bool = False
    root_step_id: Optional[int] = None
    current_step_id: int = 0
    successful_chains: List[int] = field(default_factory=list)
    failed_chains: List[int] = field(default_factory=list)

    def add_step(self, predicate: str, status: StepStatus, depth: int = 0, 
                 parent_step_id: Optional[int] = None, premises: List[str] = None,
                 justification: Optional[str] = None) -> int:
        """Añade un nuevo paso a la traza y retorna su ID."""
        self.current_step_id += 1
        step_id = self.current_step_id
        
        step = InferenceStep(
            step_id=step_id,
            predicate=predicate,
            status=status,
            depth=depth,
            parent_step_id=parent_step_id,
            premises=premises or [],
            justification=justification
        )
        
        self.steps[step_id] = step
        
        # Actualizar relaciones padre-hijo
        if parent_step_id and parent_step_id in self.steps:
            self.steps[parent_step_id].children_step_ids.append(step_id)
        
        # Marcar como raíz si es el primer paso
        if self.root_step_id is None:
            self.root_step_id = step_id
            
        # Verificar si es el objetivo
        if self.goal_clause and self._is_goal_achieved(predicate):
            step.add_annotation("is_goal", True)
            if status == StepStatus.SUCCEEDED:
                self.solution_found = True
        
        return step_id

    def _is_goal_achieved(self, predicate: str) -> bool:
        """Verifica si el predicado corresponde al objetivo."""
        if not self.goal_clause:
            return False
        
        if "(" in self.goal_clause and "(" in predicate:
            goal_pred = self.goal_clause.split("(")[0]
            derived_pred = predicate.split("(")[0]
            return goal_pred == derived_pred
        else:
            return predicate == self.goal_clause

    def extract_reasoning_chains(self):
        """Extrae todas las cadenas de razonamiento del árbol."""
        self.reasoning_chains.clear()
        self.successful_chains.clear()
        self.failed_chains.clear()
        
        if self.root_step_id:
            self._extract_chains_recursive(self.root_step_id, [], 0)

    def _extract_chains_recursive(self, step_id: int, current_chain: List[InferenceStep], chain_id: int):
        """Extrae cadenas recursivamente desde un nodo."""
        if step_id not in self.steps:
            return chain_id
        
        step = self.steps[step_id]
        new_chain = current_chain + [step]
        
        # Si es una hoja (sin hijos), crear una cadena
        if not step.children_step_ids:
            is_successful = step.status == StepStatus.SUCCEEDED
            goal_achieved = step.get_annotation("is_goal", False) and is_successful
            
            chain = ReasoningChain(
                chain_id=chain_id,
                steps=new_chain,
                is_successful=is_successful,
                goal_achieved=goal_achieved
            )
            
            self.reasoning_chains.append(chain)
            
            if is_successful:
                self.successful_chains.append(chain_id)
            else:
                self.failed_chains.append(chain_id)
                
            return chain_id + 1
        
        # Si tiene hijos, continuar recursivamente
        for child_id in step.children_step_ids:
            chain_id = self._extract_chains_recursive(child_id, new_chain, chain_id)
        
        return chain_id

    def get_successful_chains(self) -> List[ReasoningChain]:
        """Retorna todas las cadenas exitosas."""
        return [chain for chain in self.reasoning_chains if chain.is_successful]

    def get_failed_chains(self) -> List[ReasoningChain]:
        """Retorna todas las cadenas fallidas."""
        return [chain for chain in self.reasoning_chains if not chain.is_successful]

    def get_goal_achieving_chains(self) -> List[ReasoningChain]:
        """Retorna las cadenas que alcanzan el objetivo."""
        return [chain for chain in self.reasoning_chains if chain.goal_achieved]

    def annotate_step(self, step_id: int, key: str, value: Any):
        """Añade una anotación a un paso específico."""
        if step_id in self.steps:
            self.steps[step_id].add_annotation(key, value)

    def annotate_chain(self, chain_id: int, key: str, value: Any):
        """Añade una anotación a una cadena específica."""
        if 0 <= chain_id < len(self.reasoning_chains):
            self.reasoning_chains[chain_id].add_annotation(key, value)

    def pretty_print(self):
        """Imprime la traza de inferencia de forma legible."""
        print("\n=== TRAZA DE INFERENCIA COMPLETA ===")
        if self.goal_clause:
            print(f"Objetivo: {self.goal_clause}")
        
        print(f"\nTotal de pasos: {len(self.steps)}")
        print(f"Solución encontrada: {'Sí' if self.solution_found else 'No'}")
        
        # Extraer cadenas si no se ha hecho
        if not self.reasoning_chains:
            self.extract_reasoning_chains()
        
        print(f"\nTotal de cadenas de razonamiento: {len(self.reasoning_chains)}")
        print(f"Cadenas exitosas: {len(self.successful_chains)}")
        print(f"Cadenas fallidas: {len(self.failed_chains)}")
        
        # Mostrar árbol de pasos
        print("\n--- ÁRBOL DE INFERENCIA ---")
        if self.root_step_id:
            self._print_tree_recursive(self.root_step_id, set())
        
        # Mostrar cadenas de razonamiento
        print("\n--- CADENAS DE RAZONAMIENTO ---")
        for chain in self.reasoning_chains:
            print(f"\n{chain}")
            for step in chain.steps:
                print(f"  {step}")

    def _print_tree_recursive(self, step_id: int, visited: Set[int]):
        """Imprime el árbol recursivamente."""
        if step_id in visited or step_id not in self.steps:
            return
        
        visited.add(step_id)
        step = self.steps[step_id]
        print(step)
        
        for child_id in step.children_step_ids:
            self._print_tree_recursive(child_id, visited)

# Ejemplo de uso
if __name__ == "__main__":
    trace = InferenceTrace(goal_clause="mortal(X)")
    
    # Simular una traza de Prolog
    root_id = trace.add_step("mortal(X)", StepStatus.CALLED, depth=0)
    human_id = trace.add_step("humano(X)", StepStatus.CALLED, depth=1, parent_step_id=root_id)
    socrates_id = trace.add_step("humano(socrates)", StepStatus.SUCCEEDED, depth=2, parent_step_id=human_id)
    mortal_socrates_id = trace.add_step("mortal(socrates)", StepStatus.SUCCEEDED, depth=1, parent_step_id=root_id)
    
    trace.annotate_step(socrates_id, "source", "fact")
    trace.annotate_step(mortal_socrates_id, "rule", "mortal(X) :- humano(X)")
    
    trace.extract_reasoning_chains()
    trace.pretty_print()
