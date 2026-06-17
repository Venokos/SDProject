# ============================================================
#
#   项目名称:    Scribble ControlNet · 商品场景生成器
#   文件名称:    app.py
#   版本号:      v2.0.0
#   创建日期:    2026-04-18
#   最后修改:    2026-04-20
#   作者:        
#
#   描述:
#       基于 Gradio Blocks 构建的商品场景图生成工具前端原型。
#       用户上传商品图、选择场景风格、手绘 Scribble 草稿后,
#       通过 ControlNet 管线生成高质量的商品场景合成图。
#       已接入 ControlNet 生成管线, 调用 WebUI API 进行真实图像生成。
#
#   运行环境:
#       Python      >= 3.9
#       Gradio      == 6.0.x  (pip install gradio==6.0.0)
#       NumPy       >= 1.24   (pip install numpy)
#       Pillow      >= 10.0   (pip install pillow)
#
#   快速启动:
#       pip install gradio==6.0.0 numpy pillow
#       python app.py
#       浏览器访问 http://127.0.0.1:7860
#
#   架构概览:
#       模块一  团队协作接口    generate_prompt / process_scribble / generate_image
#       模块二  主管线          main_process -> 串联三个接口
#       模块三  界面与样式      CUSTOM_CSS + Gradio Blocks 布局
#       模块四  应用启动        demo.launch()
#
#   管线流程:
#       用户点击[生成] -> extract_and_process()
#         -> Step 1: generate_prompt(bg_type, image)   返回 prompt 文本
#         -> Step 2: process_scribble(raw_scribble)    返回 512x512 线稿
#         -> Step 3: generate_image(prompt, scribble, weight, image) 返回结果图
#         -> 结果显示在右侧预览区
#
#   已知约束 (Gradio 6.0):
#       - 外框容器不可设 overflow:hidden, 否则画笔颜色选择器弹窗被裁剪
#       - 多显示器 DPI 缩放会导致空画板渲染异常, 需通过 JS 触发 ResizeObserver 修复
#       - css 参数须传入 launch() 而非 Blocks() 构造函数
#       - <script> 标签会被 Gradio 过滤, 需用 onclick 内联或 demo.load(js=...)
#
#   变更记录:
#       v1.0.0  2026-04-18  初始版本: 界面布局 + 桩函数 + 管线串联
#       v1.1.0  2026-04-18  修复画笔颜色选择器; 整理重构; 添加深色模式
#       v1.2.1  2026-04-20  通过 JS 抖动容器彻底修复多显示器 DPI 画板渲染 Bug
#       v2.0.0  2026-06-02  接入 ControlNet 生成管线, 替换桩函数为真实 API 调用
#
# ============================================================


# ----------------------------------------------------------
# 标准库导入
# ----------------------------------------------------------
import os                       # 文件路径操作
import sys                      # 模块搜索路径
import tempfile                 # 临时文件处理
import time                     # 模拟推理耗时

# ----------------------------------------------------------
# 第三方库导入
# ----------------------------------------------------------
import gradio as gr             # Web UI 框架 (v6.0)
import numpy as np              # 数值计算 (预留, 后续模型推理使用)
from PIL import (               # 图像处理
    Image,
    ImageDraw,
    ImageFont,
)

# ----------------------------------------------------------
# 项目模块导入
# ----------------------------------------------------------
# 将项目根目录添加到 sys.path
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, PROJECT_ROOT)

# 导入 ControlNet 图像生成模块 (成员A)
from backend.generate import generate_image as sd_generate_image

# 导入 Prompt 生成模块 (成员C)
from prompt.prompt_generator import EcommercePromptGenerator

# 导入 Scribble 模板映射 (成员B)
from scribble.scribble_map import (
    get_scribble_path,
    get_scribble_options,
    parse_scribble_key,
    SCRIBBLE_DISPLAY_NAMES,
)


# ============================================================
#
#   模块一: 团队协作接口定义
#
# ============================================================

