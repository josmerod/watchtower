# Metadata

- Caso de uso: Microsoft Applied Skills Certification Monitoring System
- Plataformas involucradas: Microsoft Learn Platform, MS Credentials Website
- Descripción corta: Sistema de monitoreo continuo de certificaciones Microsoft Applied Skills con detección automática de nuevas credenciales y cambios en el programa
- Patrón de ejecución: Continuo con verificaciones cada hora para detectar nuevas certificaciones y actualizaciones

## Dependencias

- Fuentes de datos externas:
  - Microsoft Learn Platform (learn.microsoft.com)
  - Microsoft Credentials Browse Page
  - Individual skill detail pages
  - Microsoft Training Modules and Learning Paths
- Bibliotecas de Python principales:
  - `playwright`: Automatización de navegador para JavaScript rendering
  - `beautifulsoup4`: Parsing HTML y extracción de datos estructurados
  - `asyncio`: Procesamiento asíncrono para navegación de múltiples páginas
  - `requests`: Comunicación HTTP para fallback scenarios
  - `datetime`: Manejo de timestamps y tracking de cambios
  - `pathlib`: Manejo de archivos y directorios

## Stack Tecnológico

- Lenguaje de programación: Python 3.10+
- Framework: Watcher system con base en BaseWatcher pattern
- Browser Automation: Playwright con rendering completo de JavaScript
- Almacenamiento de datos: JSON estructurado con archivos de eventos
- Change Detection: Sistema de detección de cambios con alarmas
- Logging: Sistema centralizado con debugging detallado

## Implementación

La implementación consta de los siguientes componentes:

1. **MS Applied Skills Watcher** (`src/watchers/ms_skills_watcher.py`):
   - Motor principal de monitoreo de certificaciones Microsoft
   - Navegación automatizada con Playwright
   - Extracción detallada de metadatos de cada certificación
   - Sistema de detección de cambios y alertas

2. **Skill Detail Extraction Engine**:
   - Navegación automática a páginas individuales de certificaciones
   - Extracción de descripciones, tareas evaluadas, y módulos de aprendizaje
   - Análisis de roles asociados y fechas de actualización
   - Manejo robusto de diferentes layouts de página

3. **Change Detection System**:
   - Comparación inteligente de estados anteriores vs actuales
   - Detección de nuevas certificaciones agregadas
   - Identificación de cambios en certificaciones existentes
   - Sistema de alarmas para notificaciones

4. **Fallback and Recovery Mechanisms**:
   - Lista de certificaciones conocidas para fallback
   - Múltiples estrategias de extracción para robustez
   - Manejo de errores y timeouts de red
   - Debug HTML saving para troubleshooting

## Características Avanzadas

### 1. **Advanced Web Scraping with JavaScript Rendering**
- **Playwright Integration**: Navegador real con soporte completo de JavaScript
- **Dynamic Content Handling**: Espera inteligente para carga de contenido dinámico
- **Multi-Page Navigation**: Navegación automática a páginas de detalle
- **Responsive Selectors**: Múltiples estrategias de selección CSS

### 2. **Comprehensive Skill Data Extraction**
- **Skill Metadata**: Nombre, descripción, URL, estado de certificación
- **Evaluated Tasks**: Lista detallada de habilidades evaluadas
- **Learning Resources**: Módulos y rutas de aprendizaje recomendadas
- **Role Mapping**: Roles profesionales asociados con cada certificación
- **Update Tracking**: Fechas de última actualización y cambios

### 3. **Intelligent Change Detection**
- **New Skills Detection**: Identificación automática de nuevas certificaciones
- **Content Change Tracking**: Detección de cambios en descripciones y tareas
- **Learning Path Updates**: Monitoring de cambios en recursos de aprendizaje
- **Metadata Evolution**: Tracking de cambios en metadatos

### 4. **Robust Error Handling and Recovery**
- **Multiple Extraction Strategies**: Fallback methods para diferentes layouts
- **Timeout Management**: Timeouts configurables para navegación
- **Error Logging**: Logging detallado de errores para debugging
- **Graceful Degradation**: Continuidad de servicio con datos parciales

### 5. **Monitoring and Alerting System**
- **Real-time Monitoring**: Verificaciones continuas cada hora
- **Change Alerts**: Notificaciones automáticas de cambios detectados
- **Health Monitoring**: Verificación de estado del watcher
- **Event Logging**: Registro completo de eventos y cambios

## Pseudocódigo

