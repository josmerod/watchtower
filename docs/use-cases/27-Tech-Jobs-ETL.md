# Metadata

- Caso de uso: Tech Jobs Intelligence and Salary Analytics System
- Plataformas involucradas: Job Market APIs + Recruitment Intelligence
- Descripción corta: Sistema de inteligencia para analizar job market trends, salary analytics y tech recruiting patterns con focus en career intelligence
- Patrón de ejecución: Periódico (cada 12-24 horas) con analysis de job postings, salary trends y skill demand

## Dependencias

- APIs y fuentes externas:
  - Job market APIs (LinkedIn, Indeed, AngelList, Stack Overflow Jobs)
  - Salary data aggregation sources
  - Company data y tech stack information
  - Geographic job market data
- Bibliotecas de Python principales:
  - `requests`: HTTP requests para job APIs
  - `json`: Structured data processing
  - `datetime`: Job posting dating y market analysis
  - `csv`: CSV export functionality
  - `collections`: Salary statistics y skill aggregation
  - `random`: Mock data generation para development

## Stack Tecnológico

- Lenguaje de programación: Python 3.10+
- Framework: ETL con API-based data extraction
- Data Extraction: Multiple job site integration con retry strategies
- Career Intelligence: Job categorization y salary analysis
- Market Analytics: Skill demand tracking y location analysis
- Export: JSON y CSV con career analytics metadata

## Implementación

La implementación consta de los siguientes componentes:

1. **Tech Jobs ETL** (`src/etl/news/news_get_techjobs.py`):
   - Motor principal de extracción de tech job postings
   - Multi-platform job aggregation con standardized processing
   - Mock data generation system para demonstration
   - Salary analysis y market trend detection

2. **Career Intelligence Engine**:
   - **Job Categorization**: Categorization de jobs por technology y experience level
   - **Salary Analytics**: Analysis de salary trends y compensation patterns
   - **Skill Demand Assessment**: Assessment de skill demand y market requirements
   - **Location Intelligence**: Intelligence sobre job markets por geographic areas

3. **Recruitment Analytics Features**:
   - **Attractiveness Scoring**: Scoring de job attractiveness basado en multiple factors
   - **Market Demand Analysis**: Analysis de market demand por skills y roles
   - **Company Tier Assessment**: Assessment de company tiers y reputation
   - **Remote Work Intelligence**: Intelligence sobre remote work trends

4. **Career Development Processing**:
   - **Experience Level Analysis**: Analysis de experience requirements y career paths
   - **Skill Gap Identification**: Identification de skill gaps en market
   - **Salary Benchmarking**: Benchmarking de salaries por roles y locations
   - **Career Progression Insights**: Insights sobre career progression patterns

## Características Avanzadas

### 1. **Comprehensive Mock Job Generation**
```python
def generate_mock_tech_jobs() -> List[Dict[str, Any]]:
    """
    Generate mock tech job data for demonstration.
    In production, replace with actual job site APIs or scraping.
    """
    jobs = []
    
    # Job titles and their typical salary ranges
    job_data = {
        "Software Engineer": {"min_salary": 80000, "max_salary": 180000, "level": "mid"},
        "Senior Software Engineer": {"min_salary": 120000, "max_salary": 250000, "level": "senior"},
        "Data Scientist": {"min_salary": 90000, "max_salary": 200000, "level": "mid"},
        "Machine Learning Engineer": {"min_salary": 110000, "max_salary": 220000, "level": "senior"},
        "DevOps Engineer": {"min_salary": 95000, "max_salary": 200000, "level": "senior"},
        "Product Manager": {"min_salary": 100000, "max_salary": 210000, "level": "senior"},
        "AI Engineer": {"min_salary": 120000, "max_salary": 240000, "level": "senior"}
    }
    
    for i in range(100):
        job_title = random.choice(list(job_data.keys()))
        job_info = job_data[job_title]
        
        # Generate realistic job posting
        job = create_realistic_job_posting(job_title, job_info, i)
        jobs.append(job)
    
    return jobs
```

