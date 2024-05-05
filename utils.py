import os
import requests
from datetime import datetime, timedelta

def find_markdown_files(directory):
    md_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                md_files.append(os.path.join(root, file))
    return md_files


def get_file_last_modified(file_path):
    timestamp = os.path.getmtime(file_path) # 获取文件的最后修改时间戳
    last_modified_dt = datetime.fromtimestamp(timestamp)    # 将时间戳转换为datetime对象
    adjusted_time = last_modified_dt - timedelta(hours=8)   # 调整时间以适应时区（这里提前8小时）
    return adjusted_time.isoformat()    # 返回ISO格式的日期字符串

def get_unique_cover_url():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # 生成格式化的当前时间戳
    cover_url = f"https://source.unsplash.com/random/?sig={timestamp}"  # 添加时间戳作为查询参数
    return cover_url
def archive_page(api_key, page_id,title):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    payload = {"archived": True}
    response = requests.patch(url, headers=headers, json=payload)
    if response.status_code == 200:
        return True
    else:
        print(f"❌页面《{title}》归档失败: {response.text}")
        return False
