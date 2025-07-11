# Metadata

- Caso de uso: **Udemy Universal Course Miner**
- Plataformas involucradas: Udemy, Real.discount, Coursera (extensible)
- Descripción corta: Sistema automatizado para descubrir, evaluar y enrollarse en cursos gratuitos de Udemy de forma masiva
- Patrón de ejecución: Programado (diario), puntual para ofertas especiales, modo batch

## Dependencias

- APIs y servicios externos:
  - Udemy Platform (web scraping)
  - Real.discount API/RSS
  - Third-party course aggregators
  - Course review platforms
  - Educational deal sites

- Bibliotecas de Python principales:
  - `selenium` - Automatización web para enrollment
  - `requests` - HTTP client para APIs
  - `beautifulsoup4` - Web scraping
  - `undetected-chromedriver` - Anti-detection browsing
  - `pydantic` - Data validation
  - `asyncio` - Procesamiento asíncrono

## Stack Tecnológico

- Lenguaje de programación: Python 3.10+
- Framework: Custom mining framework con CLI
- Almacenamiento de datos: JSON, CSV para cursos
- Automatización: Selenium WebDriver
- Orquestación: CLI con scheduler interno
- Logging: Sistema avanzado de logging con rotación

## Implementación

La implementación consta de los siguientes componentes:

1. **Core Miner** (`src/miners/udemy-universal/base.py`):
   - Motor principal de descubrimiento de cursos
   - Sistema de evaluación de calidad de cursos
   - Automatización de enrollment process
   - Gestión de sesiones y anti-detection

2. **CLI Interface** (`src/miners/udemy-universal/cli.py`):
   - Interfaz de línea de comandos para operaciones
   - Configuración flexible de mining parameters
   - Reporting y estadísticas en tiempo real
   - Modo interactivo y batch processing

3. **Enrollment Engine** (`src/miners/udemy-universal/enroll.py`):
   - Motor automatizado de enrollment en cursos
   - Manejo de diferentes tipos de promociones
   - Rate limiting y respeto a términos de servicio
   - Retry logic para fallos de enrollment

4. **Data Management**:
   - **Course Database**: Almacenamiento local de cursos descubiertos
   - **Enrollment Tracking**: Seguimiento de cursos enrollados
   - **Quality Metrics**: Métricas de calidad y relevancia

## Pseudocódigo

