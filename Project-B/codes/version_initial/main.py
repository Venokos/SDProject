import base64
import io
import os
import requests
from PIL import Image
from typing import List, Optional

def img2img_with_scribble(
    init_image_path: str,                # 初始图像路径（图生图的底图）
    control_image_path: str,             # Scribble 控制图路径（原始图像，将由预处理器生成涂鸦效果）
    prompt: str,                         # 提示词（支持多行）
    negative_prompt: str = "",
    width: Optional[int] = 512,
    height: Optional[int] = 512,
    steps: int = 20,
    sampler_name: str = "DPM++ 2M",
    cfg_scale: float = 7,
    denoising_strength: float = 0.51,
    resize_mode: int = 1,
    batch_size: int = 4,
    save_dir: Optional[str] = None,
    api_url: str = "http://127.0.0.1:7860"
) -> List[Image.Image]:
    """
    使用固定的 Scribble ControlNet 进行图生图生成。
    - 初始图像和控制图分开提供。
    - 内部固定使用 scribble 预处理器和对应的 ControlNet 模型。
    - 固定权重 1.0，控制模式偏向 ControlNet (2)，全程介入。

    :param init_image_path: 初始图像路径（img2img 的基础图）
    :param control_image_path: 控制图像路径（用于 Scribble 预处理的原图）
    :param prompt: 提示词（支持长文本，可用括号权重）
    :param negative_prompt: 反向提示词
    :param width, height: 生成尺寸，不指定则使用初始图像尺寸
    :param steps: 采样步数
    :param sampler_name: 采样器名称
    :param cfg_scale: CFG 强度
    :param denoising_strength: 去噪强度 (0-1)
    :param resize_mode: 尺寸调整模式 (0=调整大小, 1=裁剪, 2=拉伸)
    :param batch_size: 批量生成数量
    :param save_dir: 保存目录，None 则只返回图像列表
    :param api_url: WebUI API 地址
    :return: PIL Image 对象列表
    """
    # 1. 读取并编码初始图像
    with open(init_image_path, "rb") as f:
        init_img_b64 = base64.b64encode(f.read()).decode("utf-8")

    # 2. 读取并编码控制图像（用于 Scribble 预处理）
    with open(control_image_path, "rb") as f:
        control_img_b64 = base64.b64encode(f.read()).decode("utf-8")

    # 3. 如果未指定尺寸，使用初始图像尺寸
    if width is None or height is None:
        with Image.open(init_image_path) as img:
            width = width or img.width
            height = height or img.height

    # 4. 固定 ControlNet 配置（Scribble）
    #   注意：模型名称必须与你的 WebUI 中显示的完全一致，可能包含哈希值
    controlnet_config = {
        "enabled": True,
        "image": control_img_b64,          # 使用单独的控制图
        "module": "scribble_pidinet",# 固定 scribble 预处理器
        "model": "control_v11p_sd15_scribble [d4ba51ff]",  # 根据实际安装修改
        "weight": 2.0,
        "control_mode": "ControlNet is more important",                       # 偏向 ControlNet
        "guidance_start": 0.0,
        "guidance_end": 1.0
    }

    # 5. 构建 payload
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "init_images": [init_img_b64],
        "width": width,
        "height": height,
        "steps": steps,
        "sampler_name": sampler_name,
        "cfg_scale": cfg_scale,
        "denoising_strength": denoising_strength,
        "resize_mode": resize_mode,
        "batch_size": batch_size,
        "alwayson_scripts": {
            "controlnet": {
                "args": [controlnet_config]
            }
        }
    }

    # 6. 发送请求
    response = requests.post(
        f"{api_url}/sdapi/v1/img2img",
        json=payload,
        timeout=300
    )
    if response.status_code != 200:
        raise Exception(f"API 请求失败: {response.status_code}, {response.text}")

    result = response.json()
    images_base64 = result.get("images")
    if not images_base64:
        raise Exception("未返回任何图像")

    # 7. 解码并保存
    pil_images = []
    for i, img_b64 in enumerate(images_base64):
        img_data = base64.b64decode(img_b64)
        pil_img = Image.open(io.BytesIO(img_data))
        pil_images.append(pil_img)

        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, f"output_{i:03d}.png")
            pil_img.save(save_path)
            print(f"已保存: {save_path}")

    return pil_images