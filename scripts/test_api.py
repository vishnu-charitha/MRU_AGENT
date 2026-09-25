import requests
import json
import os
import sys

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    report = []
    
    # 1. Health checks
    try:
        r_health = requests.get(f"{BASE_URL}/health")
        report.append({"endpoint": "/health", "status_code": r_health.status_code, "response": r_health.json()})
        
        r_api_health = requests.get(f"{BASE_URL}/api/health")
        report.append({"endpoint": "/api/health", "status_code": r_api_health.status_code, "response": r_api_health.json()})
    except Exception as e:
        print(f"Failed to connect to server: {e}")
        sys.exit(1)

    # 2. Chat Tests
    test_queries = [
        {"question": "What are the B.Tech admission eligibility requirements?"},
        {"question": "What are the B.Tech fees?", "program": "B.Tech"},
        {"question": "What departments are available at MRDU?"},
        {"question": "What is the MR24 regulation?", "regulation": "MR24"},
        {"question": "What information is available about the Tirupati campus?", "campus": "tirupati"},
        {"question": "What is the examination timetable?"},
        {"question": "What is the MBA admission process?"},
        {"question": "What is the BCA admission process?"}
    ]

    for req_data in test_queries:
        r = requests.post(f"{BASE_URL}/api/chat", json=req_data)
        if r.status_code == 200:
            res_json = r.json()
            is_out_of_scope = "out of scope" in res_json["answer"].lower()
            report.append({
                "request": req_data,
                "status_code": r.status_code,
                "answer": res_json["answer"],
                "source_count": len(res_json["sources"]),
                "out_of_scope_detected": is_out_of_scope
            })
        else:
            report.append({
                "request": req_data,
                "status_code": r.status_code,
                "error": r.text
            })

    report_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'api_test_report.json')
    with open(report_path, "w", encoding='utf-8') as f:
        json.dump(report, f, indent=2)
        
    print(f"API Test completed. Results saved to {report_path}")

if __name__ == "__main__":
    run_tests()
