# Metadata

- Caso de uso: Coursera Educational Intelligence and Online Learning Analytics System
- Plataformas involucradas: Coursera (via ClassCentral Provider Aggregation)
- Descripción corta: Sistema de inteligencia para mining de cursos educativos de Coursera con analysis de learning trends, skill development y educational market intelligence
- Patrón de ejecución: Periódico (cada 24-48 horas) con first run extensive crawling (150 pages) y subsequent incremental updates (10 pages)

## Dependencias

- APIs y fuentes externas:
  - ClassCentral Coursera Provider Page (classcentral.com/provider/coursera)
  - Coursera course metadata y descriptions
  - Institution information y course ratings
  - Course pricing y enrollment data
- Bibliotecas de Python principales:
  - `playwright`: Browser automation para web scraping
  - `beautifulsoup4`: HTML parsing y content extraction
  - `json`: Structured data processing
  - `pandas`: Data processing y CSV export
  - `asyncio`: Asynchronous scraping operations

## Stack Tecnológico

- Lenguaje de programación: Python 3.10+
- Framework: ETL con Playwright-based web scraping
- Data Extraction: Advanced browser automation con anti-detection
- Educational Analysis: Course quality assessment y trend detection
- Learning Intelligence: Skill mapping y educational pathway analysis
- Export: JSON y CSV con educational metadata

## Implementación

La implementación consta de los siguientes componentes:

1. **Coursera ETL** (`src/etl/goldigging/goldigging_coursera_courses.py`):
   - Motor principal de scraping de cursos Coursera
   - Playwright automation para content extraction
   - Course metadata parsing y quality assessment
   - Incremental vs full scraping modes

2. **Educational Intelligence Engine**:
   - **Course Quality Assessment**: Assessment de course quality basado en ratings y reviews
   - **Skill Mapping Analysis**: Mapping de skills y learning paths
   - **Institution Intelligence**: Intelligence sobre educational institutions
   - **Market Trend Detection**: Detection de trends en educational market

3. **Learning Analytics Features**:
   - **Certificate Tracking**: Tracking de certificate offerings y value
   - **Duration Analysis**: Analysis de course duration y time investment
   - **Pricing Intelligence**: Intelligence sobre course pricing strategies
   - **Subject Classification**: Classification avanzada de subjects y topics

4. **Educational Market Processing**:
   - **Institution Reputation**: Reputation assessment de educational institutions
   - **Course Popularity**: Popularity metrics y enrollment estimation
   - **Learning Path Optimization**: Optimization de learning paths
   - **Career Development Mapping**: Mapping de courses a career development

## Características Avanzadas

### 1. **Sophisticated Web Scraping Architecture**
```python
class CourseraScraper:
    """Scraper for retrieving Coursera courses from Class Central."""
    
    BASE_URL = "https://www.classcentral.com/provider/coursera"
    
    async def scrape_courses(self) -> List[Dict[str, Any]]:
        """Scrape courses using Playwright automation."""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Configure anti-detection
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            # Process pages with intelligent pagination
            for page_num in range(1, self.max_pages + 1):
                await page.goto(f"{self.BASE_URL}?page={page_num}")
                await page.wait_for_load_state('networkidle')
                
                # Extract course elements
                course_elements = await page.query_selector_all("li.course-list-course")
                
                for element in course_elements:
                    course_data = await self.extract_course_info(element)
                    if course_data:
                        all_courses.append(course_data)
```

### 2. **Advanced Course Information Extraction**
```python
def extract_course_info(self, course_element, soup) -> Dict[str, Any]:
    """Extract comprehensive course information."""
    course_data = {}
    
    # Core course information
    course_name_element = course_element.find("h2", class_="text-1")
    if course_name_element:
        course_data["title"] = course_name_element.text.strip()
        # Extract course URL
        a_tag = course_name_element.find_parent("a")
        if a_tag:
            relative_url = a_tag.get("href", "")
            course_data["url"] = f"https://www.classcentral.com{relative_url}"
    
    # Institution and provider
    institution_element = course_element.find("a", href=lambda x: x and "/institution/" in x)
    if institution_element:
        course_data["institution"] = institution_element.text.strip()
    
    # Enhanced metadata extraction
    track_props = course_element.find(attrs={"data-track-props": True})
    if track_props:
        try:
            props = json.loads(track_props["data-track-props"])
            course_data["subject"] = props.get("course_subject", "")
            course_data["language"] = props.get("course_language", "")
            course_data["certificate_offered"] = props.get("course_certificate", False)
        except json.JSONDecodeError:
            pass
```

### 3. **Intelligent Scraping Mode Selection**
```python
def __init__(self, max_pages: Optional[int] = None) -> None:
    """Initialize with intelligent page selection."""
    # Determine if this is first run
    self.is_first_run = not os.path.exists(self.last_run_file)
    
    # Set max pages based on whether this is first run
    if self.max_pages is None:
        if self.is_first_run:
            logger.info(f"First run detected, will scrape {MAX_PAGES_FIRST_RUN} pages")
            self.max_pages = MAX_PAGES_FIRST_RUN  # 150 pages
        else:
            logger.info(f"Not first run, using default of {MAX_PAGES_SUBSEQUENT_RUN} pages")
            self.max_pages = MAX_PAGES_SUBSEQUENT_RUN  # 10 pages
```

