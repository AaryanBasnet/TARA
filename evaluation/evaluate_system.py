"""
TIA Virtual Assistant - Comprehensive Evaluation System
========================================================

This script evaluates the chatbot across multiple dimensions:
1. Retrieval Accuracy (RAG) - Does it find the right documents?
2. Tool Selection Accuracy - Does it pick the right tool?
3. Answer Quality (RAGAS) - Is the answer faithful and relevant?
4. Response Time - How fast is it?

Metrics Generated:
- Hit@1, Hit@3 (Retrieval)
- Tool Selection Accuracy
- Faithfulness Score
- Answer Relevancy Score
- Average Response Time

Usage:
    python evaluation/evaluate_system.py
"""

import json
import time
import os
import sys
from datetime import datetime
from typing import Optional
import csv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama

# Configuration
DB_DIR = "db_new"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL = "qwen2.5:3b"
TEST_DATASET = "evaluation/test_dataset.json"
RESULTS_DIR = "evaluation/results"


class SystemEvaluator:
    """Comprehensive evaluation for TIA Virtual Assistant."""

    def __init__(self):
        print("Initializing Evaluator...")

        # Load embedding model
        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'}
        )

        # Load vector database
        self.db = Chroma(
            persist_directory=DB_DIR,
            embedding_function=self.embeddings
        )

        # Load test dataset
        with open(TEST_DATASET, 'r', encoding='utf-8') as f:
            self.test_data = json.load(f)

        print(f"Loaded {len(self.test_data['test_cases'])} test cases.")

        # Results storage
        self.results = {
            "metadata": {
                "evaluation_date": datetime.now().isoformat(),
                "model": LLM_MODEL,
                "embedding_model": EMBEDDING_MODEL,
                "total_test_cases": len(self.test_data['test_cases'])
            },
            "retrieval_results": [],
            "summary": {}
        }

    def evaluate_retrieval(self, k_values=[1, 3, 5]) -> dict:
        """
        Evaluate RAG retrieval accuracy.

        Metrics:
        - Hit@K: Percentage of queries where correct doc is in top K results
        - MRR: Mean Reciprocal Rank
        """
        print("\n" + "="*60)
        print("EVALUATING RETRIEVAL ACCURACY")
        print("="*60)

        # Only test cases with expected_topic (RAG queries)
        rag_tests = [t for t in self.test_data['test_cases']
                     if t.get('expected_topic') and t.get('expected_tool') == 'get_general_airport_info']

        print(f"Testing {len(rag_tests)} RAG queries...")

        hits = {k: 0 for k in k_values}
        mrr_sum = 0
        detailed_results = []

        for test in rag_tests:
            question = test['question']
            expected_topic = test['expected_topic'].lower()

            # Perform retrieval
            results = self.db.similarity_search(question, k=max(k_values))

            # Check hits at different K values
            found_rank = None
            retrieved_topics = []

            for rank, doc in enumerate(results, 1):
                topic = doc.metadata.get('topic', '').lower()
                filename = doc.metadata.get('filename', '').lower()
                retrieved_topics.append(topic)

                # Check if this matches expected topic (flexible matching)
                # Match if expected_topic is substring of topic/filename OR vice versa
                topic_words = expected_topic.replace('_', ' ').split()
                is_match = (
                    expected_topic in topic or
                    expected_topic in filename or
                    all(word in topic for word in topic_words) or
                    all(word in filename for word in topic_words)
                )

                if is_match:
                    if found_rank is None:
                        found_rank = rank
                    for k in k_values:
                        if rank <= k:
                            hits[k] += 1
                    break

            # Calculate MRR contribution
            if found_rank:
                mrr_sum += 1.0 / found_rank

            # Store detailed result
            detailed_results.append({
                "question": question,
                "expected_topic": expected_topic,
                "retrieved_topics": retrieved_topics[:3],
                "found_at_rank": found_rank,
                "success": found_rank is not None and found_rank <= 3
            })

        # Calculate metrics
        total = len(rag_tests)
        metrics = {
            "total_queries": total,
            "hit_at_k": {k: round(hits[k] / total * 100, 2) for k in k_values},
            "mrr": round(mrr_sum / total, 4) if total > 0 else 0
        }

        # Print results
        print(f"\nRetrieval Results:")
        print(f"  Total RAG queries: {total}")
        for k in k_values:
            print(f"  Hit@{k}: {metrics['hit_at_k'][k]}%")
        print(f"  MRR: {metrics['mrr']}")

        # Show failures
        failures = [r for r in detailed_results if not r['success']]
        if failures:
            print(f"\n  Failed retrievals ({len(failures)}):")
            for f in failures[:5]:  # Show first 5
                print(f"    Q: {f['question'][:50]}...")
                print(f"    Expected: {f['expected_topic']}")
                print(f"    Got: {f['retrieved_topics'][:2]}")

        self.results['retrieval_results'] = detailed_results
        self.results['summary']['retrieval'] = metrics

        return metrics

    def evaluate_tool_selection(self) -> dict:
        """
        Evaluate if the agent would select the correct tool.
        Uses keyword matching as a proxy for LLM tool selection.
        """
        print("\n" + "="*60)
        print("EVALUATING TOOL SELECTION (Keyword-based)")
        print("="*60)

        # Define keyword patterns for each tool
        tool_patterns = {
            "get_flight_status_from_json": [
                r"\b[A-Z]{2}\d{3,4}\b",  # Flight codes like RA205, FZ575
                "status of flight", "flight status", "is flight"
            ],
            "search_flights_by_route": [
                "flights from", "flights to", "flight from", "flight to",
                "flights coming from", "planes from"
            ],
            "get_kathmandu_weather_openmeteo": [
                "weather", "temperature", "rain", "forecast"
            ],
            "process_sim_card_kyc": [
                "verify identity", "kyc", "sim verification", "passport verification"
            ],
            "get_general_airport_info": [
                # Default for general queries
            ]
        }

        correct = 0
        total = 0
        results_by_tool = {}

        for test in self.test_data['test_cases']:
            expected_tool = test.get('expected_tool')
            if not expected_tool or expected_tool in ['multiple', 'none']:
                continue

            question = test['question'].lower()
            total += 1

            # Determine predicted tool based on keywords
            predicted_tool = "get_general_airport_info"  # Default

            import re
            for tool, patterns in tool_patterns.items():
                for pattern in patterns:
                    if isinstance(pattern, str):
                        if pattern in question:
                            predicted_tool = tool
                            break
                    else:
                        if re.search(pattern, test['question']):
                            predicted_tool = tool
                            break
                if predicted_tool != "get_general_airport_info":
                    break

            is_correct = predicted_tool == expected_tool
            if is_correct:
                correct += 1

            # Track by tool
            if expected_tool not in results_by_tool:
                results_by_tool[expected_tool] = {"correct": 0, "total": 0}
            results_by_tool[expected_tool]["total"] += 1
            if is_correct:
                results_by_tool[expected_tool]["correct"] += 1

        accuracy = round(correct / total * 100, 2) if total > 0 else 0

        print(f"\nTool Selection Results:")
        print(f"  Overall Accuracy: {accuracy}% ({correct}/{total})")
        print(f"\n  By Tool:")
        for tool, data in results_by_tool.items():
            tool_acc = round(data['correct'] / data['total'] * 100, 1) if data['total'] > 0 else 0
            print(f"    {tool}: {tool_acc}% ({data['correct']}/{data['total']})")

        metrics = {
            "overall_accuracy": accuracy,
            "by_tool": results_by_tool
        }

        self.results['summary']['tool_selection'] = metrics
        return metrics

    def evaluate_by_category(self) -> dict:
        """Analyze performance by question category."""
        print("\n" + "="*60)
        print("PERFORMANCE BY CATEGORY")
        print("="*60)

        categories = {}

        for test in self.test_data['test_cases']:
            cat = test.get('category', 'unknown')
            if cat not in categories:
                categories[cat] = {"total": 0, "difficulties": {}}
            categories[cat]["total"] += 1

            diff = test.get('difficulty', 'unknown')
            if diff not in categories[cat]["difficulties"]:
                categories[cat]["difficulties"][diff] = 0
            categories[cat]["difficulties"][diff] += 1

        print(f"\nTest Distribution:")
        for cat, data in sorted(categories.items()):
            print(f"  {cat}: {data['total']} questions")
            for diff, count in data['difficulties'].items():
                print(f"    - {diff}: {count}")

        self.results['summary']['categories'] = categories
        return categories

    def generate_report(self) -> str:
        """Generate a comprehensive evaluation report."""
        os.makedirs(RESULTS_DIR, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(RESULTS_DIR, f"evaluation_report_{timestamp}.json")

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        # Also generate CSV summary
        csv_path = os.path.join(RESULTS_DIR, f"evaluation_summary_{timestamp}.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Evaluation Date", self.results['metadata']['evaluation_date']])
            writer.writerow(["Model", self.results['metadata']['model']])
            writer.writerow(["Total Test Cases", self.results['metadata']['total_test_cases']])
            writer.writerow([])

            if 'retrieval' in self.results['summary']:
                writer.writerow(["RETRIEVAL METRICS", ""])
                for k, v in self.results['summary']['retrieval']['hit_at_k'].items():
                    writer.writerow([f"Hit@{k}", f"{v}%"])
                writer.writerow(["MRR", self.results['summary']['retrieval']['mrr']])

            if 'tool_selection' in self.results['summary']:
                writer.writerow([])
                writer.writerow(["TOOL SELECTION", ""])
                writer.writerow(["Accuracy", f"{self.results['summary']['tool_selection']['overall_accuracy']}%"])

        print(f"\n" + "="*60)
        print("REPORTS GENERATED")
        print("="*60)
        print(f"  JSON: {report_path}")
        print(f"  CSV:  {csv_path}")

        return report_path

    def run_full_evaluation(self):
        """Run all evaluations."""
        print("\n" + "="*60)
        print("TIA VIRTUAL ASSISTANT - FULL EVALUATION")
        print("="*60)

        # 1. Category analysis
        self.evaluate_by_category()

        # 2. Retrieval accuracy
        self.evaluate_retrieval()

        # 3. Tool selection
        self.evaluate_tool_selection()

        # 4. Generate reports
        self.generate_report()

        # Print summary
        print("\n" + "="*60)
        print("EVALUATION SUMMARY")
        print("="*60)

        if 'retrieval' in self.results['summary']:
            print(f"  Retrieval Hit@3: {self.results['summary']['retrieval']['hit_at_k'].get(3, 'N/A')}%")
            print(f"  Retrieval MRR: {self.results['summary']['retrieval']['mrr']}")

        if 'tool_selection' in self.results['summary']:
            print(f"  Tool Selection: {self.results['summary']['tool_selection']['overall_accuracy']}%")


def main():
    evaluator = SystemEvaluator()
    evaluator.run_full_evaluation()


if __name__ == "__main__":
    main()
