# Next Step LMI Platform - Feature Roadmap & Enhancements

## 📊 Current Status

### ✅ Implemented Features
- Multi-source job scraping (BrighterMonday, Indeed, LinkedIn, CareerJet, JobWebKenya, MyJobMag)
- Basic deduplication (URL-based)
- Job data cleaning and normalization
- Title normalization (50+ job families)
- Skill extraction using NLP
- Semantic search using embeddings
- Career recommendations
- LMI analytics (weekly insights, salary data, trending skills)
- WhatsApp bot integration
- User authentication and profiles
- Job application tracking
- Saved jobs

### 🚀 Recent Additions (January 2026)
- **Enhanced Deduplication System** with:
  - URL normalization (removes tracking parameters)
  - Fuzzy title matching (80%+ similarity)
  - Content similarity using embeddings (90%+ similarity)
  - Composite matching (company + title + location)
  - Repost count tracking (urgency signal)
  - Data quality scoring

---

## 🎯 Feature Categories & Prioritization

### PHASE 1: Core Infrastructure (In Progress - Q1 2026)

#### 1. Enhanced Job Ingestion Pipeline ✅
**Status**: In Development
**Priority**: Critical
**Value**: Foundation for all features

**Components**:
- [x] Enhanced deduplication service
- [ ] MyJobMag scraper (91% of existing data)
- [ ] JobWebKenya scraper (7% of existing data)
- [ ] Unified scraper orchestrator
- [ ] Scheduling system (cron-based or Celery)
- [ ] Health monitoring dashboard
- [ ] Data quality validation

**Business Impact**:
- Reduce duplicate jobs by 60-70%
- Improve data freshness (scrape every 6 hours)
- Better coverage of Kenya job market

---

### PHASE 2: User Engagement Features (Q1-Q2 2026)

#### 2. Smart Job Alerts (AI-Powered)
**Priority**: High
**Estimated Effort**: 2 weeks
**Revenue Impact**: Increases user retention by 40%

**Features**:
- Semantic matching (not just keywords)
- "Jobs you'd be qualified for" based on profile skills
- "Similar to jobs you've saved" recommendations
- Priority alerts for high-match roles (85%+ match)
- Multi-channel delivery (WhatsApp, Email, SMS)
- Alert frequency control (instant, daily, weekly)
- Salary threshold filters

**Tech Stack**: Existing embeddings + Twilio + Celery

**User Story**:
> "As a job seeker, I want to receive only relevant job alerts that match my skills and career goals, so I don't waste time on mismatched roles"

---

#### 3. Job Match Scoring
**Priority**: High
**Estimated Effort**: 1 week
**Revenue Impact**: Increases application conversion by 30%

**Features**:
```
Job: Senior Data Analyst at Safaricom
Your Match: 87% ⭐⭐⭐⭐

✓ 8/10 required skills matched
✓ Experience level: Match (5 years)
✓ Salary expectations: Aligned (KES 250K)
✗ Missing: Tableau, Advanced SQL

Recommendation: Take a Tableau course on Coursera (4 weeks)
```

**Matching Criteria**:
- Skills overlap (weight: 40%)
- Experience level (weight: 25%)
- Salary alignment (weight: 15%)
- Location preference (weight: 10%)
- Education match (weight: 10%)

---

#### 4. Skills Gap Analysis & Learning Paths
**Priority**: Medium-High
**Estimated Effort**: 3 weeks
**Revenue Potential**: Partnership revenue + subscription upsell

**Features**:
- Analyze user's current skills vs. target role requirements
- Visual skill gap representation
- Recommended courses (Coursera, Udemy, LinkedIn Learning affiliate)
- Time-to-ready estimation (e.g., "3 months with 10 hrs/week study")
- Track learning progress
- Skill endorsements from connections

**Monetization**:
- Affiliate commissions from course platforms (10-20%)
- Premium tier feature ($5/month)

**Integrations**:
- Coursera API
- Udemy API
- LinkedIn Learning

---