```python
async def ms_applied_skills_monitoring_process():
    # 1. Initialize Browser Environment
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # 2. Navigate to MS Credentials Browse Page
        browse_url = "https://learn.microsoft.com/es-es/credentials/browse/?credential_types=applied%20skills"
        await page.goto(browse_url, wait_until="networkidle")
        
        # 3. Extract Skills List with URLs
        skills_with_urls = await extract_skills_from_browse_page(page)
        
        # 4. Detailed Skill Information Extraction
        all_skills_data = []
        for skill in skills_with_urls:
            skill_details = await fetch_skill_details(skill["url"], page)
            skill_data = {
                "name": skill["name"],
                "url": skill["url"],
                "description": skill_details["description"],
                "evaluated_tasks": skill_details["evaluated_tasks"],
                "learning_modules": skill_details["learning_modules_recommended"],
                "roles": skill_details["roles"],
                "last_updated": skill_details["last_updated"]
            }
            all_skills_data.append(skill_data)
        
        # 5. Change Detection and Comparison
        previous_data = load_previous_skill_data()
        changes_detected = detect_changes(previous_data, all_skills_data)
        
        # 6. Alert Generation and Logging
        if changes_detected:
            trigger_change_alerts(changes_detected)
            log_change_events(changes_detected)
        
        # 7. Save Updated Data
        save_skills_data(all_skills_data)
        update_monitoring_metrics()
```

## Microsoft Applied Skills Tracked

### Current Known Certifications (24+ Skills)
1. **Microsoft 365 Copilot**: AI-powered productivity enhancement
2. **Azure Virtual Desktop**: Virtual desktop infrastructure management
3. **Windows Server Hybrid Administrator**: Hybrid cloud server management
4. **Azure Support Engineer for Connectivity**: Network connectivity expertise
5. **Microsoft 365 Security Solutions**: Comprehensive security implementation
6. **Microsoft Security Operations Analyst**: Security incident response
7. **Microsoft 365 Apps Management**: Enterprise app deployment
8. **Microsoft 365 Messaging**: Email and messaging systems
9. **Azure AI Engineer**: Artificial intelligence solutions
10. **Azure Data Scientist**: Data science and machine learning
11. **Azure Data Engineer**: Data pipeline and analytics
12. **Azure Database Administrator**: Database management and optimization
13. **Azure Developer**: Cloud application development
14. **Azure Administrator**: Cloud infrastructure management
15. **Microsoft 365 Developer**: Custom M365 solutions
16. **Microsoft 365 Teams Administrator**: Teams deployment and management
17. **Microsoft 365 Modern Desktop**: Desktop modernization
18. **Microsoft 365 Enterprise Administrator**: Enterprise-level administration
19. **Microsoft 365 Security Administrator**: Security policies and controls
20. **Windows Server Administrator**: Server infrastructure management
21. **Windows Client Administrator**: Desktop and client management
22. **Microsoft Identity and Access Administrator**: Identity management
23. **Microsoft Information Protection**: Data protection and compliance
24. **Microsoft Azure IoT Developer**: Internet of Things solutions

## Métricas y KPIs

### Métricas de Cobertura
- **Skills Monitored**: Número total de certificaciones monitoreadas
- **Detail Coverage**: Porcentaje de skills con información detallada extraída
- **Page Navigation Success**: Tasa de éxito en navegación a páginas individuales
- **Data Completeness**: Completitud de datos extraídos por certificación

### Métricas de Calidad
- **Change Detection Accuracy**: Precisión en detección de cambios reales
- **False Positive Rate**: Tasa de falsos positivos en alertas de cambios
- **Data Extraction Success**: Porcentaje de extracción exitosa de metadatos
- **Update Frequency**: Frecuencia de actualizaciones detectadas

### Métricas de Performance
- **Monitoring Cycle Time**: Tiempo promedio por ciclo completo de monitoreo
- **Page Load Performance**: Tiempo promedio de carga de páginas
- **Browser Resource Usage**: Uso de recursos durante navegación
- **Error Recovery Rate**: Tasa de recuperación exitosa de errores

## Casos de Uso Específicos

1. **IT Training Managers**: Tracking de nuevas certificaciones para programas de capacitación
2. **Career Development Professionals**: Identificación de oportunidades de crecimiento profesional
3. **Microsoft Partners**: Monitoreo de requisitos de certificación para partnerships
4. **Educational Institutions**: Actualización de currículos con nuevas certificaciones
5. **HR Departments**: Planificación de desarrollo de habilidades del personal
6. **Certification Consultants**: Intelligence para servicios de consultoría

## Change Detection Logic

