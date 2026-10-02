import json
import os
import argparse
from datetime import datetime

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Setup environment before importing services
from dotenv import load_dotenv
load_dotenv()

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    LLMContextPrecisionWithReference as ContextPrecision,
    LLMContextRecall as ContextRecall,
    Faithfulness,
    AnswerRelevancy
)
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings

# Import RAG service
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.services.rag_service import get_rag_service

def load_dataset(filepath):
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def run_evaluation(dataset, subset_size=None):
    rag_service = get_rag_service()

    # Filter out unverified records
    dataset = [item for item in dataset if item.get('evaluation_notes') == "VERIFIED"]

    print("Selected Test IDs for Evaluation:", [item.get('test_id') for item in dataset])
    print("Verification Statuses:", [item.get('evaluation_notes') for item in dataset])

    if subset_size:
        dataset = dataset[:subset_size]

    print("Final Evaluated Test IDs:", [item.get('test_id') for item in dataset])

    print(f"Evaluating {len(dataset)} questions...")

    eval_results = []

    # Ragas required format (as of 0.4.x, dataset format can be list of dicts or HF Dataset)
    # The expected keys are: question, answer, contexts, ground_truth
    ragas_data = {
        "user_input": [],       # In ragas 0.4.x, some metrics expect user_input
        "question": [],
        "response": [],         # In ragas 0.4.x, answer is renamed to response in some cases
        "answer": [],
        "retrieved_contexts": [], # contexts is now retrieved_contexts
        "contexts": [],
        "reference": [],          # ground_truth is now reference
        "ground_truth": []
    }

    from openai import AsyncOpenAI
    from ragas.llms import llm_factory

    # Initialize evaluator LLM
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        print("Warning: OPENROUTER_API_KEY not found. Ragas metrics will fail.")
        llm = None
    else:
        openai_client = AsyncOpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1", timeout=30.0, max_retries=1)
        llm = llm_factory(
            model=os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it"),
            client=openai_client
        )

    from langchain_community.embeddings import HuggingFaceEmbeddings as LcHuggingFaceEmbeddings
    lc_embeddings = LcHuggingFaceEmbeddings(model_name=os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2'))
    from ragas.embeddings import LangchainEmbeddingsWrapper
    embeddings = LangchainEmbeddingsWrapper(lc_embeddings)

    # Ragas 0.4.3 hack for AnswerRelevancy
    if not hasattr(embeddings, 'embed_query'):
        embeddings.embed_query = lambda text: lc_embeddings.embed_query(text)

    # Ragas 0.4.x workaround to bypass _validate_embeddings
    embeddings.__class__.__name__ = "OpenAIEmbeddings"

    metrics = [
        ContextPrecision(llm=llm),
        ContextRecall(llm=llm),
        Faithfulness(llm=llm),
        AnswerRelevancy(llm=llm, embeddings=embeddings)
    ]

    for item in dataset:
        query = item['question']
        history = item.get('conversation_history', [])

        # Call RAG pipeline
        hits = rag_service.retrieve(query=query)
        response = rag_service.generate_answer(query=query, hits=hits, history=history)

        answer = response['answer']

        # Extract contexts
        retrieved_contexts = []
        for h in hits:
            retrieved_contexts.append(h.payload.get('content', ''))

        eval_result = {
            "test_id": item['test_id'],
            "question": query,
            "expected_answer": item['expected_answer'],
            "generated_answer": answer,
            "retrieved_contexts": retrieved_contexts,
            "category": item['category'],
            "answerable": item['answerable']
        }
        eval_results.append(eval_result)

        # Add to Ragas dataset
        ragas_data["question"].append(query)
        ragas_data["user_input"].append(query)
        ragas_data["answer"].append(answer)
        ragas_data["response"].append(answer)
        ragas_data["contexts"].append(retrieved_contexts)
        ragas_data["retrieved_contexts"].append(retrieved_contexts)
        ragas_data["ground_truth"].append(item['expected_answer'])
        ragas_data["reference"].append(item['expected_answer'])

    hf_dataset = Dataset.from_dict(ragas_data)

    from ragas import RunConfig

    try:
        run_config = RunConfig(timeout=30, max_retries=1)
        ragas_result = evaluate(
            dataset=hf_dataset,
            metrics=metrics,
            llm=llm,
            embeddings=embeddings,
            run_config=run_config,
            raise_exceptions=False
        )
        print("Ragas Evaluation Complete.")

        df = ragas_result.to_pandas()
        df.to_csv('evaluation/results/ragas_detailed_results.csv', index=False)
        for i, row in df.iterrows():
            eval_results[i]['context_precision'] = row.get('context_precision', None)
            eval_results[i]['context_recall'] = row.get('context_recall', None)
            eval_results[i]['faithfulness'] = row.get('faithfulness', None)
            eval_results[i]['answer_relevancy'] = row.get('answer_relevancy', None)

    except Exception as e:
        print(f"Error during Ragas evaluation: {e}")

    return eval_results, ragas_result if 'ragas_result' in locals() else None

def save_reports(eval_results, summary):
    os.makedirs('evaluation/results', exist_ok=True)

    with open('evaluation/results/per_question_results.jsonl', 'w', encoding='utf-8') as f:
        for res in eval_results:
            f.write(json.dumps(res) + '\n')

    with open('evaluation/results/summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=4)

    with open('evaluation/results/latest_results.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=4)

    report = f"# MRDU Chatbot Evaluation Report\n\n"
    report += f"**Date**: {datetime.now().isoformat()}\n\n"
    report += f"## Summary\n"
    report += f"- Total Questions Evaluated: {summary.get('total', 0)}\n"

    for k, v in summary.items():
        if k != 'total':
            report += f"- **{k}**: {v}\n"

    report += "\n## Recommended Corrective Actions\n"
    report += "1. Verify the 'expected_answer' in mrdu_eval.jsonl manually against the 100-page knowledge base.\n"
    report += "2. Execute this runner fully to obtain the baseline.\n"

    with open('evaluation/results/evaluation_report.md', 'w', encoding='utf-8') as f:
        f.write(report)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--subset", type=int, default=None, help="Run a subset of queries")
    args = parser.parse_args()

    data = load_dataset('evaluation/datasets/mrdu_eval.jsonl')
    results, ragas_summary = run_evaluation(data, subset_size=args.subset)

    summary_data = {"total": len(results)}
    if ragas_summary:
        # In ragas 0.4.x, ragas_result is an EvaluationResult object
        if hasattr(ragas_summary, 'to_pandas'):
            summary_dict = ragas_summary.to_pandas().to_dict('records')[0]
        else:
            try:
                summary_dict = dict(ragas_summary)
            except Exception:
                summary_dict = vars(ragas_summary)
        for k, v in summary_dict.items():
            summary_data[k] = v

    save_reports(results, summary_data)
    print("Reports saved to evaluation/results/")
