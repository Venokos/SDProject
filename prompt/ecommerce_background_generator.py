#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电商背景生成系统

完整的电商背景生成系统，包含prompt生成和用户交互界面。
用户可以通过自然语言描述来生成适合的prompt。
"""

from prompt_generator import EcommercePromptGenerator


def main():
    """
    主函数，处理用户交互并生成prompt
    """
    # 创建生成器实例
    generator = EcommercePromptGenerator()
    
    print("====================================")
    print("       电商背景生成系统")
    print("====================================")
    print("\n请输入您的产品描述，系统会自动生成对应的prompt")
    print("例如：")
    print("  - 我想要一个手机的科技感背景，用冷色调")
    print("  - 给这件衣服拍个照，要简约白色背景，自然光")
    print("  - 食品拍摄，自然木质背景，暖色调")
    print("  - 化妆品特写，奢华金色背景，棚拍灯光")
    print("\n支持的参数：")
    print(f"  产品类型: {', '.join(generator.get_product_types())}")
    print(f"  背景类型: {', '.join(generator.get_background_options())}")
    print(f"  构图方式: {', '.join(generator.get_composition_options())}")
    print(f"  光线类型: {', '.join(generator.get_lighting_options())}")
    print(f"  颜色方案: {', '.join(generator.get_color_scheme_options())}")
    print("\n（输入 'exit' 退出程序）")
    
    while True:
        # 获取用户输入
        print("\n" + "=" * 50)
        user_input = input("\n请输入您的描述: ")
        
        # 检查是否退出
        if user_input.lower() == 'exit':
            print("\n谢谢使用电商背景生成系统！")
            break
        
        # 检查输入是否为空
        if not user_input.strip():
            print("输入不能为空，请重新输入！")
            continue
        
        # 生成prompt
        prompt, params = generator.generate_prompt_from_text(user_input)
        
        # 显示识别出的参数
        print("\n识别出的参数:")
        print(f"  产品类型: {params['product_type']}")
        print(f"  背景类型: {params['background']}")
        print(f"  构图方式: {params['composition']}")
        print(f"  光线类型: {params['lighting']}")
        print(f"  颜色方案: {params['color_scheme']}")
        
        # 显示生成的prompt
        print("\n====================================")
        print("生成的Prompt:")
        print("====================================")
        print(prompt)
        print("====================================")
        
        # 询问用户是否要保存生成的prompt
        save_choice = input("\n是否要保存生成的prompt? (y/n): ")
        if save_choice.lower() == 'y':
            with open("generated_prompts.txt", "a", encoding="utf-8") as f:
                f.write(f"用户输入: {user_input}\n")
                f.write(f"识别参数: 产品类型={params['product_type']}, "
                       f"背景类型={params['background']}, "
                       f"构图方式={params['composition']}, "
                       f"光线类型={params['lighting']}, "
                       f"颜色方案={params['color_scheme']}\n")
                f.write(f"生成的Prompt: {prompt}\n")
                f.write("-" * 50 + "\n")
            print("Prompt已保存到 generated_prompts.txt 文件中")


if __name__ == "__main__":
    main()