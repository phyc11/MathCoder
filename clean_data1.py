import json
import re

input_path = "Math6_clean.jsonl"       # File đã lọc dòng rỗng user
final_output_path = "Math6_clean_final.jsonl"   # File sau khi đã sửa

def split_solution(solution_text):
    # Tách phần trước và sau "Lời giải:"
    parts = re.split(r"\n*Lời giải:\n*", solution_text, maxsplit=1)
    if len(parts) == 2:
        question_part = parts[0].strip()
        solution_part = parts[1].strip()
    else:
        question_part = ""
        solution_part = solution_text.strip()
    return question_part, solution_part

with open(input_path, "r", encoding="utf-8") as infile, open(final_output_path, "w", encoding="utf-8") as outfile:
    for line in infile:
        data = json.loads(line)

        solution_text = data.get("ground_truth", {}).get("solution", "")
        question, cleaned_solution = split_solution(solution_text)

        # Thay thế content rỗng của user bằng question
        for msg in data.get("messages", []):
            if msg["role"] == "user":
                for block in msg["content"]:
                    if block["type"] == "text" and not block["content"].strip():
                        block["content"] = question

        # Gán lại solution đã loại phần câu hỏi
        data["ground_truth"]["solution"] = cleaned_solution

        outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
