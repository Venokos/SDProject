from generate import generate_image

if __name__ == "__main__":
    prompt = "a product on the table, minimal studio background"
    control_types = ["scribble", "canny"]
    for ctype in control_types:
        print(f"\n=== 开始生成，control_type = {ctype} ===")
        path = generate_image(
            prompt=prompt,
            scribble_path="./test1.png",
            weight=1.1,
            control_type=ctype,
            width=512,
            height=512,
            steps=30
        )
        print(f"图片已生成: {path}")
    print("\n所有测试完成！")
