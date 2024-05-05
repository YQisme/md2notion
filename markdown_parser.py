import re
import os
from config import image_host_url, local_imgs
from img_upload import upload_imgs


# 处理标题
def handle_headings(line):
    """处理从一级到六级的Markdown标题，并返回Notion块结构。"""
    heading_levels = {
        "# ": ("heading_1", 2),
        "## ": ("heading_2", 3),
        "### ": ("heading_3", 4),
        "#### ": ("paragraph", 5, "red", True),
        "##### ": ("paragraph", 6, "green", True),
        "###### ": ("paragraph", 7, "blue", True),
    }
    for prefix, settings in heading_levels.items():
        if line.startswith(prefix):
            content = line[len(prefix) :]  # 移除Markdown标题前缀
            if len(settings) == 2:
                heading_type, cut_len = settings
                color = "default"
                annotations = None
            else:
                heading_type, cut_len, color, bold = settings
                annotations = {"bold": bold}
            rich_texts = process_rich_text(content)
            if annotations:
                rich_texts[0]["annotations"] = annotations

            return {
                "object": "block",
                "type": heading_type,
                heading_type: {"rich_text": rich_texts, "color": color},
            }


# 处理无序列表项，支持 '-', '+', '*'
def handle_list(line, leading_spaces):
    prefix = "  " * leading_spaces + "📖 "
    if line.startswith("- ") or line.startswith("+ ") or line.startswith("* "):
        content = line[2:]
        rich_texts = process_rich_text(content)
        list_type = "bulleted_list_item"
        if leading_spaces == 0:
            # Top-level bullet, treat as a bulleted list item
            return {
                "object": "block",
                "type": list_type,
                list_type: {"rich_text": rich_texts, "color": "default"},
            }
        else:
            # Nested bullet, use prefix with tabs and symbol
            return {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": prefix}}]
                    + rich_texts,
                    "color": "default",
                },
            }
    elif re.match(r"\d+\.", line):
        content = line[2:]
        rich_texts = process_rich_text(content)
        list_type = "numbered_list_item"
        if leading_spaces == 0:
            # Top-level bullet, treat as a bulleted list item
            return {
                "object": "block",
                "type": list_type,
                list_type: {"rich_text": rich_texts, "color": "default"},
            }
        else:
            # Nested bullet, use prefix with tabs and symbol
            formatted_line = prefix + line[2:]
            return {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": prefix}}]
                    + rich_texts,
                    "color": "default",
                },
            }


# 处理代码块
def handle_code_block(line, blocks, code_state):
    """处理Markdown代码块，维护代码的原始格式，包括缩进和空行。

    :param line: 当前处理的文本行
    :param blocks: 存储块元素的列表
    :param code_state: 包含代码块状态和内容的字典
    :return: 返回True如果当前行处理为代码块的一部分，否则返回False
    """
    if line.startswith("```"):
        if code_state["in_code_block"]:
            # 代码块结束，创建代码块并重置状态
            # 移除最后一个换行符
            if code_state["content"].endswith("\n"):
                code_state["content"] = code_state["content"][:-1]
            blocks.append(
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [
                            {"type": "text", "text": {"content": code_state["content"]}}
                        ],
                        "language": code_state["language"],
                    },
                }
            )
            code_state["in_code_block"] = False
            code_state["content"] = ""
            code_state["language"] = "plain text"  # 重置为默认语言
        else:
            # 代码块开始
            code_state["in_code_block"] = True
            code_state["language"] = line[3:].strip() or "plain text"
        return True  # 当前行为代码块开始或结束标记
    elif code_state["in_code_block"]:
        # 直接添加原始行到内容中，保留缩进
        code_state["content"] += line
        return True  # 当前行为代码块内的内容
    return False  # 当前行不属于代码块


# 处理引用块
def handle_quote(line):
    if line.startswith(">"):
        quote_content = line[2:]  # 移除 "> " 并获取剩余内容
        # 将内容转换为富文本
        rich_texts = process_rich_text(quote_content)
        return {
            "object": "block",
            "type": "quote",
            "quote": {"rich_text": rich_texts, "color": "default"},
        }


# 处理 LaTeX 表达式
def handle_equation(line):
    if "$$" in line:
        # 处理显示模式的 LaTeX 公式，使用 `$$...$$`
        equation_matches = re.finditer(r"\$\$(.+?)\$\$", line)
        for match in equation_matches:
            expression = match.group(1)
            return {
                "object": "block",
                "type": "equation",
                "equation": {"expression": expression.strip()},
            }
    if "$" in line:
        # 处理行内模式的 LaTeX 公式，使用 `$...$`
        equation_matches = re.finditer(r"\$(.+?)\$", line)
        for match in equation_matches:
            expression = match.group(1)
            return {
                "object": "block",
                "type": "equation",
                "equation": {"expression": expression.strip()},
            }


def handle_embed(line):
    """处理Markdown中的iframe嵌入内容，并返回Notion块结构。"""
    # 正则表达式匹配iframe中的src属性
    match = re.search(r'<iframe [^>]*//([^"]+)"', line)
    if match:
        # 获取完整URL（添加https:前缀）
        url = f"https://{match.group(1)}&autoplay=0"  # b站视频会自动播放，禁用自动播放
        return {"object": "block", "type": "embed", "embed": {"url": url}}
    return None


