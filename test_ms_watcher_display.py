#!/usr/bin/env python3
"""
Script de prueba para verificar que el MS Skills Watcher se muestra correctamente
en la interfaz de watchers.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

def check_ms_watcher_data():
    """Verificar los datos del MS Skills Watcher"""
    print("🔍 Verificando datos del MS Skills Watcher...")
    
    # Paths
    ms_watcher_dir = Path("data/watchers/ms_applied_skills")
    state_file = ms_watcher_dir / "state.json"
    events_dir = ms_watcher_dir / "events"
    debug_dir = events_dir / "debug"
    
    print(f"📁 Directorio del watcher: {ms_watcher_dir}")
    print(f"📄 Archivo de estado: {state_file}")
    
    # Check if directories exist
    if not ms_watcher_dir.exists():
        print("❌ El directorio del MS Watcher no existe")
        return False
    
    # Check state file
    if state_file.exists():
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    state_data = json.loads(content)
                    print("✅ Archivo de estado encontrado y leído correctamente")
                    print(f"📊 Estado: {json.dumps(state_data, indent=2, ensure_ascii=False)}")
                    
                    # Check last_value structure
                    if 'last_value' in state_data:
                        last_value = state_data['last_value']
                        if isinstance(last_value, dict):
                            skills_count = last_value.get('skills_count', last_value.get('count', 0))
                            skills = last_value.get('skills', [])
                            print(f"🔢 Número de skills: {skills_count}")
                            print(f"📝 Skills encontradas: {len(skills)}")
                            
                            # Show sample skills
                            if skills:
                                print("📋 Primeras 3 skills:")
                                for i, skill in enumerate(skills[:3]):
                                    if isinstance(skill, dict):
                                        name = skill.get('name', skill.get('title', 'Unknown'))
                                        url = skill.get('url', 'No URL')
                                        print(f"  {i+1}. {name}")
                                        print(f"     URL: {url}")
                        else:
                            print("⚠️  last_value no es un diccionario")
                    else:
                        print("⚠️  No hay 'last_value' en el estado")
                else:
                    print("⚠️  El archivo de estado está vacío")
                    return False
        except Exception as e:
            print(f"❌ Error leyendo el archivo de estado: {e}")
            return False
    else:
        print("❌ El archivo de estado no existe")
        return False
    
    # Check events directory
    if events_dir.exists():
        event_files = list(events_dir.glob("*.json"))
        print(f"📁 Eventos encontrados: {len(event_files)}")
        
        if event_files:
            # Show latest event
            latest_event = max(event_files, key=lambda p: p.stat().st_mtime)
            print(f"🕐 Evento más reciente: {latest_event.name}")
            
            try:
                with open(latest_event, 'r', encoding='utf-8') as f:
                    event_data = json.load(f)
                    print(f"📄 Contenido del evento: {json.dumps(event_data, indent=2, ensure_ascii=False)}")
            except Exception as e:
                print(f"⚠️  Error leyendo evento: {e}")
    else:
        print("❌ El directorio de eventos no existe")
    
    # Check debug files
    if debug_dir.exists():
        debug_files = list(debug_dir.glob("*.html"))
        print(f"🐛 Archivos debug encontrados: {len(debug_files)}")
        
        if debug_files:
            latest_debug = max(debug_files, key=lambda p: p.stat().st_mtime)
            print(f"🕐 Debug más reciente: {latest_debug.name}")
    else:
        print("📁 Directorio debug no existe")
    
    return True

def simulate_watchers_tab_loading():
    """Simular la carga de datos como en watchers_tab.py"""
    print("\n🔄 Simulando carga de datos de watchers_tab.py...")
    
    try:
        # Import the actual function from watchers_tab
        sys.path.append("src/web/fullstreamlit/components")
        from watchers_tab import load_watcher_states
        
        print("📥 Cargando estados de watchers...")
        watcher_states = load_watcher_states()
        
        print(f"📊 Total de watchers encontrados: {len(watcher_states)}")
        
        # Find MS Applied Skills watcher specifically
        ms_watcher = None
        for watcher in watcher_states:
            if watcher['name'] == 'ms_applied_skills':
                ms_watcher = watcher
                break
        
        if ms_watcher:
            print("✅ MS Applied Skills watcher encontrado en la lista")
            print(f"📄 Estado: {json.dumps(ms_watcher['state'], indent=2, ensure_ascii=False)}")
            print(f"📊 Número de eventos: {ms_watcher['event_count']}")
            
            # Check last_value format
            last_value = ms_watcher['state'].get('last_value')
            if last_value and isinstance(last_value, dict):
                skills_count = last_value.get('skills_count', last_value.get('count', 0))
                skills = last_value.get('skills', [])
                print(f"🔢 Skills count: {skills_count}")
                print(f"📝 Skills array length: {len(skills)}")
                
                if skills and isinstance(skills[0], dict):
                    sample_skill = skills[0]
                    print(f"📋 Sample skill: {sample_skill}")
                    print(f"  - Name: {sample_skill.get('name', sample_skill.get('title', 'Unknown'))}")
                    print(f"  - URL: {sample_skill.get('url', 'No URL')}")
            
        else:
            print("❌ MS Applied Skills watcher NO encontrado en la lista")
            print("📋 Watchers disponibles:")
            for watcher in watcher_states:
                print(f"  - {watcher['name']}")
        
    except Exception as e:
        print(f"❌ Error simulando carga: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🧪 Prueba del MS Skills Watcher - Verificación de Display")
    print("=" * 60)
    
    # Test 1: Check raw data files
    success = check_ms_watcher_data()
    
    if success:
        # Test 2: Simulate watchers tab loading
        simulate_watchers_tab_loading()
    
    print("\n" + "=" * 60)
    print("🏁 Prueba completada")
    
    print("\n💡 Para ver el watcher en Streamlit:")
    print("   1. Ejecuta: streamlit run src/web/fullstreamlit/app.py")
    print("   2. Ve a la tab 'Monitoring'")
    print("   3. Busca 'Ms Applied Skills' en la lista de watchers")

if __name__ == "__main__":
    main() 