# 初始化 Prompt 生成器 (成员C模块)
_prompt_generator = EcommercePromptGenerator()

# 场景风格映射 (UI显示名 -> prompt_generator参数)
BG_TYPE_MAP = {
    "studio": "简约",
    "beach": "海滩",
    "nature": "自然",
    "luxury": "奢华",
    "minimal": "简约",
}

# 场景风格对应的详细参数配置
BG_CONFIG_MAP = {
    "studio":    {"composition": "中心", "lighting": "棚拍", "color_scheme": "中性"},
    "beach":     {"composition": "三分法", "lighting": "自然光", "color_scheme": "暖色调"},
    "nature":    {"composition": "三分法", "lighting": "自然光", "color_scheme": "绿色调"},
    "luxury":    {"composition": "中心", "lighting": "棚拍", "color_scheme": "奢华"},
    "minimal":   {"composition": "中心", "lighting": "柔光", "color_scheme": "中性"},
}


def generate_prompt(bg_type, image=None):
    """
    根据场景风格与商品图生成文本提示词。
    整合成员C的 Prompt 生成模块。
    """
    # 将 UI 的 bg_type 映射到 prompt_generator 的参数
    prompt_bg_type = BG_TYPE_MAP.get(bg_type, "简约")
    
    # 获取该场景风格的详细配置
    bg_config = BG_CONFIG_MAP.get(bg_type, {})
    composition = bg_config.get("composition", "中心")
    lighting = bg_config.get("lighting", "自然光")
    color_scheme = bg_config.get("color_scheme", "中性")

    # 使用成员C的 Prompt 生成器
    prompt = _prompt_generator.generate_prompt(
        product_type="配饰",  # 默认产品类型，可根据需要扩展
        background=prompt_bg_type,
        composition=composition,
        lighting=lighting,
        color_scheme=color_scheme,
    )

    # 添加高质量关键词
    prompt += ", high quality, 8k resolution, professional product photography"

    return prompt


def process_scribble(raw_scribble):
    """预处理画板原始涂鸦数据为 ControlNet 标准输入。
    
    Gradio 6.0 Sketchpad 可能返回 dict 格式数据，需要提取图像。
    """
    # 处理 Gradio 6.0 Sketchpad 返回的 dict 格式
    if isinstance(raw_scribble, dict):
        # 尝试从 dict 中提取图像数据
        # 可能的键: 'image', 'composite', 'background', 'layers' 等
        print(f"Sketchpad returned dict with keys: {list(raw_scribble.keys())}")
        
        # 优先尝试常见的图像键
        for key in ['composite', 'image', 'background', 'layer']:
            if key in raw_scribble and raw_scribble[key] is not None:
                raw_scribble = raw_scribble[key]
                print(f"Extracted image from dict key: {key}")
                break
        else:
            # 如果找不到图像键，尝试第一个非 None 值
            for key, value in raw_scribble.items():
                if value is not None and key != 'layers':
                    raw_scribble = value
                    print(f"Extracted image from dict key: {key}")
                    break
    
    # 如果还是 dict 或 None，返回白色占位图
    if raw_scribble is None:
        print("No scribble data, returning white placeholder")
        return Image.new("RGB", (512, 512), color=(255, 255, 255))
    
    if isinstance(raw_scribble, dict):
        print("WARNING: Still got dict after extraction, returning white placeholder")
        return Image.new("RGB", (512, 512), color=(255, 255, 255))
    
    # 现在应该是 PIL Image 了
    if hasattr(raw_scribble, 'mode'):
        # 转换为 RGB 模式（处理 RGBA 透明通道）并缩放到 512x512
        if raw_scribble.mode == "RGBA":
            background = Image.new("RGB", raw_scribble.size, (255, 255, 255))
            background.paste(raw_scribble, mask=raw_scribble.split()[3])
            scribble = background
        else:
            scribble = raw_scribble.convert("RGB")
        return scribble.resize((512, 512))
    
    # 未知类型
    print(f"WARNING: Unknown scribble type: {type(raw_scribble)}, returning white placeholder")
    return Image.new("RGB", (512, 512), color=(255, 255, 255))


