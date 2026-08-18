## 大一立项：可控文胜图 项目概况（后半阶段）
*项目主页：https://github.com/Venokos/SDProject*
### 项目总目标
开发一个：
**基于ControlNet的可控电商背景生成系统**
用户可以：
```上传商品图 → 选择背景 → 选择结构 → 生成背景图```

技术核心：
- prompt 控制风格
- scribble 控制结构
- ControlNet 控制生成过程
- ==ComfyUI 控制工作流==

---

#### 项目结构

ui/app.py（UI + 编排）
   ├── generate_prompt()        # 调用 prompt 生成器
   ├── process_scribble()       # 处理自定义画板
   ├── generate_image()         # 调用模板映射 + 商品图保存
   │       └── sd_generate_image()  # 调用 backend/generate.py
   │               └── WebUI API

备注：项目四个成员分别在各自的git分支上进行工作。

当前git分支情况：

- A-backend
- B-scribble
- C-prompt
- D-UI
- integration
- master

---


### 目前项目进度

#### 总述：

当前，项目可以实现“一键生成”：
1. 打开本地SD WebUI
2. 运行 ui界面/app.py，这会打开一个Gradio可交互界面
3. 上传商品图（可选）
4. 选择场景风格（studio / beach / nature / luxury / minimal）
5. 选择 Scribble 模板（桌面 / 展示台 / 自定义画板）
6. 调节 ControlNet 强度（建议 0.7-1.0）
7. 在画板绘制构图草稿（若选了自定义画板）
8. 点击 **生成** 按钮

##### 具体技术实现：
- 核心生成：backend/generate.py
- Scribble模板：Project-B/
- Gradio界面：ui/app.py
- 场景风格：prompt/prompt_generator.py


现在最大的难点是：我们进行了**几百次手动调参**，前后总计生成了**超过1500张图片**，但是图片生成效果始终不理想，具体问题包括但不限于：
- 原商品扭曲变形
- 原商品消失
- 原商品嵌入背景

#### 结论：
当前方案（原生SD1.5）**已经接近它的能力上限**。
#### 解决方案：
- 引入ComfyUI工作流。
- 考虑使用多个模型，而不只是Scribble。

*2026.08.18 Venokos*