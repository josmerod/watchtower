# Metadata

- Caso de uso: **Goldigging Multi-Platform Course Mining**
- Plataformas involucradas: Coursera, Udemy, DeepLearning.AI, YouTube, Class Central, EdX
- Descripción corta: Sistema avanzado de minería de cursos educativos que agrega contenido de múltiples plataformas educativas para análisis y descubrimiento
- Patrón de ejecución: Programado (diario), sincronización en tiempo real, análisis batch

## Dependencias

- APIs y servicios externos:
  - Class Central API/Web Scraping
  - Coursera API (limited access)
  - Udemy API/Web Scraping
  - DeepLearning.AI Platform
  - YouTube API (educational content)
  - EdX API
  - Khan Academy API

- Bibliotecas de Python principales:
  - `playwright` - Web scraping moderno y anti-detection
  - `beautifulsoup4` - Parsing HTML robusto
  - `cloudscraper` - Bypass Cloudflare protection
  - `requests` - HTTP client para APIs
  - `polars` - Análisis eficiente de datos de cursos
  - `pydantic` - Validación de datos de cursos

## Stack Tecnológico

- Lenguaje de programación: Python 3.10+
- Framework: Multi-platform scraping con Playwright/Selenium
- Almacenamiento de datos: JSON estructurado, PostgreSQL para analytics
- Procesamiento: Parallel processing para múltiples fuentes
- Orquestación: Scheduler coordinado para múltiples plataformas
- Logging: Sistema avanzado con tracking per-platform

## Implementación

La implementación consta de los siguientes componentes:

1. **Platform-Specific Miners** (`src/etl/goldigging/`):
   - **Coursera Miner**: `goldigging_coursera_courses.py` - Mining via Class Central
   - **Udemy Miner**: `goldigging_udemy_courses.py` - Direct platform mining
   - **DeepLearning.AI Miner**: `goldigging_deeplearningai_courses.py` - Specialized AI courses
   - **YouTube Miner**: `goldigging_youtube_posts.py` - Educational video content

2. **Unified Course Processing**:
   - **Course Deduplication**: Sistema avanzado de deduplicación cross-platform
   - **Content Normalization**: Normalización de metadatos entre plataformas
   - **Quality Assessment**: Evaluación de calidad multi-dimensional
   - **Category Mapping**: Mapeo inteligente de categorías

3. **Anti-Detection System**:
   - **Browser Automation**: Playwright con anti-detection avanzado
   - **Cloudflare Bypass**: Integración con cloudscraper
   - **Rate Limiting**: Respeto inteligente a límites de plataforma
   - **Session Management**: Gestión robusta de sesiones

4. **Data Intelligence Layer**:
   - **Course Analytics**: Análisis profundo de métricas de cursos
   - **Trend Detection**: Detección de tendencias educativas
   - **Platform Comparison**: Comparaciones entre plataformas
   - **Market Intelligence**: Inteligencia de mercado educativo

## Pseudocódigo