def generate_image(prompt, scribble, weight, image, scribble_template=None):
    """
    调用 ControlNet 模型生成最终商品场景图。
    整合成员A的图像生成模块与成员B的模板系统。

    参数:
        prompt: 文本提示词
        scribble: PIL Image 格式的涂鸦图 (来自画板)
        weight: ControlNet 权重
        image: 商品原图 (预留，暂未使用)
        scribble_template: 预设模板 key (如 "desk", "stand") 或 "custom"
    """
    # --- 调试日志 ---
    print("=" * 50)
    print("generate_image() 被调用:")
    print(f"  prompt   : {prompt}")
    print(f"  scribble : {type(scribble)} | "
          f"{scribble.size if isinstance(scribble, Image.Image) else 'N/A'}")
    print(f"  weight   : {weight}")
    print(f"  image    : {'有商品图' if image is not None else '无商品图'}")
    print(f"  template : {scribble_template}")
    print("=" * 50)

    # 确定使用的 scribble 路径
    scribble_path = None
    cleanup_temp = False

    if scribble_template == "custom" and scribble is not None:
        # 用户选择自定义画板，且画板有内容 -> 使用画板绘制的涂鸦
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            scribble.save(tmp.name)
            scribble_path = tmp.name
            cleanup_temp = True
            print(f"  使用画板涂鸦: {scribble_path}")
    elif scribble_template and scribble_template != "custom":
        # 使用预设模板 (成员B)
        scribble_path = get_scribble_path(scribble_template)
        print(f"  使用预设模板: {scribble_path}")
    elif scribble is not None:
        # 无模板选择但画板有内容 -> 使用画板
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            scribble.save(tmp.name)
            scribble_path = tmp.name
            cleanup_temp = True
            print(f"  使用画板涂鸦: {scribble_path}")
    else:
        # 无涂鸦，使用默认模板
        scribble_path = get_scribble_path("desk")
        print(f"  使用默认模板: {scribble_path}")

    # 保存商品图到临时文件（如果存在）
    product_image_path = None
    if image is not None:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            image.save(tmp.name)
            product_image_path = tmp.name
            print(f"Saved product image to: {product_image_path}")

    try:
        # 调用成员A的 ControlNet 生成函数
        print(f"Calling sd_generate_image with:")
        print(f"  prompt: {prompt[:100]}...")
        print(f"  scribble_path: {scribble_path}")
        print(f"  weight: {weight}")
        print(f"  product_image_path: {product_image_path}")
        
        output_path = sd_generate_image(
            prompt=prompt,
            scribble_path=scribble_path,
            weight=weight,
            product_image_path=product_image_path,
        )

        if output_path is None:
            # 生成失败，返回错误提示图
            print("ERROR: sd_generate_image returned None")
            result = Image.new("RGB", (512, 512), color=(200, 50, 50))
            draw = ImageDraw.Draw(result)
            try:
                font = ImageFont.truetype("arial.ttf", 28)
            except (OSError, IOError):
                font = ImageFont.load_default()
            draw.text((80, 200), "Generation Failed!", fill=(255, 255, 255), font=font)
            draw.text((40, 260), "Check console for details", fill=(255, 200, 200), font=font)
            return result

        # 读取生成的图片并返回
        print(f"Success! Output at: {output_path}")
        return Image.open(output_path)
    except Exception as e:
        print(f"ERROR in generate_image: {e}")
        import traceback
        traceback.print_exc()
        # 返回错误提示图
        result = Image.new("RGB", (512, 512), color=(200, 50, 50))
        draw = ImageDraw.Draw(result)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except (OSError, IOError):
            font = ImageFont.load_default()
        draw.text((40, 200), f"Error: {str(e)[:40]}", fill=(255, 255, 255), font=font)
        return result
    finally:
        # 清理临时文件
        if cleanup_temp:
            try:
                os.unlink(scribble_path)
            except OSError:
                pass
        if product_image_path:
            try:
                os.unlink(product_image_path)
            except OSError:
                pass


