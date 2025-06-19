#!/usr/bin/env python
"""
Script para ejecutar la aplicación Streamlit de Watchtower
Configura los paths correctamente y ejecuta la aplicación.
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    # Obtener el directorio del proyecto
    script_dir = Path(__file__).parent
    src_dir = script_dir / "src"
    streamlit_dir = script_dir / "src" / "web" / "fullstreamlit"
    
    # Agregar src al PYTHONPATH
    env = os.environ.copy()
    current_pythonpath = env.get('PYTHONPATH', '')
    if current_pythonpath:
        env['PYTHONPATH'] = f"{src_dir}{os.pathsep}{current_pythonpath}"
    else:
        env['PYTHONPATH'] = str(src_dir)
    
    print(f"🚀 Iniciando Watchtower Streamlit App...")
    print(f"📁 Directorio del proyecto: {script_dir}")
    print(f"📁 Directorio src: {src_dir}")
    print(f"📁 Directorio streamlit: {streamlit_dir}")
    print(f"🐍 PYTHONPATH: {env['PYTHONPATH']}")
    
    # Cambiar al directorio de streamlit
    os.chdir(streamlit_dir)
    
    # Ejecutar streamlit
    try:
        result = subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py", 
            "--server.port", "8502"
        ], cwd=streamlit_dir, env=env, check=True)
        print("✅ Streamlit ejecutado exitosamente")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando Streamlit: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n🛑 Aplicación detenida por el usuario.")
        return 0
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 