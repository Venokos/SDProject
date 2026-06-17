import requests
import base64
import json
import os
import time
import argparse
import sys

sys.stdout.reconfigure(encoding='utf-8')

def generate_image(
        prompt,
        scribble_path,
        weight=1.0,
        output_dir="pyOutput",
        control_type="scribble",
        width=512,
        height=512,
        steps=30
):
    """基于ControlNet的可控图像生成函数

    Args:
        prompt: 文本提示词，如 "studio background, product photography"
        scribble_path: ControlNet引导图路径
        weight: ControlNet强度，默认1.0（建议范围0.5-1.5）
        output_dir: 输出目录，默认"pyOutput"
        control_type: 控制类型，"scribble"或"canny"，默认"scribble"
        width: 输出图像宽度，默认512
        height: 输出图像高度，默认512
        steps: 采样步数，默认30

    Returns:
        str: 生成图片的路径，失败返回None
    """
    # 确保输出文件夹存在
    os.makedirs(output_dir, exist_ok=True)

    # 读取引导图
    with open(scribble_path, "rb") as f:
        control_base64 = base64.b64encode(f.read()).decode()

    # 不同控制类型的ControlNet配置
    control_settings = {
        "scribble": {
            "module": "scribble_xdog",
            "model": "controlnet_v11p_sd15_scribble"
        },
        "canny": {
            "module": "canny",
            "model": "control_v11p_sd15_canny"
        }
    }

    if control_type not in control_settings:
        raise ValueError(
            f"不支持的control_type：{control_type}。"
            f"可用类型：{list(control_settings.keys())}"
        )

    module_name = control_settings[control_type]["module"]
    model_name = control_settings[control_type]["model"]

    # WebUI API地址
    url = "http://127.0.0.1:7860/sdapi/v1/txt2img"

    # 生成参数
    payload = {
        "prompt": prompt,
        "steps": steps,
        "width": width,
        "height": height,
        "sampler_name": "Euler a",
        "controlnet_units": [
            {
                "input_image": control_base64,
                "module": module_name,
                "model": model_name,
                "weight": weight
            }
        ]
    }

    # 发送请求
    image_base64 = None
    try:
        print(f"Sending request to {url}...")
        print(f"Payload keys: {list(payload.keys())}")
        print(f"ControlNet units: {len(payload.get('controlnet_units', []))} unit(s)")
        
        response = requests.post(url, json=payload, timeout=120)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        response.raise_for_status()
        result = response.json()

        # 调试输出
        print("API request successful. Checking result...")
        print(f"Result keys: {list(result.keys())}")

        # 检查是否成功
        if "images" not in result:
            print("Generation failed: missing images in result.")
            print(f"Full result: {result}")
            return None

        # 取出图片
        image_base64 = result["images"][0]
        print(f"Got image base64 length: {len(image_base64) if image_base64 else 0}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        try:
            error_body = response.text
            print(f"Error response body: {error_body[:500]}")
        except:
            pass
        return None
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during API call: {e}")
        import traceback
        traceback.print_exc()
        return None

    # 保存图片
    if image_base64 is None:
        print("生成失败：未获取到图片数据")
        return None

    # 1.创建子文件夹 pyOutput（如果不存在）
    os.makedirs(output_dir, exist_ok=True)

    # 2.自动生成不重复的文件名
    filename = f"output_{int(time.time())}.png"
    output_path = os.path.join(output_dir, filename)

    # 3.保存图片
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(image_base64))

    return output_path


# 命令行调用
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="可控文生图 - 支持scribble/canny引导")
    parser.add_argument("--prompt", type=str, default="a product on a table, minimal studio background",
                        help="文本提示词")
    parser.add_argument("--scribble_path", type=str, default="./test1.png",
                        help="引导图（输入图像）路径")
    parser.add_argument("--weight", type=float, default=1.1,
                        help="ControlNet强度")
    parser.add_argument("--control_type", type=str, default="scribble",
                        choices=["scribble", "canny"],
                        help="控制类型，scribble或canny")
    parser.add_argument("--width", type=int, default=512,
                        help="输出图像宽度")
    parser.add_argument("--height", type=int, default=512,
                        help="输出图像高度")
    parser.add_argument("--steps", type=int, default=30,
                        help="采样步数")
    args = parser.parse_args()

    path = generate_image(
        prompt=args.prompt,
        scribble_path=args.scribble_path,
        weight=args.weight,
        control_type=args.control_type,
        width=args.width,
        height=args.height,
        steps=args.steps
    )

    print("图片已生成:", path)