```python
class UdemyUniversalMiner:
    def __init__(self, config_path="duce-cli-settings.json"):
        # Cargar configuración
        self.config = self._load_config(config_path)
        self.browser = self._setup_browser()
        self.enrolled_courses = []
        self.discovered_courses = []
        
    def mine_courses(self, max_courses=100):
        """Proceso principal de mining de cursos."""
        
        # Fase 1: Descubrimiento
        print("🔍 Discovering free courses...")
        discovered = self._discover_free_courses()
        
        # Fase 2: Filtrado y evaluación
        print("⚖️ Evaluating course quality...")
        quality_courses = self._evaluate_courses(discovered)
        
        # Fase 3: Enrollment automatizado
        print("📚 Auto-enrolling in selected courses...")
        enrolled = self._auto_enroll_courses(quality_courses[:max_courses])
        
        # Fase 4: Reporte
        self._generate_report(enrolled)
        
        return enrolled
        
    def _discover_free_courses(self):
        """Descubrir cursos gratuitos de múltiples fuentes."""
        sources = [
            self._scrape_real_discount(),
            self._scrape_udemy_free_section(),
            self._scrape_course_aggregators(),
            self._check_promotional_sites()
        ]
        
        all_courses = []
        for source_courses in sources:
            all_courses.extend(source_courses)
            
        # Deduplicar por URL
        unique_courses = self._deduplicate_courses(all_courses)
        
        return unique_courses
        
    def _evaluate_courses(self, courses):
        """Evaluar calidad y relevancia de cursos."""
        quality_courses = []
        
        for course in courses:
            # Extraer métricas del curso
            metrics = self._extract_course_metrics(course)
            
            # Calcular score de calidad
            quality_score = self._calculate_quality_score(metrics)
            
            # Filtros de calidad
            if self._passes_quality_filters(course, quality_score):
                course['quality_score'] = quality_score
                course['metrics'] = metrics
                quality_courses.append(course)
                
        # Ordenar por calidad
        return sorted(quality_courses, 
                     key=lambda x: x['quality_score'], 
                     reverse=True)
        
    def _auto_enroll_courses(self, courses):
        """Enrollment automatizado en cursos seleccionados."""
        enrolled = []
        
        for course in courses:
            try:
                # Navegar al curso
                self.browser.get(course['url'])
                
                # Verificar si está disponible gratis
                if self._is_course_free():
                    # Procesar enrollment
                    success = self._enroll_in_course()
                    
                    if success:
                        enrolled.append(course)
                        print(f"✅ Enrolled: {course['title']}")
                        
                        # Rate limiting
                        time.sleep(random.uniform(5, 15))
                    else:
                        print(f"❌ Failed: {course['title']}")
                        
            except Exception as e:
                logger.error(f"Error enrolling in {course['title']}: {e}")
                
        return enrolled
        
    def _calculate_quality_score(self, metrics):
        """Calcular score de calidad basado en métricas."""
        score = 0.0
        
        # Rating (40% del score)
        if metrics.get('rating'):
            score += (metrics['rating'] / 5.0) * 0.4
            
        # Number of students (30% del score)
        if metrics.get('students'):
            # Normalizar logarítmicamente
            normalized_students = min(1.0, math.log10(metrics['students']) / 6.0)
            score += normalized_students * 0.3
            
        # Course duration (15% del score)
        if metrics.get('duration_hours'):
            # Cursos de 5-20 horas son ideales
            ideal_duration = 1.0 if 5 <= metrics['duration_hours'] <= 20 else 0.5
            score += ideal_duration * 0.15
            
        # Instructor reputation (15% del score)
        if metrics.get('instructor_rating'):
            score += (metrics['instructor_rating'] / 5.0) * 0.15
            
        return min(1.0, score)
        
    def _passes_quality_filters(self, course, quality_score):
        """Aplicar filtros de calidad configurables."""
        
        # Score mínimo
        if quality_score < self.config.get('min_quality_score', 0.6):
            return False
            
        # Rating mínimo
        if course.get('rating', 0) < self.config.get('min_rating', 4.0):
            return False
            
        # Número mínimo de estudiantes
        if course.get('students', 0) < self.config.get('min_students', 1000):
            return False
            
        # Filtros de categoría
        excluded_categories = self.config.get('excluded_categories', [])
        if course.get('category') in excluded_categories:
            return False
            
        # Filtros de idioma
        preferred_languages = self.config.get('preferred_languages', ['English'])
        if course.get('language') not in preferred_languages:
            return False
            
        return True
```

## Características Principales

### Descubrimiento Inteligente
- **Multi-Source Discovery**: Monitorea múltiples fuentes de cursos gratuitos
- **Real-time Detection**: Detecta nuevas ofertas en tiempo real
- **Duplicate Filtering**: Eliminación automática de duplicados
- **Category Mapping**: Mapeo inteligente de categorías

### Evaluación de Calidad
- **Quality Scoring**: Sistema de puntuación multi-factor
- **Instructor Analysis**: Análisis de reputación de instructores
- **Content Evaluation**: Evaluación de contenido y estructura
- **Student Feedback**: Análisis de reviews y ratings

### Enrollment Automatizado
- **Browser Automation**: Automatización con anti-detection
- **Session Management**: Gestión robusta de sesiones
- **Error Handling**: Manejo de errores y retry logic
- **Rate Limiting**: Respeto a límites de la plataforma

### Data Intelligence
- **Course Analytics**: Análisis detallado de métricas de cursos
- **Trend Detection**: Detección de tendencias en ofertas
- **Performance Tracking**: Seguimiento de performance de enrollment
- **ROI Calculation**: Cálculo de retorno de inversión educativo

## Casos de Uso Principales

### Educación Continua
- **Skill Development**: Desarrollo continuo de habilidades
- **Career Advancement**: Avance profesional mediante certificaciones
- **Learning Path Optimization**: Optimización de rutas de aprendizaje
- **Knowledge Gap Filling**: Llenar gaps de conocimiento específicos

