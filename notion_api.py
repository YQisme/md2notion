import requests
import os
import sys
from datetime import datetime, timedelta
from utils import get_file_last_modified, get_unique_cover_url, archive_page
from markdown_parser import parse_markdown


def get_page_properties(database_id, api_key, page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        properties = data["properties"]
        cover = data.get("cover", None)  # 如果封面存在，就获取该封面
        return properties, cover
    else:
        print(f"❌获取页面属性失败: {response.text}")
        return None, None


# 获取数据库的属性
def get_database_properties(api_key, database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["properties"]
    else:
        print("错误:", response.text)
        return None


def upload_blocks_to_page(page_id, blocks, headers):
    """向指定页面追加块"""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    payload = {"children": blocks}
    response = requests.patch(url, json=payload, headers=headers)
    if response.status_code in [200, 201]:
        pass
    else:
        print(f"❌长文本添加失败: {response.text}")


# 检查是否存在指定的属性，如果不存在则创建
def check_and_create_property(api_key, database_id, property_name, property_type):
    properties = get_database_properties(api_key, database_id)
    if properties and property_name not in properties:
        url = f"https://api.notion.com/v1/databases/{database_id}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        data = {"properties": {property_name: {property_type: {}}}}
        response = requests.patch(url, headers=headers, json=data)
        if response.status_code in [200, 201]:
            print(f"属性 '{property_name}' 已成功创建")
        else:
            print("创建属性失败:", response.text)
    elif properties:
        pass


def check_if_exists_and_updated(
    database_id, api_key, title, last_modified, force_update=False
):
    # 检查并创建Date类型的"last modified"属性
    check_and_create_property(api_key, database_id, "last modified", "date")
    check_and_create_property(api_key, database_id, "category", "select")
    check_and_create_property(api_key, database_id, "date", "date")
    check_and_create_property(api_key, database_id, "status", "select")
    check_and_create_property(api_key, database_id, "type", "select")
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    payload = {"filter": {"property": "title", "title": {"equals": title}}}
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        return "error", response.text

    results = response.json().get("results", [])
    if not results:
        return "create", None  # No existing entry found, need to create a new one.
    # 检查命令行参数，如果有参数'-u'，则将force_update设为True
    # 即使文本内容没变化，也可以强制更新
    if "-u" in sys.argv:
        force_update = True

    for result in results:
        if force_update:
            return "update", result["id"]
        notion_last_modified = datetime.fromisoformat(
            result["properties"]["last modified"]["date"]["start"]
        ).replace(tzinfo=None)
        local_last_modified = datetime.fromisoformat(last_modified).replace(tzinfo=None)

        # Compare dates to the minute precision
        if notion_last_modified.strftime(
            "%Y-%m-%d %H:%M"
        ) != local_last_modified.strftime("%Y-%m-%d %H:%M"):
            return "update", result["id"]  # Existing entry is outdated, needs update.

    return "skip", None  # Entry exists and is up-to-date.


def upload_markdown_to_notion(database_id, api_key, markdown_file_path):
    title = os.path.splitext(os.path.basename(markdown_file_path))[0]
    current_time = (datetime.now() - timedelta(hours=8)).isoformat()
    last_modified = get_file_last_modified(markdown_file_path)
    blocks = parse_markdown(markdown_file_path)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    action, page_id = check_if_exists_and_updated(
        database_id, api_key, title, last_modified
    )

    if action == "update":
        old_properties, old_cover = get_page_properties(database_id, api_key, page_id)
        if not old_properties:
            print("❌获取旧属性失败，停止更新。")
            return
        if archive_page(api_key, page_id, title):
            # 保留除了last modified外的所有旧属性，更新last modified
            old_properties["last modified"] = {"date": {"start": last_modified}}
        else:
            print("❌归档旧页面失败，停止更新。")
            return

    cover_image_url = get_unique_cover_url()

    if action in ["create", "update"]:
        # 创建新页面或更新页面时使用old_properties
        payload = {
            "parent": {"database_id": database_id},
            "properties": (
                old_properties
                if action == "update"
                else {
                    "title": {"title": [{"text": {"content": title}}]},
                    "category": {"select": {"name": "未分类"}},
                    "date": {"date": {"start": current_time}},
                    "status": {"select": {"name": "Published"}},
                    "type": {"select": {"name": "Post"}},
                    "last modified": {"date": {"start": last_modified}},
                }
            ),
            "cover": (
                old_cover
                if action == "update"
                else {"type": "external", "external": {"url": cover_image_url}}
            ),
            "children": blocks[:100],  # 只取前100个块来创建页面
        }
        response = requests.post(
            f"https://api.notion.com/v1/pages", headers=headers, json=payload
        )
        if response.status_code in [200, 201]:
            new_page_id = response.json()["id"]
            print(f"✅页面《{title}》创建成功")

            # 如果有更多块需要追加
            if len(blocks) > 100:
                upload_blocks_to_page(new_page_id, blocks[100:], headers)
        else:
            print(f"❌页面《{title}》创建/更新失败", response.text)
    else:
        print(f"⛔无需对《{title}》内容进行更改 。")
