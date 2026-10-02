import json
import uuid

# Define the categories and required questions based on prompt instructions
categories = [
    "B.Tech admissions and eligibility",
    "M.Tech admissions and eligibility",
    "Fees and admission procedures",
    "B.Tech/M.Tech academic regulations",
    "MR20, MR21, MR22 and MR24 regulations",
    "Engineering departments, faculty and syllabus",
    "Examination timetables, fees, results and circulars",
    "University information and student policies",
    "Tirupati campus information",
    "Unanswerable or unavailable questions",
    "Multi-turn follow-up questions"
]

questions = [
    # B.Tech Admissions
    ("What are the eligibility criteria for B.Tech admission at MRDU?", 0, True),
    ("Is there an entrance exam for B.Tech?", 0, True),
    ("What is the intake capacity for B.Tech CSE?", 0, True),
    ("Can lateral entry students apply for B.Tech?", 0, True),
    ("What is the application deadline for B.Tech?", 0, True),

    # M.Tech Admissions
    ("What are the eligibility criteria for M.Tech?", 1, True),
    ("Do I need a valid GATE score for M.Tech admissions?", 1, True),
    ("Which specializations are offered in M.Tech?", 1, True),
    ("What is the intake for M.Tech in Computer Science?", 1, True),
    ("How do I apply for the M.Tech program?", 1, True),

    # Fees and Admission Procedures
    ("What is the annual tuition fee for B.Tech?", 2, True),
    ("What are the hostel fees per year?", 2, True),
    ("Is there any application fee during the admission process?", 2, True),
    ("What documents are required at the time of admission?", 2, True),
    ("Does MRDU offer any scholarships for merit students?", 2, True),

    # B.Tech/M.Tech Academic Regulations
    ("How is the CGPA calculated for B.Tech students?", 3, True),
    ("What is the minimum attendance required to appear for exams?", 3, True),
    ("Are there any provisions for makeup exams?", 3, True),
    ("How many credits are required to graduate with a B.Tech degree?", 3, True),

    # MR20, MR21, MR22, MR24 Regulations
    ("What are the key changes introduced in the MR24 regulation?", 4, True),
    ("Under MR22 regulation, how are the mid-term exams weighted?", 4, True),
    ("Can a student from MR20 regulation switch to MR24?", 4, True),
    ("What is the promotion criteria under MR21 regulation?", 4, True),

    # Engineering Departments, Faculty and Syllabus
    ("Who is the Head of the Computer Science Department?", 5, True),
    ("What is the syllabus for the first year B.Tech CSE?", 5, True),
    ("How many faculty members does the ECE department have?", 5, True),
    ("Are there specialized labs for Artificial Intelligence?", 5, True),

    # Examinations
    ("Where can I find the examination timetable for the current semester?", 6, True),
    ("What is the fee for semester-end examinations?", 6, True),
    ("How long does it take for semester results to be announced?", 6, True),
    ("Where are the latest result circulars posted?", 6, True),

    # University Info and Policies
    ("What are the library timings at MRDU?", 7, True),
    ("Is there a strict dress code for students on campus?", 7, True),
    ("What anti-ragging policies are in place?", 7, True),
    ("Where is the main campus of MRDU located?", 7, True),

    # Tirupati Campus
    ("Where is the MRDU Tirupati campus located?", 8, True),
    ("Which courses are offered at the Tirupati off-campus?", 8, True),
    ("Are the placement drives for Tirupati students held separately?", 8, True),
    ("Who is the director of the Tirupati campus?", 8, True),

    # Unanswerable / Unavailable
    ("What is the admission fee for the MBA program?", 9, False), # MBA is out of scope
    ("Can I apply for a Ph.D. in English literature?", 9, False), # Unrelated / out of scope
    ("What is the exact date for the annual sports meet next year?", 9, False),
    ("How many students failed the MR22 exams last year?", 9, False),
    ("Tell me the exact recipe used in the campus cafeteria.", 9, False),

    # Multi-turn Follow-up
    ("What are the eligibility criteria for B.Tech?", 10, True, "conv-1"),
    ("What about the fees for that program?", 10, True, "conv-1", [{"role": "user", "content": "What are the eligibility criteria for B.Tech?"}, {"role": "assistant", "content": "The candidate must have passed 10+2 with 60% aggregate..."}]),
    ("What documents do I need to bring?", 10, True, "conv-1", [{"role": "user", "content": "What are the eligibility criteria for B.Tech?"}, {"role": "assistant", "content": "The candidate must have passed 10+2 with 60% aggregate..."}, {"role": "user", "content": "What about the fees for that program?"}, {"role": "assistant", "content": "The annual fee is..."}]),

    ("Where is the Tirupati campus?", 10, True, "conv-2"),
    ("Are B.Tech CSE courses offered there?", 10, True, "conv-2", [{"role": "user", "content": "Where is the Tirupati campus?"}, {"role": "assistant", "content": "It is located in Renigunta Mandal, Tirupati District..."}]),
    ("Does the main campus have the same courses?", 10, True, "conv-2", [{"role": "user", "content": "Where is the Tirupati campus?"}, {"role": "assistant", "content": "It is located in Renigunta Mandal, Tirupati District..."}, {"role": "user", "content": "Are B.Tech CSE courses offered there?"}, {"role": "assistant", "content": "Yes, B.Tech CSE is offered."}])
]

dataset = []
for idx, item in enumerate(questions):
    q_text = item[0]
    cat_idx = item[1]
    answerable = item[2]

    conv_id = None
    history = []
    if len(item) > 3:
        conv_id = item[3]
    if len(item) > 4:
        history = item[4]

    if conv_id is None:
        conv_id = f"single-{idx}"

    record = {
        "test_id": f"eval-{idx+1:03d}",
        "question": q_text,
        "expected_answer": "DRAFT_ANSWER_REQUIRES_VERIFICATION",
        "expected_source_urls": ["https://mrdu.edu.in/draft"],
        "expected_document_ids": ["draft_doc_1"],
        "relevant_contexts": ["Draft context pending verification against MRDU_Chatbot_Knowledge_Base_100pages.md"],
        "category": categories[cat_idx],
        "answerable": answerable,
        "conversation_id": conv_id,
        "conversation_history": history,
        "evaluation_notes": "Draft record. Requires manual verification against the official knowledge base."
    }
    dataset.append(record)

with open('evaluation/datasets/mrdu_eval.jsonl', 'w') as f:
    for row in dataset:
        f.write(json.dumps(row) + '\n')

print(f"Generated {len(dataset)} evaluation records.")
