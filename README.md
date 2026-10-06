# 基于 ControlNet 的可控智能电商背景生成系统

本仓库在「已冻结的最终 ComfyUI 工作流」之上，封装了一个面向普通用户的 Web/UI，
实现「上传商品图 → 选择/输入背景描述 → 一键生成背景图」。

> 当前最终冻结工作流：`workflow/z-turbo (FINAL2) .json`
> 最终 Web/UI 入口：`ui/app_final.py`

---
## 效果展示
![最终Web UI展示图](https://img.remit.ee/i/3u54AWmHPyMb)

---

## 一、项目结构

```text
PythonSD/
├── backend/
│   └── comfyui_client.py        # 最终后端：UI 工作流转 API、上传图片、提交/轮询/取图
│
├── ui/
│   ├── app_final.py             # 最终 Web/UI（宽屏三栏深色界面）
│   └── requirements.txt         # 前端 Python 依赖
│
├── prompt/
│   ├── prompt_generator.py      # Prompt 生成器 + 五种场景风格中文示例提示词
│   ├── examples.py              # 解析 prompts3.txt 示例提示词
│   └── prompts3.txt             # 七组商品/场景示例提示词
│
├── workflow/
│   └── z-turbo (FINAL2) .json   # ★ 最终冻结工作流（Web 实际使用）
│
├── deprecated/                  # 已废弃 / 过时 / 实验性文件（按类别归档）
│   ├── backend/                 #   旧 A1111 后端 generate.py
│   ├── ui/                      #   旧 Scribble UI app.py + README
│   ├── prompt/                  #   旧 Prompt CLI + README
│   ├── scribble/                #   旧 Scribble 模板方案
│   ├── project-b/               #   旧 Scribble 模板（B 分支）
│   ├── workflow/                #   早期/实验工作流与 fragrance 专项
│   └── docs/                    #   旧启动说明与旧计划
│
├── input/                       # 测试商品图（已 gitignore）
├── pyOutput/                    # 旧输出图片（历史遗留，已 gitignore）
│
├── README.md                    # 本说明
├── PROJECT.md                   # 项目概况
├── WEB_INTEGRATION.md           # Web/UI 整合说明
└── .gitignore
```

核心数据流：

```text
前端 ui/app_final.py
  └─ 只传 { image, prompt, seed_mode, seed }
       └─ backend/comfyui_client.py
            ├─ 读取 workflow/z-turbo (FINAL2) .json 并转为 ComfyUI API 格式
            ├─ 上传商品图  ->  LoadImage(58).image
            ├─ 写入 Prompt ->  CLIPTextEncode(83).text
            ├─ 写入 Seed   ->  SeedNode(85).seed
            └─ ComfyUI /prompt -> /history -> /view 取回结果图
```

---

## 二、Web 启动方式（面向用户）

### 1. 先启动 ComfyUI

确保 ComfyUI 已启动，并且 API 服务可用，默认地址为：

```text
http://127.0.0.1:8188
```

如果 ComfyUI 不在默认地址，请在启动 Web 前设置环境变量：

```powershell
$env:COMFYUI_URL = "http://127.0.0.1:8188"
```

### 2. 安装 Python 依赖

```powershell
pip install -r ui/requirements.txt
```

依赖内容（见 `ui/requirements.txt`）：

- `gradio==6.0.0`
- `numpy>=1.24`
- `pillow>=10.0`
- `requests>=2.28`

### 3. 启动 Web 界面

```powershell
python ui/app_final.py
```

浏览器打开：

```text
http://127.0.0.1:7861
```

### 4. 使用流程

1. 左侧上传商品图。
2. 选择 Seed 模式（默认随机；也可选固定并输入整数）。
3. 右侧选择「示例提示词」或「示例风格」，或在「背景描述」中直接输入提示词。
4. 点击中栏底部的「生成背景」。
5. 等待生成完成后，查看结果图与「本次 Seed」。
6. 可点击「下载结果」保存图片，或点击「换一个结果」重新生成。

> 说明：普通用户只需接触“上传图片 / 提示词 / Seed / 生成 / 下载”，
> 不需要了解 ControlNet、Mask、Canny、KSampler 等技术概念。

### 5. 服务端配置项（用户无需修改）

以下内容全部封装在 `backend/comfyui_client.py`，普通用户不可修改：

- ComfyUI 地址（默认 `http://127.0.0.1:8188`，可用 `COMFYUI_URL` 覆盖）
- 工作流文件（默认 `workflow/z-turbo (FINAL2) .json`）
- 模型名称
- ControlNet / Canny / BiRefNet / KSampler 参数
- 节点 ID 映射

---

## 三、运行环境与依赖

### 1. ComfyUI 版本

本项目在以下环境实测跑通：

| 项目 | 版本 / 环境 |
| --- | --- |
| ComfyUI | `0.38.2 + 35 commits (ae913fd)` |
| ComfyUI 前端 | `1.53.10` |
| Workflow Templates | `0.11.76` |
| Python | `3.13.12` |
| PyTorch | `2.12.1+cu130` |
| 操作系统 | Windows11 x64 |
| 实测 GPU | NVIDIA GeForce RTX 4070 Laptop GPU（8 GB） |
| 运行方式 | ComfyUI Desktop（本地版） |

> 最低要求建议：使用包含下列内置节点与工作流模板的 ComfyUI 版本（0.38.2 已验证）。
> 其他 NVIDIA GPU 也可运行，需保证显存足够加载 Z-Image-Turbo + Qwen3 文本编码器 + ControlNet。

### 2. 自定义节点

本工作流使用的核心节点都是 **ComfyUI 内置核心节点**，**无需额外安装第三方自定义节点**。

仅实验时，ComfyUI原始工作流引入了Deno Custom Nodes （版本0.7.109）进行图像对比，该节点在Web端实际应用过程中不使用。

关键内置节点及其来源模块：

| 节点类型 | 用途 | 来源模块 |
| --- | --- | --- |
| `ZImageFunControlnet` | 应用 Fun ControlNet | `comfy_extras.nodes_model_patch` |
| `ModelPatchLoader` | 加载 ControlNet Model Patch | `comfy_extras.nodes_model_patch` |
| `ModelSamplingAuraFlow` | 采样 shift 配置 | `comfy_extras.nodes_model_advanced` |
| `SeedNode` | 输出 Seed | `comfy_extras.nodes_seed` |
| `LoadBackgroundRemovalModel` | 加载 BiRefNet 背景移除模型 | `comfy_extras.nodes_bg_removal` |
| `RemoveBackground` | BiRefNet 主体分割 | `comfy_extras.nodes_bg_removal` |
| `JoinImageWithAlpha` | Alpha 合成（子图内部） | `comfy_extras.nodes_compositing` |
| `ImageScaleToMaxDimension` / `GetImageSize` | 图像缩放 / 尺寸读取 | `comfy_extras.nodes_images` |
| `EmptySD3LatentImage` | 生成 latent | `comfy_extras.nodes_sd3` |
| `LoadImage` / `CLIPLoader` / `UNETLoader` / `VAELoader` / `CLIPTextEncode` / `Canny` / `MaskToImage` / `InvertMask` / `KSampler` / `ConditioningZeroOut` / `VAEDecode` / `SaveImage` | 基础管线 | ComfyUI 核心 `nodes` |

BiRefNet 部分在最终工作流中被保存为一个内置子图（Subgraph）：
`Remove Background (BiRefNet)`，由 `LoadBackgroundRemovalModel → RemoveBackground` 组成，
后端已在 `backend/comfyui_client.py` 中自动展开该子图。

### 3. 模型

需要以下模型文件，并放置到 ComfyUI 对应的 `models` 目录：

| 模型 | 文件 | 放置目录 | 对应节点 |
| --- | --- | --- | --- |
| 文本编码器 | `qwen_3_4b_fp4_mixed.safetensors` | `models/clip/` | `CLIPLoader`（type=`lumina2`） |
| 扩散模型 | `z_image_turbo_bf16.safetensors` | `models/diffusion_models/` | `UNETLoader`（weight_dtype=`default`） |
| VAE | `ae.safetensors` | `models/vae/` | `VAELoader` |
| ControlNet Patch | `Z-Image-Turbo-Fun-Controlnet-Union-2.1-2601-8steps.safetensors` | `models/model_patches/z-image-turbo-fun-controlnet-union/` | `ModelPatchLoader` |
| BiRefNet | `birefnet.safetensors` | `models/background_removal/` | `LoadBackgroundRemovalModel` |

---

## 四、Workflow 冻结参数

最终工作流 `workflow/z-turbo (FINAL2) .json` 的完整管线：

```text
上传商品图
  → LoadImage
  → ImageScaleToMaxDimension
  → BiRefNet 主体分割（子图）
  → Mask Invert
  → MaskToImage
  → Canny（得到商品轮廓）
原商品 Resize 后作为 inpaint_image
  → Z-Image-Turbo + Z-Image-Turbo-Fun-Controlnet-Union
  → ModelSamplingAuraFlow
  → KSampler
  → VAEDecode
  → SaveImage
```

### 动态修改（仅 3 个，由后端根据用户输入写入）

| 节点 ID | 节点类型 | 动态输入 |
| --- | --- | --- |
| `58` | `LoadImage` | `image`（上传的商品图文件名） |
| `83` | `CLIPTextEncode` | `text`（用户/示例 Prompt） |
| `85` | `SeedNode` | `seed`（真实参与 KSampler 的种子，链路 `85 → 79`） |

### 冻结参数（不得修改、不向用户暴露）

| 节点 | 冻结值 |
| --- | --- |
| `ImageScaleToMaxDimension` | `upscale_method = lanczos`，`largest_size = 1024` |
| BiRefNet | 模型 `birefnet.safetensors`；Mask 必须经 `InvertMask`；不使用 Mask Expand；Mask Feather = 0 |
| `Canny` | `low_threshold = 0.1`，`high_threshold = 0.32` |
| `ZImageFunControlnet` | `strength = 1`，`start_percent = 0`，`end_percent = 1` |
| `ModelSamplingAuraFlow` | `shift = 3`，`sampling = flow` |
| `EmptySD3LatentImage` | `batch_size = 1`（宽高由 `GetImageSize` 自动读取） |
| `KSampler` | `steps = 8`，`cfg = 1`，`sampler_name = res_multistep`，`scheduler = simple`，`denoise = 1` |

### 算法约束（已冻结，禁止回退）

- 使用 `Z-Image-Turbo`，不更换模型。
- ControlNet 使用 `Z-Image-Turbo-Fun-Controlnet-Union-2.1-2601-8steps`。
- 文本编码器使用 `Qwen3-4B FP4`。
- 使用 `BiRefNet` 提取商品 Mask。
- 不使用 Upscale、不使用 Hard Composite。
- 不重新引入旧版 ControlNet，不改成 Qwen Image Edit 或 SD1.5。

2026.10.06