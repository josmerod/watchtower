# Metadata

- Caso de uso: Udemy Universal Course Mining and Intelligence System
- Plataformas involucradas: Udemy Universal Miner, File System Processing
- Descripción corta: Sistema de minería y agregación de cursos de Udemy que procesa outputs de miners externos para crear inteligencia educativa y análisis de tendencias
- Patrón de ejecución: Periódico (diario) con procesamiento de archivos de miners y deduplicación inteligente

## Dependencias

- Fuentes de datos:
  - Udemy Universal Miner output files (src/miners/udemy-universal/Courses)
  - Text files con formato "título - URL" por timestamp
  - Archivos timestamped con formato YYYY-MM-DD--HH-MM.txt
- Bibliotecas de Python principales:
  - `pandas`: Manipulación y análisis de datos de cursos
  - `json`: Procesamiento de datos estructurados
  - `datetime`: Manejo de timestamps y parsing de fechas
  - `logging`: Sistema de logging detallado
  - Custom utilities: `course_deduplication`, `file_system`

## Stack Tecnológico

- Lenguaje de programación: Python 3.10+
- Framework: ETL con procesamiento de archivos locales
- Data Processing: Pandas para análisis y agregaciones
- File Processing: Sistema de lectura de archivos timestamped
- Deduplication: Sistema custom de deduplicación inteligente
- Storage: JSON y CSV para diferentes tipos de análisis

## Implementación

La implementación consta de los siguientes componentes:

1. **Udemy Universal Courses ETL** (`src/etl/goldigging/goldigging_udemy_courses.py`):
   - Motor principal de agregación de cursos Udemy
   - Procesamiento de archivos output de miners externos
   - Sistema de deduplicación inteligente de cursos
   - Combinación temporal de datos históricos y nuevos

2. **Course Deduplication Engine** (`src/utils/course_deduplication.py`):
   - Deduplicación basada en URLs únicas
   - Preferencia por cursos más recientes
   - Mantenimiento de metadatos temporales
   - Estadísticas de deduplicación

3. **File System Processing**:
   - Lectura ordenada de archivos por timestamp (newest first)
   - Parsing automático de timestamps desde nombres de archivo
   - Manejo robusto de errores de lectura
   - Procesamiento incremental de nuevos archivos

4. **Data Aggregation and Analytics**:
   - Combinación de datos históricos con nuevos
   - Análisis temporal de trends en cursos
   - Métricas de volumen y crecimiento
   - Export a múltiples formatos

## Características Avanzadas

### 1. **Intelligent File Processing**
- **Timestamp Parsing**: Extracción automática de timestamps desde nombres de archivo
- **Chronological Ordering**: Procesamiento ordenado desde más reciente a más antiguo
- **Error Recovery**: Manejo robusto de archivos corruptos o mal formateados
- **Incremental Processing**: Solo procesamiento de archivos nuevos cuando sea necesario

### 2. **Advanced Course Deduplication**
- **URL-based Deduplication**: Deduplicación basada en URLs únicas de cursos
- **Temporal Preference**: Preferencia automática por versiones más recientes
- **Metadata Preservation**: Preservación de información temporal y de fuente
- **Statistics Tracking**: Tracking detallado de duplicados removidos

### 3. **Data Integration and Aggregation**
- **Historical Combination**: Combinación inteligente de datos históricos y nuevos
- **Incremental Updates**: Actualización incremental sin pérdida de datos históricos
- **Multi-format Output**: Salida en JSON para procesamiento y CSV para análisis
- **Data Validation**: Validación de integridad de datos durante procesamiento

### 4. **Educational Intelligence Features**
- **Course Trend Analysis**: Análisis de tendencias temporales en cursos
- **Topic Category Detection**: Detección automática de categorías por título
- **Popular Course Identification**: Identificación de cursos populares/trending
- **Educational Gap Analysis**: Análisis de gaps en contenido educativo

### 5. **Mining Integration System**
- **External Miner Support**: Integración con miners externos (Udemy Universal)
- **Flexible Input Processing**: Soporte para diferentes formatos de miners
- **Batch Processing**: Procesamiento en lotes de múltiples archivos
- **Error Tolerance**: Tolerancia a errores en archivos individuales

## Pseudocódigo