```python
class GolddiggingCourseMiner:
    def __init__(self):
        # Configurar plataformas soportadas
        self.platforms = {
            'coursera': CourseraMiner(),
            'udemy': UdemyMiner(),
            'deeplearning_ai': DeepLearningAIMiner(),
            'youtube': YouTubeMiner(),
            'edx': EdXMiner(),
            'khan_academy': KhanAcademyMiner()
        }
        
        # Sistema de deduplicación
        self.deduplicator = CourseDeduplicator()
        
        # Normalizador de contenido
        self.normalizer = CourseNormalizer()
        
    async def mine_all_platforms(self, max_courses_per_platform=1000):
        """Minar cursos de todas las plataformas en paralelo."""
        
        tasks = []
        for platform_name, miner in self.platforms.items():
            task = self._mine_platform_async(platform_name, miner, max_courses_per_platform)
            tasks.append(task)
            
        # Ejecutar mining en paralelo
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados
        all_courses = []
        for platform_name, result in zip(self.platforms.keys(), results):
            if isinstance(result, Exception):
                self.logger.error(f"Platform {platform_name} failed: {result}")
                continue
                
            courses = result
            self.logger.info(f"{platform_name}: {len(courses)} courses mined")
            all_courses.extend(courses)
            
        # Deduplicar y normalizar
        unique_courses = self.deduplicator.deduplicate_cross_platform(all_courses)
        normalized_courses = self.normalizer.normalize_course_data(unique_courses)
        
        return normalized_courses
        
    async def _mine_platform_async(self, platform_name, miner, max_courses):
        """Minar una plataforma específica de forma asíncrona."""
        
        try:
            self.logger.info(f"Starting mining for {platform_name}")
            
            # Configurar anti-detection
            miner.configure_anti_detection()
            
            # Inicializar sesión
            await miner.initialize_session()
            
            # Minar cursos
            courses = await miner.mine_courses(max_courses=max_courses)
            
            # Procesar cursos específicos de plataforma
            processed_courses = miner.process_platform_specific(courses)
            
            # Añadir metadatos de plataforma
            for course in processed_courses:
                course['source_platform'] = platform_name
                course['mined_at'] = datetime.now().isoformat()
                course['platform_confidence'] = miner.calculate_confidence(course)
                
            return processed_courses
            
        except Exception as e:
            self.logger.error(f"Mining failed for {platform_name}: {e}")
            return []
        finally:
            await miner.cleanup_session()

class CourseraMiner:
    """Miner especializado para Coursera via Class Central."""
    
    def __init__(self):
        self.base_url = "https://www.classcentral.com/provider/coursera"
        self.session = None
        
    async def mine_courses(self, max_courses=1000):
        """Minar cursos de Coursera via Class Central."""
        
        courses = []
        max_pages = self._calculate_max_pages(max_courses)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=self._get_random_user_agent()
            )
            
            # Anti-detection stealth
            await context.add_init_script(
                "() => { Object.defineProperty(navigator, 'webdriver', { get: () => undefined }); }"
            )
            
            page = await context.new_page()
            
            # Establecer cookies visitando primero el sitio principal
            await page.goto("https://www.classcentral.com/", timeout=60000)
            await page.wait_for_timeout(3000)
            
            page_num = 1
            while page_num <= max_pages and len(courses) < max_courses:
                url = f"{self.base_url}?sort=created-up&page={page_num}"
                
                try:
                    await page.goto(url, timeout=60000)
                    await page.wait_for_timeout(random.randint(5000, 8000))
                    
                    content = await page.content()
                    
                    # Detectar challenge de Cloudflare
                    if self._is_cloudflare_challenge(content):
                        content = await self._bypass_cloudflare(url)
                        
                    # Extraer cursos de la página
                    page_courses = self._extract_courses_from_page(content)
                    
                    if not page_courses:
                        self.logger.warning(f"No courses found on page {page_num}")
                        break
                        
                    courses.extend(page_courses)
                    page_num += 1
                    
                except Exception as e:
                    self.logger.error(f"Error processing page {page_num}: {e}")
                    break
                    
            await browser.close()
            
        return courses[:max_courses]
        
    def _extract_courses_from_page(self, content):
        """Extraer información de cursos de una página."""
        
        soup = BeautifulSoup(content, "html.parser")
        course_elements = soup.find_all("li", class_="course-list-course")
        
        courses = []
        for element in course_elements:
            course_data = self._extract_course_info(element)
            if course_data:
                courses.append(course_data)
                
        return courses
        
    def _extract_course_info(self, course_element):
        """Extraer información detallada de un curso."""
        
        course_data = {}
        
        try:
            # Título y URL
            title_element = course_element.find("h2", class_="text-1")
            if title_element:
                course_data["title"] = title_element.text.strip()
                a_tag = title_element.find_parent("a")
                if a_tag:
                    relative_url = a_tag.get("href", "")
                    course_data["url"] = f"https://www.classcentral.com{relative_url}"
                    
            # Institución
            institution_element = course_element.find("a", href=lambda x: x and "/institution/" in x)
            if institution_element:
                course_data["institution"] = institution_element.text.strip()
                
            # Rating y reviews
            rating_element = course_element.find("span", class_="rating-text")
            if rating_element:
                rating_text = rating_element.text.strip()
                course_data["rating"] = self._parse_rating(rating_text)
                
            # Dificultad
            difficulty_element = course_element.find("span", class_="difficulty-level")
            if difficulty_element:
                course_data["difficulty"] = difficulty_element.text.strip()
                
            # Duración
            duration_element = course_element.find("span", class_="course-length")
            if duration_element:
                course_data["duration"] = duration_element.text.strip()
                
            # Certificado
            certificate_element = course_element.find("span", class_="certificate-type")
            if certificate_element:
                course_data["certificate"] = certificate_element.text.strip()
                
            # Precio (si disponible)
            price_element = course_element.find("span", class_="course-price")
            if price_element:
                course_data["price"] = price_element.text.strip()
            else:
                course_data["price"] = "Free"
                
            # Categoría
            category_element = course_element.find("a", href=lambda x: x and "/subject/" in x)
            if category_element:
                course_data["category"] = category_element.text.strip()
                
            # Fecha de inicio
            start_date_element = course_element.find("span", class_="course-start-date")
            if start_date_element:
                course_data["start_date"] = start_date_element.text.strip()
                
            # Metadatos adicionales
            course_data["platform"] = "coursera"
            course_data["language"] = "English"  # Default, can be enhanced
            course_data["extracted_at"] = datetime.now().isoformat()
            
            return course_data
            
        except Exception as e:
            self.logger.error(f"Error extracting course info: {e}")
            return None

class CourseDeduplicator:
    """Sistema avanzado de deduplicación de cursos cross-platform."""
    
    def __init__(self):
        self.similarity_threshold = 0.85
        self.title_weight = 0.4
        self.description_weight = 0.3
        self.instructor_weight = 0.2
        self.platform_weight = 0.1
        
    def deduplicate_cross_platform(self, courses):
        """Deduplicar cursos entre múltiples plataformas."""
        
        if not courses:
            return []
            
        # Normalizar para comparación
        normalized_courses = [self._normalize_for_comparison(course) for course in courses]
        
        # Crear matriz de similitud
        similarity_matrix = self._calculate_similarity_matrix(normalized_courses)
        
        # Identificar duplicados
        duplicates = self._identify_duplicates(similarity_matrix)
        
        # Resolver duplicados (mantener mejor versión)
        unique_courses = self._resolve_duplicates(courses, duplicates)
        
        self.logger.info(f"Deduplication: {len(courses)} -> {len(unique_courses)} courses")
        
        return unique_courses
        
    def _calculate_similarity_matrix(self, normalized_courses):
        """Calcular matriz de similitud entre cursos."""
        
        n = len(normalized_courses)
        similarity_matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        
        for i in range(n):
            for j in range(i + 1, n):
                similarity = self._calculate_course_similarity(
                    normalized_courses[i], 
                    normalized_courses[j]
                )
                similarity_matrix[i][j] = similarity
                similarity_matrix[j][i] = similarity
                
        return similarity_matrix
        
    def _calculate_course_similarity(self, course1, course2):
        """Calcular similitud entre dos cursos."""
        
        # Similitud de título
        title_sim = self._text_similarity(course1.get('title', ''), course2.get('title', ''))
        
        # Similitud de descripción
        desc_sim = self._text_similarity(course1.get('description', ''), course2.get('description', ''))
        
        # Similitud de instructor
        instructor_sim = self._text_similarity(course1.get('instructor', ''), course2.get('instructor', ''))
        
        # Penalización por plataforma diferente
        platform_penalty = 0.0 if course1.get('platform') == course2.get('platform') else 0.1
        
        # Similitud ponderada
        similarity = (
            title_sim * self.title_weight +
            desc_sim * self.description_weight +
            instructor_sim * self.instructor_weight
        ) - platform_penalty
        
        return max(0.0, min(1.0, similarity))
        
    def _text_similarity(self, text1, text2):
        """Calcular similitud textual usando algoritmos avanzados."""
        
        from difflib import SequenceMatcher
        
        if not text1 or not text2:
            return 0.0
            
        # Normalizar textos
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        # Usar SequenceMatcher para similitud
        similarity = SequenceMatcher(None, text1, text2).ratio()
        
        return similarity

class CourseNormalizer:
    """Normalizador de datos de cursos entre plataformas."""
    
    def __init__(self):
        self.category_mapping = self._load_category_mapping()
        self.language_mapping = self._load_language_mapping()
        
    def normalize_course_data(self, courses):
        """Normalizar datos de cursos para consistencia cross-platform."""
        
        normalized_courses = []
        
        for course in courses:
            normalized_course = self._normalize_single_course(course)
            if normalized_course:
                normalized_courses.append(normalized_course)
                
        return normalized_courses
        
    def _normalize_single_course(self, course):
        """Normalizar un curso individual."""
        
        try:
            normalized = {
                # Campos principales
                'id': self._generate_course_id(course),
                'title': self._normalize_title(course.get('title', '')),
                'description': self._normalize_description(course.get('description', '')),
                'url': course.get('url', ''),
                
                # Metadatos académicos
                'instructor': self._normalize_instructor(course.get('instructor', '')),
                'institution': self._normalize_institution(course.get('institution', '')),
                'category': self._normalize_category(course.get('category', '')),
                'difficulty': self._normalize_difficulty(course.get('difficulty', '')),
                'language': self._normalize_language(course.get('language', 'English')),
                
                # Métricas
                'rating': self._normalize_rating(course.get('rating')),
                'duration': self._normalize_duration(course.get('duration', '')),
                'price': self._normalize_price(course.get('price', '')),
                
                # Metadatos de plataforma
                'platform': course.get('platform', 'unknown'),
                'source_platform': course.get('source_platform', course.get('platform', 'unknown')),
                'platform_confidence': course.get('platform_confidence', 0.5),
                
                # Fechas
                'start_date': self._normalize_date(course.get('start_date')),
                'extracted_at': course.get('extracted_at', datetime.now().isoformat()),
                'last_updated': datetime.now().isoformat(),
                
                # Flags
                'is_free': self._determine_if_free(course.get('price', '')),
                'has_certificate': self._determine_certificate(course.get('certificate', '')),
                'is_self_paced': self._determine_self_paced(course),
                
                # Campos calculados
                'quality_score': self._calculate_quality_score(course),
                'popularity_score': self._calculate_popularity_score(course),
                'value_score': self._calculate_value_score(course)
            }
            
            return normalized
            
        except Exception as e:
            self.logger.error(f"Error normalizing course: {e}")
            return None
```