### Research y Análisis
- **Market Research**: Investigación de mercado educativo
- **Trend Analysis**: Análisis de tendencias en educación online
- **Competitor Analysis**: Análisis de competidores en educación
- **Content Gap Analysis**: Identificación de gaps de contenido

### Business Intelligence
- **Educational ROI**: Cálculo de ROI en educación
- **Team Training**: Entrenamiento de equipos empresariales
- **Skill Assessment**: Evaluación de habilidades disponibles
- **Learning Strategy**: Estrategia de aprendizaje organizacional

## Métricas y KPIs

### Métricas de Descubrimiento
- **Courses Discovered**: 500-2000 cursos por día
- **Source Coverage**: 15+ fuentes monitoreadas
- **Discovery Latency**: <30 minutos desde publicación
- **Duplicate Rate**: <5% duplicados

### Métricas de Calidad
- **Quality Score**: Promedio >0.7 en cursos seleccionados
- **False Positive Rate**: <10% cursos de baja calidad
- **Filtering Accuracy**: >90% precisión en filtros
- **Content Relevance**: >85% relevancia temática

### Métricas de Enrollment
- **Success Rate**: >90% enrollment exitoso
- **Processing Speed**: 100-200 cursos por hora
- **Error Rate**: <5% fallos en enrollment
- **Account Safety**: 0% suspensiones de cuenta

### Métricas de Valor
- **Total Courses Enrolled**: Tracking acumulativo
- **Education Value**: Valor educativo estimado
- **Time Saved**: Tiempo ahorrado vs búsqueda manual
- **Learning Efficiency**: Eficiencia de aprendizaje

## Integración con el Ecosistema

### Dashboard Educational
- **Course Portfolio**: Portfolio de cursos enrollados
- **Learning Progress**: Progreso de aprendizaje
- **Skill Mapping**: Mapeo de habilidades adquiridas
- **Certification Tracking**: Seguimiento de certificaciones

### Analytics Integration
- **Learning Analytics**: Análisis de patrones de aprendizaje
- **Performance Metrics**: Métricas de performance educativo
- **ROI Calculation**: Cálculo de retorno de inversión
- **Skill Gap Analysis**: Análisis de gaps de habilidades

### External Integrations
- **LinkedIn Learning**: Integración con LinkedIn
- **Calendar Integration**: Integración con calendarios
- **Slack Notifications**: Notificaciones en Slack
- **CRM Integration**: Integración con sistemas CRM

## Estructura de Datos

```json
{
  "course_id": "udemy_course_12345",
  "title": "Complete Python Programming Masterclass",
  "url": "https://www.udemy.com/course/python-programming/",
  "instructor": {
    "name": "John Doe",
    "rating": 4.7,
    "students": 150000,
    "courses": 25
  },
  "metrics": {
    "rating": 4.6,
    "students": 85000,
    "reviews": 12500,
    "duration_hours": 42.5,
    "lectures": 280,
    "level": "All Levels",
    "language": "English",
    "subtitles": ["Spanish", "French"],
    "last_updated": "2024-11-01",
    "category": "Development",
    "subcategory": "Programming Languages"
  },
  "pricing": {
    "original_price": 84.99,
    "current_price": 0.00,
    "discount_percentage": 100,
    "promotion_end": "2024-12-15T23:59:59Z"
  },
  "quality_assessment": {
    "quality_score": 0.82,
    "content_quality": 0.85,
    "instructor_quality": 0.78,
    "student_satisfaction": 0.84,
    "relevance_score": 0.89
  },
  "enrollment_status": {
    "enrolled": true,
    "enrollment_date": "2024-12-01T14:30:00Z",
    "completion_status": "in_progress",
    "progress_percentage": 15.5,
    "estimated_completion": "2024-12-20"
  },
  "metadata": {
    "discovered_at": "2024-12-01T10:15:00Z",
    "source": "real_discount",
    "discovery_method": "rss_feed",
    "processing_time": 2.3,
    "last_checked": "2024-12-01T14:30:00Z"
  }
}
```

## Configuración y Deployment

