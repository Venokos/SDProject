#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E-commerce Background Generator - Prompt Generator

This module generates suitable background description prompts for e-commerce products,
able to generate personalized prompts based on different product types, styles, compositions, etc.
Supports automatic parameter extraction from natural language descriptions.
"""

import re


class EcommercePromptGenerator:
    """
    E-commerce Background Prompt Generator class
    """
    
    def __init__(self):
        """
        Initialize generator, set base template and parameter options
        """
        # Base prompt template
        self.base_template = "Professional e-commerce product photography, {product_type}, {background_description}, {composition}, {lighting}, {color_scheme}, high definition, rich details, commercial quality"
        
        # Product type options and their descriptions
        self.product_types = {
            "服装": "fashion clothing",
            "电子产品": "modern electronic product",
            "食品": "delicious food",
            "美妆": "exquisite beauty product",
            "家具": "modern furniture",
            "配饰": "fashion accessory",
            "玩具": "children's toy",
            "书籍": "beautiful book"
        }
        
        # Product type keyword mapping (for natural language recognition)
        self.product_keywords = {
            "服装": ["衣服", "服装", "裙子", "裤子", "上衣", "外套", "T恤", "衬衫", "女装", "男装", "童装"],
            "电子产品": ["手机", "电脑", "耳机", "平板", "相机", "电子", "数码", "智能手表", "充电器"],
            "食品": ["食物", "食品", "零食", "水果", "蛋糕", "面包", "饮料", "咖啡", "茶", "美食"],
            "美妆": ["化妆品", "护肤品", "口红", "粉底", "眼影", "美妆", "香水", "面膜"],
            "家具": ["家具", "沙发", "桌子", "椅子", "床", "柜子", "书架", "家居"],
            "配饰": ["配饰", "首饰", "项链", "手链", "耳环", "戒指", "包包", "手表", "眼镜"],
            "玩具": ["玩具", "玩偶", "积木", "乐高", "模型", "益智玩具", "儿童玩具"],
            "书籍": ["书", "书籍", "杂志", "小说", "教材", "绘本", "图书"]
        }
        
        # Background description options
        self.background_options = {
            "简约": "simple clean background, white or light gray",
            "自然": "natural environment background, such as wooden table, grass or forest",
            "海滩": "beach scene with golden sand, ocean waves, blue sky and tropical atmosphere",
            "都市": "modern urban background, such as coffee shop or studio",
            "奢华": "luxurious background, such as gold decorations or high-end fabric",
            "科技感": "tech background, such as geometric patterns or blue light effects",
            "节日": "festive theme background, such as Christmas or Valentine's Day decorations"
        }
        
        # Background keyword mapping
        self.background_keywords = {
            "简约": ["简约", "简单", "干净", "极简", "白色", "纯色", "空白"],
            "自然": ["自然", "木质", "草地", "沙滩", "户外", "植物", "绿色"],
            "都市": ["都市", "城市", "咖啡厅", "工作室", "办公室", "现代", "室内"],
            "奢华": ["奢华", "豪华", "金色", "高级", "高档", "精致", "贵气"],
            "科技感": ["科技", "科技感", "几何", "蓝色", "光效", "未来", "数字"],
            "节日": ["节日", "圣诞", "情人节", "春节", "喜庆", "庆祝", "装饰"]
        }
        
        # Composition options
        self.composition_options = {
            "中心": "center composition, product located in the center of the frame",
            "对角线": "diagonal composition, product arranged along the diagonal",
            "三分法": "rule of thirds composition, product located at the golden section point",
            "平铺": "flat lay composition, multiple products neatly arranged",
            "特写": "close-up composition, highlighting product details"
        }
        
        # Composition keyword mapping
        self.composition_keywords = {
            "中心": ["中心", "中间", "居中", "正中"],
            "对角线": ["对角线", "斜线", "对角"],
            "三分法": ["三分法", "黄金分割", "三分", "九宫格"],
            "平铺": ["平铺", "俯拍", "俯视", "平放", "整齐"],
            "特写": ["特写", "近景", "细节", "放大", "聚焦"]
        }
        
        # Lighting options
        self.lighting_options = {
            "自然光": "soft natural light, illuminating from the side",
            "棚拍": "professional studio lighting, evenly illuminating the product",
            "侧光": "side lighting, highlighting product three-dimensionality",
            "背光": "backlighting effect, clear product outline",
            "柔光": "soft diffused light, no harsh shadows"
        }
        
        # Lighting keyword mapping
        self.lighting_keywords = {
            "自然光": ["自然光", "阳光", "日光", "自然", "户外光"],
            "棚拍": ["棚拍", "摄影棚", "专业灯光", "打光", "布光"],
            "侧光": ["侧光", "侧面光", "侧光照明"],
            "背光": ["背光", "逆光", "轮廓光", "剪影"],
            "柔光": ["柔光", "散射光", "柔光箱", "漫射光"]
        }
        
        # Color scheme options
        self.color_scheme_options = {
            "中性": "neutral tones, such as white, gray, beige",
            "暖色调": "warm tones, such as orange, red, yellow",
            "冷色调": "cool tones, such as blue, green, purple",
            "单色调": "monochromatic color scheme, unified and harmonious",
            "对比色": "complementary color matching, vivid and prominent"
        }
        
        # Color scheme keyword mapping
        self.color_keywords = {
            "中性": ["中性", "黑白灰", "米色", "灰色", "白色", "低调"],
            "暖色调": ["暖色", "暖色调", "橙色", "红色", "黄色", "温暖", "温馨"],
            "冷色调": ["冷色", "冷色调", "蓝色", "绿色", "紫色", "清凉", "冷静"],
            "单色调": ["单色", "单色调", "同色系", "统一", "协调"],
            "对比色": ["对比色", "撞色", "鲜明", "突出", "对比", "强烈"]
        }
    
    def parse_user_input(self, user_text):
        """
        Parse parameters from user's natural language input
        
        Parameters:
            user_text (str): User's description text
            
        Returns:
            dict: Dictionary containing parsed parameters
        """
        user_text_lower = user_text.lower()
        
        # Initialize parameters
        params = {
            "product_type": None,
            "background": None,
            "composition": None,
            "lighting": None,
            "color_scheme": None
        }
        
        # Identify product type
        for product_type, keywords in self.product_keywords.items():
            for keyword in keywords:
                if keyword in user_text_lower:
                    params["product_type"] = product_type
                    break
            if params["product_type"]:
                break
        
        # Identify background type
        for background, keywords in self.background_keywords.items():
            for keyword in keywords:
                if keyword in user_text_lower:
                    params["background"] = background
                    break
            if params["background"]:
                break
        
        # Identify composition type
        for composition, keywords in self.composition_keywords.items():
            for keyword in keywords:
                if keyword in user_text_lower:
                    params["composition"] = composition
                    break
            if params["composition"]:
                break
        
        # Identify lighting type
        for lighting, keywords in self.lighting_keywords.items():
            for keyword in keywords:
                if keyword in user_text_lower:
                    params["lighting"] = lighting
                    break
            if params["lighting"]:
                break
        
        # Identify color scheme
        for color_scheme, keywords in self.color_keywords.items():
            for keyword in keywords:
                if keyword in user_text_lower:
                    params["color_scheme"] = color_scheme
                    break
            if params["color_scheme"]:
                break
        
        return params
    
    def generate_prompt_from_text(self, user_text):
        """
        Generate prompt based on user's natural language input
        
        Parameters:
            user_text (str): User's description text
            
        Returns:
            tuple: (generated prompt string, identified parameters dictionary)
        """
        # Parse user input
        params = self.parse_user_input(user_text)
        
        # Set default values for unidentified parameters
        if not params["product_type"]:
            params["product_type"] = "服装"  # Default product type
        if not params["background"]:
            params["background"] = "简约"  # Default background
        if not params["composition"]:
            params["composition"] = "中心"  # Default composition
        if not params["lighting"]:
            params["lighting"] = "自然光"  # Default lighting
        if not params["color_scheme"]:
            params["color_scheme"] = "中性"  # Default color scheme
        
        # Generate prompt
        prompt = self.generate_prompt(
            product_type=params["product_type"],
            background=params["background"],
            composition=params["composition"],
            lighting=params["lighting"],
            color_scheme=params["color_scheme"]
        )
        
        return prompt, params
    
    def generate_prompt(self, product_type, background, composition, lighting, color_scheme):
        """
        Generate complete prompt
        
        Parameters:
            product_type (str): Product type
            background (str): Background type
            composition (str): Composition method
            lighting (str): Lighting type
            color_scheme (str): Color scheme
            
        Returns:
            str: Generated complete prompt
        """
        # Get corresponding descriptions
        product_desc = self.product_types.get(product_type, "product")
        background_desc = self.background_options.get(background, "suitable background")
        composition_desc = self.composition_options.get(composition, "good composition")
        lighting_desc = self.lighting_options.get(lighting, "appropriate lighting")
        color_scheme_desc = self.color_scheme_options.get(color_scheme, "coordinated color scheme")
        
        # Fill template to generate complete prompt
        prompt = self.base_template.format(
            product_type=product_desc,
            background_description=background_desc,
            composition=composition_desc,
            lighting=lighting_desc,
            color_scheme=color_scheme_desc
        )
        
        return prompt
    
    def get_product_types(self):
        """
        Get all available product types
        
        Returns:
            list: Product type list
        """
        return list(self.product_types.keys())
    
    def get_background_options(self):
        """
        Get all available background options
        
        Returns:
            list: Background option list
        """
        return list(self.background_options.keys())
    
    def get_composition_options(self):
        """
        Get all available composition options
        
        Returns:
            list: Composition option list
        """
        return list(self.composition_options.keys())
    
    def get_lighting_options(self):
        """
        Get all available lighting options
        
        Returns:
            list: Lighting option list
        """
        return list(self.lighting_options.keys())
    
    def get_color_scheme_options(self):
        """
        Get all available color scheme options
        
        Returns:
            list: Color scheme option list
        """
        return list(self.color_scheme_options.keys())


# ---------------------------------------------------------------------------
# 五种场景风格的中文示例提示词
#
# 写法参考 prompts3.txt：场景清楚 + 商品明确 + 光线明确 + 摄影方式明确。
# 商品主体保持原有形状、比例、颜色和结构，避免人物 / 额外商品 / 文字 / 水印。
# ---------------------------------------------------------------------------

STYLE_OPTIONS = [
    ("studio", "影棚纯色背景"),
    ("beach", "海滩阳光氛围"),
    ("nature", "自然草地森林"),
    ("luxury", "高端大理石台面"),
    ("minimal", "极简留白风"),
]

STYLE_PROMPTS = {
    "studio": (
        "一件商品作为画面主体，保持商品原有的形状、比例、颜色和结构。"
        "商品放置在干净的浅灰色影棚背景前，背景为简洁的纯色渐变，周围没有其他物品和人物。"
        "左侧大型柔光箱提供柔和主光，右侧补充轻微轮廓光，在商品边缘和材质表面形成自然细腻的高光。"
        "台面产生柔和真实的接触阴影。专业商业产品摄影，真实摄影质感，浅景深，"
        "画面干净、简洁、高级，没有人物、文字和水印。"
    ),
    "beach": (
        "一件商品作为画面主体，保持商品原有的形状、比例、颜色和结构。"
        "商品放置在细腻的金色沙滩上，背景是开阔的海滩，远处有蓝天、白云和柔和海浪。"
        "傍晚阳光从侧后方照射，在商品表面形成温暖自然的高光，沙滩表面有轻微的接触阴影。"
        "高级商业产品摄影，真实摄影质感，浅景深，画面通透、温暖、有度假氛围，"
        "没有人物、文字和水印。"
    ),
    "nature": (
        "一件商品作为画面主体，保持商品原有的形状、比例、颜色和结构。"
        "商品放置在自然的草地上，背景是柔和虚化的绿色草地与森林。"
        "清晨自然光从侧面照入，在商品表面形成清爽自然的高光和细腻阴影，"
        "草地表面有柔和接触阴影，周围有少量虚化的绿色植物但不喧宾夺主。"
        "高级商业产品摄影，真实摄影质感，浅景深，画面清新、自然、干净，"
        "没有人物、文字和水印。"
    ),
    "luxury": (
        "一件商品作为画面主体，保持商品原有的形状、比例、颜色和结构。"
        "商品放置在高级白色大理石台面上，背景是低调奢华的深色室内空间。"
        "暖色灯光从侧后方照射，在商品边缘和材质表面形成精致的高光，"
        "大理石台面产生柔和真实的接触阴影。奢侈品商业广告摄影，真实摄影质感，浅景深，"
        "画面高级、克制、精致，没有人物、文字和水印。"
    ),
    "minimal": (
        "一件商品作为画面主体，保持商品原有的形状、比例、颜色和结构。"
        "商品放置在纯白色极简背景中，周围大量留白，没有其他物品和人物。"
        "柔和均匀的漫射光照射，避免生硬阴影，在商品表面形成干净细腻的高光，"
        "台面产生极轻微、柔和的接触阴影。极简商业产品摄影，真实摄影质感，浅景深，"
        "画面简洁、干净、高级，没有人物、文字和水印。"
    ),
}


def get_style_display_names():
    """返回五种场景风格的中文显示名。"""
    return [display for _, display in STYLE_OPTIONS]


def get_style_prompt(display_name):
    """根据中文显示名返回对应场景风格的完整提示词。"""
    for key, display in STYLE_OPTIONS:
        if display == display_name:
            return STYLE_PROMPTS.get(key, "")
    return ""


# Example usage
if __name__ == "__main__":
    # Create generator instance
    generator = EcommercePromptGenerator()
    
    # Test natural language input
    test_inputs = [
        "我想要一个手机的科技感背景，用冷色调",
        "给这件衣服拍个照，要简约白色背景，自然光",
        "食品拍摄，自然木质背景，暖色调",
        "化妆品特写，奢华金色背景，棚拍灯光",
        "家具平铺俯拍，中性色调"
    ]
    
    print("=" * 60)
    print("Natural language input test")
    print("=" * 60)
    
    for i, user_text in enumerate(test_inputs, 1):
        print(f"\nExample {i}:")
        print(f"User input: {user_text}")
        prompt, params = generator.generate_prompt_from_text(user_text)
        print(f"Identified parameters: {params}")
        print(f"Generated Prompt: {prompt}")
        print("-" * 60)
