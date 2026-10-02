import pandas as pd
import json

df = pd.read_csv('evaluation/results/ragas_detailed_results.csv')

print("Columns in CSV:", df.columns.tolist())

# Dump the rows for eval-002 and eval-003 to JSON for easy reading
for index, row in df.iterrows():
    print(f"\n--- Question: {row['question']} ---")

    # We want to check faithfulness logic for eval-002 and answer_relevancy logic for eval-003
    # Look for explanation columns or similar
    interesting_cols = [c for c in df.columns if 'explanation' in c or c in ['faithfulness', 'answer_relevancy', 'question', 'answer', 'contexts', 'ground_truth']]
    for c in interesting_cols:
        if c in row:
            print(f"{c}: {row[c]}")
