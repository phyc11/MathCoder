import requests
from bs4 import BeautifulSoup
import json
import os
import html
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

def extract_plain_text_from_mathml(mathml_str):
    """Trích xuất văn bản từ MathML"""
    try:
        soup = BeautifulSoup(html.unescape(mathml_str), "xml")
        result = []

        def parse_node(node):
            try:
                if not node or not hasattr(node, 'name'):
                    return ""
                    
                if node.name == "msup":
                    children = node.find_all(recursive=False)
                    if len(children) >= 2:
                        base = parse_node(children[0]) or ""
                        exponent = parse_node(children[1]) or ""
                        return f"{base}^{exponent}"
                elif node.name == "msub":
                    children = node.find_all(recursive=False)
                    if len(children) >= 2:
                        base = parse_node(children[0]) or ""
                        subscript = parse_node(children[1]) or ""
                        return f"{base}_{subscript}"
                elif node.name == "msubsup":
                    children = node.find_all(recursive=False)
                    if len(children) >= 3:
                        base = parse_node(children[0]) or ""
                        subscript = parse_node(children[1]) or ""
                        superscript = parse_node(children[2]) or ""
                        return f"{base}_{subscript}^{superscript}"
                elif node.name == "msqrt":
                    content_parts = []
                    for child in node.find_all(recursive=False):
                        child_result = parse_node(child)
                        if child_result:
                            content_parts.append(child_result)
                    content = ''.join(content_parts)
                    return f"√({content})"
                elif node.name == "mroot":
                    children = node.find_all(recursive=False)
                    if len(children) >= 2:
                        radicand = parse_node(children[0]) or ""
                        index = parse_node(children[1]) or ""
                        return f"√[{index}]({radicand})"
                elif node.name == "mfrac":
                    children = node.find_all(recursive=False)
                    if len(children) >= 2:
                        num = parse_node(children[0]) or ""
                        denom = parse_node(children[1]) or ""
                        return f"({num}/{denom})"
                elif node.name == "mrow":
                    content_parts = []
                    for child in node.find_all(recursive=False):
                        child_result = parse_node(child)
                        if child_result:
                            content_parts.append(child_result)
                    return ''.join(content_parts)
                elif node.name in ["mi", "mn", "mo"]:
                    return html.unescape(node.text or "")
                elif node.name == "mfenced":
                    # Xử lý các ký tự đóng mở ngoặc
                    open_attr = node.get('open', '(')
                    close_attr = node.get('close', ')')
                    content_parts = []
                    for child in node.find_all(recursive=False):
                        child_result = parse_node(child)
                        if child_result:
                            content_parts.append(child_result)
                    content = ''.join(content_parts)
                    return f"{open_attr}{content}{close_attr}"
                elif node.name == "mtable":
                    # Xử lý bảng/ma trận
                    rows = []
                    for mtr in node.find_all("mtr"):
                        cells = []
                        for mtd in mtr.find_all("mtd"):
                            cell_content = parse_node(mtd) or ""
                            cells.append(cell_content)
                        rows.append(" | ".join(cells))
                    return "[" + " ; ".join(rows) + "]"
                elif node.name == "mtext":
                    # Xử lý text trong MathML, decode HTML entities
                    text = html.unescape(node.text or "")
                    # Xử lý các ký tự đặc biệt tiếng Việt
                    text = text.replace('&nbsp;', ' ')
                    return text
                else:
                    content_parts = []
                    for child in node.find_all(recursive=False):
                        child_result = parse_node(child)
                        if child_result:
                            content_parts.append(child_result)
                    return ''.join(content_parts)
            except Exception as e:
                print(f"Lỗi khi parse node {node.name if hasattr(node, 'name') else 'unknown'}: {e}")
                return ""

        # Tìm tất cả các thẻ math
        for math_tag in soup.find_all("math"):
            parsed_result = parse_node(math_tag)
            if parsed_result:
                result.append(parsed_result)

        return " ; ".join(result) if result else ""
    except Exception as e:
        print(f"Lỗi khi extract MathML: {e}")
        return ""

