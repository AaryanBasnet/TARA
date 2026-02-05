"""
End-to-End Evaluation - Tests actual agent responses
=====================================================

This script runs real queries through the agent and measures:
1. Response Time
2. Tool Used (correct or not)
3. Answer contains expected keywords

Usage:
    python evaluation/evaluate_e2e.py
"""

import json
import time
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Configuration
DB_DIR = "db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL = "qwen2.5:3b"


def create_rag_chain():
    """Create a simple RAG chain for testing."""
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={'device': 'cpu'}
    )

    db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    retriever = db.as_retriever(search_kwargs={"k": 2})

    llm = ChatOllama(
        model=LLM_MODEL,
        temperature=0,
        num_ctx=2048,
        num_predict=150,
        num_gpu=99,
        keep_alive="30m"
    )

    prompt = ChatPromptTemplate.from_template(
        """Answer based on context only. Be brief.

Context: {context}

Question: {question}

Answer:"""
    )

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain, retriever


def run_evaluation():
    """Run end-to-end evaluation."""
    print("="*60)
    print("END-TO-END EVALUATION")
    print("="*60)

    # Test queries with expected keywords in answer
    test_queries = [
        {
            "question": "Is there free wifi at the airport?",
            "expected_keywords": ["wifi", "free", "available"],
            "category": "facilities"
        },
        {
            "question": "Where is the smoking area?",
            "expected_keywords": ["smoking", "departure", "lounge", "terminal"],
            "category": "facilities"
        },
        {
            "question": "How many mobile phones can I bring?",
            "expected_keywords": ["one", "phone", "mobile", "duty"],
            "category": "customs"
        },
        {
            "question": "Do I need visa for Nepal?",
            "expected_keywords": ["visa", "arrival", "days"],
            "category": "visa"
        },
        {
            "question": "Where can I exchange money?",
            "expected_keywords": ["exchange", "money", "counter", "atm"],
            "category": "facilities"
        },
        {
            "question": "Is wheelchair assistance available?",
            "expected_keywords": ["wheelchair", "available", "airline", "help"],
            "category": "facilities"
        },
        {
            "question": "What is the gold limit for customs?",
            "expected_keywords": ["gold", "gram", "50", "ornament"],
            "category": "customs"
        },
        {
            "question": "How do I get a taxi from airport?",
            "expected_keywords": ["taxi", "prepaid", "arrival"],
            "category": "transport"
        },
        {
            "question": "Can I bring a laptop without duty?",
            "expected_keywords": ["laptop", "one", "18", "duty"],
            "category": "customs"
        },
        {
            "question": "Is there a business lounge?",
            "expected_keywords": ["lounge", "business", "departure"],
            "category": "facilities"
        }
    ]

    print(f"\nCreating RAG chain...")
    chain, retriever = create_rag_chain()

    results = []
    total_time = 0
    correct_answers = 0

    print(f"\nRunning {len(test_queries)} test queries...\n")

    for i, test in enumerate(test_queries, 1):
        question = test["question"]
        expected_keywords = test["expected_keywords"]

        print(f"[{i}/{len(test_queries)}] {question[:50]}...")

        # Measure response time
        start_time = time.time()
        try:
            answer = chain.invoke(question)
            response_time = time.time() - start_time
        except Exception as e:
            answer = f"ERROR: {str(e)}"
            response_time = 0

        total_time += response_time

        # Check if answer contains expected keywords
        answer_lower = answer.lower()
        found_keywords = [kw for kw in expected_keywords if kw.lower() in answer_lower]
        keyword_score = len(found_keywords) / len(expected_keywords)

        is_correct = keyword_score >= 0.5  # At least 50% keywords found
        if is_correct:
            correct_answers += 1

        result = {
            "question": question,
            "answer": answer[:200],
            "expected_keywords": expected_keywords,
            "found_keywords": found_keywords,
            "keyword_score": round(keyword_score * 100, 1),
            "response_time": round(response_time, 2),
            "correct": is_correct,
            "category": test["category"]
        }
        results.append(result)

        status = "✓" if is_correct else "✗"
        print(f"    {status} Time: {response_time:.2f}s | Keywords: {len(found_keywords)}/{len(expected_keywords)}")

    # Calculate metrics
    accuracy = round(correct_answers / len(test_queries) * 100, 1)
    avg_time = round(total_time / len(test_queries), 2)

    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    print(f"  Total Queries: {len(test_queries)}")
    print(f"  Correct Answers: {correct_answers}/{len(test_queries)}")
    print(f"  Accuracy: {accuracy}%")
    print(f"  Average Response Time: {avg_time}s")
    print(f"  Total Time: {round(total_time, 1)}s")

    # Results by category
    print("\n  By Category:")
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"correct": 0, "total": 0}
        categories[cat]["total"] += 1
        if r["correct"]:
            categories[cat]["correct"] += 1

    for cat, data in sorted(categories.items()):
        cat_acc = round(data["correct"] / data["total"] * 100, 1)
        print(f"    {cat}: {cat_acc}% ({data['correct']}/{data['total']})")

    # Save results
    os.makedirs("evaluation/results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"evaluation/results/e2e_results_{timestamp}.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "metadata": {
                "date": datetime.now().isoformat(),
                "model": LLM_MODEL,
                "total_queries": len(test_queries),
                "accuracy": accuracy,
                "avg_response_time": avg_time
            },
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n  Results saved to: {output_path}")

    # Show failures
    failures = [r for r in results if not r["correct"]]
    if failures:
        print(f"\n  Failed Queries ({len(failures)}):")
        for f in failures:
            print(f"    Q: {f['question']}")
            print(f"    Expected: {f['expected_keywords']}")
            print(f"    Found: {f['found_keywords']}")
            print(f"    Answer: {f['answer'][:100]}...")
            print()


if __name__ == "__main__":
    run_evaluation()
