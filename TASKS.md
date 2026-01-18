# TASKS.md - Bitcoin SOPR Analytics Dashboard

## Phase 0: Prerequisites (Manual - Outside Claude Code)
- [ ] 0.1 Create GCP project (or use existing)
- [ ] 0.2 Enable BigQuery API in GCP Console
- [ ] 0.3 Create service account with BigQuery Admin role
- [ ] 0.4 Download JSON key → save to `~/.gcp/` (not in repo!)
- [ ] 0.5 Set env var: `export GOOGLE_APPLICATION_CREDENTIALS=~/.gcp/your-key.json`
- [ ] 0.6 Create dataset: `bq mk --location=US bitcoin_analytics`

## Phase 1: Project Scaffolding
- [ ] 1.1 Create folder structure per CLAUDE.md
- [ ] 1.2 Create `requirements.txt`
- [ ] 1.3 Create `.env.example`
- [ ] 1.4 Create `.gitignore`
- [ ] 1.5 `pip install -r requirements.txt`
- [ ] 1.6 Verify BigQuery connection: `bq ls`

## Phase 2: Price Data ETL
- [ ] 2.1 Create `etl/load_prices.py`
- [ ] 2.2 Run script: `python etl/load_prices.py`
- [ ] 2.3 Verify: `bq head -n 5 bitcoin_analytics.daily_prices`

## Phase 3: UTXO Index (⚠️ COST WARNING - ~$25-50)
- [ ] 3.1 Create `etl/create_index.py`
- [ ] 3.2 Dry run to estimate cost: `bq query --dry_run --use_legacy_sql=false < sql/utxo_index.sql`
- [ ] 3.3 Review cost estimate, confirm budget
- [ ] 3.4 Execute: `python etl/create_index.py`
- [ ] 3.5 Verify: `bq show bitcoin_analytics.utxo_index`

## Phase 4: Query Layer
- [ ] 4.1 Create `src/queries.py`
- [ ] 4.2 Create `src/__init__.py`
- [ ] 4.3 Test with 7-day range in Python REPL
- [ ] 4.4 Verify SOPR values are reasonable (typically 0.9 - 1.1)

## Phase 5: Visualization
- [ ] 5.1 Create `src/charts.py`
- [ ] 5.2 Test chart rendering with mock data
- [ ] 5.3 Verify threshold line and conditional coloring

## Phase 6: Streamlit App
- [ ] 6.1 Create `main.py` with basic layout
- [ ] 6.2 Add sidebar controls (date picker, refresh)
- [ ] 6.3 Add BigQuery fetch with `st.cache_data`
- [ ] 6.4 Add metrics row (Current SOPR, Greed/Fear)
- [ ] 6.5 Integrate Plotly chart
- [ ] 6.6 Add error handling (credentials, quota)
- [ ] 6.7 Test full flow: `streamlit run main.py`

## Phase 7: Polish & Portfolio
- [ ] 7.1 Create `README.md` with setup instructions
- [ ] 7.2 Add architecture diagram
- [ ] 7.3 Add sample screenshot
- [ ] 7.4 Deploy to Streamlit Cloud (optional)
- [ ] 7.5 Record demo video (optional)

---

## Notes & Decisions
<!-- Use this section to log decisions, blockers, or learnings -->

| Date | Note |
|------|------|
| | |

## Cost Tracking
| Query/Action | Estimated Cost | Actual Cost |
|--------------|----------------|-------------|
| utxo_index creation | ~$25-50 | |
| SOPR query (30 days) | ~$0.10 | |
