# Scribble ControlNet - 商品场景生成器

基于 Gradio Blocks 构建的商品场景图生成工具前端原型。用户上传商品图、选择场景风格、手绘 Scribble 草稿后，通过 ControlNet 管线生成高质量的商品场景合成图。

---

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [系统要求](#系统要求)
- [安装部署](#安装部署)
- [快速启动](#快速启动)
- [项目结构](#项目结构)
- [界面说明](#界面说明)
- [接口文档](#接口文档)
- [管线流程](#管线流程)
- [开发指南](#开发指南)
- [已知约束](#已知约束)
- [常见问题](#常见问题)
- [变更日志](#变更日志)

---

## 项目简介

本项目为商品场景图自动生成系统的前端原型，采用模块化架构设计。当前版本 (v1.2.1) 为桩函数 (Stub) 模式，各接口返回占位假数据，供团队各模块独立开发与联调使用。

后续各负责人只需替换对应接口函数的内部实现，即可无缝接入真实模型，函数签名无需变更。

### 架构概览

```
模块一  团队协作接口    generate_prompt / process_scribble / generate_image
模块二  主管线          main_process -> 串联三个接口
模块三  界面与样式      CUSTOM_CSS + Gradio Blocks 布局
模块四  应用启动        demo.launch()
```

---

## 功能特性

- 三列式固定布局 (28% / 44% / 28%)，不换行、自动等高
- 支持五种场景风格切换：studio / beach / nature / luxury / minimal
- 场景风格采用 Radio 卡片按钮选择，选中状态有视觉反馈
- 可调节 ControlNet 控制强度 (0.0 - 1.5)
- 内置 Sketchpad 手绘画板，支持 8 种画笔颜色
- 浅色 / 深色主题切换 (右上角按钮)
- 生成结果以 PNG 格式下载
- 分享按钮已通过 JS 精准移除，保留下载按钮
- 模块化接口设计，各函数可独立替换与测试
- 完整的终端调试日志输出
- 默认启用深色主题
- 多显示器 DPI 缩放自动修复 (页面加载后无感抖动画板容器触发 ResizeObserver)

---

## 系统要求

| 依赖项   | 版本要求       | 说明                  |
|----------|----------------|-----------------------|
| Python   | >= 3.9         | 推荐 3.10+            |
| Gradio   | == 6.0.x       | Web UI 框架           |
| NumPy    | >= 1.24        | 数值计算              |
| Pillow   | >= 10.0        | 图像处理              |

操作系统支持: Windows 10/11, macOS 12+, Ubuntu 20.04+

---

## 安装部署

### 1. 克隆项目



### 2. 创建虚拟环境 (推荐)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install gradio==6.0.0 numpy pillow
```

国内网络环境建议使用清华镜像源:

```bash
pip install gradio==6.0.0 numpy pillow -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. 验证安装

```bash
python -c "import gradio; print(gradio.__version__)"
```

输出版本号 (如 `6.0.0`) 即表示安装成功。

---

## 快速启动

```bash
python app.py
```

启动成功后终端将输出:

```
* Running on local URL:  http://127.0.0.1:7860
```

浏览器将自动打开界面。若未自动打开，请手动访问 `http://127.0.0.1:7860`。

### 启动参数

| 参数          | 当前值        | 说明                                     |
|---------------|---------------|------------------------------------------|
| server_name   | 127.0.0.1     | 仅本地访问; 改为 0.0.0.0 允许局域网访问  |
| server_port   | 7860          | 监听端口                                 |
| inbrowser     | True          | 启动后自动打开浏览器                     |
| css           | CUSTOM_CSS    | 注入自定义样式 (Gradio 6.0 须在 launch 中传入) |

---

## 项目结构

```
scribble-controlnet-studio/
|
|-- app.py                  # 主程序入口 (界面 + 接口 + 管线 + 样式)
|-- README.md               # 项目说明文档
|-- requirements.txt        # 依赖清单
```

requirements.txt 内容:

```
gradio==6.0.0
numpy>=1.24
pillow>=10.0
```

### 推荐的模块化拆分结构 (后续重构)

```
scribble-controlnet-studio/
|
|-- app.py                  # 主程序入口 (仅界面布局与事件绑定)
|-- README.md
|-- requirements.txt
|
|-- modules/                # 业务逻辑模块
|   |-- __init__.py
|   |-- prompt_engine.py    # 负责人 A: generate_prompt 逻辑
|   |-- image_processor.py  # 负责人 B: process_scribble 逻辑
|   |-- model_inference.py  # 负责人 C: generate_image (模型推理)
|
|-- assets/                 # 静态资源
    |-- screenshot.png       # 界面截图
```

---

## 界面说明

界面采用三列式固定布局，列宽比为 28:44:28，包裹在统一的白色圆角面板中:

```
+----------------+------------------------+------------------+
|    左侧列 28%  |     中间列 44%          |   右侧列 28%     |
|                |                        |                  |
| [商品图上传]    |  [Sketchpad 手绘画板]   | [生成结果预览]    |
|  240px 高度    |   500px 高度            |  440px 高度      |
|                |   8种画笔颜色           |                  |
| [场景风格]     |   支持鼠标/触控笔        |                  |
|  Radio 卡片    |                        | [生成按钮]        |
|                |                        |                  |
| [ControlNet]   |  [操作提示条]           | [状态提示条]      |
|  强度滑动条    |                        |                  |
+----------------+------------------------+------------------+
                         |
               [底部版权信息]
```

### 左侧列 - 商品与参数

| 组件              | 类型       | 说明                                       |
|-------------------|------------|--------------------------------------------|
| 商品图上传        | Image      | 支持拖拽上传, 输出 PIL 格式, 高度 240px    |
| 场景风格          | Radio      | 五种预设风格, 卡片按钮样式, 默认 studio    |
| ControlNet 强度   | Slider     | 范围 0.0-1.5, 步长 0.05, 默认 0.7         |

### 中间列 - 手绘画板

| 组件              | 类型       | 说明                                       |
|-------------------|------------|--------------------------------------------|
| Scribble 画板     | Sketchpad  | 高度 500px, 8 种画笔颜色, 输出 dict        |

画笔颜色: 黑 / 红 / 绿 / 蓝 / 橙 / 紫 / 青 / 白

### 右侧列 - 结果展示

| 组件              | 类型       | 说明                                       |
|-------------------|------------|--------------------------------------------|
| 结果预览          | Image      | 只读, 高度 440px, 下载格式 PNG             |
| 生成按钮          | Button     | 触发 extract_and_process() -> main_process() |

### 主题切换

右上角圆形按钮，点击在浅色/深色主题间切换:

- 浅色: 白色背景, 紫色渐变标题与按钮
- 深色: 深海军蓝背景, 蓝色渐变标题与按钮, Gradio 原生暗色变量覆盖

---

## 接口文档

### 接口 1: generate_prompt

生成文本提示词。

```python
def generate_prompt(bg_type: str, image: PIL.Image.Image = None) -> str
```

| 参数    | 类型            | 必填 | 说明                                                    |
|---------|-----------------|------|---------------------------------------------------------|
| bg_type | str             | 是   | 场景风格: "studio" / "beach" / "nature" / "luxury" / "minimal" |
| image   | PIL.Image.Image | 否   | 商品图, 默认 None                                       |

| 返回值 | 类型 | 说明               |
|--------|------|--------------------|
| prompt | str  | 英文 Prompt 文本   |

负责人: 

---

### 接口 2: process_scribble

预处理手绘涂鸦。

```python
def process_scribble(raw_scribble: dict | PIL.Image.Image) -> PIL.Image.Image
```

| 参数          | 类型                      | 必填 | 说明                            |
|---------------|---------------------------|------|---------------------------------|
| raw_scribble  | dict 或 PIL.Image.Image   | 是   | Gradio Sketchpad 组件原始输出   |

| 返回值   | 类型            | 说明                      |
|----------|-----------------|---------------------------|
| scribble | PIL.Image.Image | 512x512 RGB 标准线稿图    |

负责人: 

---

### 接口 3: generate_image

调用模型生成最终图片。

```python
def generate_image(
    prompt: str,
    scribble: PIL.Image.Image,
    weight: float,
    image: PIL.Image.Image = None
) -> PIL.Image.Image
```

| 参数     | 类型            | 必填 | 说明                             |
|----------|-----------------|------|----------------------------------|
| prompt   | str             | 是   | 文本提示词                       |
| scribble | PIL.Image.Image | 是   | 512x512 预处理后线稿图           |
| weight   | float           | 是   | ControlNet 权重, 范围 [0.0, 1.5] |
| image    | PIL.Image.Image | 否   | 商品原图, 默认 None              |

| 返回值 | 类型            | 说明                    |
|--------|-----------------|-------------------------|
| result | PIL.Image.Image | 512x512 最终生成图像    |

负责人: 

---

### 辅助函数: extract_and_process

Gradio 按钮回调入口, 从 Radio 组件的显示文本中提取风格标识符。

```python
def extract_and_process(product_image, style_full, controlnet_weight, raw_scribble)
```

Radio 选项格式: `"studio  |  影棚纯色背景"` -> 以 `|` 分割取左侧 -> `"studio"`

---

## 管线流程

```
用户点击 [生成] 按钮
        |
        v
extract_and_process()             -- 提取风格标识符
        |
        v
main_process()                    -- 串联三个接口
        |
        +-- Step 1: generate_prompt(bg_type, image)
        |       -> "A professional product photo in beach style..."
        |
        +-- Step 2: process_scribble(raw_scribble)
        |       -> PIL.Image (512x512 白色画布)
        |
        +-- Step 3: generate_image(prompt, scribble, weight, image)
        |       -> PIL.Image (512x512 带 "Test Success" 文字)
        |
        v
result_image 组件                 -- 右侧预览区显示结果
```

---

## 开发指南

### 接口替换流程

各模块负责人按以下步骤替换桩函数为真实逻辑:

1. 定位目标函数 (如 `generate_image`)。
2. 保持函数签名 (参数名、类型、返回类型) 不变。
3. 替换函数体内部实现。
4. 确保返回值类型与文档一致。
5. 运行完整管线测试。

### 示例: 替换 generate_prompt

```python
# 替换前 (桩函数)
def generate_prompt(bg_type, image=None):
    has_image = "with product image" if image is not None else "without product image"
    return f"A professional product photo in {bg_type} style, {has_image}..."

# 替换后 (接入真实模型)
def generate_prompt(bg_type, image=None):
    prompt = call_llm_api(bg_type)
    if image is not None:
        desc = image_captioning(image)
        prompt += f", featuring {desc}"
    return prompt
```

### 测试检查清单

| 序号 | 测试项                                | 预期结果                                    |
|------|---------------------------------------|---------------------------------------------|
| 1    | 不上传图片, 直接点击生成              | 终端显示 image = 无商品图, 正常出图         |
| 2    | 上传商品图后点击生成                  | 终端显示 image = 有商品图                   |
| 3    | 切换场景风格为各选项后点击生成        | 终端显示对应的 bg_type 值                   |
| 4    | 拖动滑动条至 0.0 和 1.5              | 终端显示对应的 weight 值                    |
| 5    | 在画板用不同颜色绘制后点击生成        | 终端显示 raw_scribble 类型为 dict           |
| 6    | 连续点击两次生成按钮                  | 终端打印两次完整日志, 无报错                |
| 7    | 右侧结果区域                          | 显示带 Test Success 文字的测试图            |
| 8    | 点击结果图下载按钮                    | 下载 PNG 格式文件                           |
| 9    | 点击右上角主题切换按钮                | 界面在浅色/深色主题间切换                   |

### 调试日志示例

点击生成按钮后, 终端将输出:

```
============================================================
main_process() 启动
============================================================

Step 1: generate_prompt()...
  -> prompt = 'A professional product photo in studio style, with product image, high quality, 8k resolution'

Step 2: process_scribble()...
  -> scribble size = (512, 512)

Step 3: generate_image()...
==================================================
generate_image() 被调用:
  prompt   : A professional product photo in studio style...
  scribble : <class 'PIL.Image.Image'> | (512, 512)
  weight   : 0.7
  image    : 有商品图
==================================================
  -> result size = (512, 512)
============================================================
```

---

## 已知约束

以下为 Gradio 6.0 环境下的已知限制, 修改代码时需注意:

| 约束                                    | 原因                                           | 影响                               |
|-----------------------------------------|------------------------------------------------|------------------------------------|
| CSS 不可覆盖 Sketchpad 内部元素         | 会破坏多层 canvas 的透明度合成                  | 画布半黑半白、颜色面板不可见       |
| 外框容器不可设 overflow:hidden          | 颜色选择器为弹出层, hidden 会裁剪               | 画笔无法切换颜色                   |
| css 参数须传入 launch() 而非 Blocks()   | Gradio 6.0 API 变更                            | 否则触发 UserWarning               |
| `<script>` 标签会被过滤                | Gradio 6.0 安全策略                            | 需用 onclick 内联或 demo.load(js=) |
| gr.Button 的 click 被 Gradio 拦截      | 主题切换按钮不能用 gr.Button                   | 需用 gr.HTML 原生按钮              |
| Radio 组件自带灰色背景                 | Gradio 内部多层 div 有默认 background          | 需用通配符 * 清除后单独恢复 label  |
| 剪切板粘贴功能不可用                   | 浏览器安全策略 / Gradio 兼容性                 | 已移除 clipboard source            |
| 多显示器 DPI 缩放导致画板半黑半白    | Gradio Canvas 初始化时使用了错误的 devicePixelRatio | 已通过 JS 无感抖动容器触发 ResizeObserver 修复 |

---

## 常见问题

### Q: 安装 Gradio 时下载速度慢或超时

使用国内镜像源安装:

```bash
pip install gradio==6.0.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: 启动后终端 "卡住" 不动

这是正常现象。Gradio 服务器启动后会持续监听请求, 终端处于等待状态。需要停止时按 `Ctrl + C`。

### Q: 出现 ModuleNotFoundError: No module named 'gradio'

确保使用与运行脚本相同的 Python 解释器安装依赖:

```bash
python -m pip install gradio==6.0.0 numpy pillow
```

### Q: 画笔只有黑色, 无法切换颜色

两个可能原因:

1. 外框容器设了 `overflow: hidden`, 裁剪了颜色选择器弹窗。解决: 删除该属性。
2. Sketchpad 未配置 `brush` 参数。解决: 显式传入 `gr.Brush(colors=[...], color_mode="defaults")`。

### Q: 深色/浅色切换按钮无反应

Gradio 6.0 会过滤 `<script>` 标签, 且 `gr.Button` 的 click 事件会被拦截。解决: 使用 `gr.HTML` 渲染原生 `<button>`, 通过 `onclick` 内联 JavaScript 实现切换。

### Q: 下载的图片是 .webp 格式

在 `gr.Image` 组件中设置 `format="png"` 参数。

### Q: 分享按钮点击报错

Gradio 的分享功能依赖海外隧道服务器, 国内网络环境无法使用。当前版本已通过 JS 自动删除分享按钮。

### Q: 画板显示一半黑一半白 (多显示器环境)

这是 Gradio Sketchpad 在多显示器不同 DPI 缩放下的初始化 Bug。画板组件在首次加载时使用了错误的 `devicePixelRatio` 计算 Canvas 物理像素尺寸。当拖动窗口到另一个显示器时, 浏览器触发 `ResizeObserver`, Gradio 重新计算画布尺寸后恢复正常。

当前版本已通过 JS 在页面加载 300ms 后自动微调画板容器的 `paddingBottom` (1px, 50ms 后恢复), 无感触发 `ResizeObserver` 修复此问题。

如果仍然出现, 可尝试:

1. 刷新页面 (`F5`)
2. 调整浏览器窗口大小

### Q: 如何修改默认主题

当前默认为深色主题。如需改为浅色主题:

1. 在 `demo.load` 的 JS 中删除 `document.body.classList.add('dark')` 和 `document.documentElement.classList.add('dark')` 两行。
2. 将主题切换按钮的初始文字从 `☀️` 改回 `🌙`。

### Q: 如何调整三列宽度比例

修改 `CUSTOM_CSS` 中 `#col-left`, `#col-center`, `#col-right` 的百分比数值, 三个数字之和保持 100% 即可。

### Q: 如何调整整体容器宽度

修改 `CUSTOM_CSS` 中 `.gradio-container` 的 `max-width` 值。设为 `100%` 可撑满全屏。

---

## 变更日志

### v1.2.1 (2026-04-20)

- 通过 JS 无感抖动容器 paddingBottom 彻底修复多显示器 DPI 画板渲染 Bug
- 放大中间画板高度至 600px, 右侧结果图高度至 540px
- 默认启用深色主题
- 整体容器宽度从 1440px 调整为 1700px
- 添加多显示器 DPI 问题的常见问题说明
- 添加布局调整 (三列比例、容器宽度) 的常见问题说明

### v1.1.0 (2026-04-18)

- 修复画板半黑半白: 删除 canvas_size, 改用 height 控制显示大小
- 修复画笔颜色选择器不可用: 删除外框 overflow:hidden, 显式配置 gr.Brush
- 修复分享按钮删除误伤下载按钮: 改用 SVG path 内容精准识别
- 场景风格选择器从 Dropdown 改为 Radio 卡片按钮
- 添加浅色/深色主题切换功能
- 添加 8 种画笔颜色配置
- CSS 全面重构为 CSS 变量驱动, 支持双主题
- 删除所有 Sketchpad 相关的 CSS 规则 (避免干扰画布渲染)
- 添加 Gradio 6.0 已知约束文档

### v1.0.0 (2026-04-18)

- 初始版本发布
- 完成三列式 Gradio Blocks 界面布局
- 定义三个团队协作接口 (桩函数模式)
- 实现 main_process 主管线串联逻辑
- 适配 Gradio 6.0 API 变更