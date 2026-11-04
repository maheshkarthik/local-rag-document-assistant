# Project Atlas Kickoff Meeting Minutes
> Quillmark Analytics (fictional). Meeting held Tuesday, August 4, 2026, 10:00 to 11:30 a.m. PT, Portland office room "Willamette" and video call. Minutes taken by Grace Liu.

## Attendees

- Marcus Bell, VP of Engineering (meeting chair)
- Priya Raman, Chief Information Security Officer
- Tomas Novak, Director of Platform Engineering (Atlas project lead)
- Aisha Kamara, Finance Business Partner
- Ben Hartley, Site Reliability Engineering Manager
- Sofia Delgado, Customer Success Director
- Grace Liu, Technical Program Manager (minutes)

Absent: Luis Ferreira, CTO (on leave; briefed separately on August 5).

## 1. Purpose of Project Atlas

Marcus opened the meeting by explaining that Project Atlas will move Quillmark's production workloads from on-demand cloud instances to a mix of reserved capacity and autoscaling spot instances, and will split the single forecasting cluster into three regional clusters (US West, US East, Canada Central). The goals are to:

1. Reduce cloud hosting costs by at least **22%** (about $1.9 million per year at current usage).
2. Remove the single point of failure that caused the April 17 outage (INC-2026-0417).
3. Keep Canadian customer data in Canada, which three enterprise prospects have asked for.

## 2. Budget

Aisha presented the budget approved by the executive team on July 28, 2026:

| Item | Amount |
|---|---|
| Engineering time (6 engineers for 5 months, internal cost) | $780,000 |
| Migration tooling and consultants | $140,000 |
| Temporary duplicate infrastructure during cutover | $210,000 |
| Contingency (10%) | $113,000 |
| Total | $1,243,000 |

Aisha noted that, at the target savings, the project pays for itself in roughly eight months after completion. She asked for monthly spend reports by the 5th business day of each month.

<!-- pagebreak -->

## 3. Timeline

Tomas walked through the plan. Dates are targets and will be confirmed at the design review.

| Phase | Dates | Exit criteria |
|---|---|---|
| Design and architecture review | Aug 4 to Aug 28 | Architecture document approved by Marcus and Priya |
| Build regional clusters | Aug 31 to Oct 9 | All three clusters pass load test at 2x peak traffic |
| Migrate internal and beta customers | Oct 12 to Oct 30 | Waste Insights beta customers running on new clusters for 2 weeks |
| Migrate production customers in waves | Nov 2 to Dec 11 | All 232 customers migrated; old cluster in read-only mode |
| Decommission old cluster | Jan 11 to Jan 22, 2027 | Old cluster shut down; final cost report issued |

There will be a **change freeze from December 14, 2026 to January 8, 2027** for the holiday peak, when grocery forecasting traffic is at its highest. No migration waves will run during the freeze.

## 4. Discussion

### 4.1 Security and data residency

Priya said the Canada Central cluster must be in place before any Canadian customer data moves, and that encryption keys for that cluster must be managed in the Canadian region. She asked for a security review of the spot instance design, since spot instances can be reclaimed with two minutes' notice and in-memory data must not be left on reclaimed hosts.

### 4.2 Customer communication

Sofia asked for at least **three weeks' notice** to customers before each migration wave, and for enterprise customers to be able to choose their wave. It was agreed that FreshWay Markets and the other five largest customers will move in the final production wave, after the process has been proven on smaller accounts.

### 4.3 Reliability

Ben raised the risk of running two clusters in parallel. The team agreed that each wave must have a rollback plan that can be completed within **30 minutes**, and that the on-call rotation will be doubled during each wave.

### 4.4 Open question

Whether to keep the US East cluster active-active with US West, or warm standby only. Active-active costs about $260,000 more per year. Decision deferred to the design review.

<!-- pagebreak -->

## 5. Decisions

- D1. Project Atlas is approved to start immediately with Tomas Novak as project lead and Grace Liu as program manager.
- D2. The Canada Central cluster will be built first.
- D3. The largest six customers will migrate in the final wave.
- D4. No migration activity during the December 14 to January 8 change freeze.

## 6. Action Items

| ID | Action | Owner | Due |
|---|---|---|---|
| A1 | Write the Atlas architecture document | Tomas Novak | Aug 21 |
| A2 | Security review of spot instance design and key management | Priya Raman | Aug 26 |
| A3 | Cost model for active-active vs warm standby in US East | Aisha Kamara | Aug 19 |
| A4 | Draft customer migration notice template | Sofia Delgado | Aug 25 |
| A5 | Rollback runbook template and on-call plan | Ben Hartley | Aug 28 |
| A6 | Set up weekly status report and risk register | Grace Liu | Aug 7 |
| A7 | Brief Luis Ferreira on kickoff outcomes | Marcus Bell | Aug 5 |

## 7. Next Meeting

Design review on **Thursday, August 27, 2026**, 1:00 to 3:00 p.m. PT. Weekly status meetings every Monday at 9:30 a.m. PT starting August 10.
