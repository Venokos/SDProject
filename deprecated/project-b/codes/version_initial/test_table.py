
from main import img2img_with_scribble

prompts = ("(only two same complete shoes with the same color and shape as the input picture:1.3),"
          "(placed on the center of a brown wooden table:1.3),product photography,side view,"
          "entire shoes visible,sharp focus,shoes with clear and reasonable outline,clear respective relationship,"
          "the table follow the scribble outline exactly,clear table legs，whole round table surface")

negative_prompts=("poor quality,floating,no table,the shoes are separated from the table,"
                 "two tables,split composition,distorted,bad anatomy,watermark,integrated with the desk,"
                 "edges melt together,mixed and multiple color,solid color block,transparent,glisten")

images=img2img_with_scribble(init_image_path=r"C:\Users\DDDlx\Desktop\Project-B\sample\shoes.png",control_image_path=r"C:\Users\DDDlx\Desktop\Project-B\Scribble_mold_picture\desk.png",
                      prompt=prompts,negative_prompt=negative_prompts,save_dir=r"C:\Users\DDDlx\Desktop\Project-B\output")