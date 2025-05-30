"""
FitMirror 主入口 - 健身助手聊天界面

一个简单的命令行界面，允许用户与 FitMirror 智能健身助手交互
用户可以询问健身知识或请求分析视频
"""

import os
import time
import sys
import argparse
from dotenv import load_dotenv

# 加载环境变量，确保在导入其他模块前执行
load_dotenv()

# 导入 Agent 实现
# 注意：确保 agent_react.py 中的 FitMirrorLangChainAgent 类已定义
try:
    from agent_react import FitMirrorLangChainAgent
    print("✓ 成功导入 LangChain Agent (agent_react.py)")
except ImportError as e:
    print(f"✗ 无法导入 Agent: {e}")
    print("请确保 agent_react.py 文件存在且包含 FitMirrorLangChainAgent 类。")
    sys.exit(1)

def print_with_delay(message, delay=0.03):
    """逐字打印文本，模拟打字效果"""
    for char in message:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def print_welcome_message():
    """打印欢迎信息"""
    banner = r"""
    ███████╗██╗████████╗███╗   ███╗██╗██████╗ ██████╗  ██████╗ ██████╗ 
    ██╔════╝██║╚══██╔══╝████╗ ████║██║██╔══██╗██╔══██╗██╔═══██╗██╔══██╗
    █████╗  ██║   ██║   ██╔████╔██║██║██████╔╝██████╔╝██║   ██║██████╔╝
    ██╔══╝  ██║   ██║   ██║╚██╔╝██║██║██╔══██╗██╔══██╗██║   ██║██╔══██╗
    ██║     ██║   ██║   ██║ ╚═╝ ██║██║██║  ██║██║  ██║╚██████╔╝██║  ██║
    ╚═╝     ╚═╝   ╚═╝   ╚═╝     ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝
                      智能健身助手 - LangChain (Qwen)版                                                                
    """
    print(banner)
    print("="*70)
    print_with_delay("欢迎使用 FitMirror 智能健身助手！")
    print_with_delay("我可以：")
    print_with_delay("  1. 分析你的健身视频，计数并识别动作错误")
    print_with_delay("  2. 回答健身相关问题，提供个性化建议")
    print_with_delay("  3. 帮助你改进运动姿势，预防受伤")
    print_with_delay("\n示例命令：")
    print_with_delay("  - \"帮我分析这个深蹲视频: c:/path/to/video.mp4\"")
    print_with_delay("  - \"深蹲时膝盖疼是怎么回事？\"") 
    print_with_delay("  - \"请告诉我正确的俯卧撑姿势\"")
    print_with_delay("\n输入 'exit' 或 'quit' 退出程序")
    print("="*70)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='FitMirror 智能健身助手')
    parser.add_argument('--verbose', action='store_true', help='显示详细的Agent执行过程')
    # 修改模型默认值为 Qwen 模型
    parser.add_argument('--model', default="qwen-plus", help='指定使用的模型名称，如 qwen-plus, qwen-turbo, qwen-max, gpt-4o, gpt-4-turbo 等')
    args = parser.parse_args()
    
    # 显示欢迎信息
    print_welcome_message()
    
    # 初始化 Agent (目前只支持 LangChain Agent)
    print("正在初始化 FitMirror Agent...")
    try:
        agent = FitMirrorLangChainAgent(verbose=args.verbose, model_name=args.model)
        agent_type = "LangChain ReAct (Qwen)"
        print(f"初始化完成！使用 {agent_type} Agent 开始聊天...\n")
    except Exception as e:
        print(f"\033[31m错误: 初始化 Agent 失败: {e}\033[0m")
        print("请检查 agent_react.py 文件和依赖项。")
        sys.exit(1)
    
    # 主循环
    while True:
        try:
            user_input = input("\033[34m用户 > \033[0m")
            
            if user_input.lower() in ['exit', 'quit', 'q', '退出', '结束']:
                print_with_delay("\n感谢使用 FitMirror！祝您健康运动！")
                break
                
            if not user_input.strip():
                continue
                
            print("\033[32mFitMirror 正在思考...\033[0m")
            
            start_time = time.time()
            response = agent.run(user_input)
            end_time = time.time()
            
            print("\033[32mFitMirror > \033[0m", end='')
            if response and response.get("success"):
                print_with_delay(response.get("message", "抱歉，发生未知错误。"))
            elif response:
                print(f"\033[31m错误: {response.get('message', '处理请求时出错。')}\033[0m")
            else:
                print(f"\033[31m错误: Agent 返回了无效的响应。\033[0m")
                
            print(f"\033[90m[响应时间: {end_time - start_time:.2f}秒]\033[0m\n")
            
        except KeyboardInterrupt:
            print("\n\n正在退出 FitMirror...")
            break
        except Exception as e:
            print(f"\033[31m发生错误: {str(e)}\033[0m")
            import traceback
            traceback.print_exc()
            print("请尝试重新输入或重启程序")

if __name__ == "__main__":
    main()