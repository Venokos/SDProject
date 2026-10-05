#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ComfyUI 客户端封装。

负责把最终冻结的 ComfyUI workflow 稳定封装成后端生成服务：
1. 读取 UI 保存格式的 workflow JSON；
2. 展开 subgraph、丢弃前端预览节点，生成 /prompt 所需的 API 格式；
3. 上传商品图；
4. 仅动态修改 LoadImage(58)、CLIPTextEncode(83)、SeedNode(85) 三个节点；
5. 提交 /prompt，轮询 /history，取回最终图片。

模型、ControlNet、BiRefNet、Canny、KSampler 等参数全部保持 workflow 原值。
"""

from __future__ import annotations

import copy
import json
import os
import random
import tempfile
import time
import uuid
from io import BytesIO
from typing import Any, Dict, Optional, Tuple

import requests
from PIL import Image


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_WORKFLOW_PATH = os.path.join(PROJECT_ROOT, "workflow", "z-turbo (FINAL2) .json")
DEFAULT_SERVER_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")

NODE_LOAD_IMAGE = "58"
NODE_PROMPT = "83"
NODE_SEED = "85"
NODE_SAVE_IMAGE = "108"
INPUT_LOAD_IMAGE = "image"
INPUT_PROMPT = "text"
INPUT_SEED = "seed"

DROP_NODE_TYPES = {"PreviewImage", "MaskPreview", "DenoImageCompare"}
UI_ONLY_WIDGETS = {"control_after_generate", "upload", "fixed"}
DEFAULT_TIMEOUT = 900


class ComfyUIError(Exception):
    """面向用户的生成错误，附带面向开发的详细日志。"""

    def __init__(self, user_message: str, detail: str = ""):
        super().__init__(user_message)
        self.user_message = user_message
        self.detail = detail

    def __str__(self) -> str:
        if self.detail:
            return f"{self.user_message}（详情：{self.detail}）"
        return self.user_message


def _flatten_graph(workflow: Dict[str, Any]) -> Dict[str, Any]:
    subgraphs = {
        sg["id"]: sg
        for sg in workflow.get("definitions", {}).get("subgraphs", [])
    }
    raw_nodes = {n["id"]: n for n in workflow.get("nodes", [])}
    link_by_id = {l[0]: l for l in workflow.get("links", [])}

    norm: Dict[str, Any] = {}
    sub_out: Dict[Tuple[int, int], Tuple[Optional[str], int]] = {}

    def resolve_origin(origin_id: int, origin_slot: int) -> Tuple[Optional[str], int]:
        node = raw_nodes.get(origin_id)
        if node is None:
            return (str(origin_id), origin_slot)
        if node["type"] in subgraphs:
            key = (origin_id, origin_slot)
            if key in sub_out:
                return sub_out[key]
            return (None, origin_slot)
        if node["type"] in DROP_NODE_TYPES:
            inputs = node.get("inputs", [])
            if inputs and inputs[0].get("link") is not None:
                link = link_by_id[inputs[0]["link"]]
                return resolve_origin(link[1], link[2])
            return (str(origin_id), origin_slot)
        return (str(origin_id), origin_slot)

    for node in workflow.get("nodes", []):
        if node["type"] in subgraphs or node["type"] in DROP_NODE_TYPES:
            continue
        nid = str(node["id"])
        norm[nid] = {
            "type": node["type"],
            "inputs": [
                {"name": i["name"], "src": None, "link_id": i.get("link")}
                for i in node.get("inputs", [])
            ],
            "widgets_named": dict(node.get("widgets_values_named", {})),
        }

    def expand_subgraph(parent_node: Dict[str, Any], sg: Dict[str, Any]) -> None:
        parent_raw_id = parent_node["id"]
        prefix = str(parent_raw_id)
        sg_links = {l["id"]: l for l in sg.get("links", [])}
        inner_nodes = sg.get("nodes", [])
        inner_id_map: Dict[int, str] = {}

        for inner in inner_nodes:
            inner_nid = f"{prefix}:{inner['id']}"
            inner_id_map[inner["id"]] = inner_nid
            norm[inner_nid] = {
                "type": inner["type"],
                "inputs": [],
                "widgets_named": dict(inner.get("widgets_values_named", {})),
            }

        parent_inputs = parent_node.get("inputs", [])
        parent_widgets = parent_node.get("widgets_values_named", {})
        sg_inputs = sg.get("inputs", [])

        def parent_input_source(slot: int) -> Tuple[str, Any]:
            pi = parent_inputs[slot] if slot < len(parent_inputs) else None
            if pi and pi.get("link") is not None:
                link = link_by_id[pi["link"]]
                return ("link", resolve_origin(link[1], link[2]))
            name = sg_inputs[slot]["name"] if slot < len(sg_inputs) else None
            return ("value", parent_widgets.get(name))

        for inner in inner_nodes:
            inner_nid = inner_id_map[inner["id"]]
            in_list = []
            for inp in inner.get("inputs", []):
                name = inp.get("name")
                link_id = inp.get("link")
                if link_id is None:
                    in_list.append({"name": name, "src": None})
                    continue
                ilink = sg_links[link_id]
                oid = ilink["origin_id"]
                oslot = ilink["origin_slot"]
                if oid == -10:
                    kind, val = parent_input_source(oslot)
                    if kind == "link":
                        in_list.append({"name": name, "src": val})
                    else:
                        in_list.append({"name": name, "src": None})
                        norm[inner_nid]["widgets_named"][name] = val
                elif oid in inner_id_map:
                    in_list.append({"name": name, "src": (inner_id_map[oid], oslot)})
                else:
                    in_list.append({"name": name, "src": None})
            norm[inner_nid]["inputs"] = in_list

        for idx, out_def in enumerate(sg.get("outputs", [])):
            for link_id in out_def.get("linkIds", []):
                ilink = sg_links[link_id]
                oid = ilink["origin_id"]
                oslot = ilink["origin_slot"]
                if oid in inner_id_map:
                    sub_out[(parent_raw_id, idx)] = (inner_id_map[oid], oslot)

    for node in workflow.get("nodes", []):
        if node["type"] in subgraphs:
            expand_subgraph(node, subgraphs[node["type"]])

    for node in norm.values():
        for inp in node["inputs"]:
            link_id = inp.pop("link_id", None)
            if link_id is not None:
                link = link_by_id[link_id]
                inp["src"] = resolve_origin(link[1], link[2])

    return norm


def _build_api_prompt(norm: Dict[str, Any]) -> Dict[str, Any]:
    prompt: Dict[str, Any] = {}
    for nid, node in norm.items():
        inputs: Dict[str, Any] = {}
        for inp in node.get("inputs", []):
            src = inp.get("src")
            if src is not None and src[0] is not None:
                inputs[inp["name"]] = [src[0], src[1]]
        for wname, wval in node.get("widgets_named", {}).items():
            if wname in UI_ONLY_WIDGETS:
                continue
            if wname in inputs:
                continue
            inputs[wname] = wval
        prompt[nid] = {"class_type": node["type"], "inputs": inputs}
    return prompt


def workflow_to_api(workflow_path: str) -> Dict[str, Any]:
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)
    return _build_api_prompt(_flatten_graph(workflow))


class ComfyUIClient:
    def __init__(
        self,
        server_url: Optional[str] = None,
        workflow_path: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.server_url = (server_url or DEFAULT_SERVER_URL).rstrip("/")
        self.workflow_path = workflow_path or DEFAULT_WORKFLOW_PATH
        self.timeout = timeout
        self._api_workflow = workflow_to_api(self.workflow_path)

    @staticmethod
    def random_seed() -> int:
        return random.randint(0, 2**53 - 1)

    @staticmethod
    def _log(msg: str) -> None:
        print(f"[ComfyUIClient] {msg}")

    def check_server(self) -> None:
        try:
            resp = requests.get(f"{self.server_url}/system_stats", timeout=10)
            resp.raise_for_status()
        except requests.exceptions.ConnectionError as exc:
            raise ComfyUIError("无法连接 ComfyUI，请确认 ComfyUI 已启动。", str(exc)) from exc
        except requests.exceptions.Timeout as exc:
            raise ComfyUIError("连接 ComfyUI 超时，请稍后重试。", str(exc)) from exc
        except requests.exceptions.RequestException as exc:
            raise ComfyUIError("ComfyUI 连接异常。", str(exc)) from exc

    def upload_image(self, pil_image: Image.Image) -> str:
        if pil_image is None:
            raise ComfyUIError("没有可上传的商品图片。")
        if not isinstance(pil_image, Image.Image):
            raise ComfyUIError("商品图片格式错误，请上传 PNG/JPG 等常见图片。")
        if pil_image.mode not in ("RGB", "RGBA"):
            pil_image = pil_image.convert("RGB")

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            pil_image.save(tmp_path, format="PNG")
            with open(tmp_path, "rb") as f:
                files = {"image": ("product.png", f, "image/png")}
                resp = requests.post(
                    f"{self.server_url}/upload/image",
                    files=files,
                    timeout=60,
                )
            resp.raise_for_status()
            data = resp.json()
            name = data.get("name")
            if not name:
                raise ComfyUIError("商品图上传失败，ComfyUI 未返回文件名。", str(data))
            self._log(f"uploaded image -> {name}")
            return name
        except requests.exceptions.RequestException as exc:
            raise ComfyUIError("商品图上传失败，请检查 ComfyUI 是否正常运行。", str(exc)) from exc
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def build_prompt(
        self, image_filename: str, prompt_text: str, seed: int
    ) -> Dict[str, Any]:
        api = copy.deepcopy(self._api_workflow)
        if NODE_LOAD_IMAGE not in api:
            raise ComfyUIError("工作流缺少商品图节点，无法继续。")
        if NODE_PROMPT not in api:
            raise ComfyUIError("工作流缺少 Prompt 节点，无法继续。")
        if NODE_SEED not in api:
            raise ComfyUIError("工作流缺少 Seed 节点，无法继续。")
        api[NODE_LOAD_IMAGE]["inputs"][INPUT_LOAD_IMAGE] = image_filename
        api[NODE_PROMPT]["inputs"][INPUT_PROMPT] = prompt_text
        api[NODE_SEED]["inputs"][INPUT_SEED] = int(seed)
        return api

    def queue_prompt(self, api_prompt: Dict[str, Any]) -> str:
        client_id = str(uuid.uuid4())
        try:
            resp = requests.post(
                f"{self.server_url}/prompt",
                json={"prompt": api_prompt, "client_id": client_id},
                timeout=30,
            )
        except requests.exceptions.RequestException as exc:
            raise ComfyUIError("提交工作流失败，请检查 ComfyUI 是否正常运行。", str(exc)) from exc

        if resp.status_code == 400:
            body = resp.text
            self._log(f"prompt validation failed: {body[:2000]}")
            raise ComfyUIError(
                "生成失败：工作流输入异常，请检查 ComfyUI 是否正常运行。",
                body,
            )
        resp.raise_for_status()

        data = resp.json()
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise ComfyUIError("提交工作流失败，未返回任务 ID。", str(data))
        self._log(f"queued prompt_id={prompt_id}")
        return prompt_id

    def wait_for_result(
        self, prompt_id: str, timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        timeout = timeout or self.timeout
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = requests.get(
                    f"{self.server_url}/history/{prompt_id}", timeout=10
                )
                resp.raise_for_status()
                data = resp.json()
            except requests.exceptions.RequestException as exc:
                raise ComfyUIError("查询生成状态失败。", str(exc)) from exc

            entry = data.get(prompt_id)
            if entry is not None:
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    messages = status.get("messages", [])
                    joined = "\n".join(
                        str(m) if isinstance(m, str) else json.dumps(m, ensure_ascii=False)
                        for m in messages
                    )
                    self._log(f"execution error: {joined[:3000]}")
                    raise ComfyUIError(self._friendly_exec_error(joined), joined)
                if status.get("completed"):
                    return entry
            time.sleep(2)

        raise ComfyUIError(
            "生成超时，请稍后重试。",
            f"prompt_id={prompt_id} 在 {timeout} 秒内未完成。",
        )

    @staticmethod
    def _friendly_exec_error(detail: str) -> str:
        lowered = detail.lower()
        if "model" in lowered or "checkpoint" in lowered or "safetensors" in lowered:
            if "not found" in lowered or "missing" in lowered or "no such" in lowered:
                return "生成失败：所需模型缺失，请检查 ComfyUI 模型文件。"
        return "生成失败：ComfyUI 执行出错，请查看服务端日志。"

    def extract_image(self, history_entry: Dict[str, Any]) -> Image.Image:
        outputs = history_entry.get("outputs", {})
        node_out = outputs.get(NODE_SAVE_IMAGE)
        images = node_out.get("images", []) if node_out else []
        if not images:
            raise ComfyUIError(
                "生成完成，但未找到结果图片。",
                json.dumps(outputs, ensure_ascii=False),
            )

        first = images[0]
        filename = first.get("filename")
        subfolder = first.get("subfolder", "")
        image_type = first.get("type", "output")
        if not filename:
            raise ComfyUIError("结果图片缺少文件名。", str(first))

        params = {"filename": filename, "subfolder": subfolder, "type": image_type}
        try:
            resp = requests.get(f"{self.server_url}/view", params=params, timeout=60)
            resp.raise_for_status()
            return Image.open(BytesIO(resp.content)).convert("RGB")
        except requests.exceptions.RequestException as exc:
            raise ComfyUIError("下载结果图片失败。", str(exc)) from exc

    def generate(
        self,
        product_image: Image.Image,
        prompt_text: str,
        seed_mode: str = "random",
        seed: Optional[int] = None,
    ) -> Tuple[Image.Image, int]:
        self.check_server()
        actual_seed = self._resolve_seed(seed_mode, seed)
        filename = self.upload_image(product_image)
        api_prompt = self.build_prompt(filename, prompt_text, actual_seed)
        prompt_id = self.queue_prompt(api_prompt)
        history = self.wait_for_result(prompt_id)
        image = self.extract_image(history)
        return image, actual_seed

    @staticmethod
    def _resolve_seed(seed_mode: str, seed: Optional[int]) -> int:
        if seed_mode == "random":
            return ComfyUIClient.random_seed()
        try:
            value = int(seed)
        except (TypeError, ValueError):
            raise ComfyUIError("固定 Seed 必须是整数。")
        if value < 0:
            raise ComfyUIError("固定 Seed 不能为负数。")
        return value


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_WORKFLOW_PATH
    print(json.dumps(workflow_to_api(path), ensure_ascii=False, indent=2))
