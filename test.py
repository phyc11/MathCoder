import requests
from bs4 import BeautifulSoup
import json

def extract_vietjack(url, idx):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Tìm thẻ <b style="color:green"> chính là phần đề bài
    bold_green = soup.find("b", style="color:green;")
    if not bold_green:
        return None

    # Lấy toàn bộ phần đề bài từ thẻ <p> chứa thẻ <b>
    problem_tag = bold_green.find_parent("p")
    problem_text = problem_tag.get_text(strip=True)

    # Tìm tất cả thẻ <p> sau thẻ đề bài
    solution_lines = []
    for sibling in problem_tag.find_next_siblings():
        # Bỏ qua các thẻ quảng cáo
        if sibling.name != "p":
            continue
        text = sibling.get_text(strip=True)
        if not text:
            continue
        # Dừng lại khi gặp phần "Xem thêm" hoặc bài tiếp theo
        if "Xem thêm" in text or text.startswith("Bài "):
            break
        solution_lines.append(text)

    solution_text = "\n".join(solution_lines)
    last_line = solution_lines[-1] if solution_lines else ""

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
            "answer": last_line
        }
    }

data = extract_vietjack("https://vietjack.com/sbt-toan-6-ket-noi/bai-1-1-trang-6-sbt-toan-lop-6-tap-1-ket-noi.jsp", 1)
print(json.dumps(data, ensure_ascii=False, indent=3))
