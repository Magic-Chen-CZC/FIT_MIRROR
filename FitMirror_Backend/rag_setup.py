"""
RAG Setup Module

设置知识检索增强生成 (Retrieval-Augmented Generation) 系统
加载知识库文档、分割、嵌入并创建检索器
"""

import os
import glob
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv # 添加导入

# 加载 .env 文件中的环境变量
load_dotenv() # 添加加载

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, UnstructuredMarkdownLoader
from langchain_community.vectorstores import FAISS
# 修改：使用通义千问嵌入模型 (从 dashscope 导入)
try:
    from langchain_community.embeddings import DashScopeEmbeddings
except ImportError:
    print("警告：缺少 DashScopeEmbeddings。尝试安装: pip install langchain-community")
    # 尝试使用替代方案
    try:
        from langchain.embeddings import FakeEmbeddings as DashScopeEmbeddings
        print("使用假嵌入模型作为替代")
    except ImportError:
        DashScopeEmbeddings = None
        print("无法加载嵌入模型")
from langchain.tools import tool
from pydantic import BaseModel, Field

# 默认的知识库目录
KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")

# 全局变量，存储创建的检索器，避免重复加载
_retriever = None

def setup_retriever(knowledge_base_dir: str = KNOWLEDGE_BASE_DIR) -> Any:
    """
    设置文档检索器
    
    Args:
        knowledge_base_dir: 知识库目录路径，包含PDF、Markdown等文档
        
    Returns:
        检索器对象
    """
    global _retriever
    
    print("--- 开始执行 setup_retriever ---") # 添加开始标记
    
    if _retriever is not None:
        print("使用现有检索器")
        print("--- 结束执行 setup_retriever (使用缓存) ---") # 添加结束标记
        return _retriever
        
    print(f"正在从 {knowledge_base_dir} 加载知识库文档...")
    
    # 确保目录存在
    if not os.path.exists(knowledge_base_dir):
        print(f"知识库目录不存在: {knowledge_base_dir}")
        os.makedirs(knowledge_base_dir, exist_ok=True)
        print("--- 结束执行 setup_retriever (目录不存在) ---") # 添加结束标记
        return None
    
    # 查找所有PDF和Markdown文件
    print("查找 PDF 和 MD 文件...")
    pdf_files = glob.glob(os.path.join(knowledge_base_dir, "*.pdf"))
    md_files = glob.glob(os.path.join(knowledge_base_dir, "*.md"))
    
    # 显示找到的文件
    if pdf_files:
        print(f"找到 {len(pdf_files)} 个PDF文件: {pdf_files}")
    else:
        print("未找到 PDF 文件")
    if md_files:
        print(f"找到 {len(md_files)} 个Markdown文件: {md_files}")
    else:
        print("未找到 Markdown 文件")
        
    if not pdf_files and not md_files:
        print(f"在 {knowledge_base_dir} 中没有找到PDF或Markdown文件")
        print("--- 结束执行 setup_retriever (无文件) ---") # 添加结束标记
        return None
        
    # 加载所有文档
    all_documents = []
    print("开始加载文档...")
    
    # 加载PDF文件
    for pdf_file in pdf_files:
        print(f"加载PDF: {os.path.basename(pdf_file)}")
        loader = PyPDFLoader(pdf_file)
        try:
            documents = loader.load()
            all_documents.extend(documents)
            print(f"成功加载 {len(documents)} 页")
        except Exception as e:
            print(f"加载 {pdf_file} 时出错: {e}")
            import traceback
            traceback.print_exc() # 打印详细错误堆栈
    
    # 加载Markdown文件
    for md_file in md_files:
        print(f"加载Markdown: {os.path.basename(md_file)}")
        try:
            loader = UnstructuredMarkdownLoader(md_file)
            documents = loader.load()
            all_documents.extend(documents)
            print(f"成功加载 {len(documents)} 个文档部分")
        except Exception as e:
            print(f"加载 {md_file} 时出错: {e}")
            import traceback
            traceback.print_exc() # 打印详细错误堆栈
    
    if not all_documents:
        print("未能成功加载任何文档")
        print("--- 结束执行 setup_retriever (加载失败) ---") # 添加结束标记
        return None
    
    print(f"文档加载完成，共 {len(all_documents)} 个文档/页面")
    
    # 分割文档
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,     # 修改块大小为 500
        chunk_overlap=100,   # 块之间的重叠字符数
        separators=["\n\n", "\n", "。", ".", " ", ""],  # 优先级从高到低的分隔符
    )
    
    print(f"开始分割文档...")
    try:
        chunks = text_splitter.split_documents(all_documents)
        print(f"文档分割完成，共创建了 {len(chunks)} 个文本块")
    except Exception as e:
        print(f"分割文档时出错: {e}")
        import traceback
        traceback.print_exc() # 打印详细错误堆栈
        print("--- 结束执行 setup_retriever (分割失败) ---") # 添加结束标记
        return None

    try:
        # 创建嵌入和向量存储
        print("开始创建嵌入和向量存储...")
        if DashScopeEmbeddings is None:
            raise ImportError("无法导入 DashScopeEmbeddings")
            
        # 初始化通义千问嵌入模型
        print("初始化 DashScopeEmbeddings...")
        api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY")
        if not api_key:
            print("错误：未找到 DASHSCOPE_API_KEY 或 QWEN_API_KEY 环境变量！")
            raise ValueError("API Key not found")
        print("API Key 已找到。") # 确认找到Key
        
        embeddings = DashScopeEmbeddings(
            model="text-embedding-v2",  # 通义千问嵌入模型
            dashscope_api_key=api_key
        )
        print("DashScopeEmbeddings 初始化完成。")
        
        # 构建向量数据库
        print(f"开始使用 FAISS 创建向量数据库...")
        vector_db = FAISS.from_documents(chunks, embeddings)
        print(f"向量数据库创建完成。")
        
        # 创建检索器
        print("创建检索器...")
        retriever = vector_db.as_retriever(
            search_type="similarity",  # 也可以是 "mmr"
            search_kwargs={"k": 1}     # 修改检索的文档数量为 3
        )
        
        _retriever = retriever
        print(f"检索器设置完成!")
        print("--- 结束执行 setup_retriever (成功) ---") # 添加结束标记
        return retriever
    
    except Exception as e:
        print(f"设置检索器时出错: {e}")
        import traceback
        traceback.print_exc() # 打印详细错误堆栈
        print(f"请确保已设置有效的通义千问 API 密钥环境变量，并且网络连接正常。")
        print("--- 结束执行 setup_retriever (失败) ---") # 添加结束标记
        return None

