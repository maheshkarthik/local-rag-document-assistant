# Incident Postmortem: INC-2026-0417 Forecast Generation Outage
> Quillmark Analytics (fictional). Severity SEV-1. Date of incident: Friday, April 17, 2026. Author: Ben Hartley, SRE Manager. Status: Final, reviewed May 1, 2026. Blameless format.

## 1. Summary

On April 17, 2026, Quillmark Forecast stopped producing daily demand forecasts for all customers for **4 hours and 52 minutes**, from 03:14 to 08:06 Pacific Time. Customers could log in and see the previous day's forecasts, but no new forecasts were generated and the ordering export to customer systems failed. 187 of 229 customers had automated store orders that depend on the 05:00 export; 41 of them placed manual orders or delayed orders that morning.

The root cause was a database connection pool exhaustion in the forecasting cluster, triggered by a scheduled database maintenance task that held locks far longer than expected after a change to its configuration. Because the forecasting service runs as a single cluster, there was no unaffected capacity to fail over to.

## 2. Impact

- Forecast generation: unavailable for 4 h 52 min for all customers.
- Ordering export: missed the 05:00 PT deadline for 187 customers. Exports completed between 08:20 and 09:45 PT.
- Customer support: 312 tickets opened during the day, compared with a typical 40.
- Financial: $186,000 in service credits issued under the Service Level Agreement, recorded in Q3 FY2026.
- No data was lost and no security impact was found.

## 3. Timeline (all times Pacific)

| Time | Event |
|---|---|
| 02:30 | Weekly database maintenance job (vacuum and reindex) starts on the primary forecasting database |
| 03:05 | Nightly forecast batch begins; workers open connections as normal |
| 03:14 | Connection pool reaches its limit of 400; forecast workers start failing with "timeout acquiring connection" |
| 03:16 | Automated alert FCST-BATCH-LAG fires and pages the on-call engineer, Wei Zhang |
| 03:41 | Wei acknowledges the page (first page was missed; escalation policy triggered the secondary) |
| 04:10 | Wei restarts forecast workers; connections are exhausted again within 3 minutes |
| 04:35 | Incident declared SEV-1; Ben Hartley takes the incident commander role |
| 05:00 | Ordering export deadline missed; status page updated |
| 05:50 | Team identifies the maintenance job holding locks on the forecasts table |
| 06:12 | Maintenance job cancelled; locks released |
| 06:30 | Forecast batch restarted with reduced concurrency (50 workers instead of 200) |
| 08:06 | All forecasts generated; incident moved to monitoring |
| 09:45 | Final customer export completed |
| 11:00 | Incident closed |

<!-- pagebreak -->

## 4. Root Cause Analysis

### 4.1 What happened

On April 9, a pull request changed the maintenance job to reindex the forecasts table without the CONCURRENTLY option, because a concurrent reindex had failed the previous week on a corrupted index. The change was reviewed and approved, but the reviewers did not notice that a non-concurrent reindex takes an exclusive lock on the table. On April 17 the forecasts table had grown to 1.9 TB, so the reindex took more than three hours instead of the 20 minutes observed in staging.

Forecast workers waited on the lock while holding database connections. Each worker retried every 10 seconds and opened a new connection on each retry, so the pool of 400 connections was exhausted in nine minutes.

### 4.2 Why it took so long to resolve

1. The first page at 03:16 went to a phone that was on silent; the secondary on-call was paged automatically only after 25 minutes.
2. The runbook for FCST-BATCH-LAG recommended restarting workers, which did not help and cost 25 minutes.
3. Database lock monitoring existed but was not linked from the alert, so the team spent over an hour looking at application logs first.
4. The service runs on a single cluster, so there was no second region to serve forecasts from.

### 4.3 Contributing factors

- Staging data is about 5% of the size of production, so the reindex duration in staging was not representative.
- Maintenance windows overlapped with the nightly batch after the batch was moved earlier in March.

## 5. What Went Well

- The status page was updated within 25 minutes of the incident being declared.
- Customer Success proactively phoned the 20 largest customers before 06:00.
- Reducing worker concurrency allowed the batch to complete safely once the lock was released.

<!-- pagebreak -->

## 6. Corrective Actions

| ID | Action | Owner | Priority | Due | Status |
|---|---|---|---|---|---|
| CA-1 | Add a lint rule that blocks non-concurrent REINDEX and long-locking DDL in maintenance jobs | Wei Zhang | P1 | May 8 | Done |
| CA-2 | Make forecast workers release connections while waiting and use exponential backoff with jitter | Elena Petrova | P1 | May 15 | Done |
| CA-3 | Link lock-wait dashboard from all forecasting alerts; update runbook | Wei Zhang | P1 | May 8 | Done |
| CA-4 | Reduce escalation delay to secondary on-call from 25 to 10 minutes | Ben Hartley | P1 | Apr 24 | Done |
| CA-5 | Schedule maintenance so it cannot overlap the 03:00 to 06:00 batch window | Ben Hartley | P2 | May 22 | Done |
| CA-6 | Create a production-sized staging snapshot (anonymized) for testing maintenance changes | Elena Petrova | P2 | Jul 31 | In progress |
| CA-7 | Run forecasting in more than one region so one cluster's failure does not stop all forecasts | Tomas Novak | P1 | Q4 2026 | Tracked as Project Atlas |

## 7. Lessons Learned

- Changes to database maintenance jobs need the same review as schema migrations, including an estimate of lock duration on production-sized data.
- Retry logic that opens new connections can turn a slowdown into a full outage. Bounded retries with backoff are required for all services that use the shared database.
- Runbooks should list the most likely causes first, with links to the dashboards that confirm or rule them out.
