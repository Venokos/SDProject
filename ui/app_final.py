#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终 Web/UI：宽屏桌面布局，深色产品化视觉。"""

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


def on_sample_prompt(title: str | None):
    if not title:
        return "", gr.update(value=None)
    return _EXAMPLE_BY_TITLE.get(title, ""), gr.update(value=None)


def on_style_prompt(style_name: str | None):
    if not style_name:
        return "", gr.update(value=None)
    return get_style_prompt(style_name), gr.update(value=None)


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

        yield "⏳ 等待生成……", "", None, None
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
:root {
    --bg-body: #0b1121;
    --bg-card: #111827;
    --bg-control: #1f2937;
    --border-card: #1e3a8a;
    --border-control: #374151;
    --border-hover: #4b5563;
    --border-soft: #1f2937;
    --text: #f3f4f6;
    --muted: #9ca3af;
    --accent: #3b82f6;
    --accent-strong: #2563eb;
}

html, body {
    margin: 0 !important;
    background: var(--bg-body) !important;
    color: var(--text) !important;
}

.gradio-container {
    max-width: min(92vw, 1440px) !important;
    width: min(92vw, 1440px) !important;
    margin: 0 auto !important;
    padding: 24px 32px !important;
    background: transparent !important;
}
footer { display: none !important; }

#title-bar { text-align: center; margin-bottom: 18px; }
#title-bar h1 {
    font-size: 1.65rem !important;
    margin: 0 !important;
    background: linear-gradient(90deg, #60a5fa, #a78bfa, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
#title-bar p { color: var(--muted); margin: 6px 0 0 !important; font-size: 0.9rem !important; }

/* 三栏网格 */
#main-row {
    display: grid !important;
    grid-template-columns: minmax(250px, 290px) minmax(520px, 1fr) minmax(330px, 390px);
    gap: 16px !important;
    align-items: stretch !important;
}

#col-left, #col-center, #col-right {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-card) !important;
    border-radius: 12px !important;
    padding: 18px !important;
    min-width: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 10px !important;
    box-shadow: 0 4px 22px rgba(0, 0, 0, 0.22);
}
#col-center { border-color: rgba(59, 130, 246, 0.38) !important; }

#col-left h3, #col-center h3, #col-right h3 {
    font-size: 1rem !important;
    color: var(--text) !important;
    margin: 0 0 8px !important;
    padding-bottom: 8px !important;
    border-bottom: 1px solid var(--border-soft) !important;
}

/* 标签收紧 */
#col-left label span, #col-right label span,
#col-left .label-wrap span, #col-right .label-wrap span {
    font-size: 0.82rem !important;
    color: var(--muted) !important;
}

/* Seed 分段控件 */
#seed-radio .wrap {
    display: flex !important;
    flex-direction: row !important;
    gap: 8px !important;
    padding: 0 !important;
}
#seed-radio label {
    flex: 1 !important;
    text-align: center !important;
    background: var(--bg-control) !important;
    border: 1px solid var(--border-control) !important;
    border-radius: 8px !important;
    padding: 11px 12px !important;
    cursor: pointer !important;
    transition: background 0.2s ease, border-color 0.2s ease !important;
}
#seed-radio label:hover { border-color: var(--border-hover) !important; }
#seed-radio label.selected,
#seed-radio label:has(input:checked) {
    background: rgba(59, 130, 246, 0.18) !important;
    border-color: var(--accent) !important;
}
#seed-radio input[type="radio"] { display: none !important; }
#seed-radio label span { color: var(--text) !important; font-weight: 600 !important; font-size: 0.9rem !important; }

/* 示例风格：2 列网格 */
#style-radio .wrap {
    display: grid !important;
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 8px !important;
    padding: 0 !important;
}
#style-radio label {
    background: var(--bg-control) !important;
    border: 1px solid var(--border-control) !important;
    border-radius: 8px !important;
    padding: 11px 12px !important;
    cursor: pointer !important;
    text-align: center !important;
    transition: background 0.2s ease, border-color 0.2s ease !important;
}
#style-radio label:hover { border-color: var(--border-hover) !important; }
#style-radio label.selected,
#style-radio label:has(input:checked) {
    background: rgba(59, 130, 246, 0.18) !important;
    border-color: var(--accent) !important;
}
#style-radio input[type="radio"] { display: none !important; }
#style-radio label span { font-size: 0.88rem !important; color: var(--text) !important; font-weight: 500 !important; }

/* 背景描述 textarea 固定高度 */
#prompt-text textarea {
    height: 210px !important;
    min-height: 210px !important;
    max-height: 340px !important;
    resize: vertical !important;
}

/* 放大输入控件 */
#sample-prompt input,
#seed-input textarea, #seed-input input,
#seed-display textarea, #seed-display input {
    font-size: 0.95rem !important;
}
#seed-input textarea, #seed-display textarea { min-height: 44px !important; }

/* 状态区 */
#status-md { min-height: 24px !important; margin: 8px 0 !important; }

/* 结果预览 */
#result-img .image-container { min-height: 460px !important; border-radius: 10px !important; }
#result-img img {
    object-fit: contain !important;
    width: 100% !important;
    height: auto !important;
}

