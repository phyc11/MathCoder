
import requests
from bs4 import BeautifulSoup
import json
import os
import html
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

def post_process_latex(latex_text):
    """Xử lý hậu kỳ để sửa các lỗi LaTeX phổ biến"""
    if not latex_text:
        return latex_text
    
    # Sửa lỗi pmatrix được dùng cho hàm số từng phần
    if "\\begin{pmatrix}" in latex_text and any(keyword in latex_text.lower() for keyword in ["nếu", "if", "khi", "when", "với", "for", "≤", "≥", "<", ">", "\\leq", "\\geq"]):
        latex_text = latex_text.replace("\\begin{pmatrix}", "\\begin{cases}")
        latex_text = latex_text.replace("\\end{pmatrix}", "\\end{cases}")
    
    # Sửa lỗi khoảng cách trong text - FIXED: Tách riêng text và số
    latex_text = re.sub(r'\\text\{([^}]*)\}', lambda m: f'\\text{{{m.group(1).strip()}}}', latex_text)
    
    # FIXED: Tách text chứa cả từ khóa và số thành hai phần riêng biệt
    latex_text = re.sub(r'\\text\{(nếu|if|khi|when)\s+(\d+[^}]*)\}', r'\\text{\1} \2', latex_text)
    latex_text = re.sub(r'\\text\{([^}]*?)\s+(nếu|if|khi|when)\s+(\d+[^}]*)\}', r'\1 \\text{\2} \3', latex_text)
    
    # Sửa lỗi dấu cách không cần thiết
    latex_text = re.sub(r'\s+', ' ', latex_text).strip()
    
    return latex_text

