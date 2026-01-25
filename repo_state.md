# Repo State Snapshot

Generated: 2026-01-25 15:59:10

Repo: /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step


## Git status

```text
(rc=0)
## feat/T-000-scan-reconcile
 M .claude/ralph-loop.local.md
 M .gitignore
 M AGENTS.md
 M agent-work.md
 M changemap.md
 D scripts/smoke_test.py
?? AGENT.md
?? backend/.claude/
?? backend/=0.5.0
?? backend/backups/
?? backend/scripts/backfill_brightermonday_metadata.py
?? backend/scripts/smoke_test.py
?? backend/venv3.11/bin/ruff
?? claude.md
?? handoff.jsonl
?? handoff.md
?? repo_state.md
?? scripts/repo_smoke_test.py
?? scripts/scan_repo.py
```


## Git last 20 commits

```text
(rc=0)
e20bb81 feat: add education mappings UI and improve extraction filters
0eed686 feat: add normalized education mapping and dual summary columns
1bca420 feat: add admin summary drilldowns
8a7d605 fix: load scraper config with absolute path
1321783 fix: handle hybrid db in processing log async
37f1fa4 feat: add admin automation status tracking
7d1bee5 fix: make frontend api base runtime-aware
27c5fb2 docs: Update agent-work.md with Loop 12 progress
1d5cebd feat: Add seniority backfill script with intelligent title filtering
9cf2916 docs: Update agent-work.md with Loop 11 progress
e0905a8 fix: Add salary validation thresholds to data_cleaner.py
57a1c1e docs: Update agent-work.md with Loop 10 progress
fce026f feat: Enhance salary extraction with validation thresholds
855c519 feat: Add job alert processing, rate limiting on auth, SQLite compatibility
49df1f8 feat: Achieve source diversity target - 1863 jobs from 4 sources
7e5662d feat: P1.2 Data quality + P1.1 documentation and scripts
18b1c73 feat: P1 production hardening - rate limiting, API auth, logging, BrighterMonday
22e5bd4 feat: Enhance embedding generation with transformer model support and fallback mechanism
3a8e4a9 feat: Enhance job extraction and search functionality with structured data updates
9d3f342 Refactor scrapers and improve data extraction
```


## Git branches

```text
(rc=0)
* feat/T-000-scan-reconcile
  feature/async-db-embeddings-fallback
  main
  remotes/origin/HEAD -> origin/main
  remotes/origin/feature/async-db-embeddings-fallback
  remotes/origin/main
```


## Python

```text
(rc=0)
Python 3.14.2
```


## Project tree

```text
(rc=0)
.
AGENT.md
AGENTS.md
CHANGES.md
IMPLEMENTATION_SUMMARY.md
PR_DESCRIPTION.md
README.md
agent-work.md
backend
backend/=0.5.0
backend/DEPLOYMENT.md
backend/Dockerfile
backend/__pycache__
backend/__pycache__/celery.cpython-311.pyc
backend/__pycache__/celery.cpython-313.pyc
backend/__pycache__/ratelimit.cpython-311.pyc
backend/__pycache__/ratelimit.cpython-313.pyc
backend/__pycache__/sentence_transformers.cpython-311.pyc
backend/__pycache__/sentence_transformers.cpython-313.pyc
backend/__pycache__/test_automated_workflow.cpython-311-pytest-8.2.2.pyc
backend/__pycache__/test_automated_workflow.cpython-313-pytest-8.3.4.pyc
backend/__pycache__/test_integration.cpython-311-pytest-8.2.2.pyc
backend/__pycache__/test_integration.cpython-313-pytest-8.3.4.pyc
backend/__pycache__/test_jobwebkenya_pipeline.cpython-311-pytest-8.2.2.pyc
backend/__pycache__/test_pipeline_bridge.cpython-311-pytest-8.2.2.pyc
backend/__pycache__/test_processors.cpython-311-pytest-8.2.2.pyc
backend/__pycache__/test_processors.cpython-313-pytest-8.3.4.pyc
backend/__pycache__/test_structured_extraction.cpython-311-pytest-8.2.2.pyc
backend/__pycache__/test_unified_ingestion.cpython-311-pytest-8.2.2.pyc
backend/alembic
backend/alembic/versions
backend/alembic/versions/001_add_deduplication_fields.py
backend/alembic/versions/001_add_user_authentication.py
backend/alembic/versions/002_add_advanced_features.py
backend/alembic/versions/003_add_integrations.py
backend/app
backend/app/__pycache__
backend/app/__pycache__/main.cpython-311.pyc
backend/app/__pycache__/main.cpython-313.pyc
backend/app/api
backend/app/api/__init__.py
backend/app/api/__pycache__
backend/app/api/admin_routes.py
backend/app/api/auth_routes.py
backend/app/api/integration_routes.py
backend/app/api/routes.py
backend/app/api/user_routes.py
backend/app/api/workflow_routes.py
backend/app/core
backend/app/core/__pycache__
backend/app/core/celery_app.py
backend/app/core/config.py
backend/app/core/logging_config.py
backend/app/core/rate_limiter.py
backend/app/db
backend/app/db/__init__.py
backend/app/db/__pycache__
backend/app/db/database.py
backend/app/db/integration_models.py
backend/app/db/models.py
backend/app/ingestion
backend/app/ingestion/__init__.py
backend/app/ingestion/__pycache__
backend/app/ingestion/connectors
backend/app/ingestion/government_sources.yaml
backend/app/ingestion/runner.py
backend/app/ingestion/sources.yaml
backend/app/main.py
backend/app/ml
backend/app/ml/__init__.py
backend/app/ml/__pycache__
backend/app/ml/embeddings.py
backend/app/normalization
backend/app/normalization/__init__.py
backend/app/normalization/__pycache__
backend/app/normalization/skills.py
backend/app/normalization/titles.py
backend/app/processors
backend/app/processors/__init__.py
backend/app/processors/__pycache__
backend/app/processors/data_cleaner.py
backend/app/processors/database_saver.py
backend/app/processors/job_extractor.py
backend/app/processors/job_processor.py
backend/app/schemas
backend/app/schemas/__init__.py
backend/app/schemas/__pycache__
backend/app/schemas/base.py
backend/app/scrapers
backend/app/scrapers/__init__.py
backend/app/scrapers/__pycache__
backend/app/scrapers/base_scraper.py
backend/app/scrapers/brighter_monday_scraper.py
backend/app/scrapers/config.py
backend/app/scrapers/config.yaml
backend/app/scrapers/db.py
backend/app/scrapers/indeed_scraper.py
backend/app/scrapers/jobs.sqlite3
backend/app/scrapers/linkedin_scraper.py
backend/app/scrapers/main.py
backend/app/scrapers/migrate_to_postgres.py
backend/app/scrapers/postgres_db.py
backend/app/scrapers/scraper.log
backend/app/scrapers/scraper.py
backend/app/scrapers/spiders
backend/app/scrapers/utils.py
backend/app/services
backend/app/services/__init__.py
backend/app/services/__pycache__
backend/app/services/ai_service.py
backend/app/services/ats_service.py
backend/app/services/auth_service.py
backend/app/services/automated_workflow_service.py
backend/app/services/calendar_service.py
backend/app/services/career_tools_service.py
backend/app/services/data_processing_service.py
backend/app/services/deduplication_service.py
backend/app/services/email_service.py
backend/app/services/linkedin_service.py
backend/app/services/lmi.py
backend/app/services/notification_service.py
backend/app/services/payment_service.py
backend/app/services/personalized_recommendations.py
backend/app/services/processing_log_service.py
backend/app/services/recommend.py
backend/app/services/scraper_service.py
backend/app/services/search.py
backend/app/tasks
backend/app/tasks/__init__.py
backend/app/tasks/__pycache__
backend/app/tasks/gov_monitor_tasks.py
backend/app/tasks/processing_tasks.py
backend/app/tasks/scraper_tasks.py
backend/app/tasks/workflow_tasks.py
backend/app/webhooks
backend/app/webhooks/__init__.py
backend/app/webhooks/__pycache__
backend/app/webhooks/whatsapp.py
backend/backups
backend/backups/nextstep_backup_20260122_183852.sqlite.gz
backend/celery.py
backend/jobs.sqlite3
backend/migrations
backend/migrations/add_deduplication_fields.sql
backend/ratelimit.py
backend/requirements.txt
backend/scraper.log
backend/scripts
backend/scripts/__pycache__
backend/scripts/__pycache__/smoke_test.cpython-311-pytest-8.2.2.pyc
backend/scripts/backfill_brightermonday_metadata.py
backend/scripts/backfill_salary_data.py
backend/scripts/backfill_seniority.py
backend/scripts/backup_database.py
backend/scripts/run_brightermonday_ingestion.py
backend/scripts/run_jobwebkenya_ingestion.py
backend/scripts/run_myjobmag_ingestion.py
backend/scripts/smoke_test.py
backend/sentence_transformers.py
backend/test_automated_workflow.py
backend/test_db.sqlite
backend/test_db.sqlite-journal
backend/test_integration.py
backend/test_jobwebkenya_pipeline.py
backend/test_pipeline_bridge.py
backend/test_processors.py
backend/test_structured_extraction.py
backend/test_unified_ingestion.py
backend/var
backend/var/nextstep.sqlite
backend/venv3.11
changemap.md
claude.md
dbt
dbt/dbt_project.yml
dbt/models
dbt/models/postings_daily.sql
dbt/models/weekly_metrics.sql
dbt/profiles.example.yml
deploy-to-cyberpanel.sh
deploy_upgrades.sh
docker-compose.prod.yml
docker-compose.yml
docs
docs/ingestion-workflows.md
docs/integrations.md
docs/operations.md
docs/product.md
features.md
frontend
frontend/admin.html
frontend/auth-callback.html
frontend/dashboard.html
frontend/index.html
frontend/js
frontend/js/admin.js
frontend/js/api.js
frontend/js/auth.js
frontend/js/config.js
frontend/js/dashboard-ui.js
frontend/js/dashboard.js
frontend/js/main.js
frontend/js/search.js
frontend/reset.html
frontend/styles
frontend/styles/main.css
handoff.jsonl
handoff.md
jobs.sqlite3
repo_state.md
scan_output.log
scripts
scripts/__pycache__
scripts/__pycache__/repo_smoke_test.cpython-311-pytest-8.2.2.pyc
scripts/bootstrap_prod.sh
scripts/clean_government_sources.py
scripts/dev-start.sh
scripts/generate_government_sources.py
scripts/repo_smoke_test.py
scripts/scan_repo.py
scripts/setup_prod_environment.sh
scripts/smoke_test.sh
test_db.sqlite
userjourney.md
websites
```


## Ruff

