"""
FitMirror Agent - LangChain Core ReAct Implementation with Qwen
"""

import os
import sys
from typing import List, Dict, Any, Optional, Sequence, Union
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage

# LangChain Agent imports
from langchain.agents import create_openai_tools_agent, AgentExecutor

# Load tools
from tools import analyze_exercise_video_tool, get_last_exercise_result_tool
from rag_setup import query_fitness_knowledge_tool

# Load environment variables
load_dotenv()

class FitMirrorLangChainAgent:
    """FitMirror 健身助手 LangChain Agent 类 (使用 Qwen 模型)"""

    def __init__(self, verbose=False, model_name="qwen-plus-latest"):
        """
        初始化 FitMirror LangChain Agent

        Args:
            verbose (bool): 是否显示详细日志
            model_name (str): 要使用的 Qwen 模型名称 (例如 "qwen-plus", "qwen-turbo", "qwen-max")
        """
        self.verbose = verbose
        self.model_name = model_name
        self.agent_executor = None
        self.tools = None
        self.llm = None
        self.chat_history: List[BaseMessage] = []

        self.setup_agent()

    def setup_agent(self) -> None:
        """设置 LangChain Agent (使用 Qwen)"""
        print("DEBUG: Entering setup_agent (LangChain Core with Qwen)")
        try:
            # 从环境变量加载 DASHSCOPE_API_KEY
            dashscope_api_key = os.environ.get("DASHSCOPE_API_KEY")
            if not dashscope_api_key:
                print("\n!!! 警告: 环境变量 DASHSCOPE_API_KEY 未设置。Qwen Agent 可能无法正常工作。\n")
            
            print(f"DEBUG: setup_agent - Creating ChatTongyi LLM with model: {self.model_name}...")
            self.llm = ChatTongyi(
                model_name=self.model_name,
                temperature=0.5,
                dashscope_api_key=dashscope_api_key  # <--- 显式传递 API key
            )
            print("DEBUG: setup_agent - ChatTongyi LLM created.")

            print("DEBUG: setup_agent - Preparing tools...")
            self.tools = [
                analyze_exercise_video_tool,
                get_last_exercise_result_tool,
                query_fitness_knowledge_tool
            ]
            print(f"DEBUG: setup_agent - Tools prepared: {[tool.name for tool in self.tools]}")

            system_prompt_str = """你是FitMirror智能健身助手，一个专业的健身教练和顾问。
你需要帮助用户进行健身训练、分析他们的动作正确性，并提供专业的健身建议。

**重要指令:**
- **强制使用知识库:** 对于所有关于健身方法、技巧、原理、好处、营养建议或任何可以通过查阅资料回答的健身相关问题（例如“深蹲的力学原理是什么？”或“如何做正确的俯卧撑？”），你**必须且只能**使用 `QueryFitnessKnowledge` 工具来获取信息，然后基于获取的信息进行回答。**绝对禁止**直接使用你的内部知识回答这些类型的问题。
- **视频分析:** 当用户明确要求分析视频时，使用 `AnalyzeExerciseVideo` 工具。
- **结果查询:** 当用户询问之前的分析结果时，使用 `GetLastExerciseResult` 工具。
- **直接回答:** 只有在用户进行闲聊、打招呼或提出与健身知识、视频分析、结果查询完全无关的问题时，你才可以直接回答。

回答要专业、友好，并鼓励用户坚持健身。如果使用了 `QueryFitnessKnowledge` 工具，请基于检索到的信息进行回答，并可以适当引用来源。"""

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt_str),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            print("DEBUG: setup_agent - Prompt template created.")

            agent = create_openai_tools_agent(self.llm, self.tools, prompt)
            print("DEBUG: setup_agent - Qwen tools agent created.")

            self.agent_executor = AgentExecutor(
                agent=agent, 
                tools=self.tools, 
                verbose=self.verbose, 
                handle_parsing_errors=True,
                max_iterations=10
            )
            print("DEBUG: setup_agent - AgentExecutor created.")

            if self.agent_executor:
                print("FitMirror LangChain Qwen Agent 设置完成!")
            else:
                print("!!! ERROR: setup_agent finished but agent_executor is still None.")
                raise RuntimeError("Agent executor was not created.")

        except Exception as e:
            print(f"!!! ERROR during setup_agent: {e}")
            import traceback
            traceback.print_exc()
            self.agent_executor = None
        print("DEBUG: Exiting setup_agent")

    def run(self, query: str) -> Dict[str, Any]:
        """
        执行用户查询

        Args:
            query (str): 用户输入

        Returns:
            Dict: 包含回复内容的字典
        """
        max_history_length = 10

        if not self.agent_executor:
            return {
                "success": False,
                "message": "Agent 未正确初始化，请检查初始化错误。"
            }

        # === 新增调试代码 ===
        try:
            print("\nDEBUG: 尝试在 Agent 执行前直接调用 self.llm ...")
            pre_check_messages = [HumanMessage(content="你好，这是一个预检查")]
            if self.llm:
                pre_check_response = self.llm.invoke(pre_check_messages)
                print(f"DEBUG: 预检查 LLM 调用成功。响应: {pre_check_response.content}\n")
            else:
                print("!!! DEBUG: 在预检查前 self.llm 为 None。跳过。\n")
        except Exception as pre_check_e:
            print(f"!!! DEBUG: 预检查 LLM 调用失败: {pre_check_e}\n")
            import traceback
            traceback.print_exc()
            # 继续执行，看 Agent 执行是否也失败
        # === 调试代码结束 ===

        try:
            print(f"DEBUG: run - 当前聊天历史: {self.chat_history}")
            response = self.agent_executor.invoke({
                "input": query,
                "chat_history": self.chat_history
            })
            
            output_message = response.get("output", "抱歉，未能从 Agent 获取明确回复。")
            print(f"DEBUG: run - Agent 响应: {response}")

            self.chat_history.append(HumanMessage(content=query))
            self.chat_history.append(AIMessage(content=output_message))
            
            if len(self.chat_history) > max_history_length:
                self.chat_history = self.chat_history[-max_history_length:]
            
            print(f"DEBUG: run - 更新后的聊天历史: {self.chat_history}")

            return {
                "success": True,
                "message": output_message
            }

        except Exception as e:
            print(f"执行查询时出错: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                if self.llm:
                    print("\nDEBUG: run - Agent 失败，尝试直接 LLM 回退...")
                    
                    # === 在回退逻辑中新增调试代码 ===
                    try:
                        print("DEBUG: 尝试在回退逻辑前直接调用 self.llm ...")
                        pre_check_messages_fallback = [HumanMessage(content="你好，这是一个预检查（回退时）")]
                        pre_check_response_fallback = self.llm.invoke(pre_check_messages_fallback)
                        print(f"DEBUG: 预检查 LLM 调用（回退时）成功。响应: {pre_check_response_fallback.content}\n")
                    except Exception as pre_check_fallback_e:
                        print(f"!!! DEBUG: 预检查 LLM 调用（回退时）失败: {pre_check_fallback_e}\n")
                        # 如果 self.llm 存在持续性问题，这里也可能失败
                        import traceback
                        traceback.print_exc() # 打印回退预检查的错误堆栈
                    # === 调试代码结束 ===

                    fallback_messages = [
                        SystemMessage(content="你是FitMirror智能健身助手。你的工具调用功能暂时出现问题。请根据用户的问题，尽力提供一个直接和友好的回答。问题如下："),
                        HumanMessage(content=query)
                    ]

                    direct_response_obj = self.llm.invoke(fallback_messages)
                    direct_response = direct_response_obj.content if hasattr(direct_response_obj, 'content') else str(direct_response_obj)
                    
                    self.chat_history.append(HumanMessage(content=query))
                    self.chat_history.append(AIMessage(content=f"(Agent 运行失败，直接回复): {direct_response}"))
                    if len(self.chat_history) > max_history_length:
                         self.chat_history = self.chat_history[-max_history_length:]

                    return {
                        "success": True,
                        "message": f"(Agent 运行失败，直接回复): {direct_response}"
                    }
            except Exception as llm_e:
                print(f"LLM 后备调用也失败: {llm_e}")
                self.chat_history.append(HumanMessage(content=query))
                self.chat_history.append(AIMessage(content=f"处理请求时出错: {str(e)}"))
                if len(self.chat_history) > max_history_length:
                    self.chat_history = self.chat_history[-max_history_length:]
                pass

            return {
                "success": False,
                "message": f"处理请求时出错: {str(e)}"
            }

# --- 测试代码 ---
if __name__ == "__main__":
    print("初始化 FitMirror LangChain Qwen Agent...")
    
    if not os.environ.get("DASHSCOPE_API_KEY"):
        print("警告: DASHSCOPE_API_KEY (用于 Qwen 和 RAG) 未设置。请在 .env 文件或环境变量中设置。Agent 可能无法正常工作。")

    agent = FitMirrorLangChainAgent(verbose=True)

    if not agent.agent_executor:
        print("Agent 初始化失败，无法运行测试。")
        sys.exit(1)

    test_queries = [
        "你好",
        "深蹲的力学原理是什么？",
        "帮我分析一个俯卧撑视频 C:\\\\path\\\\to\\\\fake_video.mp4", 
        "我上次锻炼的结果怎么样？"
    ]

    for query in test_queries:
        print("\n" + "="*50)
        print(f"用户: {query}")
        response = agent.run(query)
        print(f"FitMirror: {response['message']}")
    
    print("\n" + "="*50)
    print("用户: 我想了解下跑步的技巧")
    response1 = agent.run("我想了解下跑步的技巧")
    print(f"FitMirror: {response1['message']}")

    print("\n" + "="*50)
    print("用户: 那深蹲呢？之前问过一次")
    response2 = agent.run("那深蹲呢？之前问过一次")
    print(f"FitMirror: {response2['message']}")