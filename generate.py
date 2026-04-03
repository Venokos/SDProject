import requests
import base64
import json
import os
import time

def generate_image(
        prompt,
        scribble_path,
        weight=1.0,
        output_dir="pyOutput"
):

    # 确保输出文件夹存在
    os.makedirs(output_dir, exist_ok=True)

    # 读取scribble图
    with open(scribble_path, "rb") as f:
        scribble_base64 = base64.b64encode(f.read()).decode()


    # WebUI API地址
    url = "http://127.0.0.1:7860/sdapi/v1/txt2img"

    # 生成参数
    payload = {
        "prompt": prompt,
        "steps": 30,
        "width": 512,
        "height": 512,
        "sampler_name": "Euler a",

        "controlnet_units": [
            {
                "input_image": scribble_base64,
                "module": "scribble_xdog",
                "model": "controlnet_v11p_sd15_scribble",
                "weight": weight
            }
        ]
    }

    # 发送请求
    response = requests.post(url, json=payload)

    # 转为python字典
    result = response.json()

    # 调试输出
    print(json.dumps(result, indent=2))

    # 检查是否成功
    if "images" not in result:
        print("生成失败")
        exit()

    # 取出图片
    image_base64 = result["images"][0]

    # 保存图片
    # 1.创建子文件夹 pyOutput（如果不存在）
    os.makedirs(output_dir, exist_ok=True)

    # 2.自动生成不重复的文件名
    filename = f"output_{int(time.time())}.png"
    output_path = os.path.join(output_dir, filename)

    # 3.保存图片
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(image_base64))

    return output_path


# 测试代码
if __name__ == "__main__":
    path = generate_image(
        prompt="a product on a table, minimal studio background",
        scribble_path="./test1.png",
        weight=1.1
    )
        

    print("图片已生成:", path)