```text
(rc=1)
ruff 0.14.14
F401 [*] `sqlalchemy.dialects.postgresql` imported but unused
  --> backend/alembic/versions/001_add_deduplication_fields.py:10:33
   |
 8 | from alembic import op
 9 | import sqlalchemy as sa
10 | from sqlalchemy.dialects import postgresql
   |                                 ^^^^^^^^^^
11 |
12 | # revision identifiers, used by Alembic.
   |
help: Remove unused import: `sqlalchemy.dialects.postgresql`

F401 [*] `datetime.timedelta` imported but unused
 --> backend/app/api/auth_routes.py:1:22
  |
1 | from datetime import timedelta
  |                      ^^^^^^^^^
2 | from typing import Dict, Any
3 | from fastapi import APIRouter, Depends, HTTPException, status, Form, Query, Request
  |
help: Remove unused import: `datetime.timedelta`

F401 [*] `..services.auth_service.get_current_user_optional` imported but unused
  --> backend/app/api/auth_routes.py:11:69
   |
10 | from ..db.database import get_db
11 | from ..services.auth_service import auth_service, get_current_user, get_current_user_optional, is_admin_user
   |                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^
12 | from ..db.models import User, UserProfile
13 | from ..core.config import settings
   |
help: Remove unused import: `..services.auth_service.get_current_user_optional`

F841 [*] Local variable `e` is assigned to but never used
   --> backend/app/api/auth_routes.py:117:25
    |
115 |     except HTTPException:
116 |         raise
117 |     except Exception as e:
    |                         ^
118 |         raise HTTPException(
119 |             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    |
help: Remove assignment to unused variable `e`

F401 [*] `fastapi.Request` imported but unused
 --> backend/app/api/integration_routes.py:1:71
  |
1 | from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
  |                                                                       ^^^^^^^
2 | from fastapi.responses import RedirectResponse
3 | from sqlalchemy.ext.asyncio import AsyncSession
  |
help: Remove unused import: `fastapi.Request`

F401 [*] `..db.integration_models.CalendarEvent` imported but unused
  --> backend/app/api/integration_routes.py:12:43
   |
10 | from ..db.models import User, Organization, JobApplication
11 | from ..db.integration_models import (
12 |     LinkedInProfile, CalendarIntegration, CalendarEvent, 
   |                                           ^^^^^^^^^^^^^
13 |     ATSIntegration, ATSJobSync, ATSApplicationSync, IntegrationActivityLog
14 | )
   |
help: Remove unused import

F401 [*] `..db.integration_models.ATSJobSync` imported but unused
  --> backend/app/api/integration_routes.py:13:21
   |
11 | from ..db.integration_models import (
12 |     LinkedInProfile, CalendarIntegration, CalendarEvent, 
13 |     ATSIntegration, ATSJobSync, ATSApplicationSync, IntegrationActivityLog
   |                     ^^^^^^^^^^
14 | )
15 | from ..services.auth_service import get_current_user
   |
help: Remove unused import

F401 [*] `..db.integration_models.ATSApplicationSync` imported but unused
  --> backend/app/api/integration_routes.py:13:33
   |
11 | from ..db.integration_models import (
12 |     LinkedInProfile, CalendarIntegration, CalendarEvent, 
13 |     ATSIntegration, ATSJobSync, ATSApplicationSync, IntegrationActivityLog
   |                                 ^^^^^^^^^^^^^^^^^^
14 | )
15 | from ..services.auth_service import get_current_user
   |
help: Remove unused import

F841 Local variable `calendar_integration` is assigned to but never used
   --> backend/app/api/integration_routes.py:325:9
    |
324 |         # Create or update calendar integration
325 |         calendar_integration = await calendar_service.create_or_update_calendar_integration(
    |         ^^^^^^^^^^^^^^^^^^^^
326 |             db, current_user.id, provider, token_data, user_data
327 |         )
    |
help: Remove assignment to unused variable `calendar_integration`

F401 [*] `..schemas.base.JobPostOut` imported but unused
 --> backend/app/api/routes.py:4:28
  |
2 | from fastapi import APIRouter, Depends, Query
3 | from sqlalchemy.orm import Session
4 | from ..schemas.base import JobPostOut, RecommendOut
  |                            ^^^^^^^^^^
5 | from ..db.database import get_db
6 | from ..services.search import search_jobs
  |
help: Remove unused import

F401 [*] `..schemas.base.RecommendOut` imported but unused
 --> backend/app/api/routes.py:4:40
  |
2 | from fastapi import APIRouter, Depends, Query
3 | from sqlalchemy.orm import Session
4 | from ..schemas.base import JobPostOut, RecommendOut
  |                                        ^^^^^^^^^^^^
5 | from ..db.database import get_db
6 | from ..services.search import search_jobs
  |
help: Remove unused import

F841 [*] Local variable `e` is assigned to but never used
  --> backend/app/api/user_routes.py:81:25
   |
79 |         }
80 |         
81 |     except Exception as e:
   |                         ^
82 |         raise HTTPException(
83 |             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
   |
help: Remove assignment to unused variable `e`

E712 Avoid equality comparisons to `False`; use `not UserNotification.is_read:` for false checks
   --> backend/app/api/user_routes.py:477:27
    |
476 |     if unread_only:
477 |         stmt = stmt.where(UserNotification.is_read == False)
    |                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
478 |     
479 |     stmt = stmt.order_by(desc(UserNotification.created_at)).limit(limit)
    |
help: Replace with `not UserNotification.is_read`

E712 Avoid equality comparisons to `False`; use `not UserNotification.is_read:` for false checks
   --> backend/app/api/user_routes.py:539:17
    |
537 |             and_(
538 |                 UserNotification.user_id == current_user.id,
539 |                 UserNotification.is_read == False
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
540 |             )
541 |         ).values(is_read=True, read_at=func.now())
    |
help: Replace with `not UserNotification.is_read`

F401 [*] `typing.Optional` imported but unused
 --> backend/app/api/workflow_routes.py:3:31
  |
1 | from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
2 | from sqlalchemy.ext.asyncio import AsyncSession
3 | from typing import Dict, Any, Optional
  |                               ^^^^^^^^
4 | import logging
  |
help: Remove unused import: `typing.Optional`

F821 Undefined name `asyncio`
  --> backend/app/api/workflow_routes.py:31:18
   |
29 |     db = SessionLocal()
30 |     try:
31 |         result = asyncio.run(_run_insights_async())
   |                  ^^^^^^^
32 |         update_processing_event(
33 |             db,
   |

F841 [*] Local variable `e` is assigned to but never used
  --> backend/app/db/database.py:29:25
   |
27 |         from .models import Base  # noqa: F401
28 |         Base.metadata.create_all(bind=engine)
29 |     except Exception as e:
   |                         ^
30 |         import traceback
31 |         traceback.print_exc()
   |
help: Remove assignment to unused variable `e`

F401 [*] `sqlalchemy.orm.DeclarativeBase` imported but unused
 --> backend/app/db/integration_models.py:1:28
  |
1 | from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
  |                            ^^^^^^^^^^^^^^^
2 | from sqlalchemy import String, Integer, Text, ForeignKey, Float, DateTime, Boolean, Index
3 | import os
  |
help: Remove unused import

F401 [*] `sqlalchemy.orm.relationship` imported but unused
 --> backend/app/db/integration_models.py:1:45
  |
1 | from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
  |                                             ^^^^^^^^^^^^
2 | from sqlalchemy import String, Integer, Text, ForeignKey, Float, DateTime, Boolean, Index
3 | import os
  |
help: Remove unused import

F401 [*] `sqlalchemy.Float` imported but unused
 --> backend/app/db/integration_models.py:2:59
  |
1 | from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
2 | from sqlalchemy import String, Integer, Text, ForeignKey, Float, DateTime, Boolean, Index
  |                                                           ^^^^^
3 | import os
4 | if os.getenv("DATABASE_URL", "").startswith("sqlite"):
  |
help: Remove unused import: `sqlalchemy.Float`

F401 [*] `typing.List` imported but unused
  --> backend/app/db/integration_models.py:12:20
   |
10 |         from sqlalchemy import JSON as JSONB
11 | from datetime import datetime
12 | from typing import List
   |                    ^^^^
13 | import uuid
14 | from .models import Base
   |
help: Remove unused import: `typing.List`

F401 [*] `uuid` imported but unused
  --> backend/app/db/integration_models.py:13:8
   |
11 | from datetime import datetime
12 | from typing import List
13 | import uuid
   |        ^^^^
14 | from .models import Base
   |
help: Remove unused import: `uuid`

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/greenhouse.py:21:24
   |
19 |         if not org:
20 |             org = Organization(name=org_name, ats="greenhouse", verified=True)
21 |             db.add(org); db.commit(); db.refresh(org)
   |                        ^
22 |     else:
23 |         org = None
   |

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/greenhouse.py:21:37
   |
19 |         if not org:
20 |             org = Organization(name=org_name, ats="greenhouse", verified=True)
21 |             db.add(org); db.commit(); db.refresh(org)
   |                                     ^
22 |     else:
23 |         org = None
   |

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/greenhouse.py:31:29
   |
29 |         if existing:
30 |             existing.last_seen = datetime.utcnow()
31 |             db.add(existing); continue
   |                             ^
32 |
33 |         loc = None
   |

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/greenhouse.py:36:24
   |
34 |         if j.get("location", {}).get("name"):
35 |             loc = Location(raw=j["location"]["name"])
36 |             db.add(loc); db.flush()
   |                        ^
37 |
38 |         jp = JobPost(
   |

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/greenhouse.py:47:19
   |
45 |             requirements_raw="",
46 |         )
47 |         db.add(jp); added += 1
   |                   ^
48 |
49 |     db.commit()
   |

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/lever.py:21:24
   |
19 |         if not org:
20 |             org = Organization(name=org_name, ats="lever", verified=True)
21 |             db.add(org); db.commit(); db.refresh(org)
   |                        ^
22 |     else:
23 |         org = None
   |

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/lever.py:21:37
   |
19 |         if not org:
20 |             org = Organization(name=org_name, ats="lever", verified=True)
21 |             db.add(org); db.commit(); db.refresh(org)
   |                                     ^
22 |     else:
23 |         org = None
   |

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/lever.py:31:29
   |
29 |         if existing:
30 |             existing.last_seen = datetime.utcnow()
31 |             db.add(existing); continue
   |                             ^
32 |
33 |         loc = None
   |

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/lever.py:36:40
   |
34 |         loc_raw = ", ".join(j.get("categories", {}).get("location", "").split("/")) if j.get("categories", {}).get("location") else No…
35 |         if loc_raw:
36 |             loc = Location(raw=loc_raw); db.add(loc); db.flush()
   |                                        ^
37 |
38 |         jp = JobPost(
   |

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/lever.py:36:53
   |
34 |         loc_raw = ", ".join(j.get("categories", {}).get("location", "").split("/")) if j.get("categories", {}).get("location") else No…
35 |         if loc_raw:
36 |             loc = Location(raw=loc_raw); db.add(loc); db.flush()
   |                                                     ^
37 |
38 |         jp = JobPost(
   |

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/lever.py:47:19
   |
45 |             requirements_raw="",
46 |         )
47 |         db.add(jp); added += 1
   |                   ^
48 |
49 |     db.commit()
   |

F401 [*] `...db.models.Location` imported but unused
 --> backend/app/ingestion/connectors/rss.py:3:49
  |
1 | # Generic RSS/Atom ingest (for boards exposing feeds)
2 | from sqlalchemy.orm import Session
3 | from ...db.models import JobPost, Organization, Location
  |                                                 ^^^^^^^^
4 | from datetime import datetime
5 | import httpx
  |
help: Remove unused import: `...db.models.Location`

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/rss.py:23:24
   |
21 |         if not org:
22 |             org = Organization(name=org_name, verified=False)
23 |             db.add(org); db.commit(); db.refresh(org)
   |                        ^
24 |     else:
25 |         org = None
   |

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/rss.py:23:37
   |
21 |         if not org:
22 |             org = Organization(name=org_name, verified=False)
23 |             db.add(org); db.commit(); db.refresh(org)
   |                                     ^
24 |     else:
25 |         org = None
   |

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/rss.py:40:29
   |
38 |         if existing:
39 |             existing.last_seen = datetime.utcnow()
40 |             db.add(existing); continue
   |                             ^
41 |
42 |         jp = JobPost(
   |

E702 Multiple statements on one line (semicolon)
  --> backend/app/ingestion/connectors/rss.py:49:19
   |
47 |             description_raw="",
48 |         )
49 |         db.add(jp); added += 1
   |                   ^
50 |
51 |     db.commit()
   |

E401 [*] Multiple imports on one line
 --> backend/app/ingestion/runner.py:7:1
  |
5 | from .connectors.gov_careers import ingest_gov_careers
6 | from sqlalchemy.orm import Session
7 | import yaml, os
  | ^^^^^^^^^^^^^^^
8 |
9 | DEFAULT_CONFIG_PATHS = [
  |
help: Split imports

F401 [*] `fastapi.Depends` imported but unused
 --> backend/app/main.py:2:30
  |
1 | from datetime import datetime, timedelta
2 | from fastapi import FastAPI, Depends, Request
  |                              ^^^^^^^
3 | from fastapi.middleware.cors import CORSMiddleware
4 | from starlette.middleware.base import BaseHTTPMiddleware
  |
help: Remove unused import

F401 [*] `fastapi.Request` imported but unused
 --> backend/app/main.py:2:39
  |
1 | from datetime import datetime, timedelta
2 | from fastapi import FastAPI, Depends, Request
  |                                       ^^^^^^^
3 | from fastapi.middleware.cors import CORSMiddleware
4 | from starlette.middleware.base import BaseHTTPMiddleware
  |
help: Remove unused import

F401 [*] `starlette.middleware.base.BaseHTTPMiddleware` imported but unused
 --> backend/app/main.py:4:39
  |
2 | from fastapi import FastAPI, Depends, Request
3 | from fastapi.middleware.cors import CORSMiddleware
4 | from starlette.middleware.base import BaseHTTPMiddleware
  |                                       ^^^^^^^^^^^^^^^^^^
5 | from sqlalchemy import select, func, text
6 | from sqlalchemy.orm import Session
  |
help: Remove unused import: `starlette.middleware.base.BaseHTTPMiddleware`

F401 [*] `sqlalchemy.orm.Session` imported but unused
 --> backend/app/main.py:6:28
  |
4 | from starlette.middleware.base import BaseHTTPMiddleware
5 | from sqlalchemy import select, func, text
6 | from sqlalchemy.orm import Session
  |                            ^^^^^^^
7 | from .core.config import settings
8 | from .core.rate_limiter import rate_limit_middleware
  |
help: Remove unused import: `sqlalchemy.orm.Session`

F401 [*] `.db.database.get_db` imported but unused
  --> backend/app/main.py:10:35
   |
 8 | from .core.rate_limiter import rate_limit_middleware
 9 | from .core.logging_config import setup_logging, logging_middleware, get_logger
10 | from .db.database import init_db, get_db, SessionLocal, DATABASE_URL
   |                                   ^^^^^^
11 | from .db.models import JobPost, User, Organization
12 | from .api.routes import api_router
   |
help: Remove unused import: `.db.database.get_db`

F401 [*] `.db.models.User` imported but unused
  --> backend/app/main.py:11:33
   |
 9 | from .core.logging_config import setup_logging, logging_middleware, get_logger
10 | from .db.database import init_db, get_db, SessionLocal, DATABASE_URL
11 | from .db.models import JobPost, User, Organization
   |                                 ^^^^
12 | from .api.routes import api_router
13 | from .api.admin_routes import router as admin_router
   |
help: Remove unused import: `.db.models.User`

F401 [*] `torch` imported but unused
  --> backend/app/ml/embeddings.py:20:20
   |
18 |     if _tokenizer is None and _use_transformers:
19 |         try:
20 |             import torch
   |                    ^^^^^
21 |             from transformers import AutoTokenizer, AutoModel
22 |             model_name = 'sentence-transformers/all-MiniLM-L6-v2'
   |
help: Remove unused import: `torch`

F401 [*] `typing.List` imported but unused
 --> backend/app/processors/data_cleaner.py:7:36
  |
5 | import re
6 | import logging
7 | from typing import Dict, Optional, List, Tuple
  |                                    ^^^^
8 | from datetime import datetime, timedelta
9 | from ..normalization.titles import normalize_title
  |
help: Remove unused import

F401 [*] `typing.Tuple` imported but unused
 --> backend/app/processors/data_cleaner.py:7:42
  |
5 | import re
6 | import logging
7 | from typing import Dict, Optional, List, Tuple
  |                                          ^^^^^
8 | from datetime import datetime, timedelta
9 | from ..normalization.titles import normalize_title
  |
help: Remove unused import

E713 [*] Test for membership should be `not in`
   --> backend/app/processors/data_cleaner.py:387:59
    |
385 |                             salary_max = val_max
386 |                     elif len(groups) >= 1 and groups[0]:  # Single value
387 |                         if 'k' in pattern.lower() and not groups[0].lower() in ['negotiable', 'competitive', 'attractive']:
    |                                                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
388 |                             val = handle_k_notation(groups[0])
389 |                         else:
    |
help: Convert to `not in`

F401 [*] `re` imported but unused
 --> backend/app/processors/job_extractor.py:7:8
  |
5 | import asyncio
6 | import aiohttp
7 | import re
  |        ^^
8 | import logging
9 | from typing import Dict, Optional, List, Tuple
  |
help: Remove unused import: `re`

F401 [*] `typing.Tuple` imported but unused
  --> backend/app/processors/job_extractor.py:9:42
   |
 7 | import re
 8 | import logging
 9 | from typing import Dict, Optional, List, Tuple
   |                                          ^^^^^
10 | from datetime import datetime
11 | from bs4 import BeautifulSoup
   |
help: Remove unused import: `typing.Tuple`

F401 [*] `urllib.parse.urljoin` imported but unused
  --> backend/app/processors/job_extractor.py:12:26
   |
10 | from datetime import datetime
11 | from bs4 import BeautifulSoup
12 | from urllib.parse import urljoin, urlparse
   |                          ^^^^^^^
13 | import json
   |
help: Remove unused import

F401 [*] `urllib.parse.urlparse` imported but unused
  --> backend/app/processors/job_extractor.py:12:35
   |
10 | from datetime import datetime
11 | from bs4 import BeautifulSoup
12 | from urllib.parse import urljoin, urlparse
   |                                   ^^^^^^^^
13 | import json
   |
help: Remove unused import

F811 [*] Redefinition of unused `re` from line 7
   --> backend/app/processors/job_extractor.py:348:16
    |
346 |     def _parse_myjobmag_content(self, content_text: str) -> tuple:
347 |         """Parse MyJobMag content to extract structured information"""
348 |         import re
    |                ^^ `re` redefined here
349 |
350 |         # Initialize defaults
    |
   ::: backend/app/processors/job_extractor.py:7:8
    |
  5 | import asyncio
  6 | import aiohttp
  7 | import re
    |        -- previous definition of `re` here
  8 | import logging
  9 | from typing import Dict, Optional, List, Tuple
    |
help: Remove definition: `re`

F811 [*] Redefinition of unused `re` from line 7
   --> backend/app/processors/job_extractor.py:438:16
    |
436 |     def _parse_jobwebkenya_content(self, content_text: str) -> tuple:
437 |         """Parse JobWebKenya content to extract structured information"""
438 |         import re
    |                ^^ `re` redefined here
439 |
440 |         # Initialize defaults
    |
   ::: backend/app/processors/job_extractor.py:7:8
    |
  5 | import asyncio
  6 | import aiohttp
  7 | import re
    |        -- previous definition of `re` here
  8 | import logging
  9 | from typing import Dict, Optional, List, Tuple
    |
help: Remove definition: `re`

F811 [*] Redefinition of unused `re` from line 7
   --> backend/app/processors/job_extractor.py:534:16
    |
532 |     def _extract_contact_info(self, content_text: str) -> str:
533 |         """Extract contact information from content"""
534 |         import re
    |                ^^ `re` redefined here
535 |         
536 |         # Look for email addresses
    |
   ::: backend/app/processors/job_extractor.py:7:8
    |
  5 | import asyncio
  6 | import aiohttp
  7 | import re
    |        -- previous definition of `re` here
  8 | import logging
  9 | from typing import Dict, Optional, List, Tuple
    |
help: Remove definition: `re`

F841 Local variable `extractor` is assigned to but never used
   --> backend/app/processors/job_processor.py:274:46
    |
273 |             # Test extractor
274 |             async with JobDataExtractor() as extractor:
    |                                              ^^^^^^^^^
275 |                 # This just tests that we can create the extractor
276 |                 pass
    |
help: Remove assignment to unused variable `extractor`

F401 [*] `asyncio` imported but unused
 --> backend/app/scrapers/brighter_monday_scraper.py:6:8
  |
4 | """
5 |
6 | import asyncio
  |        ^^^^^^^
7 | from bs4 import BeautifulSoup
8 | from typing import List, Dict, Optional
  |
help: Remove unused import: `asyncio`

F401 [*] `asyncio` imported but unused
 --> backend/app/scrapers/indeed_scraper.py:6:8
  |
4 | """
5 |
6 | import asyncio
  |        ^^^^^^^
7 | from bs4 import BeautifulSoup
8 | from typing import List, Dict, Optional
  |
help: Remove unused import: `asyncio`

F401 [*] `re` imported but unused
  --> backend/app/scrapers/indeed_scraper.py:9:8
   |
 7 | from bs4 import BeautifulSoup
 8 | from typing import List, Dict, Optional
 9 | import re
   |        ^^
10 | import logging
11 | from urllib.parse import urljoin, quote_plus
   |
help: Remove unused import: `re`

F401 [*] `asyncio` imported but unused
 --> backend/app/scrapers/linkedin_scraper.py:6:8
  |
4 | """
5 |
6 | import asyncio
  |        ^^^^^^^
7 | from bs4 import BeautifulSoup
8 | from typing import List, Dict, Optional
  |
help: Remove unused import: `asyncio`

F541 [*] f-string without any placeholders
  --> backend/app/scrapers/linkedin_scraper.py:52:30
   |
50 |             html = await self.fetch_page(search_url)
51 |             if not html:
52 |                 logger.error(f"Failed to fetch LinkedIn jobs page")
   |                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
53 |                 return jobs
   |
help: Remove extraneous `f` prefix

F401 [*] `datetime.datetime` imported but unused
 --> backend/app/scrapers/main.py:4:22
  |
2 | import logging
3 | import argparse
4 | from datetime import datetime
  |                      ^^^^^^^^
5 | from .scraper import SiteSpider
6 | from .config import SITES
  |
help: Remove unused import: `datetime.datetime`

F401 [*] `typing.List` imported but unused
  --> backend/app/scrapers/migrate_to_postgres.py:13:20
   |
11 | from datetime import datetime
12 | from pathlib import Path
13 | from typing import List, Dict, Any, Optional
   |                    ^^^^
14 | from urllib.parse import urlparse
   |
help: Remove unused import: `typing.List`

F401 [*] `app.db.models.Location` imported but unused
  --> backend/app/scrapers/migrate_to_postgres.py:28:60
   |
26 |     # Try absolute imports if relative imports fail
27 |     from app.db.database import SessionLocal, engine
28 |     from app.db.models import Base, JobPost, Organization, Location, TitleNorm
   |                                                            ^^^^^^^^
29 |     from app.scrapers.config import DB_PATH, TABLE_NAME
   |
help: Remove unused import

F401 [*] `app.db.models.TitleNorm` imported but unused
  --> backend/app/scrapers/migrate_to_postgres.py:28:70
   |
26 |     # Try absolute imports if relative imports fail
27 |     from app.db.database import SessionLocal, engine
28 |     from app.db.models import Base, JobPost, Organization, Location, TitleNorm
   |                                                                      ^^^^^^^^^
29 |     from app.scrapers.config import DB_PATH, TABLE_NAME
   |
help: Remove unused import

F401 [*] `app.db.models.Location` imported but unused
  --> backend/app/scrapers/postgres_db.py:21:60
   |
19 |     # Try absolute imports if relative imports fail
20 |     from app.db.database import SessionLocal, engine
21 |     from app.db.models import Base, JobPost, Organization, Location
   |                                                            ^^^^^^^^
22 |
23 | logging.basicConfig(level=logging.INFO)
   |
help: Remove unused import: `app.db.models.Location`

E402 Module level import not at top of file
  --> backend/app/scrapers/scraper.py:13:1
   |
11 | )
12 |
13 | import argparse
   | ^^^^^^^^^^^^^^^
14 | import logging
15 | import urllib3
   |

E402 Module level import not at top of file
  --> backend/app/scrapers/scraper.py:14:1
   |
13 | import argparse
14 | import logging
   | ^^^^^^^^^^^^^^
15 | import urllib3
16 | from bs4 import BeautifulSoup
   |

E402 Module level import not at top of file
  --> backend/app/scrapers/scraper.py:15:1
   |
13 | import argparse
14 | import logging
15 | import urllib3
   | ^^^^^^^^^^^^^^
16 | from bs4 import BeautifulSoup
17 | from concurrent.futures import ThreadPoolExecutor
   |

E402 Module level import not at top of file
  --> backend/app/scrapers/scraper.py:16:1
   |
14 | import logging
15 | import urllib3
16 | from bs4 import BeautifulSoup
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
17 | from concurrent.futures import ThreadPoolExecutor
18 | from urllib.parse import urljoin
   |

E402 Module level import not at top of file
  --> backend/app/scrapers/scraper.py:17:1
   |
15 | import urllib3
16 | from bs4 import BeautifulSoup
17 | from concurrent.futures import ThreadPoolExecutor
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
18 | from urllib.parse import urljoin
19 | from dataclasses import dataclass
   |

E402 Module level import not at top of file
  --> backend/app/scrapers/scraper.py:18:1
   |
16 | from bs4 import BeautifulSoup
17 | from concurrent.futures import ThreadPoolExecutor
18 | from urllib.parse import urljoin
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
19 | from dataclasses import dataclass
   |

E402 Module level import not at top of file
  --> backend/app/scrapers/scraper.py:19:1
   |
17 | from concurrent.futures import ThreadPoolExecutor
18 | from urllib.parse import urljoin
19 | from dataclasses import dataclass
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
20 |
21 | # Absolute imports assuming `scrapers/` is on PYTHONPATH
   |

E402 Module level import not at top of file
  --> backend/app/scrapers/scraper.py:22:1
   |
21 | # Absolute imports assuming `scrapers/` is on PYTHONPATH
22 | from scrapers.config import SITES, get_site_cfg, USE_POSTGRES
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
23 | from scrapers.db     import Database
24 | from scrapers.postgres_db import PostgresJobDatabase
   |

E402 Module level import not at top of file
  --> backend/app/scrapers/scraper.py:23:1
   |
21 | # Absolute imports assuming `scrapers/` is on PYTHONPATH
22 | from scrapers.config import SITES, get_site_cfg, USE_POSTGRES
23 | from scrapers.db     import Database
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
24 | from scrapers.postgres_db import PostgresJobDatabase
25 | from scrapers.utils  import get_session, rate_limited_get
   |

E402 Module level import not at top of file
  --> backend/app/scrapers/scraper.py:24:1
   |
22 | from scrapers.config import SITES, get_site_cfg, USE_POSTGRES
23 | from scrapers.db     import Database
24 | from scrapers.postgres_db import PostgresJobDatabase
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
25 | from scrapers.utils  import get_session, rate_limited_get
   |

E402 Module level import not at top of file
  --> backend/app/scrapers/scraper.py:25:1
   |
23 | from scrapers.db     import Database
24 | from scrapers.postgres_db import PostgresJobDatabase
25 | from scrapers.utils  import get_session, rate_limited_get
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
26 |
27 | # Suppress generic InsecureRequestWarning
   |

F401 [*] `os` imported but unused
 --> backend/app/scrapers/spiders/brightermonday.py:2:8
  |
1 | import logging
2 | import os
  |        ^^
3 | import sqlite3
4 | import urllib3
  |
help: Remove unused import: `os`

F401 [*] `time` imported but unused
  --> backend/app/scrapers/spiders/brightermonday.py:9:8
   |
 7 | from concurrent.futures import ThreadPoolExecutor
 8 | from urllib.parse import urljoin
 9 | import time
   |        ^^^^
10 | from ratelimit import limits, sleep_and_retry
11 | from datetime import datetime, timedelta
   |
help: Remove unused import: `time`

F401 [*] `ratelimit.limits` imported but unused
  --> backend/app/scrapers/spiders/brightermonday.py:10:23
   |
 8 | from urllib.parse import urljoin
 9 | import time
10 | from ratelimit import limits, sleep_and_retry
   |                       ^^^^^^
11 | from datetime import datetime, timedelta
   |
help: Remove unused import

F401 [*] `ratelimit.sleep_and_retry` imported but unused
  --> backend/app/scrapers/spiders/brightermonday.py:10:31
   |
 8 | from urllib.parse import urljoin
 9 | import time
10 | from ratelimit import limits, sleep_and_retry
   |                               ^^^^^^^^^^^^^^^
11 | from datetime import datetime, timedelta
   |
help: Remove unused import

F401 [*] `datetime.datetime` imported but unused
  --> backend/app/scrapers/spiders/brightermonday.py:11:22
   |
 9 | import time
10 | from ratelimit import limits, sleep_and_retry
11 | from datetime import datetime, timedelta
   |                      ^^^^^^^^
12 |
13 | urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
   |
help: Remove unused import

F401 [*] `datetime.timedelta` imported but unused
  --> backend/app/scrapers/spiders/brightermonday.py:11:32
   |
 9 | import time
10 | from ratelimit import limits, sleep_and_retry
11 | from datetime import datetime, timedelta
   |                                ^^^^^^^^^
12 |
13 | urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
   |
help: Remove unused import

F401 [*] `os` imported but unused
  --> backend/app/scrapers/spiders/careerjet.py:11:8
   |
 9 | from requests.adapters import HTTPAdapter
10 | from requests.packages.urllib3.util.retry import Retry
11 | import os
   |        ^^
12 | from typing import List, Dict, Optional
13 | from dataclasses import dataclass
   |
help: Remove unused import: `os`

F401 [*] `typing.Dict` imported but unused
  --> backend/app/scrapers/spiders/careerjet.py:12:26
   |
10 | from requests.packages.urllib3.util.retry import Retry
11 | import os
12 | from typing import List, Dict, Optional
   |                          ^^^^
13 | from dataclasses import dataclass
   |
help: Remove unused import: `typing.Dict`

F401 [*] `os` imported but unused
  --> backend/app/scrapers/spiders/jobwebkenya.py:11:8
   |
 9 | from requests.adapters import HTTPAdapter
10 | from requests.packages.urllib3.util.retry import Retry
11 | import os
   |        ^^
12 | from typing import List, Dict, Optional
13 | from dataclasses import dataclass
   |
help: Remove unused import: `os`

F401 [*] `typing.Dict` imported but unused
  --> backend/app/scrapers/spiders/jobwebkenya.py:12:26
   |
10 | from requests.packages.urllib3.util.retry import Retry
11 | import os
12 | from typing import List, Dict, Optional
   |                          ^^^^
13 | from dataclasses import dataclass
   |
help: Remove unused import: `typing.Dict`

F401 [*] `os` imported but unused
  --> backend/app/scrapers/spiders/myjobmag.py:11:8
   |
 9 | from requests.adapters import HTTPAdapter
10 | from requests.packages.urllib3.util.retry import Retry
11 | import os
   |        ^^
12 | from typing import List, Dict, Optional
13 | from dataclasses import dataclass
   |
help: Remove unused import: `os`

F401 [*] `typing.Dict` imported but unused
  --> backend/app/scrapers/spiders/myjobmag.py:12:26
   |
10 | from requests.packages.urllib3.util.retry import Retry
11 | import os
12 | from typing import List, Dict, Optional
   |                          ^^^^
13 | from dataclasses import dataclass
   |
help: Remove unused import: `typing.Dict`

F401 [*] `asyncio` imported but unused
 --> backend/app/services/ai_service.py:1:8
  |
1 | import asyncio
  |        ^^^^^^^
2 | import json
3 | import logging
  |
help: Remove unused import: `asyncio`

F401 [*] `json` imported but unused
 --> backend/app/services/ai_service.py:2:8
  |
1 | import asyncio
2 | import json
  |        ^^^^
3 | import logging
4 | from typing import List, Dict, Any, Optional, Tuple
  |
help: Remove unused import: `json`

F401 [*] `typing.Optional` imported but unused
 --> backend/app/services/ai_service.py:4:37
  |
2 | import json
3 | import logging
4 | from typing import List, Dict, Any, Optional, Tuple
  |                                     ^^^^^^^^
5 | import numpy as np
6 | from ..ml.embeddings import embed_text, generate_embeddings
  |
help: Remove unused import: `typing.Optional`

F401 [*] `..ml.embeddings.generate_embeddings` imported but unused
 --> backend/app/services/ai_service.py:6:41
  |
4 | from typing import List, Dict, Any, Optional, Tuple
5 | import numpy as np
6 | from ..ml.embeddings import embed_text, generate_embeddings
  |                                         ^^^^^^^^^^^^^^^^^^^
7 | try:
8 |     from sentence_transformers import SentenceTransformer  # type: ignore
  |
help: Remove unused import: `..ml.embeddings.generate_embeddings`

F401 [*] `sqlalchemy.orm.Session` imported but unused
  --> backend/app/services/ai_service.py:16:28
   |
14 | from sklearn.feature_extraction.text import TfidfVectorizer
15 | import openai
16 | from sqlalchemy.orm import Session
   |                            ^^^^^^^
17 | from sqlalchemy import select, text
   |
help: Remove unused import: `sqlalchemy.orm.Session`

F401 [*] `sqlalchemy.select` imported but unused
  --> backend/app/services/ai_service.py:17:24
   |
15 | import openai
16 | from sqlalchemy.orm import Session
17 | from sqlalchemy import select, text
   |                        ^^^^^^
18 |
19 | from ..db.models import JobPost, Skill, UserProfile, User
   |
help: Remove unused import

F401 [*] `sqlalchemy.text` imported but unused
  --> backend/app/services/ai_service.py:17:32
   |
15 | import openai
16 | from sqlalchemy.orm import Session
17 | from sqlalchemy import select, text
   |                                ^^^^
18 |
19 | from ..db.models import JobPost, Skill, UserProfile, User
   |
help: Remove unused import

F401 [*] `..db.models.Skill` imported but unused
  --> backend/app/services/ai_service.py:19:34
   |
17 | from sqlalchemy import select, text
18 |
19 | from ..db.models import JobPost, Skill, UserProfile, User
   |                                  ^^^^^
20 | from ..core.config import settings
   |
help: Remove unused import

F401 [*] `..db.models.User` imported but unused
  --> backend/app/services/ai_service.py:19:54
   |
17 | from sqlalchemy import select, text
18 |
19 | from ..db.models import JobPost, Skill, UserProfile, User
   |                                                      ^^^^
20 | from ..core.config import settings
   |
help: Remove unused import

F811 Redefinition of unused `text` from line 17
   --> backend/app/services/ai_service.py:128:40
    |
126 |             return 0.0
127 |     
128 |     def extract_skills_from_text(self, text: str) -> Dict[str, float]:
    |                                        ^^^^ `text` redefined here
129 |         """Extract skills from job description or user profile text."""
130 |         if not text:
    |
   ::: backend/app/services/ai_service.py:17:32
    |
 15 | import openai
 16 | from sqlalchemy.orm import Session
 17 | from sqlalchemy import select, text
    |                                ---- previous definition of `text` here
 18 |
 19 | from ..db.models import JobPost, Skill, UserProfile, User
    |
help: Remove definition: `text`

F811 Redefinition of unused `text` from line 17
   --> backend/app/services/ai_service.py:465:31
    |
463 |         return sorted(keywords)
464 |
465 |     def _split_keywords(self, text: str) -> List[str]:
    |                               ^^^^ `text` redefined here
466 |         tokens = []
467 |         for chunk in str(text).replace("|", ",").replace("/", ",").split(","):
    |
   ::: backend/app/services/ai_service.py:17:32
    |
 15 | import openai
 16 | from sqlalchemy.orm import Session
 17 | from sqlalchemy import select, text
    |                                ---- previous definition of `text` here
 18 |
 19 | from ..db.models import JobPost, Skill, UserProfile, User
    |
help: Remove definition: `text`

F811 Redefinition of unused `text` from line 17
   --> backend/app/services/ai_service.py:474:36
    |
472 |         return tokens
473 |
474 |     def _keyword_match_score(self, text: str, keywords: List[str]):
    |                                    ^^^^ `text` redefined here
475 |         if not keywords or not text:
476 |             return 0.0, []
    |
   ::: backend/app/services/ai_service.py:17:32
    |
 15 | import openai
 16 | from sqlalchemy.orm import Session
 17 | from sqlalchemy import select, text
    |                                ---- previous definition of `text` here
 18 |
 19 | from ..db.models import JobPost, Skill, UserProfile, User
    |
help: Remove definition: `text`

F401 [*] `json` imported but unused
 --> backend/app/services/ats_service.py:2:8
  |
1 | import asyncio
2 | import json
  |        ^^^^
3 | from datetime import datetime, timedelta
4 | from typing import Optional, Dict, List, Any
  |
help: Remove unused import: `json`

F401 [*] `datetime.timedelta` imported but unused
 --> backend/app/services/ats_service.py:3:32
  |
1 | import asyncio
2 | import json
3 | from datetime import datetime, timedelta
  |                                ^^^^^^^^^
4 | from typing import Optional, Dict, List, Any
5 | from sqlalchemy.ext.asyncio import AsyncSession
  |
help: Remove unused import: `datetime.timedelta`

F401 [*] `sqlalchemy.update` imported but unused
 --> backend/app/services/ats_service.py:6:32
  |
4 | from typing import Optional, Dict, List, Any
5 | from sqlalchemy.ext.asyncio import AsyncSession
6 | from sqlalchemy import select, update
  |                                ^^^^^^
7 | import httpx
8 | from urllib.parse import urljoin
  |
help: Remove unused import: `sqlalchemy.update`

F401 [*] `urllib.parse.urljoin` imported but unused
 --> backend/app/services/ats_service.py:8:26
  |
6 | from sqlalchemy import select, update
7 | import httpx
8 | from urllib.parse import urljoin
  |                          ^^^^^^^
9 | import base64
  |
help: Remove unused import: `urllib.parse.urljoin`

F401 [*] `..db.database.get_db` imported but unused
  --> backend/app/services/ats_service.py:12:27
   |
11 | from ..core.config import settings
12 | from ..db.database import get_db
   |                           ^^^^^^
13 | from ..db.models import Organization, JobPost, JobApplication, User
14 | from ..db.integration_models import ATSIntegration, ATSJobSync, ATSApplicationSync, IntegrationActivityLog
   |
help: Remove unused import: `..db.database.get_db`

F401 [*] `..db.models.Organization` imported but unused
  --> backend/app/services/ats_service.py:13:25
   |
11 | from ..core.config import settings
12 | from ..db.database import get_db
13 | from ..db.models import Organization, JobPost, JobApplication, User
   |                         ^^^^^^^^^^^^
14 | from ..db.integration_models import ATSIntegration, ATSJobSync, ATSApplicationSync, IntegrationActivityLog
15 | import logging
   |
help: Remove unused import: `..db.models.Organization`

F841 Local variable `ats_config` is assigned to but never used
   --> backend/app/services/ats_service.py:131:13
    |
129 |         """Test connection to ATS provider"""
130 |         try:
131 |             ats_config = self.supported_ats[ats_provider]
    |             ^^^^^^^^^^
132 |             
133 |             if ats_provider == 'greenhouse':
    |
help: Remove assignment to unused variable `ats_config`

E712 Avoid equality comparisons to `True`; use `ATSIntegration.is_active:` for truth checks
   --> backend/app/services/ats_service.py:807:21
    |
805 |             result = await db.execute(
806 |                 select(ATSIntegration).where(
807 |                     ATSIntegration.is_active == True,
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
808 |                     ATSIntegration.sync_status == "active"
809 |                 )
    |
help: Replace with `ATSIntegration.is_active`

F401 [*] `hashlib` imported but unused
  --> backend/app/services/auth_service.py:11:8
   |
 9 | import uuid
10 | import secrets
11 | import hashlib
   |        ^^^^^^^
12 |
13 | from ..db.models import User, UserProfile
   |
help: Remove unused import: `hashlib`

F401 [*] `asyncio` imported but unused
 --> backend/app/services/automated_workflow_service.py:1:8
  |
1 | import asyncio
  |        ^^^^^^^
2 | import logging
3 | from datetime import datetime, timedelta
  |
help: Remove unused import: `asyncio`

F401 [*] `typing.Optional` imported but unused
 --> backend/app/services/automated_workflow_service.py:4:37
  |
2 | import logging
3 | from datetime import datetime, timedelta
4 | from typing import Dict, List, Any, Optional
  |                                     ^^^^^^^^
5 | from sqlalchemy.ext.asyncio import AsyncSession
6 | from sqlalchemy import select, func, and_, or_, desc
  |
help: Remove unused import: `typing.Optional`

F401 [*] `sqlalchemy.or_` imported but unused
 --> backend/app/services/automated_workflow_service.py:6:44
  |
4 | from typing import Dict, List, Any, Optional
5 | from sqlalchemy.ext.asyncio import AsyncSession
6 | from sqlalchemy import select, func, and_, or_, desc
  |                                            ^^^
7 | from sqlalchemy.orm import selectinload
8 | import json
  |
help: Remove unused import

F401 [*] `sqlalchemy.desc` imported but unused
 --> backend/app/services/automated_workflow_service.py:6:49
  |
4 | from typing import Dict, List, Any, Optional
5 | from sqlalchemy.ext.asyncio import AsyncSession
6 | from sqlalchemy import select, func, and_, or_, desc
  |                                                 ^^^^
7 | from sqlalchemy.orm import selectinload
8 | import json
  |
help: Remove unused import

F401 [*] `sqlalchemy.orm.selectinload` imported but unused
 --> backend/app/services/automated_workflow_service.py:7:28
  |
5 | from sqlalchemy.ext.asyncio import AsyncSession
6 | from sqlalchemy import select, func, and_, or_, desc
7 | from sqlalchemy.orm import selectinload
  |                            ^^^^^^^^^^^^
8 | import json
9 | import numpy as np
  |
help: Remove unused import: `sqlalchemy.orm.selectinload`

F401 [*] `json` imported but unused
  --> backend/app/services/automated_workflow_service.py:8:8
   |
 6 | from sqlalchemy import select, func, and_, or_, desc
 7 | from sqlalchemy.orm import selectinload
 8 | import json
   |        ^^^^
 9 | import numpy as np
10 | from collections import defaultdict, Counter
   |
help: Remove unused import: `json`

F401 [*] `..db.database.get_db` imported but unused
  --> backend/app/services/automated_workflow_service.py:12:27
   |
10 | from collections import defaultdict, Counter
11 |
12 | from ..db.database import get_db
   |                           ^^^^^^
13 | from ..db.models import (
14 |     JobPost, Organization, Location, TitleNorm, Skill, JobSkill, 
   |
help: Remove unused import: `..db.database.get_db`

F401 [*] `..db.models.Organization` imported but unused
  --> backend/app/services/automated_workflow_service.py:14:14
   |
12 | from ..db.database import get_db
13 | from ..db.models import (
14 |     JobPost, Organization, Location, TitleNorm, Skill, JobSkill, 
   |              ^^^^^^^^^^^^
15 |     MetricsDaily, User, UserProfile, SearchHistory, JobApplication
16 | )
   |
help: Remove unused import

F401 [*] `..db.models.Location` imported but unused
  --> backend/app/services/automated_workflow_service.py:14:28
   |
12 | from ..db.database import get_db
13 | from ..db.models import (
14 |     JobPost, Organization, Location, TitleNorm, Skill, JobSkill, 
   |                            ^^^^^^^^
15 |     MetricsDaily, User, UserProfile, SearchHistory, JobApplication
16 | )
   |
help: Remove unused import

F401 [*] `..db.models.JobSkill` imported but unused
  --> backend/app/services/automated_workflow_service.py:14:56
   |
12 | from ..db.database import get_db
13 | from ..db.models import (
14 |     JobPost, Organization, Location, TitleNorm, Skill, JobSkill, 
   |                                                        ^^^^^^^^
15 |     MetricsDaily, User, UserProfile, SearchHistory, JobApplication
16 | )
   |
help: Remove unused import

F401 [*] `..db.models.User` imported but unused
  --> backend/app/services/automated_workflow_service.py:15:19
   |
13 | from ..db.models import (
14 |     JobPost, Organization, Location, TitleNorm, Skill, JobSkill, 
15 |     MetricsDaily, User, UserProfile, SearchHistory, JobApplication
   |                   ^^^^
16 | )
17 | from ..services.scraper_service import scraper_service
   |
help: Remove unused import

F401 [*] `..services.data_processing_service.data_processing_service` imported but unused
  --> backend/app/services/automated_workflow_service.py:18:48
   |
16 | )
17 | from ..services.scraper_service import scraper_service
18 | from ..services.data_processing_service import data_processing_service
   |                                                ^^^^^^^^^^^^^^^^^^^^^^^
19 | from ..processors.job_processor import JobProcessor
20 | from ..normalization.titles import normalize_title, update_title_mappings
   |
help: Remove unused import: `..services.data_processing_service.data_processing_service`

F401 [*] `..ml.embeddings.generate_embeddings` imported but unused
  --> backend/app/services/automated_workflow_service.py:22:29
   |
20 | from ..normalization.titles import normalize_title, update_title_mappings
21 | from ..normalization.skills import extract_and_normalize_skills, update_skill_mappings
22 | from ..ml.embeddings import generate_embeddings, update_embeddings_model
   |                             ^^^^^^^^^^^^^^^^^^^
23 | from ..core.config import settings
   |
help: Remove unused import: `..ml.embeddings.generate_embeddings`

F401 [*] `..core.config.settings` imported but unused
  --> backend/app/services/automated_workflow_service.py:23:27
   |
21 | from ..normalization.skills import extract_and_normalize_skills, update_skill_mappings
22 | from ..ml.embeddings import generate_embeddings, update_embeddings_model
23 | from ..core.config import settings
   |                           ^^^^^^^^
24 |
25 | logger = logging.getLogger(__name__)
   |
help: Remove unused import: `..core.config.settings`

F401 [*] `asyncio` imported but unused
 --> backend/app/services/calendar_service.py:1:8
  |
1 | import asyncio
  |        ^^^^^^^
2 | import json
3 | from datetime import datetime, timedelta
  |
help: Remove unused import: `asyncio`

F401 [*] `json` imported but unused
 --> backend/app/services/calendar_service.py:2:8
  |
1 | import asyncio
2 | import json
  |        ^^^^
3 | from datetime import datetime, timedelta
4 | from typing import Optional, Dict, List, Any
  |
help: Remove unused import: `json`

F401 [*] `typing.List` imported but unused
 --> backend/app/services/calendar_service.py:4:36
  |
2 | import json
3 | from datetime import datetime, timedelta
4 | from typing import Optional, Dict, List, Any
  |                                    ^^^^
5 | from sqlalchemy.ext.asyncio import AsyncSession
6 | from sqlalchemy import select, update
  |
help: Remove unused import: `typing.List`

F401 [*] `sqlalchemy.update` imported but unused
 --> backend/app/services/calendar_service.py:6:32
  |
4 | from typing import Optional, Dict, List, Any
5 | from sqlalchemy.ext.asyncio import AsyncSession
6 | from sqlalchemy import select, update
  |                                ^^^^^^
7 | import httpx
8 | from google.oauth2.credentials import Credentials
  |
help: Remove unused import: `sqlalchemy.update`

F401 [*] `exchangelib.Credentials` imported but unused
  --> backend/app/services/calendar_service.py:12:40
   |
10 | from googleapiclient.discovery import build
11 | from google_auth_oauthlib.flow import Flow
12 | from exchangelib import Credentials as ExchangeCredentials, Account, Configuration, DELEGATE
   |                                        ^^^^^^^^^^^^^^^^^^^
13 | import pytz
   |
help: Remove unused import

F401 [*] `exchangelib.Account` imported but unused
  --> backend/app/services/calendar_service.py:12:61
   |
10 | from googleapiclient.discovery import build
11 | from google_auth_oauthlib.flow import Flow
12 | from exchangelib import Credentials as ExchangeCredentials, Account, Configuration, DELEGATE
   |                                                             ^^^^^^^
13 | import pytz
   |
help: Remove unused import

F401 [*] `exchangelib.Configuration` imported but unused
  --> backend/app/services/calendar_service.py:12:70
   |
10 | from googleapiclient.discovery import build
11 | from google_auth_oauthlib.flow import Flow
12 | from exchangelib import Credentials as ExchangeCredentials, Account, Configuration, DELEGATE
   |                                                                      ^^^^^^^^^^^^^
13 | import pytz
   |
help: Remove unused import

F401 [*] `exchangelib.DELEGATE` imported but unused
  --> backend/app/services/calendar_service.py:12:85
   |
10 | from googleapiclient.discovery import build
11 | from google_auth_oauthlib.flow import Flow
12 | from exchangelib import Credentials as ExchangeCredentials, Account, Configuration, DELEGATE
   |                                                                                     ^^^^^^^^
13 | import pytz
   |
help: Remove unused import

F401 [*] `pytz` imported but unused
  --> backend/app/services/calendar_service.py:13:8
   |
11 | from google_auth_oauthlib.flow import Flow
12 | from exchangelib import Credentials as ExchangeCredentials, Account, Configuration, DELEGATE
13 | import pytz
   |        ^^^^
14 |
15 | from ..core.config import settings
   |
help: Remove unused import: `pytz`

F401 [*] `..db.database.get_db` imported but unused
  --> backend/app/services/calendar_service.py:16:27
   |
15 | from ..core.config import settings
16 | from ..db.database import get_db
   |                           ^^^^^^
17 | from ..db.models import User, JobApplication
18 | from ..db.integration_models import CalendarIntegration, CalendarEvent, IntegrationActivityLog
   |
help: Remove unused import: `..db.database.get_db`

F401 [*] `..db.models.JobApplication` imported but unused
  --> backend/app/services/calendar_service.py:17:31
   |
15 | from ..core.config import settings
16 | from ..db.database import get_db
17 | from ..db.models import User, JobApplication
   |                               ^^^^^^^^^^^^^^
18 | from ..db.integration_models import CalendarIntegration, CalendarEvent, IntegrationActivityLog
19 | import logging
   |
help: Remove unused import: `..db.models.JobApplication`

E712 Avoid equality comparisons to `True`; use `CalendarIntegration.is_active:` for truth checks
   --> backend/app/services/calendar_service.py:295:21
    |
293 |                 select(CalendarIntegration).where(
294 |                     CalendarIntegration.user_id == user_id,
295 |                     CalendarIntegration.is_active == True
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
296 |                 )
297 |             )
    |
help: Replace with `CalendarIntegration.is_active`

E712 Avoid equality comparisons to `False`; use `not CalendarEvent.reminder_sent:` for false checks
   --> backend/app/services/calendar_service.py:577:21
    |
575 |                     CalendarEvent.start_time > now,
576 |                     CalendarEvent.start_time <= now + timedelta(hours=24),
577 |                     CalendarEvent.reminder_sent == False,
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
578 |                     CalendarEvent.status == "scheduled"
579 |                 )
    |
help: Replace with `not CalendarEvent.reminder_sent`

F401 [*] `typing.Optional` imported but unused
  --> backend/app/services/career_tools_service.py:8:32
   |
 6 | import os
 7 | from datetime import datetime
 8 | from typing import Dict, List, Optional, Any
   |                                ^^^^^^^^
 9 | from sqlalchemy.orm import Session
10 | from ..db.database import SessionLocal
   |
help: Remove unused import

F401 [*] `typing.Any` imported but unused
  --> backend/app/services/career_tools_service.py:8:42
   |
 6 | import os
 7 | from datetime import datetime
 8 | from typing import Dict, List, Optional, Any
   |                                          ^^^
 9 | from sqlalchemy.orm import Session
10 | from ..db.database import SessionLocal
   |
help: Remove unused import

F401 [*] `sqlalchemy.orm.Session` imported but unused
  --> backend/app/services/career_tools_service.py:9:28
   |
 7 | from datetime import datetime
 8 | from typing import Dict, List, Optional, Any
 9 | from sqlalchemy.orm import Session
   |                            ^^^^^^^
10 | from ..db.database import SessionLocal
11 | from ..db.models import JobPost, User, UserProfile, CareerDocument
   |
help: Remove unused import: `sqlalchemy.orm.Session`

F401 [*] `..db.models.JobPost` imported but unused
  --> backend/app/services/career_tools_service.py:11:25
   |
 9 | from sqlalchemy.orm import Session
10 | from ..db.database import SessionLocal
11 | from ..db.models import JobPost, User, UserProfile, CareerDocument
   |                         ^^^^^^^
12 | import openai
13 | import json
   |
help: Remove unused import

F401 [*] `..db.models.User` imported but unused
  --> backend/app/services/career_tools_service.py:11:34
   |
 9 | from sqlalchemy.orm import Session
10 | from ..db.database import SessionLocal
11 | from ..db.models import JobPost, User, UserProfile, CareerDocument
   |                                  ^^^^
12 | import openai
13 | import json
   |
help: Remove unused import

F401 [*] `..db.models.UserProfile` imported but unused
  --> backend/app/services/career_tools_service.py:11:40
   |
 9 | from sqlalchemy.orm import Session
10 | from ..db.database import SessionLocal
11 | from ..db.models import JobPost, User, UserProfile, CareerDocument
   |                                        ^^^^^^^^^^^
12 | import openai
13 | import json
   |
help: Remove unused import

F401 [*] `typing.Optional` imported but unused
  --> backend/app/services/data_processing_service.py:8:32
   |
 6 | import logging
 7 | from datetime import datetime, timedelta
 8 | from typing import Dict, List, Optional
   |                                ^^^^^^^^
 9 | from sqlalchemy.orm import Session
10 | from ..db.database import SessionLocal
   |
help: Remove unused import: `typing.Optional`

F401 [*] `sqlalchemy.orm.Session` imported but unused
  --> backend/app/services/data_processing_service.py:9:28
   |
 7 | from datetime import datetime, timedelta
 8 | from typing import Dict, List, Optional
 9 | from sqlalchemy.orm import Session
   |                            ^^^^^^^
10 | from ..db.database import SessionLocal
11 | from ..db.models import JobPost, ProcessingLog
   |
help: Remove unused import: `sqlalchemy.orm.Session`

F401 [*] `..services.scraper_service.scraper_service` imported but unused
  --> backend/app/services/data_processing_service.py:13:40
   |
11 | from ..db.models import JobPost, ProcessingLog
12 | from ..processors.job_processor import JobProcessorService
13 | from ..services.scraper_service import scraper_service
   |                                        ^^^^^^^^^^^^^^^
14 |
15 | logger = logging.getLogger(__name__)
   |
help: Remove unused import: `..services.scraper_service.scraper_service`

E712 Avoid equality comparisons to `False`; use `not JobPost.is_active:` for false checks
   --> backend/app/services/data_processing_service.py:105:17
    |
103 |             old_jobs = db.query(JobPost).filter(
104 |                 JobPost.last_seen < cutoff_date,
105 |                 JobPost.is_active == False
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^
106 |             ).count()
    |
help: Replace with `not JobPost.is_active`

E712 Avoid equality comparisons to `False`; use `not JobPost.is_active:` for false checks
   --> backend/app/services/data_processing_service.py:111:21
    |
109 |                 db.query(JobPost).filter(
110 |                     JobPost.last_seen < cutoff_date,
111 |                     JobPost.is_active == False
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
112 |                 ).delete()
113 |                 db.commit()
    |
help: Replace with `not JobPost.is_active`

E712 Avoid equality comparisons to `True`; use `JobPost.is_active:` for truth checks
   --> backend/app/services/data_processing_service.py:134:17
    |
132 |             total_jobs = db.query(func.count(JobPost.id)).scalar()
133 |             active_jobs = db.query(func.count(JobPost.id)).filter(
134 |                 JobPost.is_active == True
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^
135 |             ).scalar()
    |
help: Replace with `JobPost.is_active`

E712 Avoid equality comparisons to `True`; use `JobPost.is_active:` for truth checks
   --> backend/app/services/data_processing_service.py:166:17
    |
164 |             new_jobs = db.query(JobPost).filter(
165 |                 JobPost.created_at > recent_cutoff,
166 |                 JobPost.is_active == True
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^
167 |             ).all()
    |
help: Replace with `JobPost.is_active`

F401 [*] `sqlalchemy.and_` imported but unused
  --> backend/app/services/deduplication_service.py:19:38
   |
17 | import logging
18 |
19 | from sqlalchemy import select, func, and_, or_
   |                                      ^^^^
20 | from sqlalchemy.ext.asyncio import AsyncSession
   |
help: Remove unused import

F401 [*] `sqlalchemy.or_` imported but unused
  --> backend/app/services/deduplication_service.py:19:44
   |
17 | import logging
18 |
19 | from sqlalchemy import select, func, and_, or_
   |                                            ^^^
20 | from sqlalchemy.ext.asyncio import AsyncSession
   |
help: Remove unused import

F401 [*] `..db.models.Location` imported but unused
  --> backend/app/services/deduplication_service.py:22:48
   |
20 | from sqlalchemy.ext.asyncio import AsyncSession
21 |
22 | from ..db.models import JobPost, Organization, Location
   |                                                ^^^^^^^^
23 | from ..ml.embeddings import generate_embeddings
   |
help: Remove unused import: `..db.models.Location`

F401 [*] `asyncio` imported but unused
 --> backend/app/services/linkedin_service.py:1:8
  |
1 | import asyncio
  |        ^^^^^^^
2 | import json
3 | from datetime import datetime, timedelta
  |
help: Remove unused import: `asyncio`

F401 [*] `json` imported but unused
 --> backend/app/services/linkedin_service.py:2:8
  |
1 | import asyncio
2 | import json
  |        ^^^^
3 | from datetime import datetime, timedelta
4 | from typing import Optional, Dict, List, Any
  |
help: Remove unused import: `json`

F401 [*] `typing.List` imported but unused
 --> backend/app/services/linkedin_service.py:4:36
  |
2 | import json
3 | from datetime import datetime, timedelta
4 | from typing import Optional, Dict, List, Any
  |                                    ^^^^
5 | from sqlalchemy.ext.asyncio import AsyncSession
6 | from sqlalchemy import select, update
  |
help: Remove unused import: `typing.List`

F401 [*] `sqlalchemy.update` imported but unused
 --> backend/app/services/linkedin_service.py:6:32
  |
4 | from typing import Optional, Dict, List, Any
5 | from sqlalchemy.ext.asyncio import AsyncSession
6 | from sqlalchemy import select, update
  |                                ^^^^^^
7 | from linkedin_api import Linkedin
8 | import httpx
  |
help: Remove unused import: `sqlalchemy.update`

F401 [*] `linkedin_api.Linkedin` imported but unused
 --> backend/app/services/linkedin_service.py:7:26
  |
5 | from sqlalchemy.ext.asyncio import AsyncSession
6 | from sqlalchemy import select, update
7 | from linkedin_api import Linkedin
  |                          ^^^^^^^^
8 | import httpx
9 | from requests_oauthlib import OAuth2Session
  |
help: Remove unused import: `linkedin_api.Linkedin`

F401 [*] `..db.database.get_db` imported but unused
  --> backend/app/services/linkedin_service.py:12:27
   |
11 | from ..core.config import settings
12 | from ..db.database import get_db
   |                           ^^^^^^
13 | from ..db.models import User, UserProfile
14 | from ..db.integration_models import LinkedInProfile, IntegrationActivityLog
   |
help: Remove unused import: `..db.database.get_db`

F401 [*] `..db.models.User` imported but unused
  --> backend/app/services/linkedin_service.py:13:25
   |
11 | from ..core.config import settings
12 | from ..db.database import get_db
13 | from ..db.models import User, UserProfile
   |                         ^^^^
14 | from ..db.integration_models import LinkedInProfile, IntegrationActivityLog
15 | import logging
   |
help: Remove unused import: `..db.models.User`

F841 Local variable `email_info` is assigned to but never used
   --> backend/app/services/linkedin_service.py:138:13
    |
136 |             # Extract profile information
137 |             profile_info = profile_data.get('profile', {})
138 |             email_info = profile_data.get('email', {})
    |             ^^^^^^^^^^
139 |             positions_info = profile_data.get('positions', {})
140 |             education_info = profile_data.get('education', {})
    |
help: Remove assignment to unused variable `email_info`

E712 Avoid equality comparisons to `True`; use `LinkedInProfile.auto_sync_enabled:` for truth checks
   --> backend/app/services/linkedin_service.py:373:21
    |
371 |                 select(LinkedInProfile).where(
372 |                     LinkedInProfile.sync_status == "active",
373 |                     LinkedInProfile.auto_sync_enabled == True
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
374 |                 )
375 |             )
    |
help: Replace with `LinkedInProfile.auto_sync_enabled`

F401 [*] `..db.models.MetricsDaily` imported but unused
 --> backend/app/services/lmi.py:3:86
  |
1 | from sqlalchemy.orm import Session
2 | from sqlalchemy import select, func, desc, and_, or_
3 | from ..db.models import JobPost, Organization, Location, TitleNorm, Skill, JobSkill, MetricsDaily
  |                                                                                      ^^^^^^^^^^^^
4 | from datetime import datetime, timedelta
5 | from collections import Counter
  |
help: Remove unused import: `..db.models.MetricsDaily`

F401 [*] `json` imported but unused
 --> backend/app/services/lmi.py:6:8
  |
4 | from datetime import datetime, timedelta
5 | from collections import Counter
6 | import json
  |        ^^^^
7 |
8 | def get_weekly_insights(db: Session, location: str | None = None) -> dict:
  |
help: Remove unused import: `json`

E712 Avoid equality comparisons to `True`; use `JobPost.attachment_flag:` for truth checks
   --> backend/app/services/lmi.py:259:19
    |
257 |     """Get companies that accept attachments/internships"""
258 |     
259 |     conditions = [JobPost.attachment_flag == True]
    |                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
260 |     
261 |     if location:
    |
help: Replace with `JobPost.attachment_flag`

E712 Avoid equality comparisons to `True`; use `JobPost.attachment_flag:` for truth checks
   --> backend/app/services/lmi.py:289:13
    |
287 |     recent_attachments = db.execute(
288 |         select(func.count(JobPost.id)).where(
289 |             JobPost.attachment_flag == True,
    |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
290 |             JobPost.first_seen >= datetime.utcnow() - timedelta(days=30)
291 |         )
    |
help: Replace with `JobPost.attachment_flag`

F401 [*] `typing.Optional` imported but unused
  --> backend/app/services/notification_service.py:8:32
   |
 6 | import logging
 7 | from datetime import datetime, timedelta
 8 | from typing import Dict, List, Optional, Set
   |                                ^^^^^^^^
 9 | from sqlalchemy.orm import Session
10 | from sqlalchemy import and_, or_
   |
help: Remove unused import

F401 [*] `typing.Set` imported but unused
  --> backend/app/services/notification_service.py:8:42
   |
 6 | import logging
 7 | from datetime import datetime, timedelta
 8 | from typing import Dict, List, Optional, Set
   |                                          ^^^
 9 | from sqlalchemy.orm import Session
10 | from sqlalchemy import and_, or_
   |
help: Remove unused import

F401 [*] `sqlalchemy.orm.Session` imported but unused
  --> backend/app/services/notification_service.py:9:28
   |
 7 | from datetime import datetime, timedelta
 8 | from typing import Dict, List, Optional, Set
 9 | from sqlalchemy.orm import Session
   |                            ^^^^^^^
10 | from sqlalchemy import and_, or_
11 | from ..db.database import SessionLocal
   |
help: Remove unused import: `sqlalchemy.orm.Session`

F401 [*] `sqlalchemy.and_` imported but unused
  --> backend/app/services/notification_service.py:10:24
   |
 8 | from typing import Dict, List, Optional, Set
 9 | from sqlalchemy.orm import Session
10 | from sqlalchemy import and_, or_
   |                        ^^^^
11 | from ..db.database import SessionLocal
12 | from ..db.models import JobPost, User, NotificationPreference, NotificationLog
   |
help: Remove unused import

F401 [*] `sqlalchemy.or_` imported but unused
  --> backend/app/services/notification_service.py:10:30
   |
 8 | from typing import Dict, List, Optional, Set
 9 | from sqlalchemy.orm import Session
10 | from sqlalchemy import and_, or_
   |                              ^^^
11 | from ..db.database import SessionLocal
12 | from ..db.models import JobPost, User, NotificationPreference, NotificationLog
   |
help: Remove unused import

F401 [*] `..db.models.JobPost` imported but unused
  --> backend/app/services/notification_service.py:12:25
   |
10 | from sqlalchemy import and_, or_
11 | from ..db.database import SessionLocal
12 | from ..db.models import JobPost, User, NotificationPreference, NotificationLog
   |                         ^^^^^^^
13 | from ..services.data_processing_service import data_processing_service
14 | from ..webhooks.whatsapp import send_whatsapp_message
   |
help: Remove unused import: `..db.models.JobPost`

E712 Avoid equality comparisons to `True`; use `NotificationPreference.enabled:` for truth checks
  --> backend/app/services/notification_service.py:66:17
   |
64 |             # Get users with notification preferences
65 |             users_with_prefs = db.query(User).join(NotificationPreference).filter(
66 |                 NotificationPreference.enabled == True
   |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
67 |             ).all()
   |
help: Replace with `NotificationPreference.enabled`

E712 Avoid equality comparisons to `True`; use `NotificationPreference.enabled:` for truth checks
   --> backend/app/services/notification_service.py:301:17
    |
300 |             total_users_with_prefs = db.query(func.count(User.id)).join(NotificationPreference).filter(
301 |                 NotificationPreference.enabled == True
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
302 |             ).scalar() or 0
    |
help: Replace with `NotificationPreference.enabled`

F401 [*] `hashlib` imported but unused
 --> backend/app/services/payment_service.py:7:8
  |
6 | import logging
7 | import hashlib
  |        ^^^^^^^
8 | import hmac
9 | import base64
  |
help: Remove unused import: `hashlib`

F401 [*] `hmac` imported but unused
  --> backend/app/services/payment_service.py:8:8
   |
 6 | import logging
 7 | import hashlib
 8 | import hmac
   |        ^^^^
 9 | import base64
10 | import json
   |
help: Remove unused import: `hmac`

F401 [*] `sqlalchemy.orm.Session` imported but unused
  --> backend/app/services/payment_service.py:13:28
   |
11 | from datetime import datetime, timedelta
12 | from typing import Dict, List, Optional
13 | from sqlalchemy.orm import Session
   |                            ^^^^^^^
14 | from ..db.database import SessionLocal
15 | from ..db.models import User, Subscription, Payment, PaymentMethod
   |
help: Remove unused import: `sqlalchemy.orm.Session`

F401 [*] `..db.models.User` imported but unused
  --> backend/app/services/payment_service.py:15:25
   |
13 | from sqlalchemy.orm import Session
14 | from ..db.database import SessionLocal
15 | from ..db.models import User, Subscription, Payment, PaymentMethod
   |                         ^^^^
16 | import requests
17 | import asyncio
   |
help: Remove unused import

F401 [*] `..db.models.PaymentMethod` imported but unused
  --> backend/app/services/payment_service.py:15:54
   |
13 | from sqlalchemy.orm import Session
14 | from ..db.database import SessionLocal
15 | from ..db.models import User, Subscription, Payment, PaymentMethod
   |                                                      ^^^^^^^^^^^^^
16 | import requests
17 | import asyncio
   |
help: Remove unused import

F401 [*] `asyncio` imported but unused
  --> backend/app/services/payment_service.py:17:8
   |
15 | from ..db.models import User, Subscription, Payment, PaymentMethod
16 | import requests
17 | import asyncio
   |        ^^^^^^^
18 |
19 | logger = logging.getLogger(__name__)
   |
help: Remove unused import: `asyncio`

F401 [*] `..db.models.UserProfile` imported but unused
  --> backend/app/services/personalized_recommendations.py:8:11
   |
 7 | from ..db.models import (
 8 |     User, UserProfile, JobPost, UserJobRecommendation, 
   |           ^^^^^^^^^^^
 9 |     SavedJob, JobApplication, SearchHistory, Organization, Location
10 | )
   |
help: Remove unused import: `..db.models.UserProfile`

E712 Avoid equality comparisons to `True`; use `UserJobRecommendation.is_active:` for truth checks
   --> backend/app/services/personalized_recommendations.py:169:21
    |
167 |                     UserJobRecommendation.user_id == user_id,
168 |                     UserJobRecommendation.recommended_at >= cutoff_date,
169 |                     UserJobRecommendation.is_active == True
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
170 |                 )
171 |             ).order_by(desc(UserJobRecommendation.match_score)).limit(limit)
    |
help: Replace with `UserJobRecommendation.is_active`

E712 Avoid equality comparisons to `True`; use `UserJobRecommendation.viewed:` for truth checks
   --> backend/app/services/personalized_recommendations.py:250:21
    |
248 |                 and_(
249 |                     UserJobRecommendation.user_id == user_id,
250 |                     UserJobRecommendation.viewed == True
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
251 |                 )
252 |             )
    |
help: Replace with `UserJobRecommendation.viewed`

E712 Avoid equality comparisons to `True`; use `UserJobRecommendation.clicked:` for truth checks
   --> backend/app/services/personalized_recommendations.py:258:21
    |
256 |                 and_(
257 |                     UserJobRecommendation.user_id == user_id,
258 |                     UserJobRecommendation.clicked == True
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
259 |                 )
260 |             )
    |
help: Replace with `UserJobRecommendation.clicked`

E712 Avoid equality comparisons to `True`; use `UserJobRecommendation.dismissed:` for truth checks
   --> backend/app/services/personalized_recommendations.py:378:21
    |
376 |                 and_(
377 |                     UserJobRecommendation.user_id == user_id,
378 |                     UserJobRecommendation.dismissed == True
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
379 |                 )
380 |             )
    |
help: Replace with `UserJobRecommendation.dismissed`

F401 [*] `..db.models.Organization` imported but unused
 --> backend/app/services/recommend.py:3:62
  |
1 | from sqlalchemy.orm import Session
2 | from sqlalchemy import select, func, desc
3 | from ..db.models import TitleNorm, JobPost, Skill, JobSkill, Organization
  |                                                              ^^^^^^^^^^^^
4 | from ..ml.embeddings import embed_text
5 | from ..normalization.titles import normalize_title, TITLE_ALIASES
  |
help: Remove unused import: `..db.models.Organization`

F401 [*] `..normalization.titles.TITLE_ALIASES` imported but unused
 --> backend/app/services/recommend.py:5:53
  |
3 | from ..db.models import TitleNorm, JobPost, Skill, JobSkill, Organization
4 | from ..ml.embeddings import embed_text
5 | from ..normalization.titles import normalize_title, TITLE_ALIASES
  |                                                     ^^^^^^^^^^^^^
6 | import numpy as np
7 | from collections import Counter
  |
help: Remove unused import: `..normalization.titles.TITLE_ALIASES`

F401 [*] `typing.Optional` imported but unused
  --> backend/app/services/scraper_service.py:9:37
   |
 7 | import sys
 8 | from pathlib import Path
 9 | from typing import List, Dict, Any, Optional
   |                                     ^^^^^^^^
10 | from datetime import datetime, timedelta
   |
help: Remove unused import: `typing.Optional`

F401 [*] `datetime.timedelta` imported but unused
  --> backend/app/services/scraper_service.py:10:32
   |
 8 | from pathlib import Path
 9 | from typing import List, Dict, Any, Optional
10 | from datetime import datetime, timedelta
   |                                ^^^^^^^^^
11 |
12 | # Ensure package root (app/) is on sys.path so `import scrapers.*` works
   |
help: Remove unused import: `datetime.timedelta`

F401 [*] `scrapers.main.scrape_site` imported but unused
  --> backend/app/services/scraper_service.py:15:27
   |
13 | sys.path.append(str(Path(__file__).parent.parent))
14 |
15 | from scrapers.main import scrape_site, scrape_all_sites
   |                           ^^^^^^^^^^^
16 | from scrapers.config import SITES, USE_POSTGRES
17 | from scrapers.postgres_db import PostgresJobDatabase
   |
help: Remove unused import

F401 [*] `scrapers.main.scrape_all_sites` imported but unused
  --> backend/app/services/scraper_service.py:15:40
   |
13 | sys.path.append(str(Path(__file__).parent.parent))
14 |
15 | from scrapers.main import scrape_site, scrape_all_sites
   |                                        ^^^^^^^^^^^^^^^^
16 | from scrapers.config import SITES, USE_POSTGRES
17 | from scrapers.postgres_db import PostgresJobDatabase
   |
help: Remove unused import

F401 [*] `sqlalchemy.orm.Session` imported but unused
  --> backend/app/services/scraper_service.py:20:28
   |
18 | from scrapers.migrate_to_postgres import JobDataMigrator
19 |
20 | from sqlalchemy.orm import Session
   |                            ^^^^^^^
21 | from ..db.database import get_db
22 | from ..db.models import JobPost, Organization
   |
help: Remove unused import: `sqlalchemy.orm.Session`

F401 [*] `..db.database.get_db` imported but unused
  --> backend/app/services/scraper_service.py:21:27
   |
20 | from sqlalchemy.orm import Session
21 | from ..db.database import get_db
   |                           ^^^^^^
22 | from ..db.models import JobPost, Organization
23 | from ..processors.job_processor import JobProcessorService
   |
help: Remove unused import: `..db.database.get_db`

F401 [*] `..db.models.JobPost` imported but unused
  --> backend/app/services/scraper_service.py:22:25
   |
20 | from sqlalchemy.orm import Session
21 | from ..db.database import get_db
22 | from ..db.models import JobPost, Organization
   |                         ^^^^^^^
23 | from ..processors.job_processor import JobProcessorService
   |
help: Remove unused import

F401 [*] `..db.models.Organization` imported but unused
  --> backend/app/services/scraper_service.py:22:34
   |
20 | from sqlalchemy.orm import Session
21 | from ..db.database import get_db
22 | from ..db.models import JobPost, Organization
   |                                  ^^^^^^^^^^^^
23 | from ..processors.job_processor import JobProcessorService
   |
help: Remove unused import

F401 [*] `sqlalchemy.func` imported but unused
 --> backend/app/services/search.py:2:32
  |
1 | from sqlalchemy.orm import Session
2 | from sqlalchemy import select, func, or_
  |                                ^^^^
3 | from ..db.models import JobPost, Organization, Location, TitleNorm, Skill, JobSkill
4 | from ..ml.embeddings import embed_text
  |
help: Remove unused import: `sqlalchemy.func`

F401 [*] `..db.models.Skill` imported but unused
 --> backend/app/services/search.py:3:69
  |
1 | from sqlalchemy.orm import Session
2 | from sqlalchemy import select, func, or_
3 | from ..db.models import JobPost, Organization, Location, TitleNorm, Skill, JobSkill
  |                                                                     ^^^^^
4 | from ..ml.embeddings import embed_text
5 | from ..normalization.titles import normalize_title, get_careers_for_degree, explain_title_match
  |
help: Remove unused import

F401 [*] `..db.models.JobSkill` imported but unused
 --> backend/app/services/search.py:3:76
  |
1 | from sqlalchemy.orm import Session
2 | from sqlalchemy import select, func, or_
3 | from ..db.models import JobPost, Organization, Location, TitleNorm, Skill, JobSkill
  |                                                                            ^^^^^^^^
4 | from ..ml.embeddings import embed_text
5 | from ..normalization.titles import normalize_title, get_careers_for_degree, explain_title_match
  |
help: Remove unused import

F401 [*] `..normalization.titles.explain_title_match` imported but unused
 --> backend/app/services/search.py:5:77
  |
3 | from ..db.models import JobPost, Organization, Location, TitleNorm, Skill, JobSkill
4 | from ..ml.embeddings import embed_text
5 | from ..normalization.titles import normalize_title, get_careers_for_degree, explain_title_match
  |                                                                             ^^^^^^^^^^^^^^^^^^^
6 | import numpy as np
7 | import re
  |
help: Remove unused import: `..normalization.titles.explain_title_match`

E722 Do not use bare `except`
  --> backend/app/services/search.py:96:13
   |
94 |                 job_embedding = eval(jp.embedding) if isinstance(jp.embedding, str) else jp.embedding
95 |                 similarity_score = cosine_similarity(query_embedding, job_embedding)
96 |             except:
   |             ^^^^^^
97 |                 similarity_score = 0.0
   |

F401 [*] `celery.current_task` imported but unused
 --> backend/app/tasks/gov_monitor_tasks.py:1:20
  |
1 | from celery import current_task
  |                    ^^^^^^^^^^^^
2 | import asyncio
3 | import logging
  |
help: Remove unused import: `celery.current_task`

F401 [*] `celery.current_task` imported but unused
 --> backend/app/tasks/processing_tasks.py:1:20
  |
1 | from celery import current_task
  |                    ^^^^^^^^^^^^
2 | import asyncio
3 | import logging
  |
help: Remove unused import: `celery.current_task`

F401 [*] `..services.data_processing_service.data_processing_service` imported but unused
  --> backend/app/tasks/processing_tasks.py:10:48
   |
 8 | from ..db.database import get_db, SessionLocal
 9 | from ..services.automated_workflow_service import automated_workflow_service
10 | from ..services.data_processing_service import data_processing_service
   |                                                ^^^^^^^^^^^^^^^^^^^^^^^
11 | from ..services.email_service import send_email
12 | from ..processors.job_processor import JobProcessor
   |
help: Remove unused import: `..services.data_processing_service.data_processing_service`

F841 Local variable `processed_job` is assigned to but never used
   --> backend/app/tasks/processing_tasks.py:272:21
    |
270 |                     }
271 |                     
272 |                     processed_job = await job_processor.process_job(job_data)
    |                     ^^^^^^^^^^^^^
273 |                     
274 |                     # Update job with processed data
    |
help: Remove assignment to unused variable `processed_job`

F401 [*] `..db.models.JobPost` imported but unused
   --> backend/app/tasks/processing_tasks.py:680:39
    |
678 |     """Process job alerts synchronously (Celery-compatible)"""
679 |     from sqlalchemy import select, and_
680 |     from ..db.models import JobAlert, JobPost, User, UserNotification
    |                                       ^^^^^^^
681 |     from ..services.search import search_jobs
    |
help: Remove unused import: `..db.models.JobPost`

E712 Avoid equality comparisons to `True`; use `JobAlert.is_active:` for truth checks
   --> backend/app/tasks/processing_tasks.py:688:17
    |
686 |         stmt = select(JobAlert).where(
687 |             and_(
688 |                 JobAlert.is_active == True,
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^
689 |                 JobAlert.frequency == frequency
690 |             )
    |
help: Replace with `JobAlert.is_active`

F541 [*] f-string without any placeholders
   --> backend/app/tasks/processing_tasks.py:819:12
    |
817 |     subject = f"🎯 {len(jobs)} new jobs match your '{alert_name}' alert"
818 |
819 |     body = f"Hi there,\n\n"
    |            ^^^^^^^^^^^^^^^^
820 |     body += f"Great news! We found {len(jobs)} new job(s) matching your '{alert_name}' job alert.\n\n"
821 |     body += "Here are the top matches:\n\n"
    |
help: Remove extraneous `f` prefix

F401 [*] `celery.current_task` imported but unused
 --> backend/app/tasks/scraper_tasks.py:1:20
  |
1 | from celery import current_task
  |                    ^^^^^^^^^^^^
2 | import asyncio
3 | import logging
  |
help: Remove unused import: `celery.current_task`

F401 [*] `typing.List` imported but unused
 --> backend/app/tasks/scraper_tasks.py:4:31
  |
2 | import asyncio
3 | import logging
4 | from typing import Dict, Any, List
  |                               ^^^^
5 |
6 | from ..core.celery_app import celery_app
  |
help: Remove unused import: `typing.List`

F541 [*] f-string without any placeholders
   --> backend/app/tasks/scraper_tasks.py:209:27
    |
207 |             state='SUCCESS',
208 |             meta={
209 |                 'status': f'Cleanup completed successfully',
    |                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
210 |                 'progress': 100,
211 |                 'result': result
    |
help: Remove extraneous `f` prefix

F401 [*] `celery.current_task` imported but unused
 --> backend/app/tasks/workflow_tasks.py:1:20
  |
1 | from celery import current_task
  |                    ^^^^^^^^^^^^
2 | from sqlalchemy.ext.asyncio import AsyncSession
3 | import asyncio
  |
help: Remove unused import: `celery.current_task`

F401 [*] `sqlalchemy.ext.asyncio.AsyncSession` imported but unused
 --> backend/app/tasks/workflow_tasks.py:2:36
  |
1 | from celery import current_task
2 | from sqlalchemy.ext.asyncio import AsyncSession
  |                                    ^^^^^^^^^^^^
3 | import asyncio
4 | import logging
  |
help: Remove unused import: `sqlalchemy.ext.asyncio.AsyncSession`

F401 [*] `datetime.datetime` imported but unused
 --> backend/app/tasks/workflow_tasks.py:5:22
  |
3 | import asyncio
4 | import logging
5 | from datetime import datetime
  |                      ^^^^^^^^
6 | from typing import Dict, Any
  |
help: Remove unused import: `datetime.datetime`

F401 [*] `..normalization.titles.normalize_title` imported but unused
 --> backend/app/webhooks/whatsapp.py:5:60
  |
3 | from ..services.recommend import transitions_for
4 | from ..services.lmi import get_weekly_insights, get_attachment_companies
5 | from ..normalization.titles import get_careers_for_degree, normalize_title
  |                                                            ^^^^^^^^^^^^^^^
6 | from ..db.database import get_db
7 | from ..core.config import settings
  |
help: Remove unused import: `..normalization.titles.normalize_title`

F841 Local variable `from_` is assigned to but never used
   --> backend/app/webhooks/whatsapp.py:146:5
    |
144 |     form = await request.form()
145 |     body = (form.get("Body") or "").strip()
146 |     from_ = form.get("From")
    |     ^^^^^
147 |     
148 |     if not body:
    |
help: Remove assignment to unused variable `from_`

F541 [*] f-string without any placeholders
   --> backend/app/webhooks/whatsapp.py:183:23
    |
182 |             if not companies["companies_with_attachments"]:
183 |                 msg = f"🎯 No attachment programs found"
    |                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
184 |                 if location:
185 |                     msg += f" in {location}"
    |
help: Remove extraneous `f` prefix

F541 [*] f-string without any placeholders
   --> backend/app/webhooks/whatsapp.py:188:23
    |
186 |                 msg += ". Try broader search or check back later."
187 |             else:
188 |                 msg = f"🎯 *Attachment Opportunities"
    |                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
189 |                 if location:
190 |                     msg += f" in {location}"
    |
help: Remove extraneous `f` prefix

F541 [*] f-string without any placeholders
   --> backend/app/webhooks/whatsapp.py:204:19
    |
202 |             insights = get_weekly_insights(db, location=location)
203 |             
204 |             msg = f"📊 *Market Insights"
    |                   ^^^^^^^^^^^^^^^^^^^^^^
205 |             if location:
206 |                 msg += f" - {location}"
    |
help: Remove extraneous `f` prefix

F541 [*] f-string without any placeholders
   --> backend/app/webhooks/whatsapp.py:207:20
    |
205 |             if location:
206 |                 msg += f" - {location}"
207 |             msg += f":*\n\n"
    |                    ^^^^^^^^^
208 |             
209 |             msg += f"📈 {insights['total_postings']} new jobs this week"
    |
help: Remove extraneous `f` prefix

F541 [*] f-string without any placeholders
   --> backend/app/webhooks/whatsapp.py:255:23
    |
253 | …         msg = "🔍 No matches found. Try:\n• 'I studied [your degree]'\n• 'transition [current role]'\n• 'attachments [location]'"
254 | …     else:
255 | …         msg = f"🔍 *Job Matches:*\n\n"
    |                 ^^^^^^^^^^^^^^^^^^^^^^^^
256 | …         for i, job in enumerate(results[:3], 1):
257 | …             if job.get("is_suggestion"):
    |
help: Remove extraneous `f` prefix

F401 [*] `typing.Tuple` imported but unused
  --> backend/scripts/backfill_brightermonday_metadata.py:19:30
   |
17 | import sys
18 | from pathlib import Path
19 | from typing import Optional, Tuple
   |                              ^^^^^
20 |
21 | # Add parent directory to path for imports
   |
help: Remove unused import: `typing.Tuple`

F841 Local variable `updates_made` is assigned to but never used
   --> backend/scripts/backfill_brightermonday_metadata.py:180:25
    |
178 |                             db.flush()
179 |                         job.location_id = loc.id
180 |                         updates_made = True
    |                         ^^^^^^^^^^^^
181 |                     location_updated += 1
    |
help: Remove assignment to unused variable `updates_made`

F541 [*] f-string without any placeholders
   --> backend/scripts/backfill_brightermonday_metadata.py:193:19
    |
191 |         # Show top companies found
192 |         if companies_found:
193 |             print(f"\nTop companies found:")
    |                   ^^^^^^^^^^^^^^^^^^^^^^^^^
194 |             for company, count in sorted(companies_found.items(), key=lambda x: -x[1])[:10]:
195 |                 print(f"  {company}: {count}")
    |
help: Remove extraneous `f` prefix

F541 [*] f-string without any placeholders
   --> backend/scripts/backfill_brightermonday_metadata.py:199:19
    |
197 |         # Show locations found
198 |         if locations_found:
199 |             print(f"\nLocations found:")
    |                   ^^^^^^^^^^^^^^^^^^^^^
200 |             for loc, count in sorted(locations_found.items(), key=lambda x: -x[1]):
201 |                 print(f"  {loc}: {count}")
    |
help: Remove extraneous `f` prefix

F541 [*] f-string without any placeholders
   --> backend/scripts/backfill_brightermonday_metadata.py:214:15
    |
212 |         total_bm = db.query(JobPost).filter(JobPost.source == 'brightermonday').count()
213 |
214 |         print(f"\nBrighterMonday coverage:")
    |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
215 |         print(f"  With organization: {jobs_with_org}/{total_bm} ({jobs_with_org/total_bm*100:.1f}%)")
216 |         print(f"  With location: {jobs_with_loc}/{total_bm} ({jobs_with_loc/total_bm*100:.1f}%)")
    |
help: Remove extraneous `f` prefix

F841 Local variable `text_lower` is assigned to but never used
  --> backend/scripts/backfill_salary_data.py:39:5
   |
37 |     MAX_SALARY_USD = 500000  # Maximum reasonable USD salary
38 |
39 |     text_lower = text.lower()
   |     ^^^^^^^^^^
40 |
41 |     # Salary patterns for Kenyan job postings - ordered by specificity
   |
help: Remove assignment to unused variable `text_lower`

F841 Local variable `skipped_count` is assigned to but never used
   --> backend/scripts/backfill_seniority.py:153:9
    |
152 |         updated_count = 0
153 |         skipped_count = 0
    |         ^^^^^^^^^^^^^
154 |         seniority_counts = {'entry': 0, 'mid': 0, 'senior': 0, 'management': 0, 'executive': 0}
    |
help: Remove assignment to unused variable `skipped_count`

F541 [*] f-string without any placeholders
   --> backend/scripts/backfill_seniority.py:174:15
    |
172 |             print(f"\n[DRY RUN] Would update {sum(seniority_counts.values())} jobs")
173 |
174 |         print(f"\nSeniority distribution:")
    |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
175 |         for level, count in sorted(seniority_counts.items(), key=lambda x: -x[1]):
176 |             if count > 0:
    |
help: Remove extraneous `f` prefix

E402 Module level import not at top of file
  --> backend/scripts/run_brightermonday_ingestion.py:23:1
   |
22 | # Load environment variables
23 | from dotenv import load_dotenv
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
24 | load_dotenv()
   |

E402 Module level import not at top of file
  --> backend/scripts/run_brightermonday_ingestion.py:29:1
   |
27 | os.environ.setdefault("DATABASE_URL", "sqlite:///var/nextstep.sqlite")
28 |
29 | import requests
   | ^^^^^^^^^^^^^^^
30 | from bs4 import BeautifulSoup
31 | from app.processors.job_processor import JobProcessor
   |

E402 Module level import not at top of file
  --> backend/scripts/run_brightermonday_ingestion.py:30:1
   |
29 | import requests
30 | from bs4 import BeautifulSoup
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
31 | from app.processors.job_processor import JobProcessor
   |

E402 Module level import not at top of file
  --> backend/scripts/run_brightermonday_ingestion.py:31:1
   |
29 | import requests
30 | from bs4 import BeautifulSoup
31 | from app.processors.job_processor import JobProcessor
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
32 |
33 | # Set up logging
   |

F541 [*] f-string without any placeholders
   --> backend/scripts/run_brightermonday_ingestion.py:129:17
    |
128 |     logger.info(f"\n{'='*60}")
129 |     logger.info(f"INGESTION COMPLETE")
    |                 ^^^^^^^^^^^^^^^^^^^^^
130 |     logger.info(f"{'='*60}")
131 |     logger.info(f"Total scraped: {len(unique_jobs)}")
    |
help: Remove extraneous `f` prefix

E402 Module level import not at top of file
  --> backend/scripts/run_jobwebkenya_ingestion.py:23:1
   |
22 | # Load environment variables
23 | from dotenv import load_dotenv
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
24 | load_dotenv()
   |

E402 Module level import not at top of file
  --> backend/scripts/run_jobwebkenya_ingestion.py:29:1
   |
27 | os.environ.setdefault("DATABASE_URL", "sqlite:///var/nextstep.sqlite")
28 |
29 | import requests
   | ^^^^^^^^^^^^^^^
30 | from bs4 import BeautifulSoup
31 | from app.processors.job_processor import JobProcessor
   |

E402 Module level import not at top of file
  --> backend/scripts/run_jobwebkenya_ingestion.py:30:1
   |
29 | import requests
30 | from bs4 import BeautifulSoup
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
31 | from app.processors.job_processor import JobProcessor
   |

E402 Module level import not at top of file
  --> backend/scripts/run_jobwebkenya_ingestion.py:31:1
   |
29 | import requests
30 | from bs4 import BeautifulSoup
31 | from app.processors.job_processor import JobProcessor
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
32 |
33 | # Set up logging
   |

F541 [*] f-string without any placeholders
   --> backend/scripts/run_jobwebkenya_ingestion.py:151:17
    |
150 |     logger.info(f"\n{'='*60}")
151 |     logger.info(f"INGESTION COMPLETE")
    |                 ^^^^^^^^^^^^^^^^^^^^^
152 |     logger.info(f"{'='*60}")
153 |     logger.info(f"Total scraped: {len(unique_jobs)}")
    |
help: Remove extraneous `f` prefix

E402 Module level import not at top of file
  --> backend/scripts/run_myjobmag_ingestion.py:23:1
   |
22 | # Load environment variables
23 | from dotenv import load_dotenv
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
24 | load_dotenv()
   |

E402 Module level import not at top of file
  --> backend/scripts/run_myjobmag_ingestion.py:29:1
   |
27 | os.environ.setdefault("DATABASE_URL", "sqlite:///var/nextstep.sqlite")
28 |
29 | import requests
   | ^^^^^^^^^^^^^^^
30 | from bs4 import BeautifulSoup
31 | from app.processors.job_processor import JobProcessor
   |

E402 Module level import not at top of file
  --> backend/scripts/run_myjobmag_ingestion.py:30:1
   |
29 | import requests
30 | from bs4 import BeautifulSoup
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
31 | from app.processors.job_processor import JobProcessor
   |

E402 Module level import not at top of file
  --> backend/scripts/run_myjobmag_ingestion.py:31:1
   |
29 | import requests
30 | from bs4 import BeautifulSoup
31 | from app.processors.job_processor import JobProcessor
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
32 |
33 | # Set up logging
   |

F541 [*] f-string without any placeholders
   --> backend/scripts/run_myjobmag_ingestion.py:150:17
    |
149 |     logger.info(f"\n{'='*60}")
150 |     logger.info(f"INGESTION COMPLETE")
    |                 ^^^^^^^^^^^^^^^^^^^^^
151 |     logger.info(f"{'='*60}")
152 |     logger.info(f"Total scraped: {len(unique_jobs)}")
    |
help: Remove extraneous `f` prefix

F401 [*] `typing.List` imported but unused
 --> backend/sentence_transformers.py:2:30
  |
1 | import os
2 | from typing import Iterable, List
  |                              ^^^^
3 |
4 | def _embedding_dim() -> int:
  |
help: Remove unused import: `typing.List`

F401 [*] `pytest` imported but unused
 --> backend/test_automated_workflow.py:5:8
  |
3 | """
4 | import asyncio
5 | import pytest
  |        ^^^^^^
6 | from sqlalchemy.ext.asyncio import AsyncSession
7 | from app.db.database import get_db
  |
help: Remove unused import: `pytest`

F401 [*] `sqlalchemy.ext.asyncio.AsyncSession` imported but unused
 --> backend/test_automated_workflow.py:6:36
  |
4 | import asyncio
5 | import pytest
6 | from sqlalchemy.ext.asyncio import AsyncSession
  |                                    ^^^^^^^^^^^^
7 | from app.db.database import get_db
8 | from app.services.automated_workflow_service import automated_workflow_service
  |
help: Remove unused import: `sqlalchemy.ext.asyncio.AsyncSession`

F401 [*] `app.tasks.workflow_tasks.run_daily_workflow` imported but unused
  --> backend/test_automated_workflow.py:9:38
   |
 7 | from app.db.database import get_db
 8 | from app.services.automated_workflow_service import automated_workflow_service
 9 | from app.tasks.workflow_tasks import run_daily_workflow
   |                                      ^^^^^^^^^^^^^^^^^^
10 | from app.tasks.scraper_tasks import test_all_scrapers
11 | from app.tasks.processing_tasks import process_raw_jobs
   |
help: Remove unused import: `app.tasks.workflow_tasks.run_daily_workflow`

F401 [*] `app.tasks.scraper_tasks.test_all_scrapers` imported but unused
  --> backend/test_automated_workflow.py:10:37
   |
 8 | from app.services.automated_workflow_service import automated_workflow_service
 9 | from app.tasks.workflow_tasks import run_daily_workflow
10 | from app.tasks.scraper_tasks import test_all_scrapers
   |                                     ^^^^^^^^^^^^^^^^^
11 | from app.tasks.processing_tasks import process_raw_jobs
12 | import logging
   |
help: Remove unused import: `app.tasks.scraper_tasks.test_all_scrapers`

F401 [*] `app.tasks.processing_tasks.process_raw_jobs` imported but unused
  --> backend/test_automated_workflow.py:11:40
   |
 9 | from app.tasks.workflow_tasks import run_daily_workflow
10 | from app.tasks.scraper_tasks import test_all_scrapers
11 | from app.tasks.processing_tasks import process_raw_jobs
   |                                        ^^^^^^^^^^^^^^^^
12 | import logging
   |
help: Remove unused import: `app.tasks.processing_tasks.process_raw_jobs`

F401 [*] `os` imported but unused
 --> backend/test_integration.py:7:8
  |
6 | import sys
7 | import os
  |        ^^
8 | from pathlib import Path
  |
help: Remove unused import: `os`

F401 [*] `app.scrapers.postgres_db.PostgresJobDatabase` imported but unused
  --> backend/test_integration.py:22:46
   |
20 |         print(f"✅ PostgreSQL enabled: {USE_POSTGRES}")
21 |         
22 |         from app.scrapers.postgres_db import PostgresJobDatabase
   |                                              ^^^^^^^^^^^^^^^^^^^
23 |         print("✅ PostgreSQL database adapter imported")
   |
help: Remove unused import: `app.scrapers.postgres_db.PostgresJobDatabase`

F401 [*] `app.scrapers.migrate_to_postgres.JobDataMigrator` imported but unused
  --> backend/test_integration.py:25:54
   |
23 |         print("✅ PostgreSQL database adapter imported")
24 |         
25 |         from app.scrapers.migrate_to_postgres import JobDataMigrator
   |                                                      ^^^^^^^^^^^^^^^
26 |         print("✅ Migration script imported")
   |
help: Remove unused import: `app.scrapers.migrate_to_postgres.JobDataMigrator`

F401 [*] `app.services.scraper_service.scraper_service` imported but unused
  --> backend/test_integration.py:28:50
   |
26 |         print("✅ Migration script imported")
27 |         
28 |         from app.services.scraper_service import scraper_service
   |                                                  ^^^^^^^^^^^^^^^
29 |         print("✅ Scraper service imported")
   |
help: Remove unused import: `app.services.scraper_service.scraper_service`

F401 [*] `app.db.models.Organization` imported but unused
   --> backend/test_integration.py:102:44
    |
101 |     try:
102 |         from app.db.models import JobPost, Organization, Location
    |                                            ^^^^^^^^^^^^
103 |         print("✅ Database models imported successfully")
    |
help: Remove unused import

F401 [*] `app.db.models.Location` imported but unused
   --> backend/test_integration.py:102:58
    |
101 |     try:
102 |         from app.db.models import JobPost, Organization, Location
    |                                                          ^^^^^^^^
103 |         print("✅ Database models imported successfully")
    |
help: Remove unused import

F401 [*] `os` imported but unused
  --> backend/test_jobwebkenya_pipeline.py:9:8
   |
 7 | import logging
 8 | import sys
 9 | import os
   |        ^^
10 | from pathlib import Path
   |
help: Remove unused import: `os`

E402 Module level import not at top of file
  --> backend/test_jobwebkenya_pipeline.py:20:1
   |
18 | sys.path.insert(0, str(backend_path))
19 |
20 | from app.scrapers.spiders.jobwebkenya import JobScraper as JobWebKenyaScraper
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
21 | from app.processors.job_processor import JobProcessor
   |

E402 Module level import not at top of file
  --> backend/test_jobwebkenya_pipeline.py:21:1
   |
20 | from app.scrapers.spiders.jobwebkenya import JobScraper as JobWebKenyaScraper
21 | from app.processors.job_processor import JobProcessor
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
22 |
23 | # Set up logging
   |

F541 [*] f-string without any placeholders
  --> backend/test_jobwebkenya_pipeline.py:57:26
   |
55 |             logger.info(f"✅ Success - ID: {job_id}")
56 |         else:
57 |             logger.error(f"❌ Failed")
   |                          ^^^^^^^^^^^^
58 |     
59 |     logger.info(f"JobWebKenya pipeline result: {success_count}/3 jobs processed successfully")
   |
help: Remove extraneous `f` prefix

F401 [*] `os` imported but unused
  --> backend/test_pipeline_bridge.py:9:8
   |
 7 | import logging
 8 | import sys
 9 | import os
   |        ^^
10 | from pathlib import Path
   |
help: Remove unused import: `os`

E402 Module level import not at top of file
  --> backend/test_pipeline_bridge.py:20:1
   |
18 | sys.path.insert(0, str(backend_path))
19 |
20 | from app.scrapers.spiders.myjobmag import JobScraper as MyJobMagScraper
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
21 | from app.processors.job_processor import JobProcessor
   |

E402 Module level import not at top of file
  --> backend/test_pipeline_bridge.py:21:1
   |
20 | from app.scrapers.spiders.myjobmag import JobScraper as MyJobMagScraper
21 | from app.processors.job_processor import JobProcessor
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
22 |
23 | # Set up logging
   |

F541 [*] f-string without any placeholders
  --> backend/test_pipeline_bridge.py:83:26
   |
81 |             logger.info(f"✅ Success - ID: {job_id}")
82 |         else:
83 |             logger.error(f"❌ Failed")
   |                          ^^^^^^^^^^^^
84 |     
85 |     logger.info(f"\nBatch Result: {success_count}/{total_count} jobs processed successfully")
   |
help: Remove extraneous `f` prefix

F541 [*] f-string without any placeholders
  --> backend/test_processors.py:42:27
   |
41 |                 if data:
42 |                     print(f"✓ Successfully extracted data")
   |                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
43 |                     print(f"  Title: {data.get('title', 'N/A')}")
44 |                     print(f"  Company: {data.get('company', 'N/A')}")
   |
help: Remove extraneous `f` prefix

F541 [*] f-string without any placeholders
   --> backend/test_processors.py:182:15
    |
180 |     try:
181 |         stats = service.get_stats()
182 |         print(f"\nProcessing Statistics:")
    |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^
183 |         print(f"  Total jobs: {stats.get('total_jobs', 0)}")
184 |         print(f"  Jobs by source: {stats.get('jobs_by_source', {})}")
    |
help: Remove extraneous `f` prefix

F401 [*] `app.db.models.JobPost` imported but unused
  --> backend/test_structured_extraction.py:15:27
   |
13 | from app.processors.job_extractor import JobDataExtractor
14 | from app.db.database import SessionLocal
15 | from app.db.models import JobPost
   |                           ^^^^^^^
16 | from sqlalchemy import text
   |
help: Remove unused import: `app.db.models.JobPost`

F541 [*] f-string without any placeholders
  --> backend/test_structured_extraction.py:44:23
   |
42 |                 quality_score = (filled_fields / len(fields)) * 100
43 |                 
44 |                 print(f"✅ Extraction successful")
   |                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^
45 |                 print(f"   Title: {data.get('title', 'NOT FOUND')[:50]}...")
46 |                 print(f"   Company: {data.get('company', 'NOT FOUND')[:50]}...")
   |
help: Remove extraneous `f` prefix

F541 [*] f-string without any placeholders
  --> backend/test_structured_extraction.py:62:23
   |
60 |                 })
61 |             else:
62 |                 print(f"❌ Extraction failed")
   |                       ^^^^^^^^^^^^^^^^^^^^^^^
63 |                 results.append({
64 |                     'source': job['source'],
   |
help: Remove extraneous `f` prefix

F541 [*] f-string without any placeholders
  --> backend/test_structured_extraction.py:72:11
   |
71 |     # Summary
72 |     print(f"\n=== EXTRACTION SUMMARY ===")
   |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
73 |     successful_tests = sum(1 for r in results if r['success'])
74 |     avg_quality = sum(r['quality_score'] for r in results) / len(results) if results else 0
   |
help: Remove extraneous `f` prefix

F541 [*] f-string without any placeholders
  --> backend/test_structured_extraction.py:81:11
   |
80 |     # Check current database quality
81 |     print(f"\n=== DATABASE QUALITY CHECK ===")
   |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
82 |     db = SessionLocal()
83 |     try:
   |
help: Remove extraneous `f` prefix

F541 [*] f-string without any placeholders
   --> backend/test_structured_extraction.py:105:11
    |
104 |     # Recommendations
105 |     print(f"\n=== RECOMMENDATIONS ===")
    |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
106 |     if avg_quality >= 80:
107 |         print("✅ Excellent extraction quality achieved!")
    |
help: Remove extraneous `f` prefix

F401 [*] `os` imported but unused
  --> backend/test_unified_ingestion.py:10:8
   |
 8 | import logging
 9 | import sys
10 | import os
   |        ^^
11 | from pathlib import Path
12 | from datetime import datetime, timedelta
   |
help: Remove unused import: `os`

F401 [*] `datetime.timedelta` imported but unused
  --> backend/test_unified_ingestion.py:12:32
   |
10 | import os
11 | from pathlib import Path
12 | from datetime import datetime, timedelta
   |                                ^^^^^^^^^
13 |
14 | # Load environment variables from .env file
   |
help: Remove unused import: `datetime.timedelta`

E402 Module level import not at top of file
  --> backend/test_unified_ingestion.py:22:1
   |
20 | sys.path.insert(0, str(backend_path))
21 |
22 | from app.scrapers.spiders.myjobmag import JobScraper as MyJobMagScraper
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
23 | from app.scrapers.spiders.jobwebkenya import JobScraper as JobWebKenyaScraper
24 | from app.processors.job_processor import JobProcessor
   |

E402 Module level import not at top of file
  --> backend/test_unified_ingestion.py:23:1
   |
22 | from app.scrapers.spiders.myjobmag import JobScraper as MyJobMagScraper
23 | from app.scrapers.spiders.jobwebkenya import JobScraper as JobWebKenyaScraper
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
24 | from app.processors.job_processor import JobProcessor
25 | from app.db.database import SessionLocal
   |

E402 Module level import not at top of file
  --> backend/test_unified_ingestion.py:24:1
   |
22 | from app.scrapers.spiders.myjobmag import JobScraper as MyJobMagScraper
23 | from app.scrapers.spiders.jobwebkenya import JobScraper as JobWebKenyaScraper
24 | from app.processors.job_processor import JobProcessor
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
25 | from app.db.database import SessionLocal
   |

E402 Module level import not at top of file
  --> backend/test_unified_ingestion.py:25:1
   |
23 | from app.scrapers.spiders.jobwebkenya import JobScraper as JobWebKenyaScraper
24 | from app.processors.job_processor import JobProcessor
25 | from app.db.database import SessionLocal
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
26 |
27 | # Set up logging
   |

F401 [*] `app.db.database.SessionLocal` imported but unused
  --> backend/test_unified_ingestion.py:25:29
   |
23 | from app.scrapers.spiders.jobwebkenya import JobScraper as JobWebKenyaScraper
24 | from app.processors.job_processor import JobProcessor
25 | from app.db.database import SessionLocal
   |                             ^^^^^^^^^^^^
26 |
27 | # Set up logging
   |
help: Remove unused import: `app.db.database.SessionLocal`

F841 Local variable `max_source_jobs` is assigned to but never used
   --> backend/test_unified_ingestion.py:123:9
    |
121 |         # Check P0 success criteria
122 |         sources_working = sum(1 for count in results.values() if count > 0)
123 |         max_source_jobs = max(results.values()) if results.values() else 0
    |         ^^^^^^^^^^^^^^^
124 |         
125 |         logger.info("\n🎯 P0 Success Criteria Check:")
    |
help: Remove assignment to unused variable `max_source_jobs`

F401 [*] `asyncio` imported but unused
 --> scripts/repo_smoke_test.py:7:8
  |
5 | """
6 |
7 | import asyncio
  |        ^^^^^^^
8 | import logging
9 | import sys
  |
help: Remove unused import: `asyncio`

F401 [*] `os` imported but unused
  --> scripts/repo_smoke_test.py:10:8
   |
 8 | import logging
 9 | import sys
10 | import os
   |        ^^
11 | from pathlib import Path
   |
help: Remove unused import: `os`

E402 Module level import not at top of file
  --> scripts/repo_smoke_test.py:21:1
   |
19 | sys.path.insert(0, str(backend_path))
20 |
21 | from app.db.database import SessionLocal, engine
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
22 | from sqlalchemy import text
   |

F401 [*] `app.db.database.SessionLocal` imported but unused
  --> scripts/repo_smoke_test.py:21:29
   |
19 | sys.path.insert(0, str(backend_path))
20 |
21 | from app.db.database import SessionLocal, engine
   |                             ^^^^^^^^^^^^
22 | from sqlalchemy import text
   |
help: Remove unused import: `app.db.database.SessionLocal`

E402 Module level import not at top of file
  --> scripts/repo_smoke_test.py:22:1
   |
21 | from app.db.database import SessionLocal, engine
22 | from sqlalchemy import text
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^
23 |
24 | # Set up logging
   |

E401 [*] Multiple imports on one line
 --> scripts/scan_repo.py:1:1
  |
1 | import os, subprocess, sqlite3, datetime
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
2 | from pathlib import Path
  |
help: Split imports

Found 286 errors.
[*] 204 fixable with the `--fix` option (29 hidden fixes can be enabled with the `--unsafe-fixes` option).
```


