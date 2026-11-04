# The Effect of Chunk Size and Hybrid Search on Retrieval Quality in Small-Scale RAG Systems
> A. Moreno, K. Takahashi and R. Osei. Fictional authors and fictional results, written as sample content for testing a document assistant.

## Abstract

Retrieval-augmented generation (RAG) systems split documents into chunks, embed them, and retrieve the most relevant chunks to ground a language model's answer. Practitioners often choose chunk sizes by habit. We measure how chunk size, chunk overlap and the choice between dense, sparse and hybrid retrieval affect retrieval quality on a corpus of 1,240 business documents and 600 annotated questions. Across our experiments, chunks of **800 to 1,200 characters** with **15 to 20% overlap** gave the best balance of recall and precision. Hybrid retrieval that combines dense embeddings with BM25 using Reciprocal Rank Fusion (RRF) improved Recall@5 from 0.71 (dense only) to **0.84**, with the largest gains on questions containing identifiers, codes and numbers. Gains from hybrid retrieval were smallest on paraphrased, conceptual questions.

## 1. Introduction

Small RAG deployments, for example on a laptop or a single server, are increasingly common because they keep documents private and avoid per-query costs. These systems typically use compact embedding models such as all-MiniLM-L6-v2 (384 dimensions) and small local language models of 3 to 8 billion parameters. With a small model, the quality of the retrieved context matters even more than it does with large models, because small models are less able to ignore irrelevant text.

Our research questions were:

1. RQ1: How does chunk size affect retrieval quality for compact embedding models?
2. RQ2: Does chunk overlap help, and how much is enough?
3. RQ3: When does hybrid retrieval outperform dense retrieval alone?

## 2. Related Work

Dense passage retrieval represents queries and passages as vectors and ranks passages by cosine similarity. Sparse methods such as BM25 rank passages by term frequency and inverse document frequency, and remain strong baselines for exact-match queries. Reciprocal Rank Fusion, introduced by Cormack, Clarke and Buettcher in 2009, combines ranked lists by summing 1 / (k + rank) for each document, with k commonly set to 60. It requires no score normalization, which makes it attractive for combining dense and sparse results whose scores are on different scales.

<!-- pagebreak -->

## 3. Method

### 3.1 Corpus and questions

The corpus contains 1,240 PDF documents (about 9,800 pages) from four domains: HR policies, technical manuals, financial reports and contracts. Three annotators wrote 600 questions and marked every passage that contained the answer. Questions were labelled by type:

| Question type | Count | Example |
|---|---|---|
| Factoid with identifier or number | 180 | "What does error code E07 mean?" |
| Factoid, natural language | 210 | "How much notice is required to end the lease early?" |
| Conceptual or paraphrased | 150 | "What happens if the system loses its internet connection?" |
| Multi-passage | 60 | "Compare the deductibles of the three medical plans." |

### 3.2 Configurations

We tested chunk sizes of 250, 500, 800, 1,000, 1,200, 2,000 and 4,000 characters, each with overlaps of 0%, 10%, 20% and 30%. Chunks never crossed page boundaries, so every chunk could be cited with a page number. Retrieval used the top 5 chunks (k = 5). We compared three retrieval methods: dense only (all-MiniLM-L6-v2, cosine similarity), sparse only (BM25 with k1 = 1.5, b = 0.75) and hybrid (RRF of the top 20 results from each method, k = 60).

### 3.3 Metrics

Recall@5 is the share of questions for which at least one relevant chunk appears in the top 5. Precision@5 is the share of retrieved chunks that are relevant. We also measured answer accuracy by giving the retrieved chunks to a 4-billion-parameter local model and having two annotators grade the answers as correct, partially correct or wrong.

<!-- pagebreak -->

## 4. Results

### 4.1 Chunk size (RQ1)

Results for hybrid retrieval with 20% overlap:

| Chunk size (characters) | Recall@5 | Precision@5 | Answer accuracy |
|---|---|---|---|
| 250 | 0.69 | 0.41 | 58% |
| 500 | 0.78 | 0.44 | 66% |
| 800 | 0.83 | 0.42 | 72% |
| 1,000 | 0.84 | 0.40 | 74% |
| 1,200 | 0.84 | 0.37 | 73% |
| 2,000 | 0.81 | 0.29 | 67% |
| 4,000 | 0.76 | 0.20 | 59% |

Very small chunks often split an answer from its context (for example, a table row from its header). Very large chunks dilute the embedding, so the chunk's vector no longer represents any single topic well, and they fill the model's context window with irrelevant text.

### 4.2 Overlap (RQ2)

With 1,000-character chunks, increasing overlap from 0% to 20% raised Recall@5 from 0.79 to 0.84. Raising overlap further to 30% gave no measurable improvement (0.84) but increased index size by 17%. We recommend 15 to 20% overlap.

### 4.3 Retrieval method (RQ3)

Results with 1,000-character chunks and 20% overlap:

| Question type | Dense Recall@5 | BM25 Recall@5 | Hybrid Recall@5 |
|---|---|---|---|
| Identifier or number | 0.52 | 0.88 | 0.91 |
| Natural-language factoid | 0.78 | 0.74 | 0.86 |
| Conceptual or paraphrased | 0.83 | 0.55 | 0.81 |
| Multi-passage | 0.66 | 0.61 | 0.72 |
| All questions | 0.71 | 0.72 | 0.84 |

Dense retrieval struggled with identifiers such as "E07", "INC-2026-0417" or "rate_expired" because the embedding model treats them as rare tokens with little meaning. BM25 found them easily. On conceptual questions, hybrid retrieval was slightly worse than dense alone (0.81 vs 0.83), because BM25 sometimes promoted chunks that shared words with the question but did not answer it.

<!-- pagebreak -->

## 5. Discussion

For small RAG systems, we recommend:

- Chunks of about 1,000 characters with 200 characters of overlap, split within page boundaries so citations can include page numbers.
- Hybrid retrieval with RRF as the default, since its large gains on identifier questions outweigh its small loss on conceptual ones.
- Checking citations after generation: in our answer-accuracy study, 6% of answers from the 4B model cited a page that was not among the retrieved chunks. Flagging such citations makes these errors visible to users.

### 5.1 Limitations

The corpus is English only and uses digitally created PDFs. Scanned documents, which require OCR, were excluded. We did not test reranking models, which may change the optimal chunk size. Results with larger embedding models may differ.

## 6. Conclusion

Chunk size and retrieval method have a larger effect on answer quality in small RAG systems than many practitioners assume. A 1,000-character chunk with 20% overlap and hybrid retrieval improved answer accuracy from 61% (500-character chunks, no overlap, dense only) to 74% in our experiments, without any change to the language model.

## References

1. Cormack, G. V., Clarke, C. L. A., and Buettcher, S. (2009). Reciprocal rank fusion outperforms Condorcet and individual rank learning methods. Proceedings of SIGIR 2009.
2. Robertson, S., and Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond. Foundations and Trends in Information Retrieval.
3. Reimers, N., and Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. Proceedings of EMNLP 2019.
4. Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. Advances in NeurIPS 2020.
