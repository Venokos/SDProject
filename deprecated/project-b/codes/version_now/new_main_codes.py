import base64
import json
import os
import time
import requests
from datetime import datetime
from PIL import Image
from io import BytesIO


def image_to_base64(image_path: str) -> str:
    """
    将图片文件转换为 Base64 编码字符串
    """
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def base64_to_pil_image(base64_str: str) -> Image.Image:
    """
    将 Base64 字符串转换为 PIL Image 对象
    """
    image_data = base64.b64decode(base64_str)
    return Image.open(BytesIO(image_data))


def save_image_from_base64(base64_str: str, save_path: str):
    """
    将 Base64 编码的图片保存到指定路径
    """
    image_data = base64.b64decode(base64_str)
    with open(save_path, 'wb') as f:
        f.write(image_data)


def generate_with_scribble(
    api_url: str,
    prompt: str,
    negative_prompt: str,
    scribble_image_base64: str,
    width: int = 768,
    height: int = 512,
    steps: int = 20,
    cfg_scale: float = 7.0,
    controlnet_weight: float = 1.0,
    lora_detail_weight: float = 0.8,
) -> str:
    """
    使用 Scribble ControlNet 根据草稿图生成背景图
    返回生成的图片的 Base64 编码
    """
    # 构造 ControlNet 配置 - Scribble 模式
    controlnet_config = [
        {
            "input_image": scribble_image_base64,
            "module": "scribble",
            "model": "control_v11p_sd15_scribble [d57f0e5f]",
            "weight": controlnet_weight,
            "resize_mode": 0,
            "lowvram": False,
            "processor_res": 512,
            "threshold_a": 64,
            "threshold_b": 64,
            "guidance_start": 0.0,
            "guidance_end": 1.0,
            "pixel_perfect": True,
            "control_mode": 0,
        }
    ]

    # 构造请求负载
    payload = {
        "prompt": f"<lora:add_detail:{lora_detail_weight}>, {prompt}",
        "negative_prompt": f"easynegative, bad_prompt_version2, {negative_prompt}",
        "steps": steps,
        "cfg_scale": cfg_scale,
        "width": width,
        "height": height,
        "sampler_name": "DPM++ 2M Karras",
        "seed": -1,
        "batch_size": 1,
        "n_iter": 1,
        "alwayson_scripts": {
            "controlnet": {
                "args": controlnet_config
            }
        },
        "enable_hr": False,
        "do_not_save_samples": True,
        "do_not_save_grid": True,
    }

    response = requests.post(f"{api_url}/sdapi/v1/txt2img", json=payload)

    if response.status_code != 200:
        raise Exception(f"Scribble 生成失败: {response.status_code} - {response.text}")

    result = response.json()
    return result["images"][0]  # 返回生成的图片的 Base64 编码


def generate_with_inpaint_and_ipadapter(
    api_url: str,
    prompt: str,
    negative_prompt: str,
    background_image_base64: str,
    mask_image_base64: str,
    ip_adapter_image_base64: str,
    width: int = 768,
    height: int = 512,
    steps: int = 30,
    cfg_scale: float = 7.0,
    denoising_strength: float = 0.75,
    controlnet_weight: float = 1.0,
    lora_detail_weight: float = 0.8,
) -> str:
    """
    使用局部重绘功能，结合 IP-Adapter 生成最终图片
    返回生成的图片的 Base64 编码
    """
    # 构造 ControlNet 配置 - Inpaint 模式
    controlnet_config = [
        {
            "input_image": background_image_base64,
            "mask": mask_image_base64,
            "module": "inpaint",
            "model": "control_v11p_sd15_inpaint [ba3219e8]",
            "weight": controlnet_weight,
            "resize_mode": 0,
            "lowvram": False,
            "processor_res": 512,
            "guidance_start": 0.0,
            "guidance_end": 1.0,
            "pixel_perfect": True,
            "control_mode": 0,
            "inpaint_crop_input": False,
        }
    ]

    # 构造请求负载
    payload = {
        "prompt": f"<lora:add_detail:{lora_detail_weight}>, {prompt}",
        "negative_prompt": f"easynegative, bad_prompt_version2, {negative_prompt}",
        "init_images": [background_image_base64],
        "mask": mask_image_base64,
        "denoising_strength": denoising_strength,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "width": width,
        "height": height,
        "sampler_name": "DPM++ 2M Karras",
        "seed": -1,
        "batch_size": 1,
        "n_iter": 1,
        "alwayson_scripts": {
            "controlnet": {
                "args": controlnet_config
            },
            "ip-adapter": {
                "args": [
                    {
                        "image": ip_adapter_image_base64,
                        "weight": 1.0,
                        "begin": 0.0,
                        "end": 1.0,
                    }
                ]
            }
        },
        "enable_hr": False,
        "do_not_save_samples": True,
        "do_not_save_grid": True,
    }

    response = requests.post(f"{api_url}/sdapi/v1/img2img", json=payload)

    if response.status_code != 200:
        raise Exception(f"局部重绘生成失败: {response.status_code} - {response.text}")

    result = response.json()
    return result["images"][0]  # 返回生成的图片的 Base64 编码


