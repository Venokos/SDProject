## 大一立项：可控文胜图 Schedule 2.0 基础版
*项目主页：https://github.com/Venokos/SDProject*
#### 项目总目标
开发一个：
**基于ControlNet的可控电商背景生成系统**
用户可以：
```上传商品图 → 选择背景 → 选择结构 → 生成背景图```

技术核心：
prompt 控制风格
scribble 控制结构
ControlNet 控制生成过程

---

#### 项目文件结构

project/
│
├── backend/
│   └── generate.py          ← 成员A
│
├── prompt/
│   └── prompt_generator.py  ← 成员C
│
├── scribble/
│   └── templates/           ← 成员B
│
├── ui/
│   └── app.py               ← 成员D
│
└── README.md


---


#### 第1阶段（第1–2周）

目标：每个人都有能运行的模块

##### 成员A（核心生成）：
通过python调用ControlNet生成图像

需要完成：
文件：
backend/generate.py
函数：
```
def generate_image(
    prompt,
    scribble_path,
    weight=1.0
):
    return output_path
```
要求：
能够运行：
```
generate_image(
    prompt="studio background",
    scribble_path="scribble/table.png",
    weight=1.0
)
```
输出：
result.png

验收标准：
scribble变化 → 生成结构变化

---
##### 成员B（结构控制）

目标：

设计3种可稳定影响生成结构的 scribble 模板

文件位置：

scribble/templates/

需要提供：

table.png
pedestal.png
room.png

要求：

尺寸：512x512

内容：

table

一条水平线

表示：

商品放在平面上


---

pedestal

圆形

表示：

展示台


---

room

角落结构

表示：

空间背景


---

验收标准：

3张图片可被成员A调用。


---

成员C（prompt生成器）

目标：

根据背景类型生成 prompt

文件：

prompt/prompt_generator.py

函数：

def generate_prompt(background_type):
    return prompt

支持类型：

studio
luxury
nature
interior
minimal

示例：

输入：

generate_prompt("studio")

输出：

"minimal studio background, product photography"

验收标准：

函数可以返回字符串。


---

成员D（界面原型）

工具：Gradio

目标：完成界面结构

文件：ui/app.py

界面需要包含：

组件：

图片上传

上传商品图片


---

背景选择

dropdown

选项：

studio
luxury
nature
interior
minimal


---

scribble选择

先用：

dropdown

选项：

table
pedestal
room


---

weight滑动条

范围：

0.5 – 1.5


---

生成按钮

点击后：

显示一张假图即可。

验收标准：

界面可以运行：

python app.py

浏览器可以打开界面。


---

#### 第2阶段（第3–4周）

目标：

打通完整流程

用户可以生成真实图片。


---

##### 成员A

支持从外部调用。

确保：
```
generate_image(
    prompt,
    scribble_path,
    weight
)
```
可被其他文件调用。

可能需要修改：

返回图片路径

例如：

```return "outputs/result.png"```


---

##### 成员B

整理scribble文件结构：

scribble/
   templates/
       table.png
       pedestal.png
       room.png

提供：

文件路径列表：
```
scribble_map = {
    "table": "scribble/templates/table.png",
    "pedestal": "scribble/templates/pedestal.png",
    "room": "scribble/templates/room.png"
}
```

---

##### 成员C

prompt与界面对接。

支持：

background_type → prompt

例如：

prompt = generate_prompt("studio")


---

##### 成员D

调用A和C模块：

流程：
```
prompt = generate_prompt(background_type)

image = generate_image(
    prompt,
    scribble_path,
    weight
)
```
最终实现：

点击按钮 → 生成真实图片。

验收标准：

界面可以生成真实图片。


---

#### 第3阶段（第5–6周）

目标：

优化效果 + 准备展示


---

##### 成员A

测试不同参数：

weight 0.7
weight 1.0
weight 1.3

挑选：

最稳定参数。


---

##### 成员B

优化scribble：

让结构更稳定。

例如：

线条粗细调整。


---

##### 成员C

优化prompt：

让背景更像电商图。

例如加入：

soft lighting
clean background
product photography
high quality


---

##### 成员D

优化界面：

增加：

图片展示区域。


---

#### 第4阶段（第7–8周）

目标：

完成答辩材料


---

需要准备：

内容：

对比展示

展示：

不同 scribble 产生不同结果。

例如：

同一个 prompt：

3种结构。


---

系统演示

流程：

上传图片
选择背景
选择结构
生成结果


---

总时间线

时间	目标

第1–2周	每人完成基础模块
第3–4周	系统整合
第5–6周	优化效果
第7–8周	准备答辩

第1阶段（2周）：
A：完成generate.py，能用scribble控制生成
B：设计3种scribble结构（table pedestal room）
C：完成prompt生成函数
D：完成界面原型（可显示假图）

第2阶段（2周）：
整合系统：
界面 → prompt → scribble → 生成图片

第3阶段（2周）：
优化生成效果

第4阶段（2周）：
准备答辩展示

