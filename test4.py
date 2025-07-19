import requests
from bs4 import BeautifulSoup
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

def extract_vietjack(url, idx):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    problem_lines = []
    bold_green = soup.find("b", style="color:green;")
    if not bold_green:
        return None

    problem_tag = bold_green.find_parent("p")
    problem_lines = [problem_tag.get_text(strip=True)]
    for sibling in problem_tag.find_next_siblings():
        if sibling.name != "p":
            continue
        if sibling.find("b", style="color:green;") and "Lời giải" in sibling.get_text():
            break
        text = sibling.get_text(strip=True)
        problem_lines.append(text)

    problem_text = "\n".join(problem_lines).strip()

    solution_tag = soup.find("p", string=lambda text: text and "Lời giải:" in text)
    if not solution_tag:
        return None 

    solution_lines = []
    answer_text = []
    collecting = False

    for sibling in solution_tag.find_next_siblings():
        if sibling.name != "p":
            continue
        text = sibling.get_text(strip=True)
        if not text:
            continue
        if "Xem thêm" in text or text.startswith("Bài "):
            break

        solution_lines.append(text)

        if any(phrase in text for phrase in ["Do đó", "Vậy", "Vì vậy"]):
            collecting = True
            answer_text.append(text)
            continue

        for marker in ["a)", "b)", "c)", "d)"]:
            if marker in text:
                answer_text.append(marker)
                collecting = False
                break

        if collecting:
            answer_text.append(text)

    solution_text = "\n".join(solution_lines)
    answer_final = "\n".join(answer_text)
    if not answer_final:
        answer_final = solution_text

    return {
        "id": str(idx),
        "messages": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "content": "Below is a math problem. Please solve it step by step."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "content": problem_text
                    }
                ]
            }
        ],
        "ground_truth": {
            "solution": solution_text,
            "answer": answer_final
        }
    }

def extract_all_data(links):
    all_data = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(extract_vietjack, link, idx): (link, idx) for idx, link in enumerate(links, start=1)}
        for future in as_completed(futures):
            data = future.result()
            link, idx = futures[future]
            if data:
                all_data.append(data)
                print(f"✅ Đã lấy dữ liệu bài {idx}: {link}")
            else:
                print(f"❌ Không lấy được dữ liệu bài {idx}: {link}")
    return all_data

if __name__ == "__main__":
    with open('valid_links.txt', 'r', encoding='utf-8') as file:
        links = [line.strip() for line in file if line.strip()]

    print(f"🔎 Đang lấy dữ liệu từ {len(links)} link...")
    all_data = extract_all_data(links)

    with open('output_data.jsonl', 'w', encoding='utf-8') as f:
        for item in all_data:
            json_line = json.dumps(item, ensure_ascii=False)
            f.write(json_line + '\n')

    print("✅ Hoàn thành! Dữ liệu đã lưu vào 'output_data.jsonl'")
