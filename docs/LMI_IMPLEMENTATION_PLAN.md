# Labor Market Intelligence (LMI) Monetization Plan

**Date:** 2026-02-15
**Goal:** Turn job advert intelligence into paying customers (B2C + B2B)

---

## ✅ What We Already Have (Current State Audit)

### Data Infrastructure (Strong Foundation)
- ✅ **Job scraping & storage** (JobPost, JobEntities models)
- ✅ **Skills extraction** (Skill, JobSkill models)
- ✅ **Demand signals** (SkillTrendsMonthly, RoleEvolution, HiringSignal)
- ✅ **Title normalization** (TitleNorm, TitleAdjacency)
- ✅ **Job embeddings** (JobEmbedding for semantic search)

### User Features (Solid)
- ✅ **Auth & profiles** (registration, login, profile management)
- ✅ **Job recommendations** (personalized matching)
- ✅ **Saved jobs & applications** (tracking system)
- ✅ **Job alerts** (notification system)
- ✅ **Career tools** (CV generator, cover letter, career advice)

### Analytics (Exists but Underutilized)
- ✅ **Skill trends API** (`/analytics/skill-trends`)
- ✅ **Role evolution API** (`/analytics/role-evolution`)
- ✅ **Title adjacency** (career mobility insights)

### Beta Program (Just Built)
- ✅ **B2C signup flow** (targeting professionals)
- ✅ **Admin dashboard** (conversion tracking)
- ✅ **User dashboard** (engagement tracking)

---

## ❌ What's Missing (Critical Gaps)

### 1. **Match Scoring System** ⚠️ HIGH PRIORITY
**Problem:** Users can't see "you match 72% - missing: Power BI + SQL joins"

**What to build:**
- Profile → Job comparison algorithm
- Skill gap identification
- Learning path recommendations
- Match percentage calculation

**Where it goes:**
- `/api/users/job-match/{job_id}` endpoint
- User dashboard: "Match Score" widget
- Job listings: Show match % on each job card

**Revenue impact:** This is the CORE of premium tier (users pay to see their gaps)

---

### 2. **Skills Gap Scan** 💰 QUICK WIN
**Problem:** No paid diagnostic product

**What to build:**
- Upload CV or fill profile
- Compare to target role(s)
- Output: missing skills, recommended projects, best-fit roles, expected pay
- 30/60/90-day action plan

**Where it goes:**
- `/api/career-tools/skills-gap-scan` endpoint
- New page: `frontend/skills-gap-scan.html`
- Pricing: KES 500 one-time (or free for premium subscribers)

**Revenue impact:** Fast cash - can start charging immediately

---

### 3. **Salary Intelligence** 💰 HIGH VALUE
**Problem:** No compensation data shown

**What to build:**
- Extract salary ranges from job posts (where stated)
- Infer salary bands using:
  - Seniority level
  - Years required
  - Employer brand
  - Industry sector
  - Location
- Build `SalaryBand` model in database

**Where it goes:**
- Job listings: "Estimated: KES 80K-120K/month"
- User dashboard: "You're earning below market" or "You're at market rate"
- Career pathways: "Entry: KES 50K → Mid: KES 100K → Senior: KES 200K"

**Revenue impact:** Premium users get full salary data (free tier sees ranges only)

---

### 4. **Career Pathway Products** 💰 UPSELL
**Problem:** No structured career roadmaps

**What to build:**
- Pre-built roadmaps: "Data Analyst in Kenya 2026"
- Includes:
  - Required skills + certs
  - Typical experience ladder
  - Employers who hire
  - Learning resources
  - Project ideas

**Where it goes:**
- `/api/career-pathways/{role_slug}` endpoint
- New section in dashboard: "Career Roadmaps"
- Pricing: KES 1,000 per roadmap or included in premium

**Revenue impact:** One-time purchases + bundled with premium

---