def extract_mathml_from_mathjax(element):
    """Trích xuất MathML từ các thẻ MathJax"""
    try:
        # Tìm thẻ script chứa MathML
        math_script = element.find('script', {'type': 'math/mml'})
        if math_script and math_script.string:
            return extract_plain_text_from_mathml(math_script.string)
        
        # Tìm trong data-mathml attribute
        mathjax_element = element.find(attrs={'data-mathml': True})
        if mathjax_element:
            mathml_content = mathjax_element.get('data-mathml')
            if mathml_content:
                # Decode HTML entities trong attribute
                mathml_content = html.unescape(mathml_content)
                return extract_plain_text_from_mathml(mathml_content)
        
        # Tìm trong thẻ MJX_Assistive_MathML
        assistive_mathml = element.find(class_='MJX_Assistive_MathML')
        if assistive_mathml:
            return extract_plain_text_from_mathml(str(assistive_mathml))
        
        return ""
    except Exception as e:
        print(f"Lỗi khi extract MathJax: {e}")
        return ""

def process_text_with_mathml(text):
    """Xử lý văn bản chứa MathML và các thẻ HTML toán học khác"""
    try:
        if not text:
            return text
        
        soup = BeautifulSoup(text, "html.parser")
        
        # Xử lý MathJax elements
        mathjax_elements = soup.find_all(class_=re.compile(r'(MathJax|mjx-|MJX)'))
        for element in mathjax_elements:
            try:
                # Tìm thẻ cha chứa toàn bộ MathJax content
                parent = element
                while parent and not parent.find('script', {'type': 'math/mml'}) and not parent.get('data-mathml'):
                    parent = parent.parent
                
                if parent:
                    math_text = extract_mathml_from_mathjax(parent)
                    if math_text:
                        # Thay thế toàn bộ parent element bằng plain text
                        parent.replace_with(math_text)
            except Exception as e:
                print(f"Lỗi khi xử lý MathJax element: {e}")
                continue
        
        # Xử lý các thẻ MathML trực tiếp
        mathml_pattern = r'<math[^>]*>.*?</math>'
        
        def replace_mathml(match):
            try:
                mathml_content = match.group(0)
                plain_text = extract_plain_text_from_mathml(mathml_content)
                return plain_text if plain_text else mathml_content
            except Exception as e:
                print(f"Lỗi khi replace MathML: {e}")
                return match.group(0)
        
        # Thay thế MathML bằng plain text
        processed_text = re.sub(mathml_pattern, replace_mathml, str(soup), flags=re.DOTALL)
        
        # Parse lại sau khi thay thế MathML
        soup = BeautifulSoup(processed_text, "html.parser")
        
        # Xử lý các thẻ HTML sup và sub thông thường
        for sup in soup.find_all('sup'):
            sup.replace_with(f"^{sup.get_text()}")
        
        for sub in soup.find_all('sub'):
            sub.replace_with(f"_{sub.get_text()}")
        
        # Lấy text và dọn dẹp
        clean_text = soup.get_text()
        
        # Dọn dẹp khoảng trắng thừa
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        return clean_text
    except Exception as e:
        print(f"Lỗi khi process text with MathML: {e}")
        return text or ""

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