#### 5. Application Tracker with ATS Integration
**Priority**: High
**Estimated Effort**: 3 weeks
**User Pain Point**: "Where did I apply? What stage am I at?"

**Features**:
- Application status pipeline:
  ```
  Saved → Applied → Reviewing → Interview Scheduled →
  Interview Completed → Offer → Accepted/Rejected
  ```
- Auto-populate applications using saved profile
- Browser extension for one-click apply
- Interview scheduling (Google/Microsoft Calendar integration)
- Follow-up reminders (e.g., "Follow up 1 week after applying")
- Application analytics (response rates, time-to-interview)

**Tech Stack**: Calendar APIs + Browser Extension (Chrome/Firefox)

---

#### 6. Enhanced WhatsApp Career Coach Bot
**Priority**: Medium
**Estimated Effort**: 2 weeks
**Current State**: Basic Q&A

**Enhanced Capabilities**:
- Resume review and feedback
- Interview prep (common questions by role/company)
- Salary negotiation coaching
- Job search strategy advice
- Voice notes support
- Image upload (for CV review)
- Contextual conversations (remembers user history)

**Tech Stack**: OpenAI API + WhatsApp Business API

**Example Conversation**:
```
User: "I have an interview at Safaricom tomorrow"
Bot: "Great! I see they're hiring for Network Engineer.
      Here are 5 common technical questions they ask:
      1. Explain OSPF vs BGP routing...
      Would you like to practice answering these?"
```

---

### PHASE 3: Company & Market Intelligence (Q2 2026)

#### 7. Company Intelligence Hub
**Priority**: Medium
**Estimated Effort**: 4 weeks
**Differentiation**: Unique value vs competitors

**Features**:
- **Company Profiles**:
  - Aggregated employee reviews (import from Glassdoor scraping)
  - Hiring patterns (frequency, roles hired, growth trends)
  - Salary benchmarks by role
  - Interview process insights (user-contributed)
  - Company culture ratings (work-life balance, benefits, diversity)
  - Employee referral network

- **Hiring Insights**:
  ```
  Safaricom
  🔥 High Hiring Activity (32 roles in last 30 days)
  💰 Avg Salary: KES 180K-450K
  ⏱️ Time to Hire: 28 days
  📈 Growing Roles: Data Analysts (+40%), DevOps Engineers (+25%)
  ⭐ Employee Rating: 4.2/5 (from 127 reviews)
  ```

**Data Sources**:
- User-contributed reviews
- Job posting frequency analysis
- LinkedIn company data
- Public financial reports

---

#### 8. Salary Negotiation Assistant
**Priority**: Medium
**Estimated Effort**: 2 weeks
**Revenue**: Premium feature ($10 one-time or included in Pro tier)

**Features**:
- Market rate calculator:
  ```
  Role: Senior Software Engineer
  Experience: 5 years
  Location: Nairobi
  Education: Bachelor's CS

  Market Range: KES 250K - 380K
  Your Target: KES 320K (65th percentile) ✓ Reasonable
  ```
- Negotiation scripts and tactics
- Total compensation calculator (base + benefits + perks)
- Offer comparison tool (compare multiple offers side-by-side)
- Counter-offer generator

**Data Source**: Your LMI salary data (102K jobs)

---

#### 9. Job Market Forecasting
**Priority**: Low-Medium
**Estimated Effort**: 3 weeks
**Unique Selling Point**: Predictive analytics

**Features**:
- Predict high-demand roles (3-6 months ahead)
- Industry growth trends (Tech, Finance, Healthcare)
- Skills becoming obsolete vs. emerging
- Remote work trends in Kenya
- Salary trajectory predictions

**ML Models**:
- Time series forecasting (ARIMA, Prophet)
- Train on your 102K historical job data

**Use Case**:
```
Predicted for Q2 2026:
📈 Data Science roles: +35% demand
📈 Cloud Engineers: +28% demand
📉 PHP Developers: -12% demand
💡 Recommendation: If you're a backend dev,
   consider upskilling to cloud technologies
```

---