```python
def udemy_course_mining_process():
    # 1. Initialize ETL System
    etl = UdemyUniversalCoursesETL()
    setup_directories_and_paths()
    
    # 2. Extract Courses from Miner Files
    all_courses = []
    
    # Get files sorted newest to oldest
    miner_files = get_sorted_miner_files(reverse=True)
    
    for filename in miner_files:
        # Parse timestamp from filename
        scraped_at = parse_timestamp_from_filename(filename)
        
        # Process file content
        file_courses = []
        with open(filename) as f:
            for line in f:
                if line.strip():
                    title, url = parse_course_line(line)
                    file_courses.append({
                        "title": title,
                        "url": url,
                        "scraped_at": scraped_at
                    })
        
        all_courses.extend(file_courses)
    
    # 3. Load and Combine with Historical Data
    if historical_data_exists():
        historical_courses = load_historical_courses()
        combined_courses = historical_courses + all_courses
    else:
        combined_courses = all_courses
    
    # 4. Intelligent Deduplication
    deduplicated_courses, removed_count = deduplicate_courses(
        combined_courses,
        key_field="url",
        prefer_newer=True
    )
    
    # 5. Course Analytics and Enhancement
    enhanced_courses = enhance_course_metadata(deduplicated_courses)
    course_analytics = generate_course_analytics(enhanced_courses)
    
    # 6. Save Results
    save_courses_to_json(enhanced_courses)
    save_courses_to_csv(enhanced_courses)
    save_analytics_report(course_analytics)
    
    # 7. Generate Intelligence Reports
    generate_trend_analysis(enhanced_courses)
    generate_educational_intelligence(enhanced_courses)
```

## Course Data Structure

### Raw Course Data
```python
{
    "title": "Complete Python Bootcamp From Zero to Hero in Python",
    "url": "https://www.udemy.com/course/complete-python-bootcamp/",
    "scraped_at": "2024-01-15T10:30:00"
}
```

### Enhanced Course Data
```python
{
    "title": "Complete Python Bootcamp From Zero to Hero in Python",
    "url": "https://www.udemy.com/course/complete-python-bootcamp/",
    "scraped_at": "2024-01-15T10:30:00",
    "course_id": "complete-python-bootcamp",
    "categories": ["Programming", "Python", "Bootcamp"],
    "level": "Beginner to Advanced",
    "popularity_score": 8.5,
    "trend_indicator": "rising"
}
```

## Métricas y KPIs

### Métricas de Volumen
- **Total Courses**: Número total de cursos únicos procesados
- **New Courses**: Cursos nuevos agregados por día/semana
- **Deduplication Rate**: Porcentaje de duplicados eliminados
- **Processing Volume**: Archivos procesados por ejecución

### Métricas de Calidad
- **Data Completeness**: Porcentaje de cursos con metadata completa
- **URL Validity**: Porcentaje de URLs válidas y accesibles
- **Parsing Success Rate**: Tasa de éxito en parsing de archivos
- **Error Recovery Rate**: Tasa de recuperación de errores de procesamiento

### Métricas de Tendencias
- **Course Growth Rate**: Tasa de crecimiento en número de cursos
- **Category Distribution**: Distribución de cursos por categoría
- **Popular Topics**: Topics más populares por período
- **Seasonal Patterns**: Patrones estacionales en tipos de cursos

### Métricas de Performance
- **Processing Speed**: Cursos procesados por minuto
- **File Processing Time**: Tiempo promedio por archivo
- **Deduplication Performance**: Tiempo de deduplicación por volumen
- **Storage Efficiency**: Eficiencia en uso de almacenamiento

## Casos de Uso Específicos

1. **Educational Content Curators**: Identificación de cursos trending y de alta calidad
2. **Learning and Development Teams**: Análisis de oferta educativa para programas corporativos
3. **EdTech Researchers**: Análisis de tendencias en educación online
4. **Career Counselors**: Identificación de skills y cursos demandados
5. **Market Analysts**: Análisis del mercado de educación online
6. **Students**: Discovery de cursos relevantes por área de interés

## Deduplication Strategy

### Deduplication Algorithm
```python
def deduplicate_courses(courses, key_field="url", prefer_newer=True):
    """
    Deduplicate courses based on unique key field.
    
    Args:
        courses: List of course dictionaries
        key_field: Field to use for deduplication (default: "url")
        prefer_newer: Prefer newer courses when duplicates found
    
    Returns:
        (deduplicated_courses, removed_count)
    """
    seen_keys = {}
    deduplicated = []
    removed_count = 0
    
    for course in courses:
        key = course.get(key_field)
        if not key:
            continue
            
        if key not in seen_keys:
            seen_keys[key] = course
            deduplicated.append(course)
        else:
            # Handle duplicate
            existing_course = seen_keys[key]
            if prefer_newer:
                existing_date = parse_date(existing_course.get("scraped_at"))
                new_date = parse_date(course.get("scraped_at"))
                
                if new_date > existing_date:
                    # Replace with newer course
                    seen_keys[key] = course
                    deduplicated[deduplicated.index(existing_course)] = course
            
            removed_count += 1
    
    return deduplicated, removed_count
```