def extract_latex_from_mathml(mathml_str):
    """Trích xuất LaTeX từ MathML"""
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
                        return f"{base}^{{{exponent}}}"
                elif node.name == "msub":
                    children = node.find_all(recursive=False)
                    if len(children) >= 2:
                        base = parse_node(children[0]) or ""
                        subscript = parse_node(children[1]) or ""
                        return f"{base}_{{{subscript}}}"
                elif node.name == "msubsup":
                    children = node.find_all(recursive=False)
                    if len(children) >= 3:
                        base = parse_node(children[0]) or ""
                        subscript = parse_node(children[1]) or ""
                        superscript = parse_node(children[2]) or ""
                        return f"{base}_{{{subscript}}}^{{{superscript}}}"
                elif node.name == "msqrt":
                    content_parts = []
                    for child in node.find_all(recursive=False):
                        child_result = parse_node(child)
                        if child_result:
                            content_parts.append(child_result)
                    content = ''.join(content_parts)
                    return f"\\sqrt{{{content}}}"
                elif node.name == "mroot":
                    children = node.find_all(recursive=False)
                    if len(children) >= 2:
                        radicand = parse_node(children[0]) or ""
                        index = parse_node(children[1]) or ""
                        return f"\\sqrt[{index}]{{{radicand}}}"
                elif node.name == "mfrac":
                    children = node.find_all(recursive=False)
                    if len(children) >= 2:
                        num = parse_node(children[0]) or ""
                        denom = parse_node(children[1]) or ""
                        return f"\\frac{{{num}}}{{{denom}}}"
                elif node.name == "mrow":
                    content_parts = []
                    for child in node.find_all(recursive=False):
                        child_result = parse_node(child)
                        if child_result:
                            content_parts.append(child_result)
                    return ''.join(content_parts)
                elif node.name in ["mi", "mn", "mo"]:
                    text = html.unescape(node.text or "")
                    # Chuyển đổi các ký tự đặc biệt sang LaTeX
                    latex_symbols = {
                        '±': '\\pm',
                        '∓': '\\mp',
                        '×': '\\times',
                        '÷': '\\div',
                        '≤': '\\leq',
                        '≥': '\\geq',
                        '≠': '\\neq',
                        '≈': '\\approx',
                        '∞': '\\infty',
                        '∑': '\\sum',
                        '∏': '\\prod',
                        '∫': '\\int',
                        '∂': '\\partial',
                        '∇': '\\nabla',
                        '√': '\\sqrt',
                        'α': '\\alpha',
                        'β': '\\beta',
                        'γ': '\\gamma',
                        'δ': '\\delta',
                        'ε': '\\epsilon',
                        'θ': '\\theta',
                        'λ': '\\lambda',
                        'μ': '\\mu',
                        'π': '\\pi',
                        'ρ': '\\rho',
                        'σ': '\\sigma',
                        'τ': '\\tau',
                        'φ': '\\phi',
                        'χ': '\\chi',
                        'ψ': '\\psi',
                        'ω': '\\omega',
                        'Γ': '\\Gamma',
                        'Δ': '\\Delta',
                        'Θ': '\\Theta',
                        'Λ': '\\Lambda',
                        'Π': '\\Pi',
                        'Σ': '\\Sigma',
                        'Φ': '\\Phi',
                        'Ψ': '\\Psi',
                        'Ω': '\\Omega',
                        '°': '^\\circ'
                    }
                    for symbol, latex in latex_symbols.items():
                        text = text.replace(symbol, latex)
                    return text
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
                    
                    # Xử lý đặc biệt cho hàm số từng phần
                    if open_attr == '{' and close_attr == '':
                        # Đây là hàm số từng phần - không cần thêm ký tự đóng mở
                        return content
                    
                    # Chuyển đổi các loại ngoặc sang LaTeX
                    bracket_map = {
                        '(': '\\left(',
                        ')': '\\right)',
                        '[': '\\left[',
                        ']': '\\right]',
                        '{': '\\left\\{',
                        '}': '\\right\\}',
                        '|': '\\left|'
                    }
                    
                    latex_open = bracket_map.get(open_attr, open_attr)
                    latex_close = bracket_map.get(close_attr, close_attr)
                    
                    return f"{latex_open}{content}{latex_close}"
                elif node.name == "mtable":
                    # Xử lý bảng/ma trận - FIXED: Cải thiện logic phân tích hàm số từng phần
                    rows = []
                    is_piecewise_function = False
                    
                    # Kiểm tra xem có phải hàm số từng phần không bằng cách xem parent node
                    parent_mfenced = node.find_parent("mfenced")
                    if parent_mfenced and parent_mfenced.get('open') == '{' and parent_mfenced.get('close') == '':
                        is_piecewise_function = True
                    
                    for mtr in node.find_all("mtr", recursive=False):
                        # FIXED: Xử lý từng cell một cách riêng biệt
                        row_parts = []
                        
                        for mtd in mtr.find_all("mtd", recursive=False):
                            # Parse từng phần tử con của mtd riêng biệt
                            cell_parts = []
                            
                            for child in mtd.children:
                                if hasattr(child, 'name'):
                                    # Xử lý các node con
                                    if child.name == 'mtext':
                                        # FIXED: Xử lý mtext đặc biệt để tách text và số
                                        text_content = html.unescape(child.text or "").strip()
                                        text_content = text_content.replace('&nbsp;', ' ').replace('\xa0', ' ')
                                        
                                        # Tách text chứa từ khóa điều kiện và số
                                        if any(keyword in text_content.lower() for keyword in ["nếu", "if", "khi", "when"]):
                                            # Tìm pattern "nếu số" hoặc "if number"
                                            match = re.match(r'(nếu|if|khi|when)\s+(.+)', text_content, re.IGNORECASE)
                                            if match:
                                                keyword = match.group(1)
                                                remaining = match.group(2).strip()
                                                cell_parts.append(f'\\text{{{keyword}}} {remaining}')
                                            else:
                                                cell_parts.append(f'\\text{{{text_content}}}')
                                        else:
                                            if text_content:
                                                cell_parts.append(f'\\text{{{text_content}}}')
                                    else:
                                        # Xử lý các node khác (số, ký hiệu toán học)
                                        child_result = parse_node(child)
                                        if child_result:
                                            cell_parts.append(child_result)
                                elif hasattr(child, 'strip') and child.strip():
                                    # Text node trực tiếp
                                    cell_parts.append(child.strip())
                            
                            # Ghép các phần của cell
                            if cell_parts:
                                cell_content = ''.join(cell_parts)
                                row_parts.append(cell_content)
                                
                                # Kiểm tra điều kiện hàm số từng phần
                                if any(keyword in cell_content.lower() for keyword in ["nếu", "if", "khi", "when", "với", "for"]) or any(op in cell_content for op in ["≤", "≥", "<", ">", "\\leq", "\\geq"]):
                                    is_piecewise_function = True
                        
                        if row_parts:
                            if is_piecewise_function:
                                # FIXED: Định dạng hàm số từng phần với & để tách biểu thức và điều kiện
                                # Tìm vị trí của từ khóa điều kiện để chèn &
                                row_text = ' '.join(row_parts)
                                # Chèn & trước từ khóa điều kiện
                                row_text = re.sub(r'\s+(\\text\{(?:nếu|if|khi|when)\})', r' & \1', row_text)
                                rows.append(row_text)
                            else:
                                # Định dạng bình thường cho ma trận
                                row_text = " & ".join(row_parts)
                                rows.append(row_text)
                    
                    if is_piecewise_function:
                        return "\\begin{cases}" + " \\\\ ".join(rows) + "\\end{cases}"
                    else:
                        return "\\begin{pmatrix}" + " \\\\ ".join(rows) + "\\end{pmatrix}"
                elif node.name == "mtext":
                    # FIXED: Xử lý text trong MathML với việc tách từ khóa và số
                    text = html.unescape(node.text or "")
                    text = text.replace('&nbsp;', ' ').replace('\xa0', ' ').strip()
                    
                    if not text:
                        return ""
                    
                    # Xử lý đặc biệt cho text chứa từ khóa điều kiện
                    if any(keyword in text.lower() for keyword in ["nếu", "if", "khi", "when"]):
                        # Tách text thành từ khóa và phần còn lại
                        match = re.match(r'(nếu|if|khi|when)\s+(.+)', text, re.IGNORECASE)
                        if match:
                            keyword = match.group(1)
                            remaining = match.group(2).strip()
                            return f'\\text{{{keyword}}} {remaining}'
                        else:
                            return f'\\text{{{text}}}'
                    else:
                        # Text bình thường
                        return f'\\text{{{text}}}'
                elif node.name == "mover":
                    # Xử lý ký hiệu trên (như vector, hat, bar)
                    children = node.find_all(recursive=False)
                    if len(children) >= 2:
                        base = parse_node(children[0]) or ""
                        accent = parse_node(children[1]) or ""
                        if accent == "→":
                            return f"\\vec{{{base}}}"
                        elif accent == "^":
                            return f"\\hat{{{base}}}"
                        elif accent == "¯" or accent == "―":
                            return f"\\bar{{{base}}}"
                        else:
                            return f"\\overset{{{accent}}}{{{base}}}"
                elif node.name == "munder":
                    # Xử lý ký hiệu dưới
                    children = node.find_all(recursive=False)
                    if len(children) >= 2:
                        base = parse_node(children[0]) or ""
                        under = parse_node(children[1]) or ""
                        return f"\\underset{{{under}}}{{{base}}}"
                elif node.name == "munderover":
                    # Xử lý ký hiệu trên và dưới (như tích phân, tổng)
                    children = node.find_all(recursive=False)
                    if len(children) >= 3:
                        base = parse_node(children[0]) or ""
                        under = parse_node(children[1]) or ""
                        over = parse_node(children[2]) or ""
                        if base in ["∑", "\\sum"]:
                            return f"\\sum_{{{under}}}^{{{over}}}"
                        elif base in ["∏", "\\prod"]:
                            return f"\\prod_{{{under}}}^{{{over}}}"
                        elif base in ["∫", "\\int"]:
                            return f"\\int_{{{under}}}^{{{over}}}"
                        else:
                            return f"\\overset{{{over}}}{{\\underset{{{under}}}{{{base}}}}}"
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

        final_result = " ".join(result) if result else ""
        
        # FIXED: Post-process cải thiện
        final_result = post_process_latex(final_result)
        
        # Dọn dẹp khoảng trắng thừa
        final_result = re.sub(r'\s+', ' ', final_result).strip()
        
        return final_result
    except Exception as e:
        print(f"Lỗi khi extract MathML: {e}")
        return ""

