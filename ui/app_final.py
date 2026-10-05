#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终 Web/UI：三栏深色布局，参考原 ui/app.py 设计。"""

from __future__ import annotations

import os
import sys
import time
import traceback
from typing import Any

import gradio as gr
from PIL import Image


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.comfyui_client import ComfyUIClient, ComfyUIError
from prompt.examples import load_example_prompts
from prompt.prompt_generator import get_style_display_names, get_style_prompt


OUTPUT_DIR = os.path.join(PROJECT_ROOT, "ui", "pyOutput")
os.makedirs(OUTPUT_DIR, exist_ok=True)

_EXAMPLES = load_example_prompts()
_EXAMPLE_TITLES = [ex["title"] for ex in _EXAMPLES]
_EXAMPLE_BY_TITLE = {ex["title"]: ex["prompt"] for ex in _EXAMPLES}
_STYLE_NAMES = get_style_display_names()

client = ComfyUIClient()


def _coerce_pil(image: Any) -> Image.Image | None:
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


def fill_prompt(title: str | None) -> str:
    if not title:
        return ""
    return _EXAMPLE_BY_TITLE.get(title, "")


def fill_style_prompt(style_name: str | None) -> str:
    if not style_name:
        return ""
    return get_style_prompt(style_name)


def toggle_seed(seed_mode: str | None) -> Any:
    if seed_mode == "固定 Seed":
        return gr.update(interactive=True, placeholder="请输入一个整数，例如：1234567890")
    return gr.update(interactive=False, placeholder="随机模式：生成后自动显示本次 Seed")


def _resolve_seed(seed_mode: str | None, seed_input: str) -> tuple[str, int | None]:
    if seed_mode == "固定 Seed":
        text = (seed_input or "").strip()
        if not text:
            raise ComfyUIError("请输入固定 Seed，或选择「随机 Seed」。")
        try:
            value = int(text)
        except ValueError:
            raise ComfyUIError("固定 Seed 必须是整数。")
        return "fixed", value
    return "random", None


def _save_result(image: Image.Image, seed: int) -> str:
    filename = f"result_{seed}_{int(time.time())}.png"
    path = os.path.join(OUTPUT_DIR, filename)
    image.save(path, format="PNG")
    return path


def on_generate(product_image: Any, prompt_text: str, seed_mode: str | None, seed_input: str):
    image = _coerce_pil(product_image)
    if image is None:
        yield "⚠️ 请先上传商品图片。", "", None, None
        return

    prompt = (prompt_text or "").strip()
    if not prompt:
        yield "⚠️ 请在「背景描述」中输入提示词，或选择示例提示词 / 示例风格。", "", None, None
        return

    try:
        mode, fixed_seed = _resolve_seed(seed_mode, seed_input)
    except ComfyUIError as exc:
        yield f"⚠️ {exc.user_message}", "", None, None
        return

    try:
        yield "🔌 正在连接 ComfyUI……", "", None, None
        client.check_server()

        yield "📤 正在上传商品图片……", "", None, None
        filename = client.upload_image(image)

        actual_seed = client.random_seed() if mode == "random" else fixed_seed
        api_prompt = client.build_prompt(filename, prompt, actual_seed)

        yield "⏳ 正在生成，请稍候……", "", None, None
        prompt_id = client.queue_prompt(api_prompt)
        history = client.wait_for_result(prompt_id)
        result = client.extract_image(history)

        download_path = _save_result(result, actual_seed)
        yield "✅ 生成完成", str(actual_seed), result, download_path
    except ComfyUIError as exc:
        yield f"❌ {exc.user_message}", "", None, None
    except Exception:  # noqa: BLE001 - 兜底，避免前端崩溃
        traceback.print_exc()
        yield "❌ 生成失败，出现未知错误，请查看服务端日志。", "", None, None