def main():
    """
    主函数：用户交互式输入参数，执行两阶段生成并保存图片
    """
    # ========== 配置信息 ==========
    API_URL = "http://127.0.0.1:7860"  # 根据您的实际 API 地址修改
    OUTPUT_DIR = "./output"  # 输出目录

    # 确保输出目录存在
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # ========== 用户输入 ==========
    print("=" * 60)
    print("Stable Diffusion 图像生成脚本")
    print("=" * 60)

    # 输入提示词
    prompt = input("请输入正面提示词 (prompt): ").strip()
    if not prompt:
        prompt = "masterpiece, best quality, high resolution"

    negative_prompt = input("请输入负面提示词 (negative prompt，可选): ").strip()
    if not negative_prompt:
        negative_prompt = ""

    # 输入图片路径
    scribble_image_path = input("请输入第一张图片路径 (用于 Scribble 生成背景): ").strip()
    mask_image_path = input("请输入蒙版图片路径 (用于局部重绘): ").strip()
    ip_adapter_image_path = input("请输入第二张图片路径 (用于 IP-Adapter): ").strip()

    # 输入生成参数
    width = int(input("请输入生成宽度 (如 768，推荐 512-1024): ") or "768")
    height = int(input("请输入生成高度 (如 512，推荐 512-1024): ") or "512")
    steps = int(input("请输入迭代步数 (如 20-50): ") or "20")
    cfg_scale = float(input("请输入 CFG Scale (如 7.0): ") or "7.0")

    # ========== 第一阶段：使用 Scribble ControlNet 生成背景 ==========
    print("\n[步骤 1/2] 使用 Scribble ControlNet 生成背景图...")

    scribble_base64 = image_to_base64(scribble_image_path)

    background_base64 = generate_with_scribble(
        api_url=API_URL,
        prompt=prompt,
        negative_prompt=negative_prompt,
        scribble_image_base64=scribble_base64,
        width=width,
        height=height,
        steps=steps,
        cfg_scale=cfg_scale,
        controlnet_weight=1.0,
        lora_detail_weight=0.8,
    )

    print("  -> 背景图生成完成")

    # ========== 第二阶段：局部重绘 + IP-Adapter ==========
    print("\n[步骤 2/2] 使用局部重绘 + IP-Adapter 生成最终图片...")

    mask_base64 = image_to_base64(mask_image_path)
    ip_adapter_base64 = image_to_base64(ip_adapter_image_path)

    final_image_base64 = generate_with_inpaint_and_ipadapter(
        api_url=API_URL,
        prompt=prompt,
        negative_prompt=negative_prompt,
        background_image_base64=background_base64,
        mask_image_base64=mask_base64,
        ip_adapter_image_base64=ip_adapter_base64,
        width=width,
        height=height,
        steps=steps,
        cfg_scale=cfg_scale,
        denoising_strength=0.75,
        controlnet_weight=1.0,
        lora_detail_weight=0.8,
    )

    # ========== 保存最终图片 ==========
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join(OUTPUT_DIR, f"final_{timestamp}.png")

    save_image_from_base64(final_image_base64, save_path)

    print(f"\n图片已保存至: {save_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()