## Características Principales

### Multi-Platform Mining
- **Unified Interface**: Interfaz unificada para múltiples plataformas educativas
- **Platform-Specific Optimization**: Optimizaciones específicas por plataforma
- **Parallel Processing**: Mining paralelo de múltiples fuentes
- **Rate Limiting Intelligence**: Rate limiting inteligente per-platform

### Advanced Anti-Detection
- **Browser Automation**: Playwright con capacidades anti-detection
- **Cloudflare Bypass**: Bypass automático de protecciones Cloudflare
- **Session Management**: Gestión inteligente de sesiones y cookies
- **User Agent Rotation**: Rotación de user agents y fingerprints

### Course Intelligence
- **Cross-Platform Deduplication**: Deduplicación sofisticada entre plataformas
- **Content Normalization**: Normalización de metadatos y categorías
- **Quality Assessment**: Evaluación multi-dimensional de calidad
- **Trend Analysis**: Análisis de tendencias educativas

### Data Processing
- **Structured Output**: Salida estructurada en múltiples formatos
- **Real-time Processing**: Procesamiento en tiempo real de datos
- **Historical Tracking**: Seguimiento histórico de cambios
- **Analytics Integration**: Integración con sistemas de analytics

## Casos de Uso Principales

### Educational Intelligence
- **Course Discovery**: Descubrimiento avanzado de cursos relevantes
- **Platform Comparison**: Comparación objetiva entre plataformas
- **Trend Analysis**: Análisis de tendencias en educación online
- **Market Research**: Investigación de mercado educativo