# --- RAG 工具类 ---
class KnowledgeQueryInput(BaseModel):
    """用于知识查询的输入模型"""
    query: str = Field(..., description="要查询的健身相关问题")

@tool("query_fitness_knowledge", args_schema=KnowledgeQueryInput, return_direct=False)
def query_fitness_knowledge_tool(query: str) -> Dict[str, Any]:
    """
    搜索健身知识库以回答健身相关的问题。
    使用此工具回答有关健身方法、技巧、好处或理论知识的问题。
    当用户询问有关健身运动的一般性信息而不是特定视频分析时，使用此工具。
    """
    print(f"--- 开始执行 query_fitness_knowledge_tool (查询: '{query}') ---") # 添加开始标记
    try:
        # 获取检索器
        print("调用 setup_retriever 获取检索器...")
        retriever = setup_retriever()
        if retriever is None:
            print("获取检索器失败。")
            result = {
                "success": False,
                "message": "无法访问知识库，请确认知识库配置和通义千问 API 设置",
                "query": query,
                "contexts": []
            }
            print(f"--- 结束执行 query_fitness_knowledge_tool (检索器失败) ---") # 添加结束标记
            return result
        
        print("获取检索器成功。开始执行检索...")
        # 执行检索
        retrieved_docs = retriever.invoke(query)
        print(f"检索完成，找到 {len(retrieved_docs)} 个文档。")
        
        # 提取上下文
        contexts = []
        for i, doc in enumerate(retrieved_docs):
            source = doc.metadata.get("source", "未知来源")
            page = doc.metadata.get("page", "未知页码")
            # 提取文件名，而不是完整路径
            if isinstance(source, str) and os.path.exists(source):
                source = os.path.basename(source)
                
            contexts.append({
                "source": f"{source} (第 {page} 页)",
                "content": doc.page_content
            })
        
        result = {
            "success": True,
            "message": f"已找到 {len(contexts)} 条相关信息",
            "query": query,
            "contexts": contexts
        }
        print(f"--- 结束执行 query_fitness_knowledge_tool (成功) ---") # 添加结束标记
        return result
        
    except Exception as e:
        print(f"查询知识库时出错: {e}")
        import traceback
        traceback.print_exc() # 打印详细错误堆栈
        result = {
            "success": False,
            "message": f"查询知识库时出错: {str(e)}",
            "query": query,
            "contexts": []
        }
        print(f"--- 结束执行 query_fitness_knowledge_tool (异常) ---") # 添加结束标记
        return result

# --- 测试代码 ---
if __name__ == "__main__":
    print("--- 开始执行 main 测试块 ---")
    # 测试检索器设置
    print("调用 setup_retriever 进行测试...")
    retriever = setup_retriever()
    
    if retriever is not None:
        print("\n检索器设置成功，开始测试查询:")
        test_query = "深蹲的正确姿势是什么？"
        print(f"测试查询内容: '{test_query}'")
        print("调用 query_fitness_knowledge_tool 进行测试...")
        result = query_fitness_knowledge_tool(test_query)
        print("\n查询结果:")
        import json
        try:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"打印 JSON 结果时出错: {e}")
            print("原始结果:", result)
    else:
        print("\n检索器设置失败，无法执行测试查询。")
        
    print("--- 结束执行 main 测试块 ---")