### PHASE 4: Monetization & B2B (Q2-Q3 2026)

#### 10. Employer Dashboard (B2B SaaS)
**Priority**: High
**Revenue Potential**: $500-5,000/month per employer
**Target**: Mid-size to large companies (50+ employees)

**Features**:
- **Job Posting**:
  - Post jobs directly to Next Step
  - Multi-site distribution (post once, syndicate everywhere)
  - Job template library
  - Screening questions

- **Candidate Database Access**:
  - Search 100K+ registered users
  - Advanced filters (skills, experience, education, location)
  - AI-recommended candidates
  - Bulk messaging

- **Analytics**:
  - Job post performance (views, clicks, applications)
  - Candidate quality scores
  - Time-to-fill metrics
  - Source effectiveness (which job boards work best)
  - Diversity metrics

**Pricing Tiers**:
- **Starter** (KES 15,000/month): 5 job posts, 50 candidate contacts
- **Professional** (KES 40,000/month): Unlimited posts, 200 contacts, analytics
- **Enterprise** (KES 100,000/month): Everything + API access + dedicated support

---

#### 11. Premium Job Seeker Subscription (Enhanced)
**Current**: Basic/Pro/Enterprise
**Enhanced Tiers**:

**FREE**:
- Job search (limited to 20/day)
- Basic alerts (weekly digest)
- Career translation
- Profile creation

**PROFESSIONAL (KES 499/month or KES 4,999/year)**:
- Unlimited job search
- Priority smart alerts (daily + instant)
- Resume builder with ATS optimization
- Skills gap analysis
- Application tracker (unlimited)
- Interview prep resources
- 3 career coaching sessions/month (WhatsApp bot)

**PREMIUM (KES 999/month or KES 9,999/year)**:
- Everything in Professional
- Auto-apply feature (apply to 50 jobs/month with one click)
- Salary negotiation assistant
- Direct recruiter contact (featured profile)
- Advanced analytics (profile views, application success rates)
- 10 career coaching sessions/month
- Resume review by human experts (monthly)

**ENTERPRISE (KES 2,499/month - for teams/universities)**:
- Bulk accounts (e.g., 50 students)
- Team admin dashboard
- Custom branding
- Dedicated support

---

#### 12. Data API & Industry Reports
**Priority**: Medium
**Revenue**: $200-2,000/month per customer
**Target**: Recruitment agencies, market research firms, government, universities

**Products**:

**A) LMI Data API**:
```
Endpoints:
- /api/v1/market-trends (salary, demand by role/location)
- /api/v1/skills-demand (trending skills)
- /api/v1/company-insights (hiring patterns)
- /api/v1/job-postings (search access to 100K+ jobs)

Pricing:
- Basic: KES 20,000/month (1,000 API calls)
- Professional: KES 50,000/month (10,000 calls)
- Enterprise: Custom (unlimited)
```

**B) Monthly Industry Reports**:
```
Tech Sector Report - January 2026
- 2,500 job postings analyzed
- Top hiring companies
- Salary benchmarks by seniority
- Skills demand heatmap
- Hiring trends (remote vs on-site)

Price: KES 15,000/report or KES 150,000/year subscription
```

**Potential Customers**:
- Recruitment agencies (20+ in Kenya)
- HR consultancies
- Ministry of Labor
- Universities (career centers)
- VC firms (market research)

---

### PHASE 5: Advanced Features (Q3-Q4 2026)

#### 13. Career Path Visualizer
**Priority**: Medium
**Effort**: 4 weeks
**Wow Factor**: High (unique feature)

**Features**:
```
Your Career Path Projection:

Current: Junior Data Analyst (KES 100K)
  ↓ (2 years, +Python, +SQL, +Tableau)
Mid-Level Data Analyst (KES 180K)
  📊 12 open roles currently
  ⏱️ Avg. 18 months to get here

  ↓ Option A (3 years, +ML, +Cloud)
Senior Data Scientist (KES 350K)
  📊 8 roles available

  ↓ Option B (3 years, +Leadership)
Analytics Manager (KES 400K)
  📊 5 roles available

  ↓ (5 years)
Head of Data (KES 650K)
  📊 2 roles (rare, competitive)
```

