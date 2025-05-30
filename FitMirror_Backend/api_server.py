"""
FitMirror API Server - 提供与前端通信的API接口

这个模块创建一个Flask服务器，提供REST API接口，允许前端应用与FitMirror智能健身助手进行通信。
主要功能包括：
- 处理聊天消息并返回AI回复
- 支持跨域请求(CORS)以便与React Native应用通信
"""

import os
import sys
import time
import json
import logging
import uuid
import random
from flask import Flask, request, jsonify, send_from_directory # Added send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 导入 FitMirrorLangChainAgent
try:
    from agent_react import FitMirrorLangChainAgent
    print("✓ 成功导入 LangChain Agent (agent_react.py)")
except ImportError as e:
    print(f"✗ 无法导入 Agent: {e}")
    print("请确保 agent_react.py 文件存在且包含 FitMirrorLangChainAgent 类。")
    sys.exit(1)

# 创建Flask应用
app = Flask(__name__)
CORS(app)  # 启用CORS支持跨域请求

# 配置上传文件夹
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# 配置报告文件夹
REPORTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_reports')
os.makedirs(REPORTS_FOLDER, exist_ok=True)
app.config['REPORTS_FOLDER'] = REPORTS_FOLDER

app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 限制上传文件大小为100MB

# 初始化FitMirror Agent
agent = None
try:
    # 检查是否设置了DASHSCOPE_API_KEY环境变量
    if not os.environ.get("DASHSCOPE_API_KEY"):
        print("警告: DASHSCOPE_API_KEY 未设置。请在 .env 文件中设置。")
        print("聊天功能将不可用，但动作分析功能仍然可用。")
    else:
        agent = FitMirrorLangChainAgent(verbose=False, model_name="qwen-plus")
        print("✓ 成功初始化 FitMirror Agent")
except Exception as e:
    print(f"✗ 初始化 Agent 失败: {e}")
    print("API服务器将继续运行，但聊天功能可能不可用。")

# 尝试导入动作分析工具
try:
    from tools import analyze_exercise_video_tool
    print("✓ 成功导入动作分析工具")
    MOTION_ANALYSIS_AVAILABLE = True
except ImportError as e:
    print(f"✗ 无法导入动作分析工具: {e}")
    print("动作分析功能将不可用。")
    MOTION_ANALYSIS_AVAILABLE = False

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    agent_status = "available" if agent and agent.agent_executor else "unavailable"
    return jsonify({
        "status": "ok",
        "agent_status": agent_status,
        "timestamp": time.time()
    })

@app.route('/chat', methods=['POST'])
def chat():
    """处理聊天请求并返回AI回复"""
    if not agent or not agent.agent_executor:
        return jsonify({
            "success": False,
            "message": "FitMirror Agent未正确初始化，请检查服务器日志。"
        }), 503  # Service Unavailable

    try:
        # 获取请求数据
        data = request.json
        if not data:
            return jsonify({
                "success": False,
                "message": "请求数据为空或格式不正确"
            }), 400  # Bad Request

        user_message = data.get('message', '')
        if not user_message:
            return jsonify({
                "success": False,
                "message": "消息内容不能为空"
            }), 400  # Bad Request

        # 可选：获取聊天历史（如果前端提供）
        # chat_history = data.get('history', [])
        # 注意：目前我们使用agent内部的chat_history，而不是前端传来的

        logger.info(f"收到用户消息: {user_message}")

        # 调用FitMirror Agent处理消息
        start_time = time.time()
        response = agent.run(user_message)
        end_time = time.time()

        logger.info(f"Agent响应时间: {end_time - start_time:.2f}秒")

        if response and response.get("success"):
            return jsonify({
                "success": True,
                "message": response.get("message", ""),
                "response_time": end_time - start_time
            })
        else:
            error_message = response.get("message", "处理请求时出错") if response else "Agent返回了无效的响应"
            logger.error(f"Agent处理失败: {error_message}")
            return jsonify({
                "success": False,
                "message": error_message
            }), 500  # Internal Server Error

    except Exception as e:
        logger.error(f"处理聊天请求时出错: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"服务器错误: {str(e)}"
        }), 500  # Internal Server Error

