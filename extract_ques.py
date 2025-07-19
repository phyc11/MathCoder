import json

# Đường dẫn tới file JSONL gốc và file đầu ra
input_path = 'Data/Train_fixed.jsonl'
output_path = 'Data/questions.jsonl'

with open(input_path, 'r', encoding='utf-8') as fin, \
     open(output_path, 'w', encoding='utf-8') as fout:
    for line_number, line in enumerate(fin, start=1):
        line = line.strip()
        if not line:
            continue  # bỏ qua dòng trống
        try:
            record = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"Lỗi JSON ở dòng {line_number}: {e}")
            continue

        question = record.get('question')
        if question is not None:
            # Tạo dict chỉ chứa question
            out_obj = {"question": question}
            # Dump thành JSON string (không escape unicode)
            json_line = json.dumps(out_obj, ensure_ascii=False)
            fout.write(json_line + '\n')
        else:
            print(f"Dòng {line_number}: không có trường 'question'")

print(f"Đã tạo file '{output_path}' với các dòng JSON chỉ chứa trường question.")
