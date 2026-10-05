#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终 Web/UI：基于冻结 ComfyUI workflow 的一键生成界面。"""

from __future__ import annotations

import os
import sys
import time
import traceback
from typing import Any, Dict, Tuple

import gradio as gr
from PIL import Image


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.comfyui_client import ComfyUIClient, ComfyUIError
from prompt.examples import load_example_prompts


OUTPUT_DIR = os.path.join(PROJECT_ROOT, "ui", "pyOutput")
os.makedirs(OUTPUT_DIR, exist_ok=True)

_EXAMPLES = load_example_prompts()
_EXAMPLE_TITLES = [ex["title"] for ex in _EXAMPLES]
_EXAMPLE_BY_TITLE = {ex["title"]: ex["prompt"] for ex in _EXAMPLES}

client = ComfyUIClient()


def _coerce_pil(image: Any) -> Image.Image | None:
    """兼容 Gradio 可能返回的 dict / 路径 / PIL 三种情况。"""
    if image is None:
        return None
    if isinstance(image, Image.Image):
        return image
    if isinstance(image, dict):
        for key in ("composite", "image", "path", "background"):
            if key in image and image[key] is not None:
                return _coerce_pil(image[key])
        return None
    if isinstance(image, str) and os.path.exists(image):
        return Image.open(image).convert("RGB")
    return None


def _status(md: str) -> str:
    return md


def fill_prompt(title: str | None) -> str:
    if not title:
        return ""
    return _EXAMPLE_BY_TITLE.get(title, "")


def toggle_seed(random_seed: bool) -> Dict[str, Any]:
    if random_seed:
        return gr.update(interactive=False, placeholder="随机模式：生成后显示本次 Seed")
    return gr.update(interactive=True, placeholder="例如：1234567890")


def _resolve_seed_input(random_seed: bool, seed_input: str) -> Tuple[str, int | None]:
    if random_seed:
        return "random", None
    text = (seed_input or "").strip()
    if not text:
        raise ComfyUIError("请输入固定 Seed，或勾选「随机 Seed」。")
    try:
        value = int(text)
    except ValueError:
        raise ComfyUIError("固定 Seed 必须是整数。")
    return "fixed", value


def _save_result(image: Image.Image, seed: int) -> str:
    filename = f"result_{seed}_{int(time.time())}.png"
    path = os.path.join(OUTPUT_DIR, filename)
    image.save(path, format="PNG")
    return path


def on_generate(
    product_image: Any,
    prompt_text: str,
    random_seed: bool,
    seed_input: str,
):
    """生成回调。用 generator 逐步向前端推送状态。"""
    image = _coerce_pil(product_image)
    if image is None:
        yield _status("⚠️ 请先上传商品图片。"), "", None, None
        return

    prompt = (prompt_text or "").strip()
    if not prompt:
        yield _status("⚠️ 请输入背景描述 / Prompt。"), "", None, None
        return

    try:
        seed_mode, seed = _resolve_seed_input(random_seed, seed_input)
    except ComfyUIError as exc:
        yield _status(f"⚠️ {exc.user_message}"), "", None, None
        return

    try:
        yield _status("🔌 正在连接 ComfyUI……"), "", None, None
        client.check_server()

        yield _status("📤 正在上传商品图片……"), "", None, None
        filename = client.upload_image(image)

        actual_seed = client.random_seed() if seed_mode == "random" else seed
        api_prompt = client.build_prompt(filename, prompt, actual_seed)

        yield _status("⏳ 正在生成，请稍候……"), "", None, None
        prompt_id = client.queue_prompt(api_prompt)
        history = client.wait_for_result(prompt_id)
        result = client.extract_image(history)

        download_path = _save_result(result, actual_seed)
        yield (
            _status("✅ 生成完成"),
            str(actual_seed),
            result,
            download_path,
        )
    except ComfyUIError as exc:
        yield _status(f"❌ {exc.user_message}"), "", None, None
    except Exception as exc:  # noqa: BLE001 - 兜底，避免前端崩溃
        traceback.print_exc()
        yield _status("❌ 生成失败，出现未知错误，请查看服务端日志。"), "", None, None


CUSTOM_CSS = """
.gradio-container { max-width: 1280px !important; margin: 0 auto !important; }
#title { text-align: center; margin: 8px 0 4px; }
#title h1 { margin-bottom: 0; }
#title p { color: #666; margin-top: 4px; }
.panel { border: 1px solid #e5e7eb; border-radius: 14px; padding: 16px; }
#generate-btn { background: linear-gradient(135deg, #6366f1, #a855f7) !important;
                color: #fff !important; border: none !important; }
"""


with gr.Blocks(title="可控智能电商背景生成系统") as demo:
    gr.Markdown(
        "# 可控智能电商背景生成系统\n"
        "上传商品图 → 输入背景描述 → 一键生成可下载的背景图",
        elem_id="title",
    )

    with gr.Row(equal_height=False):
        # ---------------- 左侧：输入 ----------------
        with gr.Column(scale=1, elem_classes="panel"):
            gr.Markdown("### 商品与描述")
            product_image = gr.Image(
                label="上传商品图",
                type="pil",
                sources=["upload"],
                height=260,
            )
            example_dropdown = gr.Dropdown(
                choices=_EXAMPLE_TITLES,
                label="示例提示词（选择后自动填充）",
                value=None,
            )
            prompt_text = gr.Textbox(
                label="背景描述 / Prompt",
                lines=7,
                placeholder="输入背景描述，或从上方选择示例提示词……",
            )
            random_seed = gr.Checkbox(value=True, label="随机 Seed")
            seed_input = gr.Textbox(
                label="固定 Seed（随机模式时忽略）",
                placeholder="随机模式：生成后显示本次 Seed",
                interactive=False,
            )
            generate_btn = gr.Button("生成背景", variant="primary", elem_id="generate-btn")

        # ---------------- 右侧：结果 ----------------
        with gr.Column(scale=1, elem_classes="panel"):
            gr.Markdown("### 生成结果")
            status_md = gr.Markdown("等待生成……")
            seed_display = gr.Textbox(label="本次 Seed", interactive=False)
            result_image = gr.Image(
                label="结果预览",
                type="pil",
                interactive=False,
                height=430,
            )
            download_btn = gr.DownloadButton(
                label="下载结果图",
                value=None,
                interactive=False,
            )
            regenerate_btn = gr.Button("重新生成", variant="secondary")

    example_dropdown.change(
        fn=fill_prompt,
        inputs=example_dropdown,
        outputs=prompt_text,
    )
    random_seed.change(
        fn=toggle_seed,
        inputs=random_seed,
        outputs=seed_input,
    )

    generate_inputs = [product_image, prompt_text, random_seed, seed_input]
    generate_outputs = [status_md, seed_display, result_image, download_btn]

    generate_btn.click(
        fn=on_generate,
        inputs=generate_inputs,
        outputs=generate_outputs,
    )
    regenerate_btn.click(
        fn=on_generate,
        inputs=generate_inputs,
        outputs=generate_outputs,
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1",
        server_port=7861,
        inbrowser=True,
        show_error=True,
        css=CUSTOM_CSS,
    )