### Deduplication Metrics
- **Duplicate Detection Rate**: Porcentaje de duplicados detectados correctamente
- **False Positive Rate**: Tasa de falsos positivos en detección
- **Metadata Preservation**: Preservación de metadata importante
- **Performance Impact**: Impacto en performance del proceso de deduplicación

## Educational Intelligence Features

### Course Category Classification
```python
COURSE_CATEGORIES = {
    "programming": [
        "python", "javascript", "java", "c++", "react", "node.js",
        "web development", "software development", "coding"
    ],
    "data_science": [
        "data science", "machine learning", "AI", "analytics",
        "statistics", "pandas", "numpy", "tensorflow"
    ],
    "business": [
        "marketing", "entrepreneurship", "business", "management",
        "finance", "accounting", "sales"
    ],
    "design": [
        "graphic design", "UI/UX", "photoshop", "illustrator",
        "web design", "animation"
    ]
}
```

### Trend Analysis
- **Rising Topics**: Identificación de topics con crecimiento acelerado
- **Seasonal Patterns**: Patrones estacionales en diferentes categorías
- **Emerging Technologies**: Detección temprana de nuevas tecnologías
- **Market Saturation**: Análisis de saturación por categoría

### Educational Gap Analysis
- **Skill Gaps**: Identificación de skills con baja oferta educativa
- **Advanced vs Beginner**: Balance entre contenido básico y avanzado
- **Technology Adoption**: Velocidad de adopción de nuevas tecnologías
- **Regional Preferences**: Preferencias por tipo de contenido por región

## Configuración y Personalización

### File Processing Configuration
```python
PROCESSING_CONFIG = {
    "source_directory": "src/miners/udemy-universal/Courses",
    "output_directory": "data/udemy",
    "file_pattern": "*.txt",
    "timestamp_format": "%Y-%m-%d--%H-%M",
    "encoding": "utf-8"
}
```

### Deduplication Settings
```python
DEDUPLICATION_CONFIG = {
    "key_field": "url",
    "prefer_newer": True,
    "similarity_threshold": 0.95,
    "title_normalization": True,
    "case_sensitive": False
}
```

### Analytics Configuration
```python
ANALYTICS_CONFIG = {
    "trend_analysis_days": 30,
    "popularity_threshold": 100,
    "category_confidence_threshold": 0.7,
    "seasonal_analysis_enabled": True
}
```

## Outputs Generados

1. **Course Data**:
   - `udemy_courses.json`: Cursos completos con metadata
   - `udemy_courses.csv`: Formato tabular para análisis
   - `course_statistics.json`: Estadísticas generales

2. **Analytics Reports**:
   - `trend_analysis.json`: Análisis de tendencias temporales
   - `category_distribution.json`: Distribución por categorías
   - `popular_courses.json`: Cursos más populares identificados

3. **Intelligence Insights**:
   - `educational_gaps.json`: Gaps educativos identificados
   - `emerging_topics.json`: Topics emergentes detectados
   - `market_intelligence.json`: Intelligence del mercado educativo

## Integration with External Miners

### Udemy Universal Miner Integration
- **File Format**: Text files con formato "title - URL"
- **Timestamp Extraction**: Parsing automático desde filename
- **Error Handling**: Manejo robusto de archivos malformados
- **Incremental Processing**: Solo procesamiento de archivos nuevos

### Extensibility for Other Miners
```python
class CourseETLAdapter:
    """Adapter pattern for different course miners."""
    
    def parse_miner_output(self, source_type: str, file_path: str):
        if source_type == "udemy_universal":
            return self._parse_udemy_universal(file_path)
        elif source_type == "coursera_miner":
            return self._parse_coursera_miner(file_path)
        # Add more miners as needed
```

## Quality Assurance

### Data Validation
- **URL Validation**: Verificación de formato y accesibilidad de URLs
- **Title Validation**: Validación de títulos no vacíos y coherentes
- **Timestamp Validation**: Verificación de timestamps válidos
- **Metadata Consistency**: Consistencia en estructura de metadatos

### Error Handling
- **File Reading Errors**: Manejo de archivos corruptos o inaccesibles
- **Parsing Errors**: Recuperación de errores de parsing de líneas
- **Encoding Issues**: Manejo de diferentes encodings de archivos
- **Memory Management**: Gestión eficiente de memoria para archivos grandes

## Performance Optimization

### Processing Optimization
- **Lazy Loading**: Carga lazy de archivos grandes
- **Batch Processing**: Procesamiento en lotes para eficiencia
- **Memory Management**: Gestión optimizada de memoria
- **Parallel Processing**: Procesamiento paralelo cuando sea posible

### Storage Optimization
- **Compression**: Compresión de datos históricos
- **Indexing**: Indexing para búsquedas rápidas
- **Partitioning**: Particionado por fecha para mejor performance
- **Archive Policies**: Políticas de archivo para datos antiguos 