@app.route('/analyze-exercise', methods=['POST'])
def analyze_exercise():
    """处理动作分析请求"""
    if not MOTION_ANALYSIS_AVAILABLE:
        return jsonify({
            "success": False,
            "message": "动作分析功能不可用，请检查服务器日志。"
        }), 503  # Service Unavailable

    try:
        # 获取运动类型
        exercise_type = request.form.get('exercise_type', 'squat')

        # 验证运动类型
        valid_exercise_types = ["squat", "pushup", "situp", "crunch", "jumping_jack", "plank"]
        if exercise_type not in valid_exercise_types:
            return jsonify({
                "success": False,
                "message": f"不支持的运动类型: {exercise_type}。支持的类型有: {', '.join(valid_exercise_types)}"
            }), 400  # Bad Request

        # 检查是否使用模拟数据
        use_mock = request.form.get('use_mock', 'false').lower() == 'true'

        # 如果使用模拟数据，直接返回模拟结果
        if use_mock:
            logger.info(f"使用模拟数据进行{exercise_type}动作分析")

            # 创建模拟分析结果
            mock_result = {
                'success': True,
                'message': "分析完成，这是模拟数据。",
                'exercise_type': exercise_type,
                'counter': random.randint(5, 15),  # 随机生成5-15之间的数
                'processed_frames': 300,
                'errors_detected': []
            }

            # 随机添加一些错误
            possible_errors = {
                "squat": ["膝盖内扣", "重心过于靠前", "下蹲不够深"],
                "pushup": ["肩部下沉", "臀部抬高", "手肘角度不正确"],
                "situp": ["躯干扭转", "头部前屈", "动作不完整"],
                "jumping_jack": ["动作不对称", "膝盖弯曲", "手臂抬起不够高"],
                "plank": ["臀部抬高", "肩部下沉", "身体不平直"]
            }

            # 50%的概率添加错误
            if random.random() > 0.5:
                errors = possible_errors.get(exercise_type, [])
                if errors:
                    # 随机选择1-2个错误
                    num_errors = random.randint(1, min(2, len(errors)))
                    for i in range(num_errors):
                        mock_result['errors_detected'].append({
                            'type': errors[i],
                            'count': random.randint(1, 5),  # 随机出现1-5次
                            'first_timestamp': random.random() * 10
                        })

            return jsonify(mock_result)

        # 检查是否有文件上传
        if 'video' not in request.files:
            return jsonify({
                "success": False,
                "message": "未找到上传的视频文件"
            }), 400  # Bad Request

        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({
                "success": False,
                "message": "没有选择视频文件"
            }), 400  # Bad Request

        # 保存上传的视频文件
        filename = f"{uuid.uuid4()}{os.path.splitext(secure_filename(video_file.filename))[1]}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        video_file.save(filepath)

        logger.info(f"视频已保存到: {filepath}")

        # 调用动作分析工具
        try:
            # 直接调用工具函数而不是通过Agent
            # result = analyze_exercise_video_tool(video_path=filepath, exercise_type=exercise_type)
            result = analyze_exercise_video_tool.invoke({"video_path": filepath, "exercise_type": exercise_type})

            # 添加视频文件路径到结果中
            # result["video_path"] = filepath # analyze_exercise_video_tool 的结果可能已经包含了更合适的路径或处理后的视频路径

            # 确保 report_path 和 processed_video_path (如果分析工具提供) 也被传递
            # tool的返回结果是 result, 它本身就是一个字典，包含了 success, message, exercise_type, counter, errors_detected, report_path
            # 我们需要确保原始视频的路径（filepath）和处理后的报告路径都包含在最终响应中

            final_response = result.copy() # 从工具的返回结果开始

            # 如果工具没有返回 video_path (例如，它返回的是处理后的视频路径，或者没有视频输出)
            # 我们可以选择添加原始上传视频的路径，或者让工具的返回结果决定视频路径
            if "video_path" not in final_response and filepath: # "video_path" might be the processed one
                 final_response["uploaded_video_path"] = filepath # 原始上传的视频路径
            
            # 如果工具返回了 report_path, 它已经在 final_response 中了
            # 现在我们基于 report_path 构建 report_url
            if final_response.get("success") and final_response.get("report_path"):
                report_filename = os.path.basename(final_response["report_path"])
                # Ensure request.host_url ends with a '/' for proper joining if needed,
                # or construct carefully. request.host_url includes scheme and host.
                base_url = request.host_url.rstrip('/') 
                final_response["report_url"] = f"{base_url}/reports/{report_filename}"
            else:
                final_response["report_url"] = None
            
            # 如果工具返回了处理后的视频路径 (例如，名为 processed_video_path), 它也应该在 final_response 中

            return jsonify(final_response)
        except Exception as tool_error:
            logger.error(f"动作分析工具执行失败: {tool_error}", exc_info=True)
            return jsonify({
                "success": False,
                "message": f"动作分析失败: {str(tool_error)}"
            }), 500  # Internal Server Error

    except Exception as e:
        logger.error(f"处理动作分析请求时出错: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"服务器错误: {str(e)}"
        }), 500  # Internal Server Error