### 5. **Labor Market Intelligence Reports (B2B)** 💰💰💰 HIGHEST MARGIN
**Problem:** No B2B product

**What to build:**
- Automated quarterly reports:
  - Top demanded skills
  - Salary bands by role/sector
  - Role demand by county
  - Sector hiring trends
- Custom dashboards for clients

**Buyers:**
- Universities/TVETs (curriculum alignment)
- County governments (skills planning)
- NGOs/donors (workforce development)
- Private companies (HR benchmarking)

**Pricing:** KES 50K-200K per report + KES 20K/month for dashboard access

**Revenue impact:** High-ticket B2B revenue (1 client = 200 B2C users)

---

### 6. **Enhanced Admin Dashboard** (Internal Need)
**Problem:** Can't track LMI quality metrics

**What to add:**
- Job scraping health (success rate, errors)
- Skills extraction accuracy
- User engagement with LMI features
- Revenue metrics (MRR, ARPU, churn)

---

## 📋 Implementation Roadmap (3 Phases)

### **PHASE 1: Foundation (Weeks 1-4) - Make Premium Worth Paying For**
**Goal:** Give users a reason to pay KES 200-300/month

| Week | Task | Priority | Owner | Revenue Impact |
|------|------|----------|-------|----------------|
| 1 | Build match scoring algorithm | P0 | Backend | Core feature |
| 1 | Add match % to job listings UI | P0 | Frontend | Visible value |
| 2 | Extract salary data from job posts | P1 | Backend | High demand |
| 2 | Show salary estimates in UI | P1 | Frontend | Conversion driver |
| 3 | Build Skills Gap Scan product | P0 | Full-stack | Immediate revenue |
| 3 | Add paywall (free tier vs premium) | P0 | Backend | Revenue enabler |
| 4 | Launch beta recruitment | P0 | Marketing | Get users |
| 4 | Track conversion (free → paid) | P0 | Analytics | Measure success |

**Deliverables:**
- ✅ Match scoring visible on all jobs
- ✅ Salary intelligence displayed
- ✅ Skills Gap Scan purchasable
- ✅ Clear free vs premium tiers
- ✅ 50 beta signups

---

### **PHASE 2: B2C Scale (Weeks 5-12) - Grow to KES 40K MRR**
**Goal:** Prove freemium model works at scale

| Week | Task | Priority | Revenue Impact |
|------|------|----------|----------------|
| 5-6 | Launch 5 career pathway products | P1 | Upsell opportunity |
| 7-8 | Build referral program | P1 | Viral growth |
| 9-10 | LinkedIn + WhatsApp ads | P0 | User acquisition |
| 11-12 | Optimize conversion funnel | P0 | Revenue growth |

**Metrics:**
- 200-500 signups
- 15-20% conversion rate
- KES 10K-15K MRR
- < 20% monthly churn

---

### **PHASE 3: B2B Intelligence (Months 4-6) - Add High-Ticket Revenue**
**Goal:** Land first B2B clients (KES 50K-200K contracts)

| Month | Task | Revenue Potential |
|-------|------|-------------------|
| 4 | Build LMI report templates | KES 0 (setup) |
| 4 | Create sample reports | KES 0 (portfolio) |
| 5 | Pitch 10 universities/NGOs | KES 100K-500K |
| 5 | Pitch 5 county governments | KES 200K-1M |
| 6 | Close 2-3 B2B contracts | KES 150K-400K |

**Target Buyers:**
1. **Universities** - Curriculum alignment reports
2. **County Governments** - Skills gap analysis for youth programs
3. **NGOs/Donors** - Workforce development insights
4. **Corporates** - Salary benchmarking + hiring intelligence

---

## 💰 Revenue Model Summary