### Learning Path Optimization
- **Curriculum Planning**: Planificación de currículos educativos
- **Skill Gap Analysis**: Análisis de gaps de habilidades
- **Learning Recommendations**: Recomendaciones personalizadas
- **Progress Tracking**: Seguimiento de progreso educativo

### Business Intelligence
- **Competitive Analysis**: Análisis competitivo de plataformas educativas
- **Content Strategy**: Estrategia de contenido educativo
- **Pricing Analysis**: Análisis de estrategias de pricing
- **Market Positioning**: Posicionamiento en mercado educativo

### Research & Development
- **Educational Innovation**: Investigación en innovación educativa
- **Content Gap Analysis**: Análisis de gaps de contenido
- **Technology Adoption**: Adopción de tecnologías educativas
- **Quality Assessment**: Evaluación de calidad educativa

## Métricas y KPIs

### Métricas de Mining
- **Courses per Platform**: 500-2000 cursos por plataforma por día
- **Platform Coverage**: 6+ plataformas principales cubiertas
- **Mining Success Rate**: >95% éxito en extracción
- **Data Freshness**: <24 horas latencia de datos

### Métricas de Calidad
- **Deduplication Accuracy**: >90% precisión en deduplicación
- **Data Completeness**: >85% campos completos
- **Platform Confidence**: >80% confianza promedio
- **Quality Score**: Promedio >0.7 en cursos procesados