# ============================================================
#
#   模块二: 主管线函数 (Main Pipeline)
#
# ============================================================

def main_process(product_image, bg_type, controlnet_weight, raw_scribble, scribble_template):
    """
    主管线函数 -- 串联所有接口, 完成端到端的图片生成流程。
    整合 A、B、C 三个模块。
    """
    print("\n" + "=" * 60)
    print("main_process() 启动")
    print("=" * 60)

    print("\nStep 1: generate_prompt() [成员C模块]...")
    prompt = generate_prompt(bg_type=bg_type, image=product_image)
    print(f"  -> prompt = '{prompt}'")

    print("\nStep 2: process_scribble()...")
    processed_scribble = process_scribble(raw_scribble=raw_scribble)
    print(f"  -> scribble size = {processed_scribble.size}")

    print("\nStep 3: generate_image() [成员A模块 + 成员B模板]...")
    result_image = generate_image(
        prompt=prompt,
        scribble=processed_scribble,
        weight=controlnet_weight,
        image=product_image,
        scribble_template=scribble_template,
    )
    print(f"  -> result size = {result_image.size}")
    print("=" * 60 + "\n")

    return result_image


def extract_and_process(product_image, style_full, controlnet_weight, raw_scribble, scribble_template_full):
    """
    Gradio 按钮回调入口 -- 从选项中提取标识符, 再调用主管线。
    """
    # 提取场景风格
    bg_type = style_full.split("|")[0].strip() if style_full else "studio"

    # 提取 scribble 模板 key
    scribble_template = "custom"  # 默认使用画板
    if scribble_template_full:
        scribble_template = parse_scribble_key(scribble_template_full)

    return main_process(product_image, bg_type, controlnet_weight, raw_scribble, scribble_template)


# ============================================================
#
#   模块三: 界面布局与样式 (UI Layout & Styling)
#
# ============================================================