### 2. **Advanced Job Processing Algorithm**
```python
def process_tech_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process and enrich tech job data with additional metrics and categorization.
    """
    processed_jobs = []
    current_time = datetime.now()
    
    for job in jobs:
        # Salary analysis
        salary_info = job.get('salary', {})
        salary_amount = salary_info.get('amount', 0)
        
        # Categorize salary level
        salary_level = categorize_salary(salary_amount)
        
        # Location analysis
        location = job.get('location', {})
        location_tier = classify_tech_hub(location.get('city', ''))
        
        # Skills analysis
        required_skills = job.get('required_skills', [])
        hot_skills_count = count_hot_skills(required_skills)
        
        # Calculate attractiveness score
        attractiveness_score = calculate_job_attractiveness(job, salary_amount, location_tier, hot_skills_count)
        
        # Job category classification
        job_category = classify_job_category(job.get('title', ''))
        
        processed_job = {
            **job,
            "salary_level": salary_level,
            "location_tier": location_tier,
            "hot_skills_count": hot_skills_count,
            "attractiveness_score": attractiveness_score,
            "job_category": job_category,
            "platform": "tech_jobs"
        }
        
        processed_jobs.append(processed_job)
    
    return sorted(processed_jobs, key=lambda x: x.get('attractiveness_score', 0), reverse=True)
```

### 3. **Job Market Analysis Engine**
```python
def analyze_job_market(jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze job market trends and statistics.
    """
    if not jobs:
        return {}
    
    from collections import Counter
    
    # Salary analysis
    salaries = [job.get('salary', {}).get('amount', 0) for job in jobs if job.get('salary', {}).get('amount', 0) > 0]
    avg_salary = sum(salaries) / len(salaries) if salaries else 0
    
    # Skills demand
    all_skills = []
    for job in jobs:
        all_skills.extend(job.get('required_skills', []))
    
    top_skills = Counter(all_skills).most_common(15)
    
    # Location trends
    locations = [job.get('location_string', 'Unknown') for job in jobs]
    top_locations = Counter(locations).most_common(10)
    
    # Remote work trends
    remote_jobs = len([job for job in jobs if job.get('remote_option', False)])
    remote_percentage = (remote_jobs / len(jobs)) * 100 if jobs else 0
    
    return {
        "total_jobs": len(jobs),
        "average_salary": round(avg_salary, 2),
        "salary_range": {
            "min": min(salaries) if salaries else 0,
            "max": max(salaries) if salaries else 0,
            "median": sorted(salaries)[len(salaries)//2] if salaries else 0
        },
        "top_skills": top_skills,
        "top_locations": top_locations,
        "remote_work": {
            "total_remote_jobs": remote_jobs,
            "percentage": round(remote_percentage, 1)
        },
        "analysis_date": datetime.now().isoformat()
    }
```

### 4. **Advanced Career Intelligence Features**
- **Salary Benchmarking**: Benchmarking de salaries por roles, experience levels y locations
- **Skill Demand Forecasting**: Forecasting de skill demand trends
- **Career Path Analysis**: Analysis de career progression paths
- **Market Opportunity Assessment**: Assessment de job market opportunities

### 5. **Recruitment Market Intelligence**
- **Hiring Trend Analysis**: Analysis de hiring trends por companies y industries
- **Remote Work Evolution**: Evolution de remote work opportunities
- **Tech Stack Popularity**: Popularity de technology stacks en job market
- **Geographic Market Analysis**: Analysis de job markets por geographic regions

## Job Data Structure

