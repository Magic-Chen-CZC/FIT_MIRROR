"""
FitMirror Tools Module

这个模块将核心健身分析逻辑封装为 Langchain Tool，以便与 Agent 集成。
"""

from langchain.tools import tool
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import os
import json
from datetime import datetime
import logging # Add logging import

# 导入核心分析模块
from fitness_analyzer import analyze_exercise_video
import shutil # Import shutil for copying files

# Configure logger for this module
logger = logging.getLogger(__name__)

# 全局变量，用于存储最近一次的分析结果
_last_analysis_result: Optional[Dict[str, Any]] = None

# === 健身分析工具的输入模型 ===
class VideoAnalysisInput(BaseModel):
    """用于视频分析的输入模型"""
    video_path: str = Field(..., description="视频文件的绝对路径")
    exercise_type: str = Field(..., description="运动类型，支持 'squat'(深蹲), 'pushup'(俯卧撑), 'situp'(仰卧起坐), 'crunch'(卷腹), 'jumping_jack'(开合跳)")

@tool("analyze_exercise_video", args_schema=VideoAnalysisInput, return_direct=False)
def analyze_exercise_video_tool(video_path: str, exercise_type: str) -> Dict[str, Any]:
    """
    分析健身运动视频，识别和计数动作，检测常见错误。
    这个工具可以分析深蹲、俯卧撑、仰卧起坐、卷腹、开合跳等运动，计算完成次数，并指出动作中的常见错误。
    
    参数:
        video_path: 视频文件的路径，必须是本地路径
        exercise_type: 运动类型，可选值有 'squat'(深蹲), 'pushup'(俯卧撑), 'situp'(仰卧起坐), 'crunch'(卷腹), 'jumping_jack'(开合跳)
    
    当用户询问分析健身视频、计算运动次数或检查动作是否标准时，应使用此工具。
    """
    global _last_analysis_result  # 声明使用全局变量
    try:
        # 检查文件是否存在
        if not os.path.exists(video_path):
            return {
                "success": False,
                "message": f"错误：无法找到视频文件，请确认路径是否正确: '{video_path}'"
            }
        
        # 验证运动类型
        valid_exercise_types = ["squat", "pushup", "situp", "crunch", "jumping_jack"]
        if exercise_type not in valid_exercise_types:
            return {
                "success": False,
                "message": f"错误：不支持的运动类型 '{exercise_type}'。支持的类型有: {', '.join(valid_exercise_types)}"
            }
        
        # 调用核心分析逻辑（显示调试窗口）
        result = analyze_exercise_video(video_path, exercise_type, debug_show_video=True)
        
        # 简化结果以更好地显示在对话中
        simplified_result = {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "exercise_type": exercise_type,
            "counter": result.get("counter", 0),
            "errors_detected": result.get("errors_detected", []),
            # "report_path": result.get("report_path", None) # Keep original report_path from analyzer
        }

        # Handle report path: copy to a publicly accessible reports folder if analysis was successful
        original_report_path = result.get("report_path")
        if simplified_result["success"] and original_report_path and os.path.exists(original_report_path):
            # Define a reports directory relative to this script or a configured one
            # This path should match what api_server.py expects for serving files.
            reports_dir = os.path.join(os.path.dirname(__file__), 'user_reports') 
            os.makedirs(reports_dir, exist_ok=True)
            report_filename = os.path.basename(original_report_path)
            new_report_path = os.path.join(reports_dir, report_filename)
            
            try:
                shutil.copy(original_report_path, new_report_path)
                simplified_result["report_path"] = new_report_path # This is the new, accessible path
                logger.info(f"Report copied to {new_report_path}")
            except Exception as e:
                logger.error(f"Failed to copy report from {original_report_path} to {new_report_path}: {e}")
                simplified_result["report_path"] = None 
        else:
            simplified_result["report_path"] = None
        
        # 如果分析成功，存储结果
        if simplified_result["success"]:
            _last_analysis_result = simplified_result.copy() # 使用副本以避免后续修改影响
            _last_analysis_result["analysis_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
        return simplified_result
        
    except Exception as e:
        return {
            "success": False,
            "message": f"分析过程中出现错误: {str(e)}"
        }

class LastExerciseResultInput(BaseModel):
    """获取最近健身结果的输入模型"""
    pass  # 不需要额外参数

@tool("get_last_exercise_result", args_schema=LastExerciseResultInput, return_direct=False)
def get_last_exercise_result_tool() -> Dict[str, Any]:
    """
    获取最近一次视频分析的结果。
    当用户询问关于刚刚进行的运动分析结果、完成次数或发现的错误时使用此工具。
    """
    global _last_analysis_result # 声明使用全局变量
    try:
        if _last_analysis_result:
            return {
                "success": True,
                "message": "已获取最近的分析结果。",
                "has_result": True,
                **_last_analysis_result # 解包存储的结果
            }
        else:
            return {
                "success": True,
                "message": "无可用的历史记录。请先使用 analyze_exercise_video 工具分析一个视频。",
                "has_result": False,
            }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"获取历史记录时出错: {str(e)}"
        }