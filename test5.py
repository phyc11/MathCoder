import requests
from bs4 import BeautifulSoup
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

def extract_vietjack(url, idx, skipped_links):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    bold_green = soup.find("b", style="color:green;")
    if not bold_green:
        return None

    problem_tag = bold_green.find_parent("p")
    if not problem_tag:
        return None

    has_img_in_problem = False
    problem_lines = [problem_tag.get_text(strip=True)]

    for sibling in problem_tag.find_next_siblings():
        # Nếu sibling là ảnh hoặc là p nhưng chứa img thì bỏ qua link
        if sibling.name == "img" or (sibling.name == "p" and sibling.find("img")):
            has_img_in_problem = True
            break
        if sibling.name == "table" or (sibling.name == "p" and sibling.find("table")):
            has_img_in_problem = True
            break
        if sibling.name != "p":
            continue
        if sibling.find("b", style="color:green;") and "Lời giải" in sibling.get_text():
            break
        problem_lines.append(sibling.get_text(strip=True))

    problem_text = "\n".join(problem_lines).strip()

    solution_tag = soup.find("p", string=lambda text: text and "Lời giải:" in text)
    if not solution_tag:
        return None

    has_img_in_solution = False
    solution_lines = []
    answer_text = []
    collecting = False

    for sibling in solution_tag.find_next_siblings():
        # Nếu sibling là ảnh hoặc là p nhưng chứa img thì bỏ qua link
        if sibling.name == "img" or (sibling.name == "p" and sibling.find("img")):
            has_img_in_solution = True
            break
        if sibling.name == "table" or (sibling.name == "p" and sibling.find("table")):
            has_img_in_solution = True
            break
        if sibling.name != "p":
            continue
        text = sibling.get_text(strip=True)
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

    if has_img_in_problem or has_img_in_solution:
        print(f"⚠️ Bỏ qua link {url} vì phần problem hoặc solution có chứa ảnh.")
        skipped_links.append(url)
        return None

    solution_text = "\n".join(solution_lines)
    answer_final = "\n".join(answer_text)
    if not answer_final or answer_final =="a)\nb)" or answer_final =="a)\nb)\nc)" or answer_final =="a)\nb)\nc)\nd)":
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
    skipped_links = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(extract_vietjack, link, idx, skipped_links): (link, idx) for idx, link in enumerate(links, start=1)}
        for future in as_completed(futures):
            data = future.result()
            link, idx = futures[future]
            if data:
                all_data.append(data)
                print(f"✅ Đã lấy dữ liệu bài {idx}: {link}")
            else:
                print(f"❌ Không lấy được dữ liệu bài {idx}: {link}")
    return all_data, skipped_links

if __name__ == "__main__":
    with open('valid_links.txt', 'r', encoding='utf-8') as file:
        links = [line.strip() for line in file if line.strip()]

    print(f"🔎 Đang lấy dữ liệu từ {len(links)} link...")
    all_data, skipped_links = extract_all_data(links)

    # Ghi dữ liệu hợp lệ vào file output_data.jsonl
    with open('Math6/raw/Math6_kn_raw.txt', 'w', encoding='utf-8') as f:
        for item in all_data:
            json_line = json.dumps(item, ensure_ascii=False)
            f.write(json_line + '\n')

    # Ghi các link bị bỏ qua vào skipped_links.txt
    with open('skipped_links_Math6_kn.txt', 'w', encoding='utf-8') as f:
        for link in skipped_links:
            f.write(link + '\n')

    print("✅ Hoàn thành! Dữ liệu đã lưu vào 'output_data.jsonl'")
    print("📂 Danh sách link bị bỏ qua (có ảnh) đã lưu vào 'skipped_links.txt'")