def extract_mathml_from_mathjax(element):
    """Trích xuất MathML từ các thẻ MathJax và chuyển sang LaTeX"""
    try:
        # Tìm thẻ script chứa MathML
        math_script = element.find('script', {'type': 'math/mml'})
        if math_script and math_script.string:
            return extract_latex_from_mathml(math_script.string)
        
        # Tìm trong data-mathml attribute
        mathjax_element = element.find(attrs={'data-mathml': True})
        if mathjax_element:
            mathml_content = mathjax_element.get('data-mathml')
            if mathml_content:
                # Decode HTML entities trong attribute
                mathml_content = html.unescape(mathml_content)
                return extract_latex_from_mathml(mathml_content)
        
        # Tìm trong thẻ MJX_Assistive_MathML
        assistive_mathml = element.find(class_='MJX_Assistive_MathML')
        if assistive_mathml:
            return extract_latex_from_mathml(str(assistive_mathml))
        
        return ""
    except Exception as e:
        print(f"Lỗi khi extract MathJax: {e}")
        return ""

def process_text_with_mathml(text):
    """Xử lý văn bản chứa MathML và các thẻ HTML toán học khác, chuyển đổi sang LaTeX"""
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
                    math_latex = extract_mathml_from_mathjax(parent)
                    if math_latex:
                        # FIXED: Sử dụng \\[ \\] cho display math thay vì $...$
                        if any(env in math_latex for env in ['\\begin{cases}', '\\begin{pmatrix}', '\\frac', '\\sum', '\\int']):
                            parent.replace_with(f"\\[ {math_latex} \\]")
                        else:
                            parent.replace_with(f"${math_latex}$")
            except Exception as e:
                print(f"Lỗi khi xử lý MathJax element: {e}")
                continue
        
        # Xử lý các thẻ MathML trực tiếp
        mathml_pattern = r'<math[^>]*>.*?</math>'
        
        def replace_mathml(match):
            try:
                mathml_content = match.group(0)
                latex_text = extract_latex_from_mathml(mathml_content)
                if latex_text:
                    # FIXED: Sử dụng \\[ \\] cho display math phức tạp
                    if any(env in latex_text for env in ['\\begin{cases}', '\\begin{pmatrix}', '\\frac', '\\sum', '\\int']):
                        return f"\\[ {latex_text} \\]"
                    else:
                        return f"${latex_text}$"
                return mathml_content
            except Exception as e:
                print(f"Lỗi khi replace MathML: {e}")
                return match.group(0)
        
        # Thay thế MathML bằng LaTeX
        processed_text = re.sub(mathml_pattern, replace_mathml, str(soup), flags=re.DOTALL)
        
        # Parse lại sau khi thay thế MathML
        soup = BeautifulSoup(processed_text, "html.parser")
        
        # Xử lý các thẻ HTML sup và sub thông thường
        for sup in soup.find_all('sup'):
            sup_text = sup.get_text()
            sup.replace_with(f"^{{{sup_text}}}")
        
        for sub in soup.find_all('sub'):
            sub_text = sub.get_text()
            sub.replace_with(f"_{{{sub_text}}}")
        
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

