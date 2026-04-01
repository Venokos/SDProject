import requests
import base64
import json

url = "http://127.0.0.1:7860/sdapi/v1/txt2img"

payload = {
    "prompt": "minimal studio background, product photography",
    "steps": 20,
    "width": 512,
    "height": 512,
    "sampler_name": "Euler a"
}

response = requests.post(url, json=payload)

result = response.json()

# 调试输出
print(json.dumps(result, indent=2))

# 检查是否成功
if "images" not in result:
    print("生成失败")
    exit()

image_base64 = result["images"][0]

with open("output.png", "wb") as f:
    f.write(base64.b64decode(image_base64))

print("图片已生成")