### Configuración Principal (`duce-cli-settings.json`)
```json
{
  "discovery": {
    "sources": ["real_discount", "udemy_free", "coursera_free"],
    "max_courses_per_source": 1000,
    "discovery_interval": 3600,
    "enable_real_time": true
  },
  "quality_filters": {
    "min_quality_score": 0.65,
    "min_rating": 4.0,
    "min_students": 1000,
    "min_duration_hours": 2,
    "max_duration_hours": 50,
    "preferred_languages": ["English", "Spanish"],
    "excluded_categories": ["Music", "Arts", "Photography"]
  },
  "enrollment": {
    "max_enrollments_per_day": 50,
    "delay_between_enrollments": [5, 15],
    "enable_auto_enrollment": true,
    "respect_rate_limits": true
  },
  "browser": {
    "headless": true,
    "user_agent_rotation": true,
    "proxy_enabled": false,
    "anti_detection": true
  },
  "logging": {
    "level": "INFO",
    "file_rotation": true,
    "max_file_size": "10MB",
    "backup_count": 5
  }
}
```

### Ejecución
```bash
# Modo interactivo
python cli.py --interactive

# Modo batch con límite
python cli.py --batch --max-courses 100

# Discovery only (sin enrollment)
python cli.py --discover-only

# Enrollment específico
python cli.py --enroll-from-file courses.json

# Modo debug
python cli.py --debug --verbose

# Scheduled mode
python cli.py --scheduled --interval 3600
```

### Variables de Entorno
```bash
# Udemy Credentials
UDEMY_EMAIL=your_email@example.com
UDEMY_PASSWORD=your_password

# Browser Configuration
CHROME_DRIVER_PATH=/path/to/chromedriver
HEADLESS_MODE=true
ANTI_DETECTION=true

# Rate Limiting
MAX_ENROLLMENTS_PER_HOUR=20
DELAY_BETWEEN_REQUESTS=5

# Logging
LOG_LEVEL=INFO
LOG_DIRECTORY=logs/
LOG_ROTATION=true
```

## Funcionalidades Avanzadas

### Anti-Detection System
- **User Agent Rotation**: Rotación automática de user agents
- **Request Timing**: Patrones humanos de navegación
- **Session Management**: Gestión natural de sesiones
- **Fingerprint Masking**: Ocultación de fingerprints del browser

### Quality Assessment Engine
- **Content Analysis**: Análisis de calidad de contenido
- **Instructor Verification**: Verificación de credenciales de instructores
- **Student Feedback Mining**: Mining de feedback de estudiantes
- **Trend Correlation**: Correlación con tendencias del mercado

### Learning Path Optimization
- **Skill Mapping**: Mapeo de habilidades requeridas
- **Prerequisite Detection**: Detección de prerequisitos
- **Learning Sequence**: Secuenciación óptima de cursos
- **Progress Tracking**: Seguimiento de progreso personalizado

## Roadmap y Mejoras Futuras

### Funcionalidades Planeadas
- **Multi-Platform Support**: Soporte para Coursera, edX, Khan Academy
- **AI-Powered Curation**: Curación mediante IA
- **Social Learning**: Características de aprendizaje social
- **Mobile Integration**: Integración con apps móviles

### Optimizaciones Técnicas
- **Parallel Processing**: Procesamiento paralelo de cursos
- **Cloud Deployment**: Deployment en cloud
- **API Development**: Desarrollo de APIs REST
- **Real-time Analytics**: Analytics en tiempo real

### Integraciones Adicionales
- **LMS Integration**: Integración con sistemas LMS
- **Career Platforms**: Integración con plataformas de carrera
- **Skill Assessment**: Evaluación automatizada de habilidades
- **Certification Tracking**: Seguimiento de certificaciones

## Consideraciones Legales y Éticas

### Compliance
- **Terms of Service**: Respeto estricto a términos de servicio
- **Rate Limiting**: Respeto a límites de plataformas
- **Fair Use**: Uso justo de recursos educativos
- **Privacy Protection**: Protección de datos personales

### Best Practices
- **Ethical Mining**: Mining ético y responsable
- **Platform Respect**: Respeto a plataformas educativas
- **Community Guidelines**: Seguimiento de guidelines de comunidad
- **Educational Purpose**: Enfoque en propósito educativo legítimo 