def generate_valid_links(lop):
    urls = []
    for tap in [1, 2]:  
        for start in range(1, 10):
            for end in range(1, 100):  
                for page in range(1, 100):
                    url = f"https://vietjack.com/sbt-toan-{lop}-kn/bai-{start}-{end}-trang-{page}-sbt-toan-lop-{lop}-tap-{tap}.jsp"
                    urls.append(url)

    valid_links = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_url, url): url for url in urls}
        for future in as_completed(futures):
            result = future.result()
            if result:
                valid_links.append(result)
    return valid_links

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
    problem_lines = []
    
    # Xử lý đoạn đầu tiên (chứa thẻ b màu xanh)
    problem_html = str(problem_tag)
    problem_text_processed = process_text_with_mathml(problem_html)
    if problem_text_processed.strip():
        problem_lines.append(problem_text_processed.strip())

    # Xử lý các đoạn tiếp theo
    for sibling in problem_tag.find_next_siblings():
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
        
        # Xử lý MathML và MathJax trong từng đoạn
        sibling_html = str(sibling)
        sibling_text_processed = process_text_with_mathml(sibling_html)
        if sibling_text_processed.strip():
            problem_lines.append(sibling_text_processed.strip())

    problem_text = "\n".join(problem_lines).strip()

    solution_tag = soup.find("p", string=lambda text: text and "Lời giải:" in text)
    if not solution_tag:
        return None

    has_img_in_solution = False
    solution_lines = []
    answer_text = []
    collecting = False

    for sibling in solution_tag.find_next_siblings():
        if sibling.name == "img" or (sibling.name == "p" and sibling.find("img")):
            has_img_in_solution = True
            break
        if sibling.name == "table" or (sibling.name == "p" and sibling.find("table")):
            has_img_in_solution = True
            break
        if sibling.name != "p":
            continue
        
        sibling_html = str(sibling)
        text_with_mathml = process_text_with_mathml(sibling_html)
        
        if "Xem thêm" in text_with_mathml or text_with_mathml.startswith("Bài ") or text_with_mathml.startswith("Lời giải SBT") or text_with_mathml.startswith("Lời giải Sách bài tập"):
            break
        
        if text_with_mathml.strip():
            solution_lines.append(text_with_mathml.strip())

            if any(phrase in text_with_mathml for phrase in ["Do đó", "Vậy", "Vì vậy"]):
                collecting = True
                answer_text.append(text_with_mathml.strip())
                continue

            for marker in ["a)", "b)", "c)", "d)"]:
                if marker in text_with_mathml:
                    answer_text.append(marker)
                    collecting = False
                    break

            if collecting:
                answer_text.append(text_with_mathml.strip())

    if has_img_in_problem or has_img_in_solution:
        print(f"⚠️ Bỏ qua link {url} vì chứa ảnh.")
        skipped_links.append(url)
        return None

    solution_text = "\n".join(solution_lines)
    answer_final = "\n".join(answer_text)
    
    if not answer_final \
        or answer_final in ["a)\nb)", "a)\nb)\nc)", "a)\nb)\nc)\nd)"] \
        or answer_final.startswith("a)\nb)\nc)\nd)") \
        or answer_final.startswith("a)\nb)") \
        or answer_final.startswith("a)\nb)\nc)"):
        answer_final = solution_text

    return {
        "id": str(idx),
        "messages": [
            {
                "role": "system",
                "content": [{"type": "text", "content": "Below is a math problem. Please solve it step by step."}]
            },
            {
                "role": "user",
                "content": [{"type": "text", "content": problem_text}]
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
    with ThreadPoolExecutor(max_workers=20) as executor:
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
    for lop in [11]: 
        print(f"\n=== 📘 Đang xử lý lớp {lop} ===")
        links = generate_valid_links(lop)
        print(f"🔗 Tổng số link tìm được cho lớp {lop}: {len(links)}")

        
        os.makedirs(f"Math{lop}", exist_ok=True)
        os.makedirs(f"Link{lop}", exist_ok=True)
        
        with open(f"Link{lop}/valid_links_math{lop}_kn.txt", "w", encoding="utf-8") as f_links:
            for link in links:
                f_links.write(link + "\n")

        all_data, skipped_links = extract_all_data(links)

        
        with open(f"Math{lop}/raw/Math{lop}_kn_raw.jsonl", "w", encoding="utf-8") as f:
            for item in all_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        
        with open(f"Link{lop}/skipped_links_math{lop}_kn.txt", 'w', encoding='utf-8') as f:
            for link in skipped_links:
                f.write(link + '\n')

        print(f"📦 Đã lưu {len(all_data)} bài cho lớp {lop} vào Math{lop}_kn_raw.jsonl")

# if __name__ == "__main__":
#     with open('Link6/valid_links_math6_cd.txt', 'r', encoding='utf-8') as file:
#         links = [line.strip() for line in file if line.strip()]

#     print(f"🔎 Đang lấy dữ liệu từ {len(links)} link...")
#     all_data, skipped_links = extract_all_data(links)

#     # Ghi dữ liệu hợp lệ vào file output_data.jsonl
#     with open('Math6/raw/Math6_cd_raw.jsonl', 'w', encoding='utf-8') as f:
#         for item in all_data:
#             json_line = json.dumps(item, ensure_ascii=False)
#             f.write(json_line + '\n')

