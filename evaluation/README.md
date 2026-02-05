# TIA Virtual Assistant - Evaluation Guide

## Overview

This folder contains evaluation tools for measuring the performance of the TIA Virtual Assistant system for thesis documentation.

## Evaluation Metrics

### 1. Retrieval Accuracy (RAG)
- **Hit@K**: Percentage of queries where the correct document appears in top K results
- **MRR (Mean Reciprocal Rank)**: Average of 1/rank for correct documents

### 2. Tool Selection Accuracy
- Measures if the agent selects the correct tool for each query type
- Tools: Flight Status, Route Search, Weather, KYC, General Info (RAG)

### 3. Answer Quality
- **Keyword Match**: Does the answer contain expected keywords?
- **Faithfulness**: Is the answer grounded in retrieved context?
- **Relevancy**: Does the answer address the question?

### 4. Performance
- **Response Time**: Average time per query
- **Throughput**: Queries per minute

## Files

| File | Description |
|------|-------------|
| `test_dataset.json` | 50 test questions with expected answers |
| `evaluate_system.py` | Retrieval and tool selection evaluation |
| `evaluate_e2e.py` | End-to-end response quality evaluation |
| `results/` | Generated evaluation reports |

## Running Evaluations

### Basic Evaluation (No LLM calls)
```bash
python evaluation/evaluate_system.py
```

### End-to-End Evaluation (Requires Ollama)
```bash
python evaluation/evaluate_e2e.py
```

### Full RAGAS Evaluation (Advanced)
```bash
python evaluate.py
```

## Expected Results for Thesis

### Good Performance Targets:
- Hit@3: > 70%
- Tool Selection: > 90%
- Response Time: < 15s (GPU) / < 30s (CPU)

### Current Results (as of evaluation):
- Hit@3: 57.5%
- Tool Selection: 93.75%
- MRR: 0.506

## Improvement Strategies

1. **Improve Retrieval**:
   - Add synonyms to documents
   - Fine-tune chunk sizes
   - Use hybrid search (keyword + semantic)

2. **Improve Answer Quality**:
   - Better prompt engineering
   - Add few-shot examples
   - Use larger LLM model

3. **Reduce Response Time**:
   - Use GPU acceleration
   - Reduce context window
   - Cache frequent queries

## Thesis Documentation

For your thesis, include:
1. Methodology section explaining evaluation approach
2. Results tables with all metrics
3. Comparison with baseline (if available)
4. Error analysis section
5. Future improvement recommendations