CUSTOM_CSS = """
/* ==========================================================
   浅色主题 CSS 变量 (默认)
   ========================================================== */
:root {
    --bg-body: #f3f4f6;
    --bg-wrapper: #ffffff;
    --border-wrapper: #e5e7eb;
    --border-col: #f3f4f6;
    --border-title: #f3f4f6;
    --text-title: #1f2937;
    --text-sub: #6b7280;
    --text-body: #4b5563;
    --text-muted: #9ca3af;
    --radio-bg: #ffffff;
    --radio-border: #e5e7eb;
    --radio-hover-border: #a5b4fc;
    --radio-hover-bg: #f8fafc;
    --radio-active-bg: #eef2ff;
    --radio-active-border: #6366f1;
    --radio-label: #4f46e5;
    --hint-bg: #f8fafc;
    --hint-border: #e2e8f0;
    --hint-text: #64748b;
}

/* ==========================================================
   深色主题 CSS 变量 (通过 body.dark 激活)
   ========================================================== */
.dark {
    --bg-body: #0b1121;
    --bg-wrapper: #111827;
    --border-wrapper: #1e3a8a;
    --border-col: #1f2937;
    --border-title: #1f2937;
    --text-title: #f3f4f6;
    --text-sub: #9ca3af;
    --text-body: #d1d5db;
    --text-muted: #6b7280;
    --radio-bg: #1f2937;
    --radio-border: #374151;
    --radio-hover-border: #3b82f6;
    --radio-hover-bg: rgba(59, 130, 246, 0.08);
    --radio-active-bg: rgba(59, 130, 246, 0.15);
    --radio-active-border: #3b82f6;
    --radio-label: #93c5fd;
    --hint-bg: rgba(59, 130, 246, 0.1);
    --hint-border: rgba(59, 130, 246, 0.2);
    --hint-text: #93c5fd;

    /* 覆盖 Gradio 原生暗色变量, 消除默认灰色 */
    --body-background-fill: var(--bg-body) !important;
    --background-fill-primary: var(--bg-wrapper) !important;
    --background-fill-secondary: #1f2937 !important;
    --border-color-primary: #374151 !important;
    --block-background-fill: #1f2937 !important;
    --block-border-color: #374151 !important;
    --input-background-fill: #1f2937 !important;
}

/* ==========================================================
   全局布局
   ========================================================== */
body { margin: 0 !important; background: var(--bg-body) !important; transition: background 0.3s ease; }
.gradio-container { max-width: 1700px !important; padding: 0 24px !important; margin: 0 auto !important; background: transparent !important; }
footer { display: none !important; }

/* 顶部标题栏 */
#title-bar { text-align: center; padding: 16px 0 8px; }
#title-bar h1 { font-size: 1.8rem; background: linear-gradient(90deg, #6366f1, #8b5cf6, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0; }
.dark #title-bar h1 { background: linear-gradient(90deg, #60a5fa, #a78bfa, #c084fc); -webkit-background-clip: text; }
#title-bar p { color: var(--text-sub); font-size: 0.9rem; margin-top: 4px; }

/* 主题切换按钮 */
#theme-toggle-wrap { position: fixed; top: 16px; right: 24px; z-index: 9999; }
#theme-toggle-wrap button { width: 42px; height: 42px; border-radius: 50%; border: 1px solid var(--border-col); background: var(--bg-wrapper); box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; }
#theme-toggle-wrap button:hover { transform: scale(1.1); }
.dark #theme-toggle-wrap button { box-shadow: 0 0 15px rgba(59, 130, 246, 0.3); border-color: #3b82f6; }

/* 外框容器 */
#outer-wrapper { border: 1px solid var(--border-wrapper); border-radius: 16px; background: var(--bg-wrapper) !important; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06); padding: 0 !important; margin-bottom: 30px; transition: all 0.3s ease; }
.dark #outer-wrapper { box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(59, 130, 246, 0.15); }

/* 三列布局 */
#main-row { display: flex !important; flex-wrap: nowrap !important; gap: 0 !important; align-items: stretch !important; }

#col-left   { flex: 0 0 24% !important; max-width: 24% !important; min-width: 0 !important; }
#col-center { flex: 0 0 48% !important; max-width: 48% !important; min-width: 0 !important; }
#col-right  { flex: 0 0 28% !important; max-width: 28% !important; min-width: 0 !important; }

/* 列内通用样式 */
.col-inner { padding: 20px !important; border: none !important; background: transparent !important; box-shadow: none !important; border-radius: 0 !important; height: 100% !important; display: flex !important; flex-direction: column !important; }
#col-left .col-inner { border-right: 1px solid var(--border-col) !important; overflow: visible !important; }
#col-center .col-inner { border-right: 1px solid var(--border-col) !important; }
.col-inner h3 { font-size: 1rem !important; color: var(--text-title) !important; font-weight: 600 !important; margin: 0 0 12px 0 !important; padding-bottom: 10px !important; border-bottom: 2px solid var(--border-title) !important; }

/* ==========================================================
   Radio 场景风格选择器美化
   ========================================================== */
#style-radio, #style-radio * { background-color: transparent !important; background: transparent !important; }
#style-radio label { background: var(--radio-bg) !important; border: 1px solid var(--radio-border) !important; border-radius: 12px !important; padding: 10px 12px !important; margin: 0 !important; cursor: pointer !important; transition: background 0.2s ease, border-color 0.2s ease !important; box-sizing: border-box !important; }
#style-radio label:hover { border-color: var(--radio-hover-border) !important; background: var(--radio-hover-bg) !important; }
#style-radio label.selected, #style-radio label:has(input:checked) { background: var(--radio-active-bg) !important; border-color: var(--radio-active-border) !important; box-shadow: inset 0 0 0 1px var(--radio-active-border) !important; }
#style-radio input[type="radio"] { display: none !important; }
#style-radio label span { font-size: 0.85rem !important; font-weight: 600 !important; color: var(--radio-label) !important; }
#style-radio .wrap { display: flex !important; flex-direction: column !important; gap: 8px !important; padding: 0 !important; }
#style-radio > .label-wrap { margin-bottom: 8px !important; }
#style-radio > .label-wrap span { font-size: 0.95rem !important; font-weight: 600 !important; color: var(--text-title) !important; }

/* Scribble 模板选择器样式 */
#scribble-radio, #scribble-radio * { background-color: transparent !important; background: transparent !important; }
#scribble-radio label { background: var(--radio-bg) !important; border: 1px solid var(--radio-border) !important; border-radius: 10px !important; padding: 8px 10px !important; margin: 0 !important; cursor: pointer !important; transition: background 0.2s ease, border-color 0.2s ease !important; box-sizing: border-box !important; }
#scribble-radio label:hover { border-color: var(--radio-hover-border) !important; background: var(--radio-hover-bg) !important; }
#scribble-radio label.selected, #scribble-radio label:has(input:checked) { background: var(--radio-active-bg) !important; border-color: var(--radio-active-border) !important; }
#scribble-radio input[type="radio"] { display: none !important; }
#scribble-radio label span { font-size: 0.8rem !important; font-weight: 500 !important; color: var(--radio-label) !important; }
#scribble-radio .wrap { display: flex !important; flex-direction: column !important; gap: 6px !important; padding: 0 !important; }

/* ==========================================================
   通用组件样式 & 深色覆盖
   ========================================================== */
.col-inner label span, .col-inner .label-wrap span { color: var(--text-body) !important; }
.col-inner img { max-width: 100% !important; object-fit: contain !important; }
.dark .col-inner .upload-area, .dark .col-inner .image-container { background: rgba(15, 25, 60, 0.5) !important; border-color: rgba(60, 100, 220, 0.3) !important; }
.dark .col-inner .upload-area * { color: #8fa0cc !important; }
.dark .col-inner input[type="number"] { background: rgba(15, 25, 60, 0.8) !important; border-color: rgba(60, 100, 220, 0.4) !important; color: #fff !important; }

/* 提示条 */
.hint-bar { display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 12px; padding: 8px 16px; background: var(--hint-bg); border: 1px solid var(--hint-border); border-radius: 10px; }
.hint-bar .hint-icon { font-size: 0.9rem; opacity: 0.8; color: var(--hint-text); }
.hint-bar .hint-text { font-size: 0.82rem; color: var(--hint-text); }

/* 生成按钮 */
#generate-btn { background: linear-gradient(135deg, #6366f1, #a855f7) !important; color: #fff !important; font-size: 1.1rem !important; font-weight: 600 !important; border: none !important; border-radius: 12px !important; padding: 14px 0 !important; margin-top: 16px; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3) !important; transition: all 0.2s ease; }
#generate-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4) !important; }
.dark #generate-btn { background: linear-gradient(135deg, #3b82f6, #8b5cf6) !important; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important; }

/* 结果图区域 */
#result-img .image-container { border-radius: 10px !important; }
#footer-text { text-align: center; padding: 10px 0; }
#footer-text p { color: var(--text-muted) !important; font-size: 0.8rem !important; margin: 0 !important; }
"""