### Types of Changes Detected
1. **New Skills Added**: Certificaciones completamente nuevas en el programa
2. **Skill Details Modified**: Cambios en descripciones, tareas, o metadatos
3. **Learning Paths Updated**: Nuevos módulos o cambios en recursos de aprendizaje
4. **Status Changes**: Cambios en disponibilidad o estado de certificaciones
5. **URL Structure Changes**: Modificaciones en enlaces o estructura de navegación

### Change Comparison Algorithm
```python
def detect_skill_changes(old_data, new_data):
    changes = {
        "new_skills": [],
        "modified_skills": [],
        "removed_skills": [],
        "metadata_changes": []
    }
    
    old_skills = {skill["name"]: skill for skill in old_data}
    new_skills = {skill["name"]: skill for skill in new_data}
    
    # Detect new skills
    for name in new_skills:
        if name not in old_skills:
            changes["new_skills"].append(new_skills[name])
    
    # Detect removed skills
    for name in old_skills:
        if name not in new_skills:
            changes["removed_skills"].append(old_skills[name])
    
    # Detect modifications
    for name in old_skills:
        if name in new_skills:
            if has_meaningful_changes(old_skills[name], new_skills[name]):
                changes["modified_skills"].append({
                    "name": name,
                    "old": old_skills[name],
                    "new": new_skills[name]
                })
    
    return changes
```

## Configuración y Personalización

### Monitoring Parameters
```python
MONITORING_CONFIG = {
    "check_interval": 3600,  # 1 hour in seconds
    "page_timeout": 60000,   # 60 seconds for page loads
    "wait_after_navigation": 3000,  # 3 seconds after page load
    "max_retries": 3,        # Maximum retry attempts
    "browser_headless": True # Run browser in headless mode
}
```

### Extraction Selectors
```python
SKILL_SELECTORS = {
    "browse_page": {
        "skill_cards": "div[data-testid='card']",
        "skill_links": "a[href*='/credentials/applied-skills/']",
        "skill_titles": "h3, h4, .card-title"
    },
    "detail_page": {
        "description": ["meta[property='og:description']", "meta[name='description']"],
        "skills_measured": ["h2:has-text('Skills measured')", "h2:has-text('Habilidades evaluadas')"],
        "learning_modules": ["section[aria-labelledby*='prepare']", "div[data-bi-name='prepare']"]
    }
}
```

## Outputs Generados

1. **Skills Data**:
   - `ms_applied_skills_latest.json`: Datos más recientes de todas las certificaciones
   - `ms_applied_skills_details.json`: Información detallada de cada certificación
   - `ms_applied_skills_history.json`: Historial de cambios detectados

2. **Change Events**:
   - `events/`: Archivos individuales de eventos de cambios detectados
   - `change_summary.json`: Resumen de cambios por período
   - `new_skills_alert.json`: Alertas de nuevas certificaciones

3. **Monitoring Metrics**:
   - `monitoring_performance.json`: Métricas de rendimiento del watcher
   - `extraction_success_rates.json`: Tasas de éxito en extracción de datos
   - `error_logs.json`: Logs detallados de errores y fallos

## Alertas y Notificaciones

### Tipos de Alertas
1. **New Skill Alert**: Nueva certificación disponible en el programa
2. **Skill Update Alert**: Cambios en certificación existente
3. **Learning Path Change**: Modificaciones en recursos de aprendizaje
4. **System Health Alert**: Problemas en el monitoreo automatizado

### Canales de Notificación
- **JSON Event Files**: Archivos estructurados para integración con otros sistemas
- **Log-based Alerts**: Alertas a través del sistema de logging
- **Email Integration**: Notificaciones por email (configuración externa)
- **Webhook Support**: Integración con sistemas de notificación externos

## Consideraciones Técnicas

### Browser Automation Challenges
- **JavaScript Heavy Pages**: Páginas con contenido dinámico extensivo
- **Rate Limiting**: Respeto por limitaciones de Microsoft Learn
- **Content Layout Changes**: Adaptabilidad a cambios en diseño de páginas
- **Timeout Management**: Manejo inteligente de timeouts de red

### Scalability and Maintenance
- **Resource Management**: Gestión eficiente de recursos de navegador
- **Error Recovery**: Recuperación automática de errores temporales
- **Update Resilience**: Adaptación a cambios en estructura de sitio
- **Performance Optimization**: Optimización de tiempo de ejecución

### Data Quality Assurance
- **Validation Rules**: Validación de datos extraídos
- **Completeness Checks**: Verificación de completitud de información
- **Consistency Monitoring**: Monitoreo de consistencia de datos
- **Quality Metrics**: Métricas de calidad de extracción 