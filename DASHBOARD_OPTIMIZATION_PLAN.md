# Watchtower Dashboard Optimization Plan

## Overview
Transform the POC dashboard into the main Watchtower application with full cleanup and optimization.

## Progress Tracking
- [ ] **Phase 1**: Remove unwanted tabs and cleanup (Steps 1-3)
- [ ] **Phase 2**: Add new tabs based on streamlit (Steps 4-6) 
- [ ] **Phase 3**: Environment cleanup and enhancement (Steps 7-9)
- [ ] **Phase 4**: Deployment and final integration (Steps 10-12)

## Detailed Steps

### Phase 1: Cleanup and Basic Integration (Steps 1-3)

#### Step 1: Remove Unwanted Tabs ✅
**Tabs to Remove:**
- Google Cloud Blog (`google_cloud_blog_tab.py`)
- AWS Training (`aws_training_tab.py`) 
- Azure Training (`azure_training_tab.py`)
- Allkeyshop Deals (`allkeyshop_tab.py`)
- Eventos Tech (`tech_events_tab.py`)
- Comunidades Dev (`dev_communities_tab.py`)
- Seguridad (`security_tab.py`)
- Innovación (`innovation_tab.py`)
- Plataformas IA (`ai_platforms_tab.py`)
- Home Server (`home_server_tab.py`)
- Other Tab (Placeholder)

**Files to Remove:**
- [ ] `src/web/new_dashboard_poc/components/google_cloud_blog_tab.py`
- [ ] `src/web/new_dashboard_poc/components/aws_training_tab.py`
- [ ] `src/web/new_dashboard_poc/components/azure_training_tab.py`
- [ ] `src/web/new_dashboard_poc/components/allkeyshop_tab.py`
- [ ] `src/web/new_dashboard_poc/components/tech_events_tab.py`
- [ ] `src/web/new_dashboard_poc/components/dev_communities_tab.py`
- [ ] `src/web/new_dashboard_poc/components/security_tab.py`
- [ ] `src/web/new_dashboard_poc/components/innovation_tab.py`
- [ ] `src/web/new_dashboard_poc/components/ai_platforms_tab.py`
- [ ] `src/web/new_dashboard_poc/components/home_server_tab.py`

**App.py Changes:**
- [ ] Remove imports for deleted tabs
- [ ] Remove tab definitions from layout
- [ ] Remove callback registrations
- [ ] Clean up unused imports

#### Step 2: Watchtower Integration ✅
- [ ] Update app title to "Watchtower Dashboard"
- [ ] Add Watchtower favicon/icon
- [ ] Update all text references
- [ ] Clean up code structure
- [ ] Update import paths if needed

#### Step 3: First Commit and Merge ❌
- [ ] Commit changes with message: "feat: Transform POC to main Watchtower dashboard - remove unwanted tabs"
- [ ] Push to current branch
- [ ] Merge with main

### Phase 2: New Tabs Implementation (Steps 4-6)

#### Step 4: Add New Tabs Based on Streamlit ❌
**New Tabs to Create:**
- [ ] **Anime Tab** (`anime_tab.py`) - Based on `src/web/fullstreamlit/components/anime_tab.py`
- [ ] **Eventos Valencia Tab** (`eventos_valencia_tab.py`) - Check if exists in streamlit
- [ ] **4chan Generals Tab** (`fourchan_tab.py`) - Based on `src/web/fullstreamlit/components/fourchan_tab.py`
- [ ] **Scavenging Tab** (`scavenging_tab.py`) - Check if exists in streamlit

**Implementation Steps:**
- [ ] Analyze streamlit components for data structure
- [ ] Convert streamlit components to Dash components
- [ ] Implement data loading functions
- [ ] Add tabs to main app layout
- [ ] Register callbacks

#### Step 5: Remove Related ETL Processes ❌
**ETL Files to Remove/Review:**
- [ ] Review and remove ETL processes for deleted tabs
- [ ] Keep ETL processes for new tabs (anime, 4chan, etc.)
- [ ] Update ETL orchestration scripts

#### Step 6: Second Commit and Merge ❌
- [ ] Commit changes with message: "feat: Add new tabs based on streamlit implementation"
- [ ] Push to current branch  
- [ ] Merge with main

### Phase 3: Environment and Enhancement (Steps 7-9)

#### Step 7: Cleanup Environment and Orchestrators ❌
- [ ] Review `run_all_etl.bat` and `run_streamlit_beta.bat`
- [ ] Create new orchestration scripts for dashboard
- [ ] Update dependency management
- [ ] Clean up unused dependencies

#### Step 8: Enhance CSS and Visualization ❌
- [ ] Improve `src/web/new_dashboard_poc/assets/style.css`
- [ ] Enhance table visualization in Dash
- [ ] Implement better responsive design
- [ ] Add consistent styling across tabs

#### Step 9: Documentation Cleanup ❌
- [ ] Clean up obsolete documentation
- [ ] Update README files
- [ ] Document new dashboard structure
- [ ] Create user guide for new dashboard

### Phase 4: Deployment and Integration (Steps 10-12)

#### Step 10: Create Deployment Scripts ❌
- [ ] **Windows deployment** (`deploy_windows.bat`)
- [ ] **Linux deployment** (`deploy_linux.sh`)
- [ ] **Mac deployment** (`deploy_mac.sh`)
- [ ] Test deployment scripts
- [ ] Create unified installer

#### Step 11: Final Commit and Merge ❌
- [ ] Commit all remaining changes
- [ ] Push to current branch
- [ ] Merge with main

#### Step 12: Repository Integration ❌
- [ ] Switch to main branch
- [ ] Merge with other repositories
- [ ] Resolve conflicts (keep our changes)
- [ ] Verify everything works
- [ ] Final commit after merges

## Notes
- Current branch: `feat/poc-new-dashboard`
- Target: Make this the main dashboard
- Priority: Keep existing functionality while improving UX
- Dependencies: UV package manager (already migrated)

## Risk Mitigation
- Create backup before major changes
- Test at each phase
- Commit frequently for rollback capability
- Validate data loading for each new tab

## Success Criteria
- ✅ POC dashboard becomes main dashboard
- ✅ All unwanted tabs removed
- ✅ New relevant tabs implemented
- ✅ Clean codebase with good documentation
- ✅ Cross-platform deployment capability
- ✅ Successful repository integration 