# ==========================================================
#   模块三续: 构建 Gradio Blocks 界面
# ==========================================================

demo = gr.Blocks(title="Scribble ControlNet Studio")

with demo:

    # ----------------------------------------------------------
    # 主题切换按钮 (纯 HTML + 内联 onclick)
    # ----------------------------------------------------------
    gr.HTML("""
    <div id="theme-toggle-wrap">
        <button id="theme-toggle-real" title="切换深色/浅色主题"
                onclick="
                    var b=document.body, d=document.documentElement;
                    var isDark=b.classList.contains('dark');
                    if(isDark){
                        b.classList.remove('dark');
                        d.classList.remove('dark');
                        this.textContent='🌙';
                    } else {
                        b.classList.add('dark');
                        d.classList.add('dark');
                        this.textContent='☀️';
                    }
                ">☀️</button>
    </div>
    """)

    # ----------------------------------------------------------
    # 顶部标题
    # ----------------------------------------------------------
    with gr.Column(elem_id="title-bar"):
        gr.Markdown(
            "# Scribble ControlNet - 商品场景生成器\n"
            "上传商品图 - 手绘构图草稿 - 一键生成高质量场景图"
        )

    # ----------------------------------------------------------
    # 外框容器 (包裹三列)
    # ----------------------------------------------------------
    with gr.Group(elem_id="outer-wrapper"):
        with gr.Row(equal_height=True, elem_id="main-row"):

            # ==================== 左侧列 ====================
            with gr.Column(scale=1, min_width=0, elem_id="col-left"):
                with gr.Column(elem_classes="col-inner"):
                    gr.Markdown("### 商品 & 参数")

                    product_image = gr.Image(
                        label="上传商品图",
                        type="pil",
                        height=240,
                        sources=["upload"],
                    )

                    scene_style = gr.Radio(
                        choices=[
                            "studio  |  影棚纯色背景",
                            "beach  |  海滩阳光氛围",
                            "nature  |  自然草地森林",
                            "luxury  |  高端大理石台面",
                            "minimal  |  极简留白风",
                        ],
                        value="studio  |  影棚纯色背景",
                        label="场景风格",
                        elem_id="style-radio",
                        interactive=True,
                    )

                    controlnet_strength = gr.Slider(
                        label="ControlNet 强度",
                        minimum=0.0,
                        maximum=1.5,
                        value=0.7,
                        step=0.05,
                        interactive=True,
                    )

                    # Scribble 模板选择 (成员B模块)
                    scribble_template = gr.Radio(
                        choices=["自定义画板 | 使用下方画板绘制"] + get_scribble_options(),
                        value="自定义画板 | 使用下方画板绘制",
                        label="Scribble 模板",
                        elem_id="scribble-radio",
                        interactive=True,
                    )

            # ==================== 中间列 ====================
            with gr.Column(scale=2, min_width=0, elem_id="col-center"):
                with gr.Column(elem_classes="col-inner"):
                    gr.Markdown("### Scribble 草稿画板")

                    # 手绘画板
                    # 修复: 移除 value=Image.new()，让 Gradio 自动初始化空画布
                    scribble_pad = gr.Sketchpad(
                        label="在此绘制构图草稿",
                        type="pil",
                        height=600,
                        elem_id="sketchpad-area",
                        brush=gr.Brush(
                            colors=[
                                "#000000", "#ef4444", "#22c55e", "#3b82f6", 
                                "#f59e0b", "#a855f7", "#00aaaa", "#ffffff",
                            ],
                            default_size=5,
                            color_mode="defaults",
                        ),
                    )

                    gr.HTML("""
                    <div class="hint-bar">
                        <span class="hint-icon">&#9998;</span>
                        <span class="hint-text">使用鼠标或触控笔绘制商品摆放位置与场景轮廓</span>
                    </div>
                    """)

            # ==================== 右侧列 ====================
            with gr.Column(scale=1, min_width=0, elem_id="col-right"):
                with gr.Column(elem_classes="col-inner"):
                    gr.Markdown("### 生成结果")

                    result_image = gr.Image(
                        label="生成结果预览",
                        type="pil",
                        format="png",
                        height=540,
                        interactive=False,
                        elem_id="result-img",
                    )

                    generate_btn = gr.Button(
                        "生成",
                        variant="primary",
                        elem_id="generate-btn",
                    )

                    gr.HTML("""
                    <div class="hint-bar">
                        <span class="hint-icon">&#9881;</span>
                        <span class="hint-text">已接入 ControlNet 生成管线 · 需启动 WebUI API (端口7860)</span>
                    </div>
                    """)

    # ----------------------------------------------------------
    # 底部版权信息
    # ----------------------------------------------------------
    gr.Markdown("Powered by Gradio Blocks - v2.0.0", elem_id="footer-text")

    # ----------------------------------------------------------
    # 事件绑定
    # ----------------------------------------------------------
    def safe_extract_and_process(product_image, scene_style, controlnet_strength, scribble_pad, scribble_template):
        """包装函数，捕获所有异常并返回错误信息图"""
        try:
            print("=" * 60)
            print("safe_extract_and_process 被调用")
            print(f"  product_image type: {type(product_image)}")
            if isinstance(product_image, dict):
                print(f"  product_image keys: {list(product_image.keys())}")
            print(f"  scene_style: {scene_style}")
            print(f"  controlnet_strength: {controlnet_strength}")
            print(f"  scribble_pad type: {type(scribble_pad)}")
            if isinstance(scribble_pad, dict):
                print(f"  scribble_pad keys: {list(scribble_pad.keys())}")
                print(f"  scribble_pad values types: {[type(v) for v in scribble_pad.values()]}")
            print(f"  scribble_template: {scribble_template}")
            print("=" * 60)
            return extract_and_process(product_image, scene_style, controlnet_strength, scribble_pad, scribble_template)
        except Exception as e:
            print(f"CRITICAL ERROR in safe_extract_and_process: {e}")
            import traceback
            traceback.print_exc()
            # 返回带错误信息的图片
            result = Image.new("RGB", (512, 512), color=(200, 50, 50))
            draw = ImageDraw.Draw(result)
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except (OSError, IOError):
                font = ImageFont.load_default()
            draw.text((20, 200), f"Error: {str(e)[:50]}", fill=(255, 255, 255), font=font)
            draw.text((20, 240), "Check Python console", fill=(255, 200, 200), font=font)
            return result

    generate_btn.click(
        fn=safe_extract_and_process,
        inputs=[product_image, scene_style, controlnet_strength, scribble_pad, scribble_template],
        outputs=[result_image],
    )

    # ----------------------------------------------------------
    # 页面加载后执行的 JS
    # ----------------------------------------------------------
    demo.load(fn=None, inputs=None, outputs=None, js="""
    function() {
        // 0. 默认启用深色主题
        document.body.classList.add('dark');
        document.documentElement.classList.add('dark');
        // 1. 精准删除分享按钮 (保留下载按钮)
        setInterval(function() {
            var c = document.getElementById('result-img');
            if (!c) return;
            c.querySelectorAll('svg[viewBox="0 0 32 32"]').forEach(function(svg) {
                var path = svg.querySelector('path');
                if (path) {
                    var d = path.getAttribute('d') || '';
                    if (d.indexOf('M23,20') === 0) {
                        var btn = svg.closest('div.small') || svg.parentElement;
                        if (btn) btn.remove();
                    }
                }
            });
        }, 500);

        // 2. 修复多显示器 DPI 画板渲染 Bug
        // 核心原理: 通过 JS 微微抖动容器宽度, 强制触发 Gradio 内部的 ResizeObserver 重新计算画布
        function fixCanvas() {
            var pad = document.getElementById('sketchpad-area');
            if (!pad) return;
            
            // 触发 window resize
            window.dispatchEvent(new Event('resize'));
            
            // 抖动容器宽度触发 ResizeObserver
            var oldWidth = pad.style.width;
            pad.style.width = '99.5%';
            setTimeout(function() {
                pad.style.width = oldWidth || '100%';
            }, 50);
        }
        
        // 在页面加载后的不同阶段多次触发, 确保覆盖组件挂载完成的时机
        setTimeout(fixCanvas, 100);
        //setTimeout(fixCanvas, 200);
        //setTimeout(fixCanvas, 800);
        //setTimeout(fixCanvas, 2000);
        //setTimeout(fixCanvas, 4000);
    }
    """)


# ============================================================
#   模块四: 启动
# ============================================================

if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7861,
        inbrowser=True,
        css=CUSTOM_CSS,
    )