### 4. **Advanced Educational Analytics Features**
- **Learning Path Intelligence**: Intelligence sobre optimal learning paths
- **Skill Gap Analysis**: Analysis de skill gaps en different domains
- **Career Transition Mapping**: Mapping de courses para career transitions
- **Industry Alignment**: Alignment con industry skill requirements

### 5. **Course Deduplication System**
- **URL-Based Deduplication**: Deduplication basada en course URLs
- **Temporal Preference**: Preference para newer course versions
- **Content Similarity**: Detection de similar courses
- **Quality-Based Selection**: Selection basada en course quality metrics

## Course Data Structure

### Enhanced Course Data
```python
{
    "id": "coursera_course_abc123",
    "title": "Machine Learning Specialization",
    "description": "Comprehensive introduction to machine learning algorithms and applications in Python.",
    "url": "https://www.classcentral.com/course/coursera-machine-learning-specialization",
    "institution": "Stanford University",
    "provider": "Coursera",
    
    # Course Details
    "subject": "Computer Science",
    "language": "English",
    "duration": "6 months",
    "start_date": "Self-paced",
    "cost": "$49/month",
    "is_free": false,
    
    # Quality Metrics
    "rating": 4.8,
    "certificate_offered": true,
    "institution_reputation": "top_tier",
    "course_quality_score": 9.2,  # 1-10 scale
    
    # Educational Analysis
    "difficulty_level": "intermediate",
    "prerequisite_level": "basic_programming",
    "target_audience": ["data_scientists", "ml_engineers", "students"],
    "learning_outcomes": ["ML algorithms", "Python programming", "Data analysis"],
    
    # Market Intelligence
    "enrollment_estimate": "high",
    "completion_rate_estimate": "medium",
    "career_relevance": "very_high",
    "industry_demand": "extremely_high",
    
    # Skill Mapping
    "skills_taught": ["machine_learning", "python", "tensorflow", "data_science"],
    "skill_level": "intermediate_to_advanced",
    "career_paths": ["data_scientist", "ml_engineer", "ai_researcher"],
    "industry_applications": ["tech", "finance", "healthcare", "retail"],
    
    # Course Structure
    "course_type": "specialization",
    "modules_count": 4,
    "estimated_hours": 240,
    "hands_on_projects": true,
    "peer_assessment": true,
    
    # Competitive Analysis
    "market_position": "leading",
    "price_competitiveness": "premium",
    "content_uniqueness": "high",
    "instructor_reputation": "excellent",
    
    # Temporal Data
    "last_updated": "2024-01-15",
    "content_freshness": "very_recent",
    "technology_relevance": "cutting_edge",
    
    # Metadata
    "scraped_at": "2024-01-16T14:30:00",
    "platform": "coursera",
    "data_source": "classcentral",
    "educational_intelligence": 9.1
}
```

## Métricas y KPIs

### Métricas de Educational Quality
- **Course Quality Distribution**: Distribution de course quality scores
- **Institution Reputation Index**: Index de reputation de institutions
- **Certificate Value Assessment**: Assessment de certificate value
- **Learning Outcome Achievement**: Achievement rates de learning outcomes

### Métricas de Market Intelligence
- **Subject Popularity Trends**: Trends de popularity por subjects
- **Pricing Strategy Analysis**: Analysis de pricing strategies
- **Enrollment Pattern Detection**: Detection de enrollment patterns
- **Career Alignment Metrics**: Metrics de alignment con career paths

### Métricas de Content Intelligence
- **Content Freshness Score**: Score de content freshness
- **Technology Relevance**: Relevance de technologies covered
- **Skill Demand Correlation**: Correlation con industry skill demand
- **Learning Path Optimization**: Optimization de learning paths

### Métricas de Platform Performance
- **Scraping Efficiency**: Efficiency de scraping operations
- **Data Quality Score**: Score de data quality
- **Coverage Completeness**: Completeness de course coverage
- **Update Frequency**: Frequency de content updates

## Casos de Uso Específicos

1. **Career Changers**: Course recommendations para career transitions
2. **HR Professionals**: Skill development planning y team training
3. **Educational Advisors**: Course selection guidance y learning path design
4. **Students**: Academic enhancement y skill development
5. **Corporate Training**: Enterprise learning y development programs
6. **Investment Analysts**: EdTech market intelligence y trends

## Educational Intelligence System

### Learning Path Optimization
```python
def optimize_learning_path(target_role: str, current_skills: List[str], available_time: int):
    """
    Optimize learning path for specific career goals.
    """
    path_optimization = {
        "skill_gap_analysis": identify_skill_gaps(target_role, current_skills),
        "course_sequence": design_optimal_sequence(target_role, available_time),
        "timeline_estimation": estimate_completion_timeline(available_time),
        "cost_optimization": optimize_cost_effectiveness(target_role),
        "career_impact": assess_career_impact(target_role)
    }
    
    # Calculate path effectiveness score
    path_score = (
        path_optimization["skill_gap_coverage"] * 0.30 +
        path_optimization["time_efficiency"] * 0.25 +
        path_optimization["cost_effectiveness"] * 0.20 +
        path_optimization["career_impact"] * 0.25
    )
    
    return path_optimization, path_score
```