/* 主 CTA */
#generate-btn {
    width: 100% !important;
    height: 50px !important;
    background: linear-gradient(135deg, #2563eb, #3b82f6) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    margin-top: 14px !important;
    box-shadow: 0 4px 16px rgba(37, 99, 235, 0.35) !important;
}
#generate-btn:hover { filter: brightness(1.08); }

/* 次级按钮 */
#result-actions { display: flex !important; gap: 10px !important; margin-top: 10px !important; }
#result-actions > * { flex: 1 !important; }
#download-btn, #regenerate-btn {
    flex: 1 !important;
    background: var(--bg-control) !important;
    color: var(--text) !important;
    border: 1px solid var(--border-control) !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    padding: 9px 0 !important;
}
#clear-btn {
    width: 100% !important;
    background: var(--bg-control) !important;
    color: var(--text) !important;
    border: 1px solid var(--border-control) !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    margin-top: 8px !important;
}

/* 深色组件覆盖 */
.dark {
    --body-background-fill: var(--bg-body) !important;
    --background-fill-primary: var(--bg-card) !important;
    --background-fill-secondary: #1f2937 !important;
    --border-color-primary: #374151 !important;
    --block-background-fill: #1f2937 !important;
    --block-border-color: #374151 !important;
    --input-background-fill: #1f2937 !important;
    --body-text-color: var(--text) !important;
    --body-text-color-subdued: var(--muted) !important;
}

/* 响应式 */
@media (min-width: 1100px) and (max-width: 1439px) {
    #main-row {
        grid-template-columns: minmax(210px, 250px) minmax(400px, 1fr) minmax(270px, 320px);
    }
}

@media (max-width: 1099px) {
    #main-row {
        grid-template-columns: minmax(240px, 1fr) minmax(320px, 1.3fr);
    }
    #col-left { grid-column: 1; grid-row: 1; }
    #col-center { grid-column: 2; grid-row: 1; }
    #col-right { grid-column: 1 / -1; grid-row: 2; }
}
"""


with gr.Blocks(title="可控智能电商背景生成系统") as demo:
    gr.HTML(
        '<div id="title-bar"><h1>可控智能电商背景生成系统</h1>'
        "<p>上传商品图 · 设置背景 · 一键生成</p></div>"
    )

    with gr.Row(elem_id="main-row"):
        # ---------------- 左栏：商品 & Seed ----------------
        with gr.Column(scale=1, elem_id="col-left"):
            gr.Markdown("### 商品 & Seed")
            product_image = gr.Image(
                label="上传商品图",
                type="pil",
                sources=["upload"],
                height=300,
            )
            seed_mode = gr.Radio(
                choices=["随机 Seed", "固定 Seed"],
                value="随机 Seed",
                label="Seed 模式",
                elem_id="seed-radio",
            )
            seed_input = gr.Textbox(
                label="固定 Seed",
                placeholder="请输入一个整数",
                interactive=False,
                elem_id="seed-input",
            )
            seed_display = gr.Textbox(
                label="本次 Seed",
                interactive=False,
                elem_id="seed-display",
            )

        # ---------------- 中栏：生成结果 ----------------
        with gr.Column(scale=2, elem_id="col-center"):
            gr.Markdown("### 生成结果")
            status_md = gr.Markdown("", elem_id="status-md")
            result_image = gr.Image(
                label="结果预览",
                type="pil",
                interactive=False,
                height=520,
                elem_id="result-img",
            )
            generate_btn = gr.Button("生成背景", variant="primary", elem_id="generate-btn")
            with gr.Row(elem_id="result-actions"):
                download_btn = gr.DownloadButton(
                    "下载结果",
                    value=None,
                    interactive=False,
                    elem_id="download-btn",
                )
                regenerate_btn = gr.Button(
                    "换一个结果",
                    variant="secondary",
                    elem_id="regenerate-btn",
                )

        # ---------------- 右栏：提示词 ----------------
        with gr.Column(scale=1, elem_id="col-right"):
            gr.Markdown("### 提示词")
            sample_prompt = gr.Dropdown(
                choices=_EXAMPLE_TITLES,
                label="示例提示词",
                value=None,
                elem_id="sample-prompt",
            )
            style_radio = gr.Radio(
                choices=_STYLE_NAMES,
                label="示例风格",
                value=None,
                elem_id="style-radio",
            )
            prompt_text = gr.Textbox(
                label="背景描述",
                lines=8,
                placeholder="场景 + 商品 + 光线 + 摄影方式",
                elem_id="prompt-text",
            )
            clear_btn = gr.Button(
                "清空",
                variant="secondary",
                elem_id="clear-btn",
            )

    sample_prompt.change(
        fn=on_sample_prompt,
        inputs=sample_prompt,
        outputs=[prompt_text, style_radio],
    )
    style_radio.change(
        fn=on_style_prompt,
        inputs=style_radio,
        outputs=[prompt_text, sample_prompt],
    )
    clear_btn.click(
        fn=lambda: "",
        inputs=None,
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
    regenerate_btn.click(
        fn=on_generate,
        inputs=[product_image, prompt_text, seed_mode, seed_input],
        outputs=[status_md, seed_display, result_image, download_btn],
    )

    demo.load(
        fn=None,
        inputs=None,
        outputs=None,
        js="""function() {
            document.body.classList.add('dark');
            document.documentElement.classList.add('dark');
        }""",
    )


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1",
        server_port=7861,
        inbrowser=True,
        show_error=True,
        css=CUSTOM_CSS,
    )
