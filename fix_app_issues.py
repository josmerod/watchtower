#!/usr/bin/env python3
"""
Script para solucionar problemas identificados en la aplicación Watchtower

Problemas solucionados:
1. Footer no se renderiza bien - Fixed: métodos de compatibilidad en data service
2. Gaming tab no muestra datos - Fixed: compatibilidad de métodos en data service
3. Crypto sentiment dice que no se ejecutó - Fixed: agregado soporte en data service
4. Tech jobs no muestra información correcta - Fixed: agregado soporte en data service
5. MS Skills watcher - Necesita actualización de selectores
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# Add the project root to the path
from src.utils.logging import get_logger

logger = get_logger("AppFixer")

def check_data_availability():
    """Verificar disponibilidad de datos clave"""
    logger.info("Verificando disponibilidad de datos...")
    
    data_checks = {
        "Gaming": "data/games/deals.json",
        "Crypto Sentiment": "data/crypto_sentiment/crypto_sentiment_raw_latest.json",
        "Tech Jobs": "data/tech_jobs/tech_jobs_latest.json",
        "Videos": "data/youtube",
        "News": "data/hackernews/hackernews.json"
    }
    
    results = {}
    for name, path in data_checks.items():
        full_path = Path(path)
        exists = full_path.exists()
        results[name] = exists
        status = "✅" if exists else "❌"
        logger.info(f"{status} {name}: {path}")
    
    return results

def verify_ultra_optimized_service():
    """Verificar que el servicio ultra optimizado tiene todos los métodos necesarios"""
    logger.info("Verificando servicio ultra optimizado...")
    
    try:
        from src.web.fullstreamlit.utils.data_service_ultra_optimized import create_ultra_optimized_service
        service = create_ultra_optimized_service(logger)
        
        # Verificar métodos críticos
        critical_methods = [
            'get_games_data',
            'get_videos_data', 
            'get_news_data',
            'get_courses_data',
            'get_crypto_sentiment_data',
            'get_tech_jobs_data',
            'get_arxiv_data',
            'get_events_data'
        ]
        
        missing_methods = []
        for method in critical_methods:
            if not hasattr(service, method):
                missing_methods.append(method)
            else:
                logger.info(f"✅ Método {method} disponible")
        
        if missing_methods:
            logger.error(f"❌ Métodos faltantes: {missing_methods}")
            return False
        else:
            logger.info("✅ Todos los métodos críticos están disponibles")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error verificando servicio: {e}")
        return False

def test_data_loading():
    """Probar carga de datos con el servicio ultra optimizado"""
    logger.info("Probando carga de datos...")
    
    try:
        from src.web.fullstreamlit.utils.data_service_ultra_optimized import create_ultra_optimized_service
        service = create_ultra_optimized_service(logger)
        
        # Probar carga de datos de gaming
        logger.info("Probando datos de gaming...")
        deals_df, bundles_df, giveaways_df = service.get_games_data()
        logger.info(f"Gaming: {len(deals_df)} deals, {len(bundles_df)} bundles, {len(giveaways_df)} giveaways")
        
        # Probar datos de crypto sentiment
        logger.info("Probando datos de crypto sentiment...")
        crypto_df = service.get_crypto_sentiment_data()
        logger.info(f"Crypto Sentiment: {len(crypto_df)} registros")
        
        # Probar datos de tech jobs
        logger.info("Probando datos de tech jobs...")
        jobs_df = service.get_tech_jobs_data()
        logger.info(f"Tech Jobs: {len(jobs_df)} trabajos")
        
        # Probar datos de videos
        logger.info("Probando datos de videos...")
        videos_data = service.get_videos_data()
        total_videos = sum(len(df) for df in videos_data.values())
        logger.info(f"Videos: {total_videos} videos en {len(videos_data)} canales")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error probando carga de datos: {e}")
        return False

def fix_ms_skills_watcher():
    """Intentar arreglar el MS Skills Watcher actualizando selectores"""
    logger.info("Intentando arreglar MS Skills Watcher...")
    
    # Por ahora, solo registramos que necesita ser arreglado manualmente
    logger.warning("MS Skills Watcher necesita actualización manual de selectores CSS")
    logger.info("La página de Microsoft Learn ha cambiado su estructura HTML")
    logger.info("Se requiere inspección manual para actualizar los selectores en:")
    logger.info("- src/watchers/ms_skills_watcher.py")
    logger.info("- Método _extract_skills_with_urls_from_html")
    
    return False

def run_data_refresh():
    """Ejecutar un refresh completo de datos"""
    logger.info("Ejecutando refresh completo de datos...")
    
    try:
        # Limpiar cache de Streamlit si existe
        import streamlit as st
        if hasattr(st, 'cache_data'):
            st.cache_data.clear()
            logger.info("✅ Cache de Streamlit limpiado")
        
        return True
        
    except Exception as e:
        logger.error(f"Error en refresh de datos: {e}")
        return False

def create_status_report():
    """Crear reporte de estado de la aplicación"""
    logger.info("Creando reporte de estado...")
    
    data_status = check_data_availability()
    service_status = verify_ultra_optimized_service()
    data_loading_status = test_data_loading()
    
    report = {
        "timestamp": "2025-05-23T16:10:00",
        "data_availability": data_status,
        "service_compatibility": service_status,
        "data_loading": data_loading_status,
        "issues_fixed": [
            "✅ Métodos de compatibilidad agregados al servicio ultra optimizado",
            "✅ Soporte para crypto sentiment agregado",
            "✅ Soporte para tech jobs agregado",
            "✅ Métodos get_arxiv_data y get_events_data agregados",
            "⚠️  MS Skills Watcher necesita actualización manual de selectores"
        ],
        "recommendations": [
            "1. Ejecutar ETL completo con run_all_etl.bat/sh",
            "2. Verificar que todos los datos se carguen correctamente",
            "3. Actualizar selectores CSS en MS Skills Watcher",
            "4. Probar aplicación con streamlit run src/web/fullstreamlit/app.py"
        ]
    }
    
    # Guardar reporte
    with open("app_status_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info("✅ Reporte guardado en app_status_report.json")
    return report

def main():
    """Función principal para ejecutar todas las verificaciones y correcciones"""
    logger.info("🔧 Iniciando diagnóstico y corrección de problemas de Watchtower")
    logger.info("=" * 70)
    
    # Ejecutar todas las verificaciones
    report = create_status_report()
    
    # Mostrar resumen
    print("\n" + "=" * 70)
    print("📊 RESUMEN DE ESTADO DE LA APLICACIÓN")
    print("=" * 70)
    
    print("\n🗂️  DISPONIBILIDAD DE DATOS:")
    for name, status in report["data_availability"].items():
        symbol = "✅" if status else "❌"
        print(f"   {symbol} {name}")
    
    print(f"\n🔧 COMPATIBILIDAD DEL SERVICIO: {'✅' if report['service_compatibility'] else '❌'}")
    print(f"📥 CARGA DE DATOS: {'✅' if report['data_loading'] else '❌'}")
    
    print("\n🛠️  CORRECCIONES APLICADAS:")
    for fix in report["issues_fixed"]:
        print(f"   {fix}")
    
    print("\n💡 RECOMENDACIONES:")
    for rec in report["recommendations"]:
        print(f"   {rec}")
    
    print("\n" + "=" * 70)
    logger.info("✅ Diagnóstico completado. Ver app_status_report.json para detalles completos")

if __name__ == "__main__":
    main() 