CUSTOM_CSS = """
/* 浅色变量（默认会被 JS 添加的 .dark 覆盖） */
:root {
    --bg-body: #0b1121;
    --bg-wrapper: #111827;
    --border-wrapper: #1e3a8a;
    --border-col: #1f2937;
    --text-title: #f3f4f6;
    --text-sub: #9ca3af;
    --text-body: #d1d5db;
    --text-muted: #6b7280;
    --radio-bg: #1f2937;
    --radio-border: #374151;
    --radio-active-bg: rgba(37, 99, 235, 0.16);
    --radio-active-border: #3b82f6;
    --radio-label: #93c5fd;
}

body {
    margin: 0 !important;
    background: var(--bg-body) !important;
    color: var(--text-title) !important;
}
.gradio-container {
    max-width: 1680px !important;
    padding: 0 20px !important;
    margin: 0 auto !important;
    background: transparent !important;
}
footer { display: none !important; }

#title-bar { text-align: center; padding: 14px 0 6px; }
#title-bar h1 {
    font-size: 1.8rem; margin-bottom: 0;
    background: linear-gradient(90deg, #60a5fa, #a78bfa, #c084fc);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
#title-bar p { color: var(--text-sub); margin-top: 4px; font-size: 0.9rem; }

#outer-wrapper {
    border: 1px solid var(--border-wrapper);
    border-radius: 16px;
    background: var(--bg-wrapper) !important;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.45);
    padding: 0 !important;
    margin-bottom: 30px;
}

#main-row { display: flex !important; flex-wrap: nowrap !important; gap: 0 !important; align-items: stretch !important; }
#col-left   { flex: 0 0 24% !important; max-width: 24% !important; min-width: 0 !important; }
#col-center { flex: 0 0 48% !important; max-width: 48% !important; min-width: 0 !important; }
#col-right  { flex: 0 0 28% !important; max-width: 28% !important; min-width: 0 !important; }

.col-inner {
    padding: 18px !important;
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
}
#col-left .col-inner   { border-right: 1px solid var(--border-col) !important; }
#col-center .col-inner { border-right: 1px solid var(--border-col) !important; }
.col-inner h3 {
    font-size: 1rem !important; color: var(--text-title) !important;
    margin: 0 0 12px !important; padding-bottom: 10px !important;
    border-bottom: 2px solid var(--border-col) !important;
}

/* Radio 选择器（Seed / 风格） */
#seed-radio label, #style-radio label {
    background: var(--radio-bg) !important;
    border: 1px solid var(--radio-border) !important;
    border-radius: 10px !important;
    padding: 9px 11px !important;
    margin: 0 !important;
    cursor: pointer !important;
    transition: background 0.2s ease, border-color 0.2s ease !important;
}
#seed-radio label:hover, #style-radio label:hover { border-color: var(--radio-active-border) !important; }
#seed-radio label.selected, #style-radio label.selected,
#seed-radio label:has(input:checked), #style-radio label:has(input:checked) {
    background: var(--radio-active-bg) !important;
    border-color: var(--radio-active-border) !important;
}
#seed-radio input[type="radio"], #style-radio input[type="radio"] { display: none !important; }
#seed-radio label span, #style-radio label span {
    font-size: 0.82rem !important; font-weight: 600 !important; color: var(--radio-label) !important;
}
#seed-radio .wrap, #style-radio .wrap { display: flex !important; flex-direction: column !important; gap: 7px !important; }

/* 生成 / 下载按钮 */
#action-row { display: flex !important; gap: 12px !important; margin-top: 14px !important; }
#generate-btn, #download-btn {
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
    transition: all 0.2s ease !important;
}
#generate-btn { background: #2563eb !important; font-size: 1.15rem !important; padding: 13px 24px !important; flex: 1 !important; }
#download-btn { background: #2563eb !important; flex: 0 0 auto !important; }
#generate-btn:hover, #download-btn:hover { filter: brightness(1.1); }

/* 结果图 */
#result-img .image-container { border-radius: 10px !important; }

/* 深色组件覆盖 */
.dark {
    --body-background-fill: var(--bg-body) !important;
    --background-fill-primary: var(--bg-wrapper) !important;
    --background-fill-secondary: #1f2937 !important;
    --border-color-primary: #374151 !important;
    --block-background-fill: #1f2937 !important;
    --block-border-color: #374151 !important;
    --input-background-fill: #1f2937 !important;
    --body-text-color: #f3f4f6 !important;
    --body-text-color-subdued: #d1d5db !important;
}
"""