def is_valid_answer_marker(text, marker):
    marker_pos = text.find(marker)
    if marker_pos == -1:
        return False
    
    if marker_pos == 0:
        return True
    
    char_before = text[marker_pos - 1]
    if char_before in [' ', '\n', '\t', '.', ';', ':', '!', '?']:
        start = max(0, marker_pos - 20)
        end = min(len(text), marker_pos + len(marker) + 20)
        context = text[start:end].lower()
        
        math_patterns = [
            r'cos\s*\(\s*[a-d]\s*\)',      
            r'sin\s*\(\s*[a-d]\s*\)',      
            r'tan\s*\(\s*[a-d]\s*\)',      
            r'f\s*\(\s*[a-d]\s*\)',      
            r'g\s*\(\s*[a-d]\s*\)',       
            r'h\s*\(\s*[a-d]\s*\)',        
            r'[a-z]+\s*\(\s*[a-d]\s*\)',   
            r'\[\s*[a-d]\s*\]',          
            r'\{\s*[a-d]\s*\}',            
            r'[a-d]\s*[+\-*/=<>≤≥]',       
            r'[+\-*/=<>≤≥]\s*[a-d]',       
            r'[a-d]\s*[²³⁴]',              
            r'[a-d]\s*\^\s*\{',            
            r'[a-d]\s*_\s*\{',             
        ]
        
        # Kiểm tra pattern toán học
        for pattern in math_patterns:
            if re.search(pattern, context):
                return False
        
        # Kiểm tra marker có theo sau bởi dấu đóng ngoặc không
        if marker_pos + len(marker) < len(text):
            char_after = text[marker_pos + len(marker)]
            if char_after == ')':
                return False
        
        return True
    
    return False

