# 最终 Web/UI 整合说明

本目录完成了「基于 ControlNet 的可控智能电商背景生成系统」的最终 Web/UI 整合，
在**不改动冻结工作流算法**的前提下，把 `workflow/z-turbo (FINAL2) .json`
封装成普通用户可直接使用的界面。

## 快速启动

1. 先启动 ComfyUI，确保其 API 服务可用（默认 `http://127.0.0.1:8188`）。

   如果 ComfyUI 不在默认地址，通过环境变量指定：

   ```powershell
   $env:COMFYUI_URL = "http://127.0.0.1:8188"
   ```

2. 安装依赖（若尚未安装）：

   ```powershell
   pip install -r ui/requirements.txt
   ```

3. 启动最终界面：

   ```powershell
   python ui/app_final.py
   ```

   浏览器打开 `http://127.0.0.1:7861`。

## 界面功能

- 上传商品图片
- 输入背景描述 / Prompt
- 从 `prompt/prompts3.txt` 选择示例提示词（自动填充 Prompt）
- 随机 Seed（默认）或固定 Seed
- 点击「生成背景」；生成时按钮进入 loading，显示「正在生成，请稍候……」
- 展示结果图、本次实际 Seed、下载按钮
- 「重新生成」按钮

## 后端封装的边界

前端只传入 `image / prompt / seed_mode / seed`。以下内容全部保留在服务端
（`backend/comfyui_client.py`），普通用户无法修改：

- ComfyUI 地址
- workflow JSON
- 模型名称
- ControlNet / Canny / BiRefNet / KSampler 参数
- 节点 ID 映射

## 需要动态修改的节点

| 节点 ID | 类型 | 动态输入 | 说明 |
| --- | --- | --- | --- |
| `58` | LoadImage | `image` | 上传的商品图文件名 |
| `83` | CLIPTextEncode | `text` | 用户 / 示例 Prompt |
| `85` | SeedNode | `seed` | 真实参与 KSampler 的种子（链路 `85 -> 79`） |

其余节点（Resize、BiRefNet 子图、InvertMask、MaskToImage、Canny、
ZImageFunControlnet、KSampler、各模型加载节点等）全部保持 workflow 原值，不暴露、不修改。

## 关键实现点

- `backend/comfyui_client.py` 会把 UI 保存格式的 workflow 转成 ComfyUI `/prompt`
  所需的 API 格式，并自动展开 workflow 中的 **BiRefNet 子图**、丢弃前端预览节点。
- 使用标准 ComfyUI API：`/system_stats`、`/upload/image`、`/prompt`、`/history`、`/view`。
- 生成时轮询 `/history/{prompt_id}` 获取状态与结果。

## 关于示例提示词

`prompt/prompts3.txt` 当前共包含 **7 组**示例（6 个单品场景 + 1 个“三瓶香水”多商品难例）。
`prompt/examples.py` 会自动解析这些条目，UI 的“示例提示词”下拉框会全部展示。

## 测试情况

已在本机（ComfyUI `127.0.0.1:8188`）实际跑通一次完整流程：

- 使用 `input/camera1.png` + 示例提示词「相机：摄影棚」
- 随机 Seed：`261799506251675`
- 成功返回 1024×1008 的结果图