**Interactivity**:
- Click on any role to see:
  - Current openings
  - Required skills
  - Salary range
  - Companies hiring
  - Learning paths

**Data Source**: Your job postings + user career progression data

---

#### 14. Referral Network
**Priority**: Low-Medium
**Effort**: 3 weeks
**Impact**: Increases job placement success by 30-40%

**Features**:
- Connect job seekers with employees at target companies
- Referral request system (in-app messaging)
- Incentivize referrers (e.g., KES 2,000 if candidate is hired)
- Track referral success rates
- Company referral policies database

**Revenue Model**:
- Take 10% commission on referral bonuses
- Or charge KES 500/referral request (job seeker pays)

---

#### 15. Mock Interview Platform
**Priority**: Low
**Effort**: 5 weeks
**Tech**: Video recording + AI analysis

**Features**:
- Record video responses to common interview questions
- AI feedback on:
  - Speech clarity and pace
  - Filler words (um, uh, like)
  - Eye contact (using webcam)
  - Body language
  - Answer quality (keyword analysis)
- Role-specific question banks
- Company-specific questions (user-contributed)
- Technical assessment practice (coding challenges)

**Monetization**: Premium feature or pay-per-use (KES 200/session)

---

#### 16. Mobile Apps (iOS + Android)
**Priority**: High (for scale)
**Effort**: 8-12 weeks
**Tech Stack**: React Native or Flutter

**Features**:
- Full job search and application
- Push notifications for alerts
- Quick Apply from phone
- Voice search ("Find data analyst jobs in Nairobi")
- Offline mode (save jobs for later)
- Barcode scanner (scan physical job ads)

**Revenue Impact**: 60% of users prefer mobile - critical for growth

---

#### 17. Browser Extension
**Priority**: Medium
**Effort**: 3 weeks
**Platforms**: Chrome, Firefox, Safari

**Features**:
- Auto-detect job postings on ANY website
- One-click save to Next Step
- Auto-fill applications using Next Step profile
- Salary data overlay (show market rate on job sites)
- Company ratings overlay (show Next Step company rating)

**Example**:
```
[User on LinkedIn job page]
Extension shows:
💡 This role is also on BrighterMonday (2 days newer)
💰 Market rate: KES 200K-280K (you're seeing: KES 180K)
⭐ Company rating: 3.8/5 from Next Step users
🎯 Your match: 82%
[Save to Next Step] [Apply with Next Step Profile]
```

---

### PHASE 6: Kenya-Specific Features (Ongoing)

#### 18. Attachment/Internship Hub (Enhanced)
**Current**: Basic list
**Enhanced**:
- University partnerships (KU, UoN, JKUAT, Strathmore, USIU)
- Application deadline tracker
- Success tips for students
- Mentorship matching (pair students with professionals)
- Industrial attachment reports repository

---

#### 19. Remote Work & International Opportunities
**Priority**: High (growing market)
**Effort**: 2 weeks

**Features**:
- Filter for remote-friendly Kenyan companies
- International jobs open to Kenyans
- Time zone compatibility checker
- Currency/salary conversion (USD → KES)
- Work permit/visa information
- Tax implications for remote work
- Best remote job boards integration (We Work Remotely, Remote.co)

---

#### 20. Government & NGO Job Hub
**Priority**: Medium
**Effort**: 2 weeks
**Rationale**: Major employer in Kenya

**Features**:
- Specialized section for public sector
- County government jobs (47 counties)
- Ministry job boards aggregation
- UN/NGO job boards (ReliefWeb, Devex)
- Public sector salary scales
- Application process guides (e.g., PSC requirements)
- Deadline calendar

---

## 📊 Database Recommendations

### Online Database Options (For Production)