with gr.Blocks(title="可控智能电商背景生成系统") as demo:
    gr.HTML(
        '<div id="title-bar"><h1>可控智能电商背景生成系统</h1>'
        "<p>上传商品图 · 选择示例提示词或风格 · 一键生成背景图</p></div>"
    )

    with gr.Group(elem_id="outer-wrapper"):
        with gr.Row(equal_height=True, elem_id="main-row"):
            # ---------------- 左栏：商品 & Seed ----------------
            with gr.Column(scale=1, min_width=0, elem_id="col-left"):
                with gr.Column(elem_classes="col-inner"):
                    gr.Markdown("### 商品 & Seed")
                    product_image = gr.Image(
                        label="上传商品图",
                        type="pil",
                        sources=["upload"],
                        height=250,
                    )
                    gr.Markdown("#### Seed 设置")
                    seed_mode = gr.Radio(
                        choices=["随机 Seed", "固定 Seed"],
                        value="随机 Seed",
                        label="Seed 模式",
                        elem_id="seed-radio",
                    )
                    seed_input = gr.Textbox(
                        label="固定 Seed",
                        placeholder="随机模式：生成后自动显示本次 Seed",
                        interactive=False,
                    )
                    seed_display = gr.Textbox(label="本次 Seed", interactive=False)

            # ---------------- 中栏：结果 ----------------
            with gr.Column(scale=2, min_width=0, elem_id="col-center"):
                with gr.Column(elem_classes="col-inner"):
                    gr.Markdown("### 生成结果")
                    status_md = gr.Markdown("等待生成……")
                    result_image = gr.Image(
                        label="结果预览",
                        type="pil",
                        interactive=False,
                        height=560,
                        elem_id="result-img",
                    )
                    with gr.Row(elem_id="action-row"):
                        generate_btn = gr.Button("生成", variant="primary", elem_id="generate-btn")
                        download_btn = gr.DownloadButton(
                            "下载结果图",
                            value=None,
                            interactive=False,
                            elem_id="download-btn",
                        )

            # ---------------- 右栏：提示词 ----------------
            with gr.Column(scale=1, min_width=0, elem_id="col-right"):
                with gr.Column(elem_classes="col-inner"):
                    gr.Markdown("### 提示词")
                    sample_prompt = gr.Dropdown(
                        choices=_EXAMPLE_TITLES,
                        label="示例提示词",
                        value=None,
                    )
                    style_radio = gr.Radio(
                        choices=_STYLE_NAMES,
                        label="示例风格",
                        value=None,
                        elem_id="style-radio",
                    )
                    prompt_text = gr.Textbox(
                        label="背景描述",
                        lines=12,
                        placeholder="场景 + 商品 + 光线 + 摄影方式",
                        elem_id="prompt-text",
                    )

    sample_prompt.change(
        fn=fill_prompt,
        inputs=sample_prompt,
        outputs=prompt_text,
    )
    style_radio.change(
        fn=fill_style_prompt,
        inputs=style_radio,
        outputs=prompt_text,
    )
    seed_mode.change(
        fn=toggle_seed,
        inputs=seed_mode,
        outputs=seed_input,
    )

    generate_btn.click(
        fn=on_generate,
        inputs=[product_image, prompt_text, seed_mode, seed_input],
        outputs=[status_md, seed_display, result_image, download_btn],
    )


if __name__ == "__main__":
    demo.load(
        fn=None,
        inputs=None,
        outputs=None,
        js="""function() {
            document.body.classList.add('dark');
            document.documentElement.classList.add('dark');
        }""",
    )
    demo.queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1",
        server_port=7861,
        inbrowser=True,
        show_error=True,
        css=CUSTOM_CSS,
    )