def is_complete_answer(answer_text):
    """Kiểm tra xem answer có hoàn chỉnh không"""
    if not answer_text or not answer_text.strip():
        return False
    
    # Tìm tất cả các marker a), b), c), d)
    markers = re.findall(r'[a-d]\)', answer_text)
    
    if not markers:
        return True  # Không có marker nào thì coi như hoàn chỉnh
    
    # Kiểm tra từng marker xem có nội dung theo sau không
    lines = answer_text.split('\n')
    incomplete_markers = []
    
    for i, line in enumerate(lines):
        # Tìm marker trong dòng hiện tại
        marker_match = re.search(r'([a-d])\)', line)
        if marker_match:
            marker = marker_match.group(0)
            
            # Lấy phần sau marker trong dòng hiện tại
            after_marker = line[marker_match.end():].strip()
            
            # Nếu không có gì sau marker trong dòng hiện tại, kiểm tra dòng tiếp theo
            if not after_marker:
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Nếu dòng tiếp theo là marker khác hoặc rỗng thì marker hiện tại không hoàn chỉnh
                    if not next_line or re.match(r'^[a-d]\)', next_line):
                        incomplete_markers.append(marker)
                else:
                    # Đây là dòng cuối và không có nội dung sau marker
                    incomplete_markers.append(marker)
            else:
                # Kiểm tra xem phần sau marker có phải chỉ là marker khác không
                if re.match(r'^[a-d]\)', after_marker):
                    incomplete_markers.append(marker)
    
    # Nếu có marker không hoàn chỉnh thì answer không hoàn chỉnh
    return len(incomplete_markers) == 0

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
    
    problem_html = str(problem_tag)
    problem_text_processed = process_text_with_mathml(problem_html)
    if problem_text_processed.strip():
        problem_lines.append(problem_text_processed.strip())

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

            # Kiểm tra từ khóa kết luận
            if any(phrase in text_with_mathml for phrase in ["Do đó", "Vậy", "Vì vậy", "Kết luận", "Đáp án"]):
                collecting = True
                answer_text.append(text_with_mathml.strip())
                continue

            # Kiểm tra marker với logic cải thiện
            found_valid_marker = False
            for marker in ["a)", "b)", "c)", "d)"]:
                if marker in text_with_mathml and is_valid_answer_marker(text_with_mathml, marker):
                    answer_text.append(marker)
                    collecting = False
                    found_valid_marker = True
                    break

            if found_valid_marker:
                continue

            if collecting:
                answer_text.append(text_with_mathml.strip())

    if has_img_in_problem or has_img_in_solution:
        print(f"⚠️ Bỏ qua link {url} vì chứa ảnh.")
        skipped_links.append(url)
        return None

    solution_text = "\n".join(solution_lines)
    answer_final = "\n".join(answer_text)
    
    # FIXED: Kiểm tra answer có hoàn chỉnh không
    if not answer_final or not is_complete_answer(answer_final):
        print(f"⚠️ Answer không hoàn chỉnh cho {url}, sử dụng solution làm answer")
        answer_final = solution_text
    
    # Kiểm tra các trường hợp answer không hợp lệ khác
    if answer_final in ["a)", "a)\nb)", "a)\nb)\nc)", "a)\nb)\nc)\nd)"] \
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
    for lop in [8]: 
        print(f"\n=== 📘 Đang xử lý lớp {lop} ===")
        links = ["https://vietjack.com/sbt-toan-12-kn/bai-4-28-trang-18-sbt-toan-12-tap-2.jsp"]
        print(f"🔗 Tổng số link tìm được cho lớp {lop}: {len(links)}")

        all_data, skipped_links = extract_all_data(links)

        with open(f"Math{lop}_kn_rawđáasdc.jsonl", "w", encoding="utf-8") as f:
            for item in all_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        

        print(f"📦 Đã lưu {len(all_data)} bài cho lớp {lop} vào Math{lop}_kn_raw.jsonl")