#### Option 1: **Supabase (Recommended)**
- **Pros**: PostgreSQL + pgvector support, generous free tier, easy scaling, built-in auth
- **Pricing**: Free (500MB), Pro ($25/month for 8GB), unlimited connections
- **Best For**: Startups, fast deployment
- **Setup Time**: < 30 minutes

#### Option 2: **Railway.app**
- **Pros**: Simple deployment, PostgreSQL, auto-scaling
- **Pricing**: Pay-as-you-go ($5-20/month expected)
- **Best For**: Developer-friendly, CI/CD integration

#### Option 3: **DigitalOcean Managed Databases**
- **Pros**: Reliable, good for Kenya (SGP region), daily backups
- **Pricing**: $15/month (1GB RAM, 10GB storage)
- **Best For**: Production-ready, predictable costs

#### Option 4: **AWS RDS (PostgreSQL)**
- **Pros**: Highly scalable, lots of features, pgvector support
- **Pricing**: $20-50/month (t3.micro + storage)
- **Best For**: Enterprise, high availability needs

#### Option 5: **Neon.tech (Serverless Postgres)**
- **Pros**: Serverless (pay for what you use), branch databases, instant provisioning
- **Pricing**: Free tier (0.5GB), $19/month for Pro
- **Best For**: Dev/staging environments, cost optimization

**Recommendation**: Start with **Supabase** (free tier), migrate to **DigitalOcean** or **Railway** when you hit 10K+ users.

---

## 🚀 Next Steps

### Immediate Actions (This Week)
1. ✅ Enhanced deduplication system created
2. [ ] Create Alembic migration and apply to test DB
3. [ ] Build MyJobMag scraper
4. [ ] Build JobWebKenya scraper
5. [ ] Set up online database (Supabase or Railway)

### Week 2-4
6. [ ] Unified scraper orchestrator
7. [ ] Smart job alerts (AI-powered)
8. [ ] Job match scoring
9. [ ] Application tracker

### Month 2-3
10. [ ] Skills gap analysis
11. [ ] Company intelligence hub
12. [ ] Employer dashboard (MVP)
13. [ ] Mobile app (MVP)

### Month 4-6
14. [ ] Career path visualizer
15. [ ] Salary negotiation assistant
16. [ ] Premium tier launch
17. [ ] Industry reports (first pilot customers)

---

## 💰 Revenue Projections (Year 1)

**Assumptions**:
- 10,000 active job seekers by month 6
- 50 companies by month 9
- 5% conversion to paid (job seekers)
- Average subscription: KES 600/month

| Revenue Stream | Month 6 | Month 12 | Notes |
|----------------|---------|----------|-------|
| Job Seeker Subscriptions | KES 300K | KES 900K | 500 → 1,500 paid users |
| Employer Subscriptions | KES 200K | KES 800K | 5 → 20 companies |
| API & Reports | KES 50K | KES 200K | 3 → 10 customers |
| Affiliate (Courses) | KES 30K | KES 100K | Learning path partnerships |
| **TOTAL** | **KES 580K** | **KES 2M** | ~$15,400/month by month 12 |

---

## 🎯 Success Metrics

### User Engagement
- Daily Active Users (DAU): Target 2,000 by month 6
- Job applications: 10,000/month by month 6
- Search queries: 50,000/month
- Average session time: 8+ minutes

### Quality Metrics
- Job duplicate rate: < 5%
- Data freshness: 90% of jobs < 24 hours old
- Match score accuracy: 80%+ user satisfaction

### Business Metrics
- Customer Acquisition Cost (CAC): < KES 500
- Lifetime Value (LTV): > KES 12,000
- LTV:CAC ratio: > 20:1
- Monthly Recurring Revenue (MRR): KES 2M by month 12
- Churn rate: < 10% monthly

---

## 📞 Contact & Support

For questions about this roadmap:
- Technical: dev@nextstep.co.ke
- Business: business@nextstep.co.ke
- Platform: [https://nextstep.co.ke](https://nextstep.co.ke)

---

**Last Updated**: January 8, 2026
**Version**: 2.0
**Status**: Phase 1 in progress