## Pytest

```text
(rc=1)
......EEEsssss.....sssss..ss....                                         [100%]
==================================== ERRORS ====================================
______________________ ERROR at setup of test_api_health _______________________
file /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/scripts/smoke_test.py, line 134
  def test_api_health(api_url: str):
E       fixture 'api_url' not found
>       available fixtures: _session_event_loop, anyio_backend, anyio_backend_name, anyio_backend_options, backend/app/webhooks::<event_loop>, backend/scripts/smoke_test.py::<event_loop>, cache, capfd, capfdbinary, caplog, capsys, capsysbinary, doctest_namespace, event_loop, event_loop_policy, free_tcp_port, free_tcp_port_factory, free_udp_port, free_udp_port_factory, monkeypatch, pytestconfig, record_property, record_testsuite_property, record_xml_attribute, recwarn, tmp_path, tmp_path_factory, tmpdir, tmpdir_factory, unused_tcp_port, unused_tcp_port_factory, unused_udp_port, unused_udp_port_factory
>       use 'pytest --fixtures [testpath]' for help on them.

/Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/scripts/smoke_test.py:134
______________________ ERROR at setup of test_api_search _______________________
file /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/scripts/smoke_test.py, line 151
  def test_api_search(api_url: str):
E       fixture 'api_url' not found
>       available fixtures: _session_event_loop, anyio_backend, anyio_backend_name, anyio_backend_options, backend/app/webhooks::<event_loop>, backend/scripts/smoke_test.py::<event_loop>, cache, capfd, capfdbinary, caplog, capsys, capsysbinary, doctest_namespace, event_loop, event_loop_policy, free_tcp_port, free_tcp_port_factory, free_udp_port, free_udp_port_factory, monkeypatch, pytestconfig, record_property, record_testsuite_property, record_xml_attribute, recwarn, tmp_path, tmp_path_factory, tmpdir, tmpdir_factory, unused_tcp_port, unused_tcp_port_factory, unused_udp_port, unused_udp_port_factory
>       use 'pytest --fixtures [testpath]' for help on them.

/Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/scripts/smoke_test.py:151
_________________ ERROR at setup of test_api_ingestion_status __________________
file /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/scripts/smoke_test.py, line 170
  def test_api_ingestion_status(api_url: str):
E       fixture 'api_url' not found
>       available fixtures: _session_event_loop, anyio_backend, anyio_backend_name, anyio_backend_options, backend/app/webhooks::<event_loop>, backend/scripts/smoke_test.py::<event_loop>, cache, capfd, capfdbinary, caplog, capsys, capsysbinary, doctest_namespace, event_loop, event_loop_policy, free_tcp_port, free_tcp_port_factory, free_udp_port, free_udp_port_factory, monkeypatch, pytestconfig, record_property, record_testsuite_property, record_xml_attribute, recwarn, tmp_path, tmp_path_factory, tmpdir, tmpdir_factory, unused_tcp_port, unused_tcp_port_factory, unused_udp_port, unused_udp_port_factory
>       use 'pytest --fixtures [testpath]' for help on them.

/Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/scripts/smoke_test.py:170
=============================== warnings summary ===============================
backend/scripts/smoke_test.py::test_database_connection
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but backend/scripts/smoke_test.py::test_database_connection returned (False, 'Database connection failed: (psycopg2.OperationalError) could not translate host name "postgres" to address: nodename nor servname provided, or not known\n\n(Background on this error at: https://sqlalche.me/e/20/e3q8)'), which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

backend/scripts/smoke_test.py::test_job_count
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but backend/scripts/smoke_test.py::test_job_count returned (False, 'Job count failed: (psycopg2.OperationalError) could not translate host name "postgres" to address: nodename nor servname provided, or not known\n\n(Background on this error at: https://sqlalche.me/e/20/e3q8)'), which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

backend/scripts/smoke_test.py::test_search_function
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but backend/scripts/smoke_test.py::test_search_function returned (False, 'Search failed: (psycopg2.OperationalError) could not translate host name "postgres" to address: nodename nor servname provided, or not known\n\n(Background on this error at: https://sqlalche.me/e/20/e3q8)'), which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

backend/scripts/smoke_test.py::test_recommendations
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but backend/scripts/smoke_test.py::test_recommendations returned (False, 'Recommendations failed: (psycopg2.OperationalError) could not translate host name "postgres" to address: nodename nor servname provided, or not known\n\n(Background on this error at: https://sqlalche.me/e/20/e3q8)'), which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

backend/scripts/smoke_test.py::test_title_normalization
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but backend/scripts/smoke_test.py::test_title_normalization returned (True, 'Title normalization working'), which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

backend/scripts/smoke_test.py::test_embeddings
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but backend/scripts/smoke_test.py::test_embeddings returned (True, 'Embeddings working (dim=384)'), which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

backend/test_automated_workflow.py: 5 warnings
backend/test_jobwebkenya_pipeline.py: 2 warnings
backend/test_pipeline_bridge.py: 2 warnings
backend/test_processors.py: 2 warnings
backend/test_structured_extraction.py: 1 warning
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:151: PytestUnhandledCoroutineWarning: async def functions are not natively supported and have been skipped.
  You need to install a suitable plugin for your async framework, for example:
    - anyio
    - pytest-asyncio
    - pytest-tornasync
    - pytest-trio
    - pytest-twisted
    warnings.warn(PytestUnhandledCoroutineWarning(msg.format(nodeid)))

backend/test_automated_workflow.py::test_celery_tasks
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but backend/test_automated_workflow.py::test_celery_tasks returned {'total_tasks': 20, 'workflow_tasks': ['app.tasks.workflow_tasks.run_daily_workflow', 'app.tasks.workflow_tasks.run_scraper_stage', 'app.tasks.workflow_tasks.run_processing_stage', 'app.tasks.workflow_tasks.run_learning_stage', 'app.tasks.workflow_tasks.generate_daily_insights', 'app.tasks.workflow_tasks.run_optimization_stage'], 'scraper_tasks': ['app.tasks.scraper_tasks.test_all_scrapers', 'app.tasks.scraper_tasks.run_single_scraper', 'app.tasks.scraper_tasks.run_all_scrapers', 'app.tasks.scraper_tasks.migrate_scraper_data', 'app.tasks.scraper_tasks.validate_scraper_config', 'app.tasks.scraper_tasks.cleanup_old_jobs'], 'processing_tasks': ['app.tasks.processing_tasks.process_raw_jobs', 'app.tasks.processing_tasks.clean_duplicate_jobs', 'app.tasks.processing_tasks.extract_job_skills', 'app.tasks.processing_tasks.normalize_job_titles', 'app.tasks.processing_tasks.calculate_job_quality_scores', 'app.tasks.processing_tasks.update_job_embeddings', 'app.tasks.processing_tasks.validate_job_data', 'app.tasks.processing_tasks.process_job_alerts']}, which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

backend/test_integration.py::test_imports
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but backend/test_integration.py::test_imports returned True, which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

backend/test_integration.py::test_sqlite_data
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but backend/test_integration.py::test_sqlite_data returned False, which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

backend/test_integration.py::test_scraper_config
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but backend/test_integration.py::test_scraper_config returned True, which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

backend/test_integration.py::test_database_models
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but backend/test_integration.py::test_database_models returned True, which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

scripts/repo_smoke_test.py::test_database_connection
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but scripts/repo_smoke_test.py::test_database_connection returned False, which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

scripts/repo_smoke_test.py::test_job_data_quality
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but scripts/repo_smoke_test.py::test_job_data_quality returned False, which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

scripts/repo_smoke_test.py::test_source_diversity
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but scripts/repo_smoke_test.py::test_source_diversity returned False, which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

scripts/repo_smoke_test.py::test_ingestion_pipeline
  /Users/hp/Library/CloudStorage/OneDrive-Personal/Codes/Next_step/backend/venv3.11/lib/python3.11/site-packages/_pytest/python.py:166: PytestReturnNotNoneWarning: Expected None, but scripts/repo_smoke_test.py::test_ingestion_pipeline returned False, which will be an error in a future version of pytest.  Did you mean to use `assert` instead of `return`?
    warnings.warn(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
ERROR backend/scripts/smoke_test.py::test_api_health
ERROR backend/scripts/smoke_test.py::test_api_search
ERROR backend/scripts/smoke_test.py::test_api_ingestion_status
17 passed, 12 skipped, 27 warnings, 3 errors in 15.19s
```


## Mypy (optional)

```text
(rc=0)
mypy not configured

bash: mypy: command not found
```


## SQLite summary

```text
DB: jobs.sqlite3
Tables (2): jobs_data, sqlite_sequence
Primary jobs table guess: jobs_data
Row count: 102170
Columns: id, full_link, title, content
```
