from notion_api import upload_markdown_to_notion
from utils import find_markdown_files
from config import api_key, database_id, base_directory


def main():

    md_files = find_markdown_files(base_directory)
    for markdown_file_path in md_files:
        upload_markdown_to_notion(database_id, api_key, markdown_file_path)


if __name__ == "__main__":
    main()
