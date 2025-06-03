#!/usr/bin/env python3
"""
Script para forzar la actualización del estado del MS Skills Watcher
y asegurar que se guarde correctamente en state.json
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Add the project root to the path
from src.watchers.ms_skills_watcher import MSAppliedSkillsWatcher
from src.utils.logging import get_logger

def main():
    print("🔧 Forzando actualización del MS Skills Watcher...")
    print("=" * 60)
    
    # Create watcher instance
    logger = get_logger("ForceUpdate")
    watcher = MSAppliedSkillsWatcher()
    
    print("🔍 1. Extrayendo datos frescos...")
    try:
        # Extract fresh data
        new_data = watcher.extract_value()
        
        if new_data and new_data.get('skills_count', 0) > 0:
            print(f"✅ Extracción exitosa: {new_data['skills_count']} skills encontradas")
            
            # Force state update using BaseWatcher's internal method
            print("💾 2. Forzando actualización del estado...")
            
            # Update the state manually using BaseWatcher's structure
            current_time = datetime.now().isoformat()
            new_state = {
                "last_check": current_time,
                "last_value": new_data,
                "first_seen": watcher.previous_state.get("first_seen", current_time)
            }
            
            # Save state using BaseWatcher's method
            watcher._save_state(new_state)
            print("✅ Estado guardado exitosamente")
            
            # Update the in-memory state as well
            watcher.previous_state = new_state
            
            # Verify the save
            print("🔍 3. Verificando que se guardó correctamente...")
            state_file = Path("data/watchers/ms_applied_skills/state.json")
            
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    saved_state = json.load(f)
                
                saved_skills_count = saved_state.get('last_value', {}).get('skills_count', 0)
                print(f"📊 Skills guardadas en estado: {saved_skills_count}")
                
                if saved_skills_count > 0:
                    print("🎉 ¡ÉXITO! El estado se ha actualizado correctamente")
                    
                    # Show sample skills
                    skills = saved_state.get('last_value', {}).get('skills', [])
                    if skills:
                        print(f"\n📝 Muestra de skills guardadas:")
                        for i, skill in enumerate(skills[:3]):
                            name = skill.get('name', 'Unknown')
                            print(f"  {i+1}. {name}")
                    
                    return True
                else:
                    print("❌ El estado no se actualizó correctamente")
                    return False
            else:
                print("❌ El archivo de estado no existe")
                return False
                
        else:
            print("❌ La extracción falló o no encontró datos")
            print(f"Datos extraídos: {new_data}")
            return False
            
    except Exception as e:
        print(f"❌ Error durante la extracción: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🚀 El MS Skills Watcher debería aparecer ahora en la interfaz!")
        print("Ve a Streamlit → Monitoring tab → Ms Applied Skills")
    else:
        print("\n💡 Si sigue sin funcionar, puede ser necesario verificar:")
        print("   1. Los permisos de escritura en el directorio data/")
        print("   2. Que el BaseWatcher esté funcionando correctamente")
        print("   3. Que no hay procesos bloqueando el archivo state.json") 