# 使用华为云作为图床，上传图片到OBS
import os
from obs import ObsClient
from config import access_key_id, secret_access_key, server


def upload_imgs(local_imgs):
    # 初始化华为云OBS客户端
    obs_client = ObsClient(
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        server=server,
    )

    bucket_name = "myimgs"
    base_folder = "blog/"

    def upload_files(directory):
        # 支持的文件扩展名列表
        supported_extensions = {
            ".bmp",
            ".gif",
            ".heic",
            ".jpeg",
            ".jpg",
            ".png",
            ".svg",
            ".tif",
            ".tiff",
        }

        # 遍历目录及其子目录
        for root, dirs, files in os.walk(directory):
            for file in files:
                if os.path.splitext(file)[1].lower() in supported_extensions:
                    if contains_chinese(file):
                        print(f"文件名包含中文，跳过上传: {file}")
                        continue

                    file_path = os.path.join(root, file)
                    # 创建OBS中的文件路径，只使用文件名，不保留目录结构
                    object_path = base_folder + os.path.basename(file_path)

                    # 检查文件是否已存在
                    if not is_file_exist(bucket_name, object_path):
                        # 上传图片
                        response = obs_client.putFile(
                            bucket_name, object_path, file_path
                        )
                        if response.status < 300:
                            # print(f"图片上传成功: {object_path}")
                            pass
                        else:
                            print(
                                f"图片上传失败: {object_path}, 状态码: {response.status}"
                            )
                    else:
                        # print(f"图片已存在，跳过上传: {object_path}")
                        pass

    def is_file_exist(bucket, object_path):
        response = obs_client.getObjectMetadata(bucket, object_path)
        return response.status == 200

    def contains_chinese(text):
        # 检查文本是否包含中文字符
        return any("\u4e00" <= char <= "\u9fff" for char in text)

    # 希望上传图片的文件夹路径
    upload_files(local_imgs)
