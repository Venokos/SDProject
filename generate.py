import requests
import base64
import json
import os

# 读取scribble图
with open("test1.png", "rb") as f:
    scribble_base64 = base64.b64encode(f.read()).decode()


# WebUI API地址
url = "http://127.0.0.1:7860/sdapi/v1/txt2img"

# 生成参数
payload = {
    "prompt": "a product on a table, minimal studio background, soft lightening",
    "steps": 30,
    "width": 512,
    "height": 512,
    "sampler_name": "Euler a",

    "controlnet_units": [
        {
            "input_image": scribble_base64,
            "module": "scribble_xdog",
            "model": "controlnet_v11p_sd15_scribble",
            "weight": 1.0
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
output_dir = "pyOutput"
os.makedirs(output_dir, exist_ok=True)

# 2.自动生成不重复的文件名
i = 1
while True:
    filename = f"output{i}.png"
    filepath = os.path.join(output_dir, filename)

    if not os.path.exists(filepath):
        break

    i += 1

# 3.保存图片
with open(filepath, "wb") as f:
    f.write(base64.b64decode(image_base64))

print("图片已生成")