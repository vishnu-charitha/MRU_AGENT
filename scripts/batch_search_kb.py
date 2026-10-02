import json

with open('MRDU_Chatbot_Knowledge_Base_100pages.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

queries = {
    'eval-016': ['CGPA calculated', 'Choice Based Credit System', 'OBE'],
    'eval-017': ['minimum attendance', 'attendance requirement'],
    'eval-018': ['makeup exam', 'supplementary exam', 'advanced supplementary'],
    'eval-019': ['credits are required', '160 credits'],
    'eval-020': ['MR24 regulation'],
    'eval-021': ['MR22 regulation', 'mid-term exam', 'mid-term weight'],
    'eval-022': ['switch to MR24', 'MR20', 'regulation transfer'],
    'eval-023': ['promotion criteria', 'MR21'],
    'eval-024': ['Head of the Computer Science', 'HoD', 'K. Vasanth Kumar'],
    'eval-025': ['syllabus for the first year B.Tech CSE', 'Freshman Engineering']
}

with open('batch_search_output.txt', 'w', encoding='utf-8') as out:
    for test_id, terms in queries.items():
        out.write(f"\n--- {test_id} ---\n")
        for term in terms:
            count = 0
            for i, line in enumerate(lines):
                if term.lower() in line.lower():
                    out.write(f"L{i+1}: {line.strip()}\n")
                    count += 1
                    if count >= 3:
                        break
