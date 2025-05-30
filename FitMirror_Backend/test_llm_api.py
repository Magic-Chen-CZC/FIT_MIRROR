import os
from dotenv import load_dotenv
from dashscope import Generation
from dashscope.api_entities.dashscope_response import Role

load_dotenv(dotenv_path="c:\\PycharmProjects\\pythonProject\\FitMirror\\.env") # 确保路径正确
api_key = os.getenv("DASHSCOPE_API_KEY")

if not api_key:
    print("错误：DASHSCOPE_API_KEY 未设置。")
else:
    try:
        messages = [{'role': Role.SYSTEM, 'content': 'You are a helpful assistant.'},
                    {'role': Role.USER, 'content': '你好'}]
        response = Generation.call(
            model='qwen-plus', # 或者您在 agent_react.py 中使用的模型
            messages=messages,
            api_key=api_key,
            result_format='message'
        )
        if response.status_code == 200:
            print("DashScope API 调用成功:")
            print(response.output.choices[0].message.content)
        else:
            print(f"DashScope API 调用失败，状态码: {response.status_code}")
            print(f"错误代码: {response.code}")
            print(f"错误信息: {response.message}")
            # 打印完整的响应，看看是否有 'request' 相关的字段
            print(f"完整响应: {response}")


    except Exception as e:
        print(f"直接调用 DashScope API 时发生错误: {e}")
        import traceback
        traceback.print_exc()