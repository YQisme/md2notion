# 用户自定义数据
import os
from dotenv import load_dotenv

env_path = os.path.join(os.getcwd(), ".env")
env_local_path = os.path.join(os.getcwd(), ".env.local")

# 首先加载 .env 文件
load_dotenv(env_path)

# 然后加载 .env.local 文件，如果存在的话，会覆盖 .env 文件中的同名变量
# 适用于本地开发环境的配置
load_dotenv(env_local_path, override=True)

api_key = os.getenv("API_KEY")
database_id = os.getenv("DATABASE_ID")
base_directory = os.getenv("BASE_DIRECTORY")
image_host_url = os.getenv("IMAGE_HOST_URL")
access_key_id = os.getenv("ACCESS_KEY_ID")
secret_access_key = os.getenv("SECRET_ACCESS_KEY")
server = os.getenv("SERVER")
image_host_path = os.getenv("IMAGE_HOST_PATH")
local_imgs = os.getenv("LOCAL_IMAGE_PATH")