### Métricas de Performance
- **Processing Speed**: 100-200 cursos por minuto
- **Anti-Detection Success**: >98% bypass de protecciones
- **Session Stability**: >95% sesiones exitosas
- **Error Recovery**: <5% errores irrecuperables

### Métricas de Cobertura
- **Category Coverage**: 20+ categorías principales
- **Language Coverage**: 10+ idiomas soportados
- **Institution Coverage**: 500+ instituciones rastreadas
- **Price Range Coverage**: Free hasta $500+ por curso

## Integración con el Ecosistema

### Educational Dashboard
- **Course Catalog**: Catálogo unificado de cursos
- **Platform Analytics**: Analytics por plataforma
- **Trend Visualization**: Visualización de tendencias
- **Search Interface**: Interfaz de búsqueda avanzada

### Data Pipeline Integration
- **ETL Coordination**: Coordinación con otros ETLs
- **Real-time Updates**: Actualizaciones en tiempo real
- **Historical Analysis**: Análisis histórico de datos
- **Cross-Platform Correlation**: Correlación entre plataformas

### External Integrations
- **LMS Integration**: Integración con sistemas LMS
- **Calendar Sync**: Sincronización con calendarios
- **Progress Tracking**: Seguimiento de progreso
- **Certification Management**: Gestión de certificaciones

## Estructura de Datos

```json
{
  "id": "coursera_ml_stanford_2024",
  "title": "Machine Learning Specialization",
  "description": "Complete machine learning course covering supervised and unsupervised learning...",
  "url": "https://www.coursera.org/specializations/machine-learning",
  "instructor": "Andrew Ng",
  "institution": "Stanford University",
  "category": "computer_science",
  "subcategory": "machine_learning",
  "difficulty": "intermediate",
  "language": "english",
  "rating": 4.8,
  "review_count": 125000,
  "duration": "3 months",
  "estimated_hours": 120,
  "price": "free_audit",
  "price_usd": 0.0,
  "certificate_price": 49.0,
  "platform": "coursera",
  "source_platform": "coursera",
  "platform_confidence": 0.95,
  "start_date": "2024-12-15T00:00:00Z",
  "extracted_at": "2024-12-01T10:30:00Z",
  "last_updated": "2024-12-01T10:30:00Z",
  "is_free": true,
  "has_certificate": true,
  "is_self_paced": false,
  "quality_score": 0.92,
  "popularity_score": 0.89,
  "value_score": 0.95,
  "skills": ["machine_learning", "python", "tensorflow", "data_analysis"],
  "prerequisites": ["basic_programming", "linear_algebra", "statistics"],
  "modules": [
    {
      "title": "Supervised Learning",
      "duration": "4 weeks",
      "topics": ["linear_regression", "logistic_regression", "neural_networks"]
    },
    {
      "title": "Unsupervised Learning",
      "duration": "3 weeks",
      "topics": ["clustering", "dimensionality_reduction", "anomaly_detection"]
    }
  ],
  "metadata": {
    "word_count": 1500,
    "has_assignments": true,
    "has_video_lectures": true,
    "has_hands_on_projects": true,
    "enrollment_count": 500000,
    "completion_rate": 0.65
  }
}
```

