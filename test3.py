import requests
from bs4 import BeautifulSoup
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

def check_url(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("Tìm thấy:", url)
            return url
        else:
            print("Không tồn tại:", url)
    except requests.RequestException:
        print("Lỗi khi truy cập:", url)
    return None

def generate_valid_links():
    base = "https://vietjack.com/sbt-toan-6-ket-noi/"
    urls = []

    for tap in [1, 2]:  
        for start in range(1, 10):
            for end in range(1, 100):  
                for page in range(1, 100):
                    slug = f"bai-{start}-{end}-trang-{page}-sbt-toan-lop-6-tap-{tap}-ket-noi.jsp"
                    url = base + slug
                    urls.append(url)

    valid_links = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_url, url): url for url in urls}
        for future in as_completed(futures):
            result = future.result()
            if result:
                valid_links.append(result)
    return valid_links

def extract_vietjack(url, idx):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    problem_lines = []
    bold_green = soup.find("b", style="color:green;")
    if not bold_green:
        return None

    problem_tag = bold_green.find_parent("p")
    problem_text = problem_tag.get_text(strip=True)
    for sibling in problem_tag.find_next_siblings():
        if sibling.name == "p" and sibling.get_text(strip=True).startswith("Lời giải:"):
            break
        if sibling.name != "p":
            continue
        text = sibling.get_text(strip=True)
        problem_lines.append(text)

    problem_text = "\n".join(problem_lines).strip()

    solution_tag = soup.find("p", string=lambda text: text and "Lời giải:" in text)
    if not solution_tag:
        return None
    solution_lines = []
    answer_text =[]
    for sibling in solution_tag.find_next_siblings():
        if sibling.name != "p":
            continue
        text = sibling.get_text(strip=True)
        if not text:
            continue
        if "Xem thêm" in text or text.startswith("Bài "):
            break
        solution_lines.append(text)
        if "a)" in text:
            answer_text.append("a)")
        elif "b)" in text:
            answer_text.append("b)")
        elif "c)" in text:
            answer_text.append("c)")
        elif "d)" in text:
            answer_text.append("d)")
        if "Do đó" in text or "Vậy" in text or "Vì vậy" in text:
            answer_text.append(text)

    solution_text = "\n".join(solution_lines)
    answer_final = "\n".join(answer_text)

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
    links = generate_valid_links()
    print("\nTổng số link tìm được:", len(links))
    
    with open("valid_links.txt", "w", encoding="utf-8") as f_links:
        for link in links:
            f_links.write(link + "\n")

    all_data = extract_all_data(links)

    with open("Math6.jsonl", "w", encoding="utf-8") as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\n📦 Đã lưu toàn bộ {len(all_data)} bài vào Math6.jsonl")