### B2C Freemium (Primary)
| Tier | Price | Features | Target |
|------|-------|----------|--------|
| **Free** | KES 0 | Basic search, save 5 jobs, basic profile | Entry-level job seekers |
| **Premium** | KES 200-300/month | Match scoring, salary data, unlimited saves, career advice, pathways | Working professionals (1-10 yrs) |
| **Skills Gap Scan** | KES 500 one-time | Diagnostic + 30/60/90-day plan | Career switchers |
| **Career Pathways** | KES 1,000 each | Role-specific roadmaps | Upskilling professionals |

**12-Month Target:**
- 2,000 users
- 10% conversion = 200 paid
- KES 50K MRR (~$380 USD)

### B2B Intelligence (Secondary, High-Margin)
| Product | Price | Buyer | Frequency |
|---------|-------|-------|-----------|
| **LMI Report** | KES 50K-200K | Universities, NGOs, Govt | Quarterly |
| **Dashboard Access** | KES 20K/month | Corporates, Agencies | Monthly |
| **Custom Study** | KES 300K-1M | Donors, Large Orgs | One-time |

**12-Month Target:**
- 5-10 B2B clients
- KES 100K-300K/month recurring

---

## 🎯 Success Metrics (12-Month Goals)

### B2C Metrics
- **Users:** 2,000 signups
- **Conversion:** 10-15% (200-300 paid)
- **MRR:** KES 50K (~$380 USD)
- **Churn:** < 20% monthly
- **ARPU:** KES 250/user

### B2B Metrics
- **Clients:** 5-10 contracts
- **ACV:** KES 150K-500K per client
- **Revenue:** KES 100K-300K/month

### Combined Target
**Total MRR:** KES 150K-350K/month (~$1,200-2,600 USD)

---

## 🚀 Immediate Next Steps (This Week)

### Day 1-2: Match Scoring
1. Write matching algorithm in `backend/app/services/matching_service.py`
2. Add `/api/users/job-match/{job_id}` endpoint
3. Update job card UI to show match %

### Day 3-4: Salary Intelligence
1. Write salary extraction in `backend/app/services/salary_service.py`
2. Add `SalaryBand` model to database
3. Update job listings to show estimated salary

### Day 5-7: Skills Gap Scan
1. Build diagnostic algorithm
2. Create paywall (Stripe/M-Pesa integration)
3. Design `frontend/skills-gap-scan.html`
4. Add payment flow

---

## 📊 Data Quality Requirements

For LMI to be valuable, we need:
1. **Skills extraction accuracy:** 85%+ (manual QA on 100 jobs)
2. **Job volume:** 1,000+ jobs/month minimum
3. **Salary data coverage:** 30%+ of jobs (extract + infer rest)
4. **Refresh rate:** Daily updates for trends

---

## Risk Mitigation

### Risk 1: Low Data Volume
**Mitigation:** Partner with BrighterMonday, scrape 5+ sources, accept user-submitted jobs

### Risk 2: Poor Skills Extraction
**Mitigation:** Use GPT-4 for extraction + human QA + feedback loop

### Risk 3: Users Don't See Value
**Mitigation:** A/B test messaging, improve match accuracy, add testimonials

### Risk 4: Payment Friction (M-Pesa)
**Mitigation:** Start with Stripe (credit cards), add M-Pesa later

---

## Tech Stack Additions Needed

### Backend
- **Matching service:** Profile → Job comparison logic
- **Salary service:** Extraction + inference + band management
- **Payment service:** Stripe/M-Pesa integration
- **Report generator:** Automated LMI reports (PDF/Excel)

### Frontend
- **Match UI:** Show % match + missing skills on job cards
- **Skills Gap page:** New product page with payment flow
- **Paywall:** Free vs Premium feature gating
- **Career Pathways:** Browsable roadmaps

### Infrastructure
- **Background jobs:** Daily scraping, weekly reports
- **Caching:** Redis for analytics queries
- **Storage:** S3 for PDF reports

---

**This plan turns your job advert data into KES 150K-350K/month in 12 months.**

Focus on Phase 1 first - that's what makes users convert!
