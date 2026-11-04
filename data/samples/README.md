# Sample Documents

14 PDFs (56 pages) for trying out the Document Intelligence Assistant. They were written for this project and are released under [CC0](https://creativecommons.org/publicdomain/zero/1.0/): use, copy and modify them freely.

Most are **fictional**: the companies, people, products, places and figures are made up. The machine learning notes and the history of the printing press are factual overviews.

## Loading them

- **In the app:** select all the PDFs in this folder in the sidebar uploader and click **Upload and process**.
- **From the command line:** run `.venv/bin/python test_ingestion.py` from the project folder. It indexes every PDF here into `./chroma_db`, and re-running it is safe.

## What's included

### Quillmark Analytics (a fictional company)

These six documents describe the same company, so you can ask questions that span several of them.

| File | Pages | What it covers |
|---|---|---|
| `quillmark-employee-handbook.pdf` | 4 | PTO, remote work, expenses, parental leave, conduct |
| `quillmark-information-security-policy.pdf` | 4 | Passwords, MFA, data classification, incident severities |
| `quillmark-q3-fy2026-financial-report.pdf` | 3 | Revenue, margins, segments, cash flow, outlook |
| `quillmark-project-atlas-kickoff-minutes.pdf` | 3 | Attendees, budget, timeline, decisions, action items |
| `quillmark-incident-postmortem-inc-2026-0417.pdf` | 5 | Outage timeline, root cause, corrective actions |
| `quillmark-benefits-summary-2027.pdf` | 3 | Medical plans, HSA/FSA, dental, vision, 401(k) |

### Other documents

| File | Pages | What it covers |
|---|---|---|
| `kestrel-t2-thermostat-user-manual.pdf` | 5 | Product manual with wiring tables and error codes E01 to E12 |
| `parcelly-shipping-api-reference.pdf` | 5 | REST API reference: endpoints, rate limits, webhooks, error codes |
| `residential-lease-agreement-sample.pdf` | 3 | Lease terms: rent, deposit, pets, early termination |
| `research-paper-chunk-size-retrieval.pdf` | 4 | Fictional study of chunk size and hybrid search in RAG |
| `weeknight-recipes-collection.pdf` | 4 | Ten recipes with times and allergens |
| `travel-guide-isle-of-carran.pdf` | 3 | Fictional island: ferries, sights, accommodation |
| `machine-learning-study-notes.pdf` | 5 | ML fundamentals, metrics, neural networks, embeddings |
| `history-of-the-printing-press.pdf` | 3 | From woodblock printing to Gutenberg and beyond |

## Questions to try

**Exact identifiers and numbers.** Keyword search (BM25) helps most with these:

- What does error code E07 mean on the Kestrel thermostat?
- What causes the `rate_expired` error in the Parcelly API?
- Who owns action item A3 and when is it due?
- What was the root cause of INC-2026-0417?

**Natural-language questions:**

- How many PTO days do I get after three years at Quillmark?
- How much notice do I need to give to end the lease early, and what does it cost?
- How long is the ferry crossing to the Isle of Carran?
- Which recipes are vegan and take 30 minutes or less?
- What is the difference between precision and recall?
- Who printed the first book in England, and when?

**Across several documents:**

- How often do Quillmark employees have to change their password? The handbook says every 90 days, but the newer security policy removes forced rotation and says it takes precedence. A good answer cites both.
- How did the April 17 outage affect Quillmark's Q3 financial results?
- How is Project Atlas meant to prevent another outage like INC-2026-0417?
- What are the deductibles of the three medical plans?

**Not in the documents.** The assistant should say it doesn't know:

- What is Quillmark's stock price?
- What is the Wi-Fi password at the Harbour Hotel?

## Editing or adding samples

The PDFs are generated from Markdown sources in [`scripts/sample_docs/`](../../scripts/sample_docs/). To change one or add another, edit or add a `.md` file there, then run:

```bash
.venv/bin/pip install fpdf2
.venv/bin/python scripts/generate_sample_docs.py
```

`fpdf2` is only needed to rebuild the PDFs, not to run the app.