def handle_image(line):
    img_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")
    match = img_pattern.search(line)
    if match:
        # 找到图片
        alt_text, img_path = match.groups()
        if img_path.startswith("http"):  # 网络图片
            return {
                "object": "block",
                "type": "image",
                "image": {"type": "external", "external": {"url": img_path}},
            }
        else:
            # 本地图片，转换为在线 URL，提取文件名并添加 URL 前缀
            filename = os.path.basename(img_path)
            if image_host_url != "xxx":
                upload_imgs(local_imgs)
                image_url = image_host_url + filename
            else:
                print("请上传本地图片{filename}到图床。")
            return {
                "object": "block",
                "type": "image",
                "image": {"type": "external", "external": {"url": image_url}},
            }


def parse_markdown(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
    blocks = []
    # 代码块状态，用于处理多行代码块
    code_state = {"in_code_block": False, "content": "", "language": "plain text"}
    for line in lines:
        # 通过计算前面的空格来计算缩进级别
        leading_spaces = len(line) - len(line.lstrip(" "))
        oringin_line = line
        line = line.strip()

        # 尝试处理代码块
        if handle_code_block(oringin_line, blocks, code_state):
            continue
        # 处理代码块放在“跳过空行”和“处理标题”前面，同时解决了2个bug，1.代码块中的空行。2.不会把注释解析为标题。
        if not line:
            # 跳过空行
            continue
        # 处理标题
        block = handle_headings(line)
        if block:
            blocks.append(block)
            continue
        # 处理列表
        block = handle_list(line, leading_spaces)
        if block:
            blocks.append(block)
            continue
        # 处理引用
        block = handle_quote(line)
        if block:
            blocks.append(block)
            continue
        # 处理公式
        block = handle_equation(line)
        if block:
            blocks.append(block)
            continue
        # 处理嵌入内容
        block = handle_embed(line)
        if block:
            blocks.append(block)
            continue
        # 处理分隔符
        if line.startswith("---"):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            continue
        # 处理图片
        block = handle_image(line)
        if block:
            blocks.append(block)
            continue
        # 处理富文本
        rich_texts = process_rich_text(line)
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": rich_texts, "color": "default"},
            }
        )
    return blocks


def process_rich_text(line):
    # 初始化富文本列表
    rich_texts = []

    # 先处理超链接，将文本分割成普通文本和超链接
    current_position = 0
    for match in re.finditer(r"\[([^\[]+)\]\((http[s]?://[^\)]+)\)", line):
        # 添加超链接之前的普通文本
        if match.start() > current_position:
            plain_text = line[current_position : match.start()]
            rich_texts.extend(process_plain_text(plain_text))
        # 添加超链接
        link_text = match.group(1)
        link_url = match.group(2)
        rich_texts.append(
            {
                "type": "text",
                "text": {"content": link_text, "link": {"url": link_url}},
                "annotations": {
                    "bold": False,
                    "italic": False,
                    "underline": False,
                    "strikethrough": False,
                    "code": False,
                    "color": "default",
                },
            }
        )
        current_position = match.end()

    # 处理剩余的普通文本
    if current_position < len(line):
        plain_text = line[current_position:]
        rich_texts.extend(process_plain_text(plain_text))

    return rich_texts


def process_plain_text(text):
    """处理普通文本中的格式化标记"""
    pieces = []
    # 定义正则表达式来匹配Markdown的各种格式化标记
    format_patterns = [
        (r"\*\*(.*?)\*\*", "bold"),
        (r"\*(.*?)\*", "italic"),
        (r"~~(.*?)~~", "strikethrough"),
        (r"`(.*?)`", "code"),
        (r"<u>(.*?)</u>", "underline"),
    ]

    last_end = 0
    # 遍历所有格式化模式并应用它们
    for pattern, style in format_patterns:
        for match in re.finditer(pattern, text):
            # 添加前一个格式和当前格式之间的文本
            if match.start() > last_end:
                pieces.append(
                    create_text_element(text[last_end : match.start()], False)
                )
            # 添加格式化的文本
            pieces.append(create_text_element(match.group(1), True, style))
            last_end = match.end()

    # 添加最后一段普通文本
    if last_end < len(text):
        pieces.append(create_text_element(text[last_end:], False))

    return pieces


def create_text_element(text, formatted, style=None):
    """创建富文本元素，可以包括各种格式"""
    element = {
        "type": "text",
        "text": {"content": text},
        "annotations": {
            "bold": False,
            "italic": False,
            "underline": False,
            "strikethrough": False,
            "code": False,
            "color": "default",
        },
    }
    if formatted:
        if style == "bold":
            element["annotations"]["bold"] = True
        elif style == "italic":
            element["annotations"]["italic"] = True
        elif style == "underline":
            element["annotations"]["underline"] = True
        elif style == "strikethrough":
            element["annotations"]["strikethrough"] = True
        elif style == "code":
            element["annotations"]["code"] = True

    return element
