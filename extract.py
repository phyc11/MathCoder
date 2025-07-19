import json

# File đầu vào và đầu ra
input_file = 'data.jsonl'
output_file = 'questions_and_solutions.jsonl'

for lop in [6, 7, 8, 9, 10, 11, 12]:
    input_file = f"Math{lop}/clean/Math{lop}_clean.jsonl"
    output_file = f"Data/Train.jsonl"
    with open(input_file, 'r', encoding='utf-8') as f_in, open(output_file, 'a', encoding='utf-8') as f_out:
        for line in f_in:
            try:
                data = json.loads(line)

                question = ""
                messages = data.get("messages", [])
                if len(messages) > 1:
                    content_list = messages[1].get("content", [])
                    if isinstance(content_list, list) and len(content_list) > 0:
                        question = content_list[0].get("content", "")

                solution = data.get("ground_truth", {}).get("solution", "")

                output_data = {
                    "question": question,
                    "answer": solution
                }
                f_out.write(json.dumps(output_data, ensure_ascii=False) + '\n')

            except json.JSONDecodeError:
                print("Lỗi đọc JSON:", line)

# with open(input_file, 'r', encoding='utf-8') as f_in, open(output_file, 'w', encoding='utf-8') as f_out:
#     for line in f_in:
#         try:
#             data = json.loads(line)

#             question = ""
#             messages = data.get("messages", [])
#             if len(messages) > 1:
#                 content_list = messages[1].get("content", [])
#                 if isinstance(content_list, list) and len(content_list) > 0:
#                     question = content_list[0].get("content", "")

#             solution = data.get("ground_truth", {}).get("solution", "")

#             output_data = {
#                 "question": question,
#                 "answer": solution
#             }
#             f_out.write(json.dumps(output_data, ensure_ascii=False) + '\n')

#         except json.JSONDecodeError:
#             print("Lỗi đọc JSON:", line)