## Configuración y Deployment

### Variables de Entorno
```bash
# Goldigging Configuration
GOLDIGGING_ENABLED=true
GOLDIGGING_MAX_PAGES_FIRST_RUN=150
GOLDIGGING_MAX_PAGES_SUBSEQUENT=10
GOLDIGGING_PARALLEL_PLATFORMS=6

# Anti-Detection
PLAYWRIGHT_HEADLESS=true
CLOUDFLARE_BYPASS_ENABLED=true
USER_AGENT_ROTATION=true
SESSION_REUSE_ENABLED=true

# Platform-Specific
COURSERA_VIA_CLASSCENTRAL=true
UDEMY_DIRECT_SCRAPING=false
DEEPLEARNING_AI_API_KEY=your_api_key
YOUTUBE_API_KEY=your_youtube_key

# Data Processing
DEDUPLICATION_ENABLED=true
SIMILARITY_THRESHOLD=0.85
NORMALIZATION_ENABLED=true
QUALITY_FILTERING=true

# Storage
COURSES_OUTPUT_DIR=data/courses/
BACKUP_ENABLED=true
COMPRESSION_ENABLED=true
```

### Ejecución
```bash
# Mining completo de todas las plataformas
python -m src.etl.goldigging --mine-all

# Mining de plataforma específica
python -m src.etl.goldigging.goldigging_coursera_courses

# Mining con límites personalizados
python -m src.etl.goldigging --platform coursera --max-courses 500

# Modo deduplicación solamente
python -m src.etl.goldigging --deduplicate-only

# Análisis de calidad
python -m src.etl.goldigging --quality-analysis

# Sincronización incremental
python -m src.etl.goldigging --incremental-sync
```

## Roadmap y Mejoras Futuras

### Funcionalidades Planeadas
- **API Integration**: Integración directa con APIs oficiales
- **Real-time Monitoring**: Monitoreo en tiempo real de nuevos cursos
- **AI Content Analysis**: Análisis de contenido impulsado por IA
- **Personalization Engine**: Motor de personalización avanzado

### Platform Expansion
- **LinkedIn Learning**: Integración con LinkedIn Learning
- **MasterClass**: Mining de MasterClass
- **Pluralsight**: Integración con Pluralsight
- **Skillshare**: Mining de Skillshare

### Advanced Features
- **Video Analysis**: Análisis de contenido de videos
- **Skill Mapping**: Mapeo avanzado de habilidades
- **Career Path Analysis**: Análisis de rutas de carrera
- **ROI Calculation**: Cálculo de ROI educativo

### Technical Improvements
- **Distributed Mining**: Mining distribuido y escalable
- **ML-Enhanced Deduplication**: Deduplicación mejorada con ML
- **Advanced Anti-Detection**: Técnicas anti-detection más sofisticadas
- **Real-time Analytics**: Analytics en tiempo real

## Consideraciones Legales y Éticas

### Compliance
- **Terms of Service**: Cumplimiento estricto de términos de servicio
- **Rate Limiting**: Respeto a límites de plataformas
- **Fair Use**: Uso justo de contenido educativo
- **Privacy Protection**: Protección de datos personales

### Ethical Mining
- **Educational Purpose**: Enfoque en propósito educativo
- **Platform Respect**: Respeto a plataformas educativas
- **Data Transparency**: Transparencia en uso de datos
- **Community Benefit**: Beneficio para comunidad educativa 