### Course Quality Assessment
```python
def assess_course_quality(course_data):
    """
    Assess course quality based on multiple factors.
    """
    quality_factors = {
        "institution_reputation": assess_institution_quality(course_data),
        "content_depth": evaluate_content_comprehensiveness(course_data),
        "practical_application": assess_hands_on_components(course_data),
        "industry_relevance": evaluate_industry_alignment(course_data),
        "student_outcomes": estimate_learning_outcomes(course_data)
    }
    
    # Weighted quality score
    quality_score = sum(
        factor * weight for factor, weight in [
            (quality_factors["institution_reputation"], 0.25),
            (quality_factors["content_depth"], 0.25),
            (quality_factors["practical_application"], 0.20),
            (quality_factors["industry_relevance"], 0.20),
            (quality_factors["student_outcomes"], 0.10)
        ]
    )
    
    return quality_score
```

## Educational Market Intelligence

### Subject Trend Analysis
- **Emerging Skill Demands**: Demand para emerging skills y technologies
- **Industry-Specific Learning**: Learning patterns por industry sectors
- **Technology Adoption Curves**: Adoption curves de new technologies
- **Career Transition Patterns**: Patterns de career transitions

### Institution Intelligence Analysis
- **University Partnerships**: Partnership patterns con universities
- **Industry Collaboration**: Collaboration con industry partners
- **Course Innovation**: Innovation en course design y delivery
- **Global Reach Analysis**: Analysis de global reach y accessibility

## Skills Intelligence Features

### Skill Mapping System
```python
def map_course_to_skills(course_data):
    """
    Map courses to specific skills and competencies.
    """
    skill_mapping = {
        "technical_skills": extract_technical_skills(course_data),
        "soft_skills": identify_soft_skills(course_data),
        "industry_skills": map_industry_specific_skills(course_data),
        "certification_value": assess_certification_value(course_data)
    }
    
    # Calculate skill development potential
    skill_score = calculate_skill_development_score(skill_mapping)
    
    return {
        "skill_mapping": skill_mapping,
        "skill_score": skill_score,
        "career_applicability": assess_career_applicability(skill_mapping)
    }
```

### Career Development Intelligence
- **Role Preparation**: Preparation para specific job roles
- **Salary Impact**: Impact en salary potential
- **Promotion Readiness**: Readiness para career advancement
- **Industry Transition**: Support para industry transitions

## Outputs Generados

1. **Course Intelligence**:
   - `coursera_courses.json`: Courses completos con educational analysis
   - `coursera_courses.csv`: Formato tabular para analysis
   - `course_quality_report.json`: Course quality assessment

2. **Educational Analytics**:
   - `learning_path_analysis.json`: Learning path optimization
   - `skill_demand_trends.json`: Skill demand y market trends
   - `institution_analysis.json`: Institution reputation y performance

3. **Market Intelligence**:
   - `educational_market_report.json`: Educational market analysis
   - `career_development_paths.json`: Career development recommendations
   - `pricing_intelligence.json`: Pricing strategy intelligence

## Configuration y Personalización

### Coursera Scraping Configuration
```python
COURSERA_CONFIG = {
    "base_url": "https://www.classcentral.com/provider/coursera",
    "first_run_pages": 150,
    "subsequent_pages": 10,
    "quality_thresholds": {
        "excellent": 8.5,
        "good": 7.0,
        "acceptable": 5.5
    },
    "scraping_mode": "adaptive",
    "anti_detection": True
}
```

### Quality Assessment Weights
```python
QUALITY_WEIGHTS = {
    "institution_reputation": 0.25,
    "content_depth": 0.25,
    "practical_application": 0.20,
    "industry_relevance": 0.20,
    "student_outcomes": 0.10
}
```

## Data Quality Assurance

### Educational Data Validation
- **Course Information Accuracy**: Accuracy de course information
- **Institution Verification**: Verification de institution data
- **Pricing Validation**: Validation de pricing information
- **Certificate Authenticity**: Authenticity de certificate offerings

### Learning Standards
- **Educational Quality**: Standards de educational quality
- **Content Relevance**: Relevance de course content
- **Skill Mapping Accuracy**: Accuracy de skill mappings
- **Career Path Validity**: Validity de career path recommendations

## Competitive Intelligence Features

### EdTech Market Analysis
- **Platform Comparison**: Comparison entre different educational platforms
- **Course Portfolio Analysis**: Analysis de course portfolios
- **Pricing Strategy Intelligence**: Intelligence sobre pricing strategies
- **Market Share Estimation**: Estimation de market share

### Educational Innovation Intelligence
- **Learning Technology Trends**: Trends en learning technologies
- **Course Delivery Innovation**: Innovation en course delivery methods
- **Assessment Method Evolution**: Evolution de assessment methods
- **Personalization Technologies**: Technologies para personalized learning 