@app.route('/reports/<path:filename>', methods=['GET'])
def serve_report(filename):
    """提供HTML报告文件"""
    logger.info(f"尝试提供报告文件: {filename} from {app.config['REPORTS_FOLDER']}")
    try:
        return send_from_directory(app.config['REPORTS_FOLDER'], filename)
    except FileNotFoundError:
        logger.error(f"报告文件未找到: {filename}")
        return jsonify({"success": False, "message": "Report not found"}), 404

@app.route('/get-analysis-reports', methods=['GET'])
def get_analysis_reports():
    """获取分析报告列表"""
    logger.info(f"Request for /get-analysis-reports received from {request.remote_addr}")
    reports_dir = app.config['REPORTS_FOLDER']
    report_files_data = []
    try:
        filenames = os.listdir(reports_dir)
        for filename in filenames:
            if filename.endswith(".html"):
                filepath = os.path.join(reports_dir, filename)
                try:
                    # Remove .html extension and split by underscore
                    # e.g., "深蹲_训练报告_20250529_232324.html"
                    name_parts = filename[:-5].split('_') 
                    
                    exercise_type = "Unknown"
                    date_str_from_file = "Unknown Date"

                    if len(name_parts) > 0:
                        exercise_type = name_parts[0] # e.g., "深蹲"
                    
                    # Try to parse date and time assuming YYYYMMDD_HHMMSS at the end of name_parts
                    # For "深蹲_训练报告_20250529_232324", parts are ['深蹲', '训练报告', '20250529', '232324']
                    if len(name_parts) >= 3: # Need at least type_date_time or type_text_date_time
                        potential_date_part = name_parts[-2] # e.g., "20250529"
                        potential_time_part = name_parts[-1] # e.g., "232324"

                        if len(potential_date_part) == 8 and potential_date_part.isdigit() and \
                           len(potential_time_part) == 6 and potential_time_part.isdigit():
                            date_str_from_file = (
                                f"{potential_date_part[:4]}-{potential_date_part[4:6]}-{potential_date_part[6:8]} "
                                f"{potential_time_part[:2]}:{potential_time_part[2:4]}:{potential_time_part[4:6]}"
                            )
                        elif len(potential_date_part) == 8 and potential_date_part.isdigit(): # Only date part found
                             date_str_from_file = f"{potential_date_part[:4]}-{potential_date_part[4:6]}-{potential_date_part[6:8]}"
                        # If pattern is different, date_str_from_file remains "Unknown Date" or last valid parse

                    modification_time = os.path.getmtime(filepath)
                    base_url = request.host_url.rstrip('/') 
                    report_url = f"{base_url}/reports/{filename}"

                    report_files_data.append({
                        "filename": filename,
                        "exercise_type": exercise_type,
                        "date_str": date_str_from_file,
                        "timestamp": modification_time, 
                        "report_url": report_url
                    })
                except Exception as e_parse:
                    logger.error(f"Error parsing metadata for report file {filename}: {e_parse}")
                    # Add with default/error values if parsing fails for a specific file
                    report_files_data.append({
                        "filename": filename,
                        "exercise_type": "Parse Error",
                        "date_str": "Parse Error",
                        "timestamp": os.path.getmtime(filepath), # Still need timestamp for sorting
                        "report_url": f"{request.host_url.rstrip('/')}/reports/{filename}"
                    })

        # Sort reports by modification time (newest first)
        report_files_data.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return jsonify({"success": True, "reports": report_files_data})

    except Exception as e_main:
        logger.error(f"Error in /get-analysis-reports endpoint: {e_main}", exc_info=True)
        return jsonify({"success": False, "message": f"Server error while listing reports: {str(e_main)}"}), 500

def main():
    """主函数，启动Flask服务器"""
    try:
        host = os.environ.get("API_HOST", "0.0.0.0")
        port = int(os.environ.get("API_PORT", 5000))

        print(f"\n{'='*50}")
        print(f"FitMirror API 服务器正在启动...")
        print(f"访问地址: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
        print(f"健康检查: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/health")
        print(f"{'='*50}\n")

        app.run(host=host, port=port, debug=True, threaded=True)
    except Exception as e:
        print(f"启动API服务器时出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()