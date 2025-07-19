import json
import re

def clean_text(text):
    text = re.sub(
        r"^Bài\s*\d+(?:\.\d+)?\s*trang\s*\d+\s*(?:sách|SGK|SBT)?[^:\n]*?:\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    return text.strip()

for lop in [6, 7, 8, 9, 10, 11, 12]:
    input_path = f"Math{lop}/raw/Math{lop}_raw.jsonl"
    output_path = f"Math{lop}/clean/Math{lop}_clean.jsonl"

    with open(input_path, "r", encoding="utf-8") as infile, open(output_path, "w", encoding="utf-8") as outfile:
        for line in infile:
            data = json.loads(line)

            for message in data.get("messages", []):
                if message["role"] == "user":
                    for content_block in message["content"]:
                        if content_block["type"] == "text":
                            content_block["content"] = clean_text(content_block["content"])

            outfile.write(json.dumps(data, ensure_ascii=False) + "\n")

# input_path = "Math12/raw/Math12_raw.jsonl"
# output_path = "Math12/clean/Math12_clean.jsonl"

# with open(input_path, "r", encoding="utf-8") as infile, open(output_path, "w", encoding="utf-8") as outfile:
#     for line in infile:
#         data = json.loads(line)

#         for message in data.get("messages", []):
#             if message["role"] == "user":
#                 for content_block in message["content"]:
#                     if content_block["type"] == "text":
#                         content_block["content"] = clean_text(content_block["content"])

#         outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
