#!/usr/bin/env python3
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib

class TestCheckpointManager:
    """
    Manejador de checkpoints para la suite de tests.
    Permite guardar y reanudar el progreso de tests largos.
    """
    
    def __init__(self, checkpoint_dir: str = "checkpoints/tests"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
    def _generate_test_suite_id(self, tests: List[Dict[str, Any]]) -> str:
        """
        Genera un ID único para la suite de tests basado en su contenido.
        """
        # Crear hash basado en los problemas de la suite
        content = json.dumps([test["problem_description"] for test in tests], sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _get_checkpoint_file(self, suite_id: str) -> Path:
        """
        Obtiene la ruta del archivo de checkpoint para una suite específica.
        """
        return self.checkpoint_dir / f"test_suite_{suite_id}.json"
    
    def save_checkpoint(self, tests: List[Dict[str, Any]], results: List[Dict[str, Any]], 
                       current_index: int, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Guarda un checkpoint del progreso actual de los tests.
        
        Args:
            tests: Lista completa de tests
            results: Resultados obtenidos hasta ahora
            current_index: Índice del test actual
            metadata: Información adicional sobre la ejecución
            
        Returns:
            str: ID del checkpoint guardado
        """
        suite_id = self._generate_test_suite_id(tests)
        checkpoint_file = self._get_checkpoint_file(suite_id)
        
        checkpoint_data = {
            "suite_id": suite_id,
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(tests),
            "completed_tests": len(results),
            "current_index": current_index,
            "tests": tests,
            "results": results,
            "metadata": metadata or {}
        }
        
        # Guardar con backup del anterior si existe
        if checkpoint_file.exists():
            backup_file = checkpoint_file.with_suffix('.json.backup')
            checkpoint_file.rename(backup_file)
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        
        print(f"Checkpoint guardado: {checkpoint_file}")
        print(f"Progreso: {len(results)}/{len(tests)} tests completados")
        
        return suite_id
    
    def load_checkpoint(self, tests: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Carga un checkpoint existente para la suite de tests dada.
        
        Args:
            tests: Lista de tests para identificar la suite
            
        Returns:
            Dict con los datos del checkpoint o None si no existe
        """
        suite_id = self._generate_test_suite_id(tests)
        checkpoint_file = self._get_checkpoint_file(suite_id)
        
        if not checkpoint_file.exists():
            return None
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            # Verificar que el checkpoint corresponde a la misma suite
            if checkpoint_data.get("suite_id") != suite_id:
                print("Advertencia: El checkpoint no corresponde a la suite actual")
                return None
            
            # Verificar integridad básica
            if len(checkpoint_data.get("tests", [])) != len(tests):
                print("Advertencia: El número de tests ha cambiado desde el checkpoint")
                return None
            
            print(f"Checkpoint cargado: {checkpoint_file}")
            print(f"Progreso previo: {checkpoint_data['completed_tests']}/{checkpoint_data['total_tests']} tests")
            
            return checkpoint_data
            
        except Exception as e:
            print(f"Error al cargar checkpoint: {e}")
            return None
    
    def delete_checkpoint(self, tests: List[Dict[str, Any]]) -> bool:
        """
        Elimina el checkpoint de la suite de tests dada.
        
        Args:
            tests: Lista de tests para identificar la suite
            
        Returns:
            bool: True si se eliminó exitosamente
        """
        suite_id = self._generate_test_suite_id(tests)
        checkpoint_file = self._get_checkpoint_file(suite_id)
        
        try:
            if checkpoint_file.exists():
                checkpoint_file.unlink()
                print(f"Checkpoint eliminado: {checkpoint_file}")
                return True
            return False
        except Exception as e:
            print(f"Error al eliminar checkpoint: {e}")
            return False
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        Lista todos los checkpoints de tests disponibles.
        
        Returns:
            Lista de información sobre checkpoints existentes
        """
        checkpoints = []
        
        for checkpoint_file in self.checkpoint_dir.glob("test_suite_*.json"):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                checkpoints.append({
                    "file": str(checkpoint_file),
                    "suite_id": data.get("suite_id"),
                    "timestamp": data.get("timestamp"),
                    "total_tests": data.get("total_tests"),
                    "completed_tests": data.get("completed_tests"),
                    "progress_percent": (data.get("completed_tests", 0) / data.get("total_tests", 1)) * 100
                })
            except Exception as e:
                print(f"Error al leer checkpoint {checkpoint_file}: {e}")
        
        return sorted(checkpoints, key=lambda x: x["timestamp"], reverse=True)
    
    def cleanup_old_checkpoints(self, max_age_days: int = 7) -> int:
        """
        Limpia checkpoints antiguos.
        
        Args:
            max_age_days: Edad máxima en días para mantener checkpoints
            
        Returns:
            int: Número de checkpoints eliminados
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        deleted_count = 0
        
        for checkpoint_file in self.checkpoint_dir.glob("test_suite_*.json"):
            try:
                # Obtener fecha de modificación del archivo
                mod_time = datetime.fromtimestamp(checkpoint_file.stat().st_mtime)
                
                if mod_time < cutoff_date:
                    checkpoint_file.unlink()
                    deleted_count += 1
                    print(f"Checkpoint antiguo eliminado: {checkpoint_file}")
                    
            except Exception as e:
                print(f"Error al procesar checkpoint {checkpoint_file}: {e}")
        
        return deleted_count

def test_checkpoint_system():
    """
    Función de prueba para el sistema de checkpoints.
    """
    print("Probando sistema de checkpoints para tests...")
    
    # Crear manager
    manager = TestCheckpointManager()
    
    # Tests de ejemplo
    sample_tests = [
        {"problem_description": "Test 1", "solution": "Sol 1"},
        {"problem_description": "Test 2", "solution": "Sol 2"},
        {"problem_description": "Test 3", "solution": "Sol 3"}
    ]
    
    # Simular progreso
    results = [
        {"index": 0, "done": True, "final_answer": "Respuesta 1"}
    ]
    
    # Guardar checkpoint
    suite_id = manager.save_checkpoint(sample_tests, results, 1)
    
    # Cargar checkpoint
    loaded = manager.load_checkpoint(sample_tests)
    print("Checkpoint cargado:", loaded is not None)
    
    # Listar checkpoints
    checkpoints = manager.list_checkpoints()
    print(f"Checkpoints encontrados: {len(checkpoints)}")
    
    # Limpiar
    manager.delete_checkpoint(sample_tests)
    print("Test completado.")

if __name__ == "__main__":
    test_checkpoint_system() 