# Test với HTML sample
# if __name__ == "__main__":
#     # Test với sample HTML từ file paste-2.txt
#     test_html = '''<p align="center"><span class="MathJax_Preview" style="color: inherit; display: none;"></span><span id="MathJax-Element-1-Frame" class="mjx-chtml MathJax_CHTML" tabindex="0" data-mathml="<math xmlns=&quot;http://www.w3.org/1998/Math/MathML&quot;><mfrac><mrow><mi>x</mi><mi>y</mi></mrow><mrow><msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><msup><mi>y</mi><mn>2</mn></msup><mo>&amp;#x2212;</mo><msup><mi>z</mi><mn>2</mn></msup></mrow></mfrac><mo>+</mo><mfrac><mrow><mi>y</mi><mi>z</mi></mrow><mrow><msup><mi>y</mi><mn>2</mn></msup><mo>+</mo><msup><mi>z</mi><mn>2</mn></msup><mo>&amp;#x2212;</mo><msup><mi>x</mi><mn>2</mn></msup></mrow></mfrac><mo>+</mo><mfrac><mrow><mi>z</mi><mi>x</mi></mrow><mrow><msup><mi>z</mi><mn>2</mn></msup><mo>+</mo><msup><mi>x</mi><mn>2</mn></msup><mo>&amp;#x2212;</mo><msup><mi>y</mi><mn>2</mn></msup></mrow></mfrac></math>" role="presentation" style="font-size: 121%; position: relative;"><span class="MJX_Assistive_MathML" role="presentation"><math xmlns="http://www.w3.org/1998/Math/MathML"><mfrac><mrow><mi>x</mi><mi>y</mi></mrow><mrow><msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><msup><mi>y</mi><mn>2</mn></msup><mo>−</mo><msup><mi>z</mi><mn>2</mn></msup></mrow></mfrac><mo>+</mo><mfrac><mrow><mi>y</mi><mi>z</mi></mrow><mrow><msup><mi>y</mi><mn>2</mn></msup><mo>+</mo><msup><mi>z</mi><mn>2</mn></msup><mo>−</mo><msup><mi>x</mi><mn>2</mn></msup></mrow></mfrac><mo>+</mo><mfrac><mrow><mi>z</mi><mi>x</mi></mrow><mrow><msup><mi>z</mi><mn>2</mn></msup><mo>+</mo><msup><mi>x</mi><mn>2</mn></msup><mo>−</mo><msup><mi>y</mi><mn>2</mn></msup></mrow></mfrac></math></span></span><script type="math/mml" id="MathJax-Element-1"><math xmlns="http://www.w3.org/1998/Math/MathML"><mfrac><mrow><mi>x</mi><mi>y</mi></mrow><mrow><msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><msup><mi>y</mi><mn>2</mn></msup><mo>−</mo><msup><mi>z</mi><mn>2</mn></msup></mrow></mfrac><mo>+</mo><mfrac><mrow><mi>y</mi><mi>z</mi></mrow><mrow><msup><mi>y</mi><mn>2</mn></msup><mo>+</mo><msup><mi>z</mi><mn>2</mn></msup><mo>−</mo><msup><mi>x</mi><mn>2</mn></msup></mrow></mfrac><mo>+</mo><mfrac><mrow><mi>z</mi><mi>x</mi></mrow><mrow><msup><mi>z</mi><mn>2</mn></msup><mo>+</mo><msup><mi>x</mi><mn>2</mn></msup><mo>−</mo><msup><mi>y</mi><mn>2</mn></msup></mrow></mfrac></math></script></p>'''
    
#     soup = BeautifulSoup(test_html, 'html.parser')
#     result = extract_text_with_math(soup)
#     print("Kết quả test:")
#     print(result)
    
#     # Chạy với link test thực tế
#     for lop in [8]: 
#         print(f"\n=== 📘 Đang xử lý lớp {lop} ===")
#         links = ["https://vietjack.com/sbt-toan-8-kn/bai-6-39-trang-15-sbt-toan-8-tap-2.jsp"]
#         print(f"🔗 Tổng số link tìm được cho lớp {lop}: {len(links)}")

#         os.makedirs(f"Math{lop}", exist_ok=True)
#         os.makedirs(f"Link{lop}", exist_ok=True)

#         with open(f"Link{lop}/valid_links_math{lop}_cd_test.txt", "w", encoding="utf-8") as f_links:
#             for link in links:
#                 f_links.write(link + "\n")

#         all_data, skipped_links = extract_all_data(links)

#         with open(f"Math{lop}/Math{lop}_kn_raw_test.jsonl", "w", encoding="utf-8") as f:
#             for item in all_data:
#                 f.write(json.dumps(item, ensure_ascii=False) + "\n")

#         with open(f"Link{lop}/skipped_links_math{lop}_kn_test.txt", 'w', encoding='utf-8') as f:
#             for link in skipped_links:
#                 f.write(link + '\n')

#         print(f"📦 Đã lưu {len(all_data)} bài cho lớp {lop} vào Math{lop}_kn_raw_test.jsonl")