### Enhanced Job Data
```python
{
    "id": "job_66_1748282691",
    "title": "DevOps Engineer",
    "company": "Anthropic",
    "location": {
        "city": "Seattle",
        "state": "WA",
        "country": "USA",
        "remote": false
    },
    "location_string": "Seattle, WA",
    
    # Compensation Details
    "salary": {
        "amount": 188235,
        "currency": "USD",
        "period": "yearly",
        "min_range": 95000,
        "max_range": 200000
    },
    
    # Job Requirements
    "experience_level": "senior",
    "employment_type": "contract",
    "remote_option": true,
    "required_skills": [
        "Jenkins", "Python", "AWS", "Kubernetes", "Terraform", "Docker"
    ],
    
    # Job Details
    "description": "We are looking for a talented DevOps Engineer to join our Anthropic team. You will be working on exciting projects involving Jenkins, Python, AWS. This role offers competitive compensation and great benefits.",
    "benefits": [
        "Remote Work", "Stock Options", "Paid Time Off"
    ],
    "job_source": "Indeed",
    
    # Temporal Data
    "posted_date": "2025-05-16T20:04:51.586379",
    "application_deadline": "2025-06-15T20:04:51.586379",
    "fetched_at": "2025-05-26T20:04:51.586379",
    "days_since_posted": 10,
    
    # Analytics Enrichment
    "salary_level": "high",  # very_high, high, medium_high, medium, low_medium, low
    "location_tier": "tier_1",  # tier_1, tier_2, tier_3, remote, other
    "hot_skills_count": 3,
    "experience_score": 3,  # 1-5 scale
    "attractiveness_score": 16.91,
    
    # Classification
    "job_category": "devops",  # ai_ml, frontend, backend, fullstack, devops, mobile, management, security, general
    "has_urgency_indicators": false,
    "is_fresh": false,
    
    # Market Intelligence
    "platform": "tech_jobs",
    "skills_count": 6,
    "benefits_count": 3,
    
    # Career Intelligence
    "career_level": "senior",
    "growth_potential": "high",
    "market_demand": "very_high",
    "skill_rarity": "moderate"
}
```

## Métricas y KPIs

### Métricas de Job Market Intelligence
- **Average Salary by Role**: Salary promedio por job categories
- **Salary Growth Trends**: Trends de salary growth over time
- **Skills Demand Index**: Index de demand para different skills
- **Remote Work Percentage**: Percentage de remote work opportunities

### Métricas de Career Intelligence
- **Experience Level Distribution**: Distribution de experience levels
- **Job Category Popularity**: Popularity de different job categories
- **Company Tier Distribution**: Distribution de company tiers
- **Location Attractiveness Score**: Score de attractiveness por locations

### Métricas de Recruitment Intelligence
- **Job Posting Volume**: Volume de job postings over time
- **Time to Fill Estimates**: Estimates de time to fill positions
- **Competition Level**: Level de competition para different roles
- **Hiring Velocity**: Velocity de hiring por companies

### Métricas de Market Dynamics
- **Skill Shortage Analysis**: Analysis de skill shortages
- **Market Saturation Levels**: Levels de market saturation
- **Emerging Role Identification**: Identification de emerging roles
- **Technology Adoption in Jobs**: Adoption de new technologies en job requirements

## Casos de Uso Específicos

1. **Job Seekers**: Salary benchmarking y job opportunity discovery
2. **Recruiters**: Market intelligence y candidate pool analysis
3. **HR Professionals**: Compensation planning y role definition
4. **Career Counselors**: Career path guidance y skill development advice
5. **Business Analysts**: Labor market analysis y workforce planning
6. **Technology Leaders**: Talent acquisition strategy y team building

## Career Intelligence System

### Salary Benchmarking Algorithm
```python
def benchmark_salary(role, experience_level, location, skills):
    """
    Benchmark salary based on role, experience, location, and skills.
    """
    base_salary = get_base_salary_for_role(role)
    
    # Experience multiplier
    exp_multiplier = {
        'junior': 0.8,
        'mid': 1.0,
        'senior': 1.4,
        'staff': 1.8,
        'principal': 2.2
    }.get(experience_level, 1.0)
    
    # Location adjustment
    location_multiplier = get_location_cost_multiplier(location)
    
    # Skills premium
    skills_premium = calculate_skills_premium(skills)
    
    benchmarked_salary = base_salary * exp_multiplier * location_multiplier * (1 + skills_premium)
    
    return {
        "base_salary": base_salary,
        "adjusted_salary": benchmarked_salary,
        "location_multiplier": location_multiplier,
        "experience_multiplier": exp_multiplier,
        "skills_premium": skills_premium
    }
```

### Market Demand Analysis
```python
def analyze_market_demand(jobs_data, time_period_days=30):
    """
    Analyze market demand for skills and roles.
    """
    demand_analysis = {
        "skill_demand": calculate_skill_demand_scores(jobs_data),
        "role_demand": calculate_role_demand_scores(jobs_data),
        "location_demand": calculate_location_demand_scores(jobs_data),
        "company_hiring_velocity": calculate_hiring_velocity(jobs_data)
    }
    
    # Calculate market competitiveness
    competitiveness = calculate_market_competitiveness(demand_analysis)
    
    return {
        "demand_analysis": demand_analysis,
        "market_competitiveness": competitiveness,
        "demand_forecast": generate_demand_forecast(demand_analysis)
    }
```

## Job Market Intelligence

### Skills Demand Tracking
- **Hot Skills Identification**: Identification de skills en high demand
- **Emerging Skills Detection**: Detection de emerging skills
- **Skill Combination Analysis**: Analysis de valuable skill combinations
- **Skills Gap Assessment**: Assessment de skills gaps en market

### Geographic Market Analysis
- **Tech Hub Classification**: Classification de cities por tech hub tier
- **Cost of Living Adjustment**: Adjustment de salaries por cost of living
- **Remote vs On-site Trends**: Trends de remote vs on-site opportunities
- **Regional Specializations**: Specializations de technology stacks por regions

## Recruitment Intelligence

### Company Analysis
```python
def analyze_company_hiring_patterns(company_jobs):
    """
    Analyze hiring patterns for specific companies.
    """
    hiring_metrics = {
        "hiring_volume": len(company_jobs),
        "average_salary": calculate_average_salary(company_jobs),
        "preferred_skills": identify_preferred_skills(company_jobs),
        "experience_distribution": calculate_experience_distribution(company_jobs),
        "remote_policy": assess_remote_work_policy(company_jobs)
    }
    
    return hiring_metrics
```

### Market Opportunity Assessment
- **Job Market Saturation**: Assessment de market saturation por roles
- **Career Growth Opportunities**: Opportunities para career advancement
- **Industry Hiring Trends**: Trends de hiring por industries
- **Compensation Competitiveness**: Competitiveness de compensation packages

## Outputs Generados

1. **Job Market Intelligence**:
   - `tech_jobs_latest.json`: Jobs completos con analytics
   - `tech_jobs_latest.csv`: Formato tabular para analysis
   - `tech_jobs_analysis.json`: Market analysis y trends

2. **Career Intelligence**:
   - `salary_benchmarks.json`: Salary benchmarking data
   - `skills_demand_report.json`: Skills demand analysis
   - `career_opportunities.json`: Career opportunity assessment

3. **Recruitment Intelligence**:
   - `hiring_trends.json`: Hiring trend analysis
   - `company_analysis.json`: Company hiring pattern analysis
   - `market_competitiveness.json`: Market competitiveness assessment

## Configuration y Personalización

### Tech Jobs Configuration
```python
TECH_JOBS_CONFIG = {
    "job_sources": ["LinkedIn", "Indeed", "AngelList", "Stack Overflow", "Company Website"],
    "tracked_roles": ["Software Engineer", "Data Scientist", "DevOps Engineer", "AI Engineer"],
    "geographic_focus": ["US", "Europe", "Remote"],
    "salary_currency": "USD",
    "experience_levels": ["junior", "mid", "senior", "staff", "principal"]
}
```

### Salary Analysis Weights
```python
SALARY_WEIGHTS = {
    "base_salary_weight": 1.0,
    "location_adjustment": 0.3,
    "experience_multiplier": 0.4,
    "skills_premium": 0.2,
    "company_tier_bonus": 0.1
}
```

## Data Quality Assurance

### Job Data Validation
- **Salary Range Validation**: Validation de realistic salary ranges
- **Skills Consistency**: Consistency de skill requirements
- **Location Verification**: Verification de location data
- **Company Data Accuracy**: Accuracy de company information

### Career Intelligence Quality Standards
- **Benchmarking Accuracy**: Accuracy de salary benchmarking
- **Market Trend Reliability**: Reliability de market trend detection
- **Skill Demand Validation**: Validation de skill demand assessment
- **Career Path Accuracy**: Accuracy de career progression insights

## Competitive Intelligence Features

### Job Market Competitive Analysis
- **Salary Competitiveness**: Competitiveness de salary offerings
- **Benefits Comparison**: Comparison de benefits packages
- **Hiring Speed Analysis**: Analysis de hiring process speed
- **Talent Acquisition Strategies**: Strategies para talent acquisition

### Career Development Intelligence
- **Skills Investment ROI**: ROI de skills development investments
- **Career Path Optimization**: Optimization de career development paths
- **Market Positioning**: Positioning en job market
- **Professional Growth Planning**: Planning para professional growth 