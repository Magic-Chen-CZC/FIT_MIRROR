"""
核心健身动作分析模块
- 接收视频路径和运动类型
- 使用 MediaPipe 进行姿态估计
- 计算角度、判断状态、计数、检测错误
- 返回结构化的分析结果
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import os
import math
from collections import deque
from typing import Dict, Any, Tuple, List, Optional

# 导入本地辅助模块
try:
    from config import (
        EXERCISE_NAMES, PROCESS_EVERY_N_FRAMES, SCREEN_WIDTH, SCREEN_HEIGHT,
        DISPLAY_SCALE, COLOR_MAP, ERROR_PERSISTENCE, MAX_BUFFER_SIZE, ANGLE_THRESHOLD
    )
    # 确保 image_utils 中的 calculate_angle 可用
    from image_utils import (
        calculate_angle as calculate_angle_2d, # 重命名以区分 3D
        cv2AddChineseText, draw_error_annotations, draw_skeleton_lines, draw_ui_elements
    )
    from training_stats import TrainingStats
    # from voice_utils import speak_error_async # 暂时注释掉语音，可在Agent层处理
except ImportError as e:
    print(f"错误：无法导入必要的本地模块: {e}")
    print("请确保 config.py, image_utils.py, training_stats.py 在同一目录下或Python路径中")
    # 提供默认值以允许部分功能运行（或直接退出）
    EXERCISE_NAMES = {"squat": "深蹲", "pushup": "俯卧撑", "situp": "仰卧起坐", "crunch": "卷腹", "jumping_jack": "开合跳"}
    PROCESS_EVERY_N_FRAMES = 1
    SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080
    DISPLAY_SCALE = 0.8
    COLOR_MAP = {"red": (0, 0, 255), "yellow": (0, 255, 255), "green": (0, 255, 0), "purple": (255, 0, 255)}
    ERROR_PERSISTENCE = 3
    MAX_BUFFER_SIZE = 5
    ANGLE_THRESHOLD = {} # 需要为不同运动定义阈值
    # 定义一个简单的 calculate_angle_2d 以防万一
    def calculate_angle_2d(a,b,c):
        a = np.array(a); b = np.array(b); c = np.array(c)
        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = np.abs(radians*180.0/np.pi)
        return angle if angle <= 180.0 else 360-angle
    # 其他函数也需要占位符或默认行为
    class TrainingStats:
        def __init__(self, *args): pass
        def add_record(self, *args): pass
        def update_count(self, *args): pass
        def export_report(self, *args): return "dummy_report.txt"
    def cv2AddChineseText(*args): pass
    def draw_error_annotations(*args): return args[0] # return image
    def draw_skeleton_lines(*args): return args[0] # return image
    def draw_ui_elements(*args): return args[0], None # return image, button_rect

# =====================
# 辅助函数区域 (从 pose_analyzer.py 迁移)
# =====================

# --- 三维向量工具函数 ---
def vec3(a, b):
    """计算三维向量 a->b"""
    return [b.x - a.x, b.y - a.y, b.z - a.z]

def norm3(u):
    """三维向量模长"""
    # 添加 epsilon 防止除零
    norm_sq = u[0]**2 + u[1]**2 + u[2]**2
    return math.sqrt(norm_sq) if norm_sq > 1e-9 else 0

def dot3(u, v):
    """三维向量点积"""
    return u[0]*v[0] + u[1]*v[1] + u[2]*v[2]

def cross3(u, v):
    """三维向量叉积"""
    return [
        u[1]*v[2] - u[2]*v[1],
        u[2]*v[0] - u[0]*v[2],
        u[0]*v[1] - u[1]*v[0]
    ]

def angle3(a, b, c):
    """三维空间角度，返回∠bac，a为顶点，单位为度"""
    v1 = vec3(a, b)
    v2 = vec3(a, c)
    n1 = norm3(v1)
    n2 = norm3(v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    # 防止浮点数精度问题导致 cos_theta 略大于 1 或小于 -1
    cos_theta = dot3(v1, v2) / (n1 * n2)
    cos_theta = max(min(cos_theta, 1.0), -1.0)
    try:
        return math.degrees(math.acos(cos_theta))
    except ValueError:
         # 如果仍然出错（理论上不应该），返回 0
        print(f"Warning: acos ValueError for cos_theta={cos_theta}")
        return 0.0


# --- 二维距离函数 ---
def distance_2d(p1, p2):
    """计算两个 2D 点之间的欧氏距离"""
    # 确保输入是数值类型
    x1, y1 = p1[0], p1[1]
    x2, y2 = p2[0], p2[1]
    return np.sqrt((x1 - x2)**2 + (y1 - y2)**2)

# --- 状态变量 (将在主函数内管理或传入) ---
# error_buffer = {}
# hip_y_history = deque(maxlen=7)
# last_error_message = ""
# last_error_time = 0

# =====================
# 核心分析函数
# =====================

def analyze_exercise_video(video_path: str, exercise_type: str, debug_show_video: bool = False) -> Dict[str, Any]:
    """
    分析给定的视频文件，识别特定运动的次数和错误。

    Args:
        video_path (str): 视频文件的路径。
        exercise_type (str): 运动类型 (e.g., 'squat', 'pushup').
        debug_show_video (bool): 是否显示带有调试信息的视频窗口。

    Returns:
        Dict[str, Any]: 包含分析结果的字典，例如:
            {
                "success": bool,
                "message": str,
                "exercise_type": str,
                "total_frames": int,
                "processed_frames": int,
                "counter": int,
                "errors_detected": List[Dict[str, Any]], # [{"type": str, "count": int, "first_timestamp": float}]
                "report_path": Optional[str],
                "error_details": Optional[str] # 如果处理失败
            }
    """
    print(f"开始分析视频: {video_path}，运动类型: {exercise_type}")

    # --- 初始化 ---
    results = {
        "success": False,
        "message": "",
        "exercise_type": exercise_type,
        "total_frames": 0,
        "processed_frames": 0,
        "counter": 0,
        "errors_detected": [],
        "report_path": None,
        "error_details": None
    }

    if not os.path.exists(video_path):
        results["message"] = "错误：视频文件未找到"
        results["error_details"] = f"路径不存在: {video_path}"
        print(results["message"])
        return results

    if exercise_type not in EXERCISE_NAMES:
        results["message"] = "错误：不支持的运动类型"
        results["error_details"] = f"未知类型: {exercise_type}"
        print(results["message"])
        return results

    exercise_name = EXERCISE_NAMES[exercise_type]
    stats = TrainingStats(exercise_type) # 用于记录和报告

    # MediaPipe 初始化
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils

    # 视频读取
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        results["message"] = "错误：无法打开视频文件"
        results["error_details"] = f"无法打开: {video_path}"
        print(results["message"])
        return results

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    results["total_frames"] = total_frames
    print(f"视频信息: {frame_width}x{frame_height} @ {fps:.2f} FPS, 总帧数: {total_frames}")

    # 分析状态变量
    counter = 0
    stage = None
    feedback = ""
    angle = 0.0
    last_angle = None
    angle_buffer = deque(maxlen=MAX_BUFFER_SIZE)
    error_buffer = {} # 每个错误类型的持续帧数
    detected_errors_log = {} # 记录检测到的错误详情 {"错误类型": {"count": N, "first_timestamp": T}}
    hip_y_history = deque(maxlen=7) # 用于深蹲膝盖检查

    # 调试窗口设置
    window_name = f"FitMirror Analysis - {exercise_name}"
    if debug_show_video:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        display_width = min(frame_width, int(SCREEN_WIDTH * DISPLAY_SCALE))
        display_height = min(frame_height, int(SCREEN_HEIGHT * DISPLAY_SCALE))
        cv2.resizeWindow(window_name, display_width, display_height)

    processed_frames = 0
    start_time = time.time()

    # --- MediaPipe Pose 模型 ---
    with mp_pose.Pose(
        min_detection_confidence=0.5, # 提高置信度要求
        min_tracking_confidence=0.5,
        model_complexity=1 # 0, 1, 2 -> 速度与精度权衡
    ) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("\n视频处理完成或读取结束.")
                break

            processed_frames += 1
            current_time_sec = processed_frames / fps if fps > 0 else 0

            # --- 帧处理 ---
            # 降低处理频率以提高性能 (可选)
            # if processed_frames % PROCESS_EVERY_N_FRAMES != 0:
            #     if debug_show_video and 'image' in locals(): # 显示上一帧处理结果
            #          cv2.imshow(window_name, image)
            #          if cv2.waitKey(1) & 0xFF == ord('q'): break
            #     continue

            # 转换颜色空间 BGR -> RGB
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False # 提高性能

            # 进行姿态检测
            pose_results = pose.process(image_rgb)

            # 转换回 BGR 以便 OpenCV 绘制
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
            image_bgr.flags.writeable = True

            # --- 姿态分析 ---
            if pose_results.pose_landmarks:
                landmarks = pose_results.pose_landmarks.landmark

                valid_pose, pose_feedback = _is_valid_pose(landmarks, mp_pose, exercise_type)
                form_valid, form_feedback, error_annotations = _check_form_errors(
                    landmarks, mp_pose, exercise_type, hip_y_history, error_buffer, current_time_sec, detected_errors_log
                )

                current_angle, additional_angles = _calculate_angles(landmarks, mp_pose, exercise_type)

                # 修改：尝试进行运动分析，即使姿势不完全有效（只要能计算角度）
                if current_angle is not None:
                    new_stage, should_count, motion_feedback, smoothed_angle = _analyze_exercise_motion(
                        landmarks, mp_pose, exercise_type, stage, angle_buffer,
                        last_angle, current_angle, additional_angles
                    )
                    stage = new_stage
                    angle = smoothed_angle
                    last_angle = smoothed_angle
                    
                    # 如果姿势有效，使用运动反馈；否则使用姿势反馈
                    if valid_pose:
                        feedback = motion_feedback
                    else:
                        feedback = f"{pose_feedback} ({motion_feedback})"

                    if should_count:
                        # 修改：无论动作是否正确，只要完成运动周期就计数
                        counter += 1
                        stats.update_count()
                        
                        # 添加质量指标数据，根据动作正确性和姿势有效性调整评分
                        pose_penalty = 0 if valid_pose else 10
                        form_penalty = 0 if form_valid else len(error_annotations) * 10
                        standard_score = max(50, 90 - pose_penalty - form_penalty)
                        stability_score = 85 if abs(smoothed_angle - (last_angle or smoothed_angle)) < 5 else 75
                        depth_score = _calculate_depth_score(exercise_type, smoothed_angle, additional_angles)
                        
                        stats.add_quality_metrics(standard_score, stability_score, depth_score)
                        
                        if valid_pose and form_valid:
                            feedback = f"{motion_feedback} ({counter})"
                        elif valid_pose and not form_valid:
                            feedback = f"动作完成但有错误: {form_feedback} ({counter})"
                        else:
                            feedback = f"动作完成但姿势不佳: {pose_feedback} ({counter})"
                        print(f"\r计数: {counter}", end="")

                    # 优先显示错误反馈（如果有的话）
                    if not form_valid and error_annotations:
                        feedback = form_feedback
                        # 记录错误到 stats - 修复：避免重复记录，只记录新确认的错误
                        new_confirmed_errors = []
                        for error_text, pos, color in error_annotations:
                            if error_text in error_buffer and error_buffer[error_text] == ERROR_PERSISTENCE:
                                new_confirmed_errors.append((error_text, pos, color))
                        if new_confirmed_errors:
                            stats.add_record(new_confirmed_errors)
                    elif not valid_pose:
                        # 如果姿势无效但没有具体的形态错误，显示姿势问题
                        feedback = pose_feedback

                else: # 无法计算角度
                    feedback = "无法识别动作，请调整位置"
                    angle = 0.0

                # --- 调试信息绘制 (如果启用) ---
                if debug_show_video:
                    # 绘制骨架
                    image_bgr = draw_skeleton_lines(image_bgr, landmarks, mp_pose, exercise_type)
                    # 绘制错误标注
                    if error_annotations:
                        image_bgr = draw_error_annotations(image_bgr, error_annotations, COLOR_MAP)
                    # 绘制 UI 元素
                    progress = (processed_frames / total_frames * 100) if total_frames > 0 else None
                    # 计算臀部像素距离
                    if processed_frames == 1:
                        left_hip = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_HIP)
                        right_hip = _get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_HIP)
                        hip_pixel_distance = 0
                        if left_hip and right_hip:
                            hip_pixel_distance = distance_2d([left_hip.x * frame_width, left_hip.y * frame_height], [right_hip.x * frame_width, right_hip.y * frame_height])

                    # 绘制 UI 元素，传递臀部像素距离
                    image_bgr, _ = draw_ui_elements(image_bgr, counter, angle, feedback, progress, hip_pixel_distance)
                    # 绘制原始骨骼点
                    mp_drawing.draw_landmarks(
                        image_bgr, pose_results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
                        mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
                    )
            else:
                # 未检测到姿势
                feedback = "未检测到人体"
                if debug_show_video:
                    image_bgr, _ = draw_ui_elements(image_bgr, counter, 0, feedback, None)


            # --- 显示调试窗口 ---
            if debug_show_video:
                cv2.imshow(window_name, image_bgr)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\n用户手动停止调试窗口.")
                    break

    # --- 清理和收尾 ---
    cap.release()
    if debug_show_video:
        cv2.destroyAllWindows()

    end_time = time.time()
    duration = end_time - start_time
    print(f"\n分析结束. 总耗时: {duration:.2f} 秒.")
    print(f"总帧数: {total_frames}, 处理帧数: {processed_frames}")
    print(f"最终计数: {counter}")

    # 生成报告
    try:
        report_path = stats.export_report()
        results["report_path"] = report_path
        print(f"分析报告已生成: {report_path}")
    except Exception as e:
        print(f"生成报告时出错: {e}")
        results["report_path"] = None


    # 整理错误日志
    results["errors_detected"] = list(detected_errors_log.values())

    results["success"] = True
    results["message"] = f"分析完成，共识别 {counter} 个动作。"
    results["counter"] = counter
    results["processed_frames"] = processed_frames

    return results

def _calculate_depth_score(exercise_type: str, angle: float, additional_angles: Dict[str, float]) -> float:
    """根据运动类型和角度计算动作深度得分"""
    if exercise_type == "squat":
        # 深蹲：膝盖角度越小（蹲得越深），得分越高
        if angle < 90:
            return 100  # 深蹲到位
        elif angle < 120:
            return 90  # 较好深度
        elif angle < 140:
            return 80  # 一般深度
        else:
            return 70  # 深度不够
            
    elif exercise_type == "pushup":
        # 俯卧撑：手肘角度越小（下压越深），得分越高
        if angle < 90:
            return 90
        elif angle < 120:
            return 80
        else:
            return 70
            
    elif exercise_type in ["situp", "crunch"]:
        # 仰卧起坐/卷腹：角度越小（起身越高），得分越高
        if angle < 80:
            return 90
        elif angle < 90:
            return 80
        else:
            return 70
            
    elif exercise_type == "jumping_jack":
        # 开合跳：根据脚踝距离判断
        ankle_width = angle  # 这里angle存储的是脚踝宽度
        if ankle_width > 0.3:
            return 90  # 张开充分
        elif ankle_width > 0.2:
            return 80
        else:
            return 70
            
    return 75  # 默认值

# ============================================================
# 下一步：实现以下内部辅助函数，迁移 pose_analyzer.py 逻辑
# ============================================================
def _get_landmark(landmarks, landmark_enum):
    """安全地获取 landmark，处理可能的索引错误或 None 值"""
    try:
        return landmarks[landmark_enum.value]
    except (IndexError, AttributeError, TypeError):
        return None

def _is_valid_pose(landmarks, mp_pose, exercise_type) -> Tuple[bool, str]:
    """检查姿势是否有效（关键点可见性，朝向）"""
    try:
        # 从 config 加载或使用默认值
        vis_threshold = 0.2  # 可见度阈值
        
        # 确定关键点和朝向要求
        key_point_names = []
        required_facing = None
        
        if exercise_type == "squat":
            key_point_names = ["LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE"]
            required_facing = 'left'
        elif exercise_type == "pushup":
            key_point_names = ["LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST", "LEFT_HIP"] 
            required_facing = 'left'
        elif exercise_type in ["situp", "crunch"]:
            key_point_names = ["LEFT_SHOULDER", "LEFT_HIP", "LEFT_KNEE"]
            required_facing = 'left'
        elif exercise_type == "jumping_jack":
            key_point_names = ["LEFT_SHOULDER", "LEFT_HIP", "LEFT_ANKLE", 
                               "RIGHT_SHOULDER", "RIGHT_HIP", "RIGHT_ANKLE"]
            required_facing = 'front'
            
        # 如果没有定义关键点，返回错误
        if not key_point_names:
             return False, "未定义关键点"

        # 获取并检查关键点可见性
        key_points = []
        for name in key_point_names:
            lm = _get_landmark(landmarks, getattr(mp_pose.PoseLandmark, name, None))
            if lm is None:
                return False, f"无法获取关键点 {name}"
            key_points.append(lm)

        if any(point.visibility < vis_threshold for point in key_points):
            invisible_points = [name for name, point in zip(key_point_names, key_points) if point.visibility < vis_threshold]
            return False, f"无法清晰识别关键点，请调整位置"

        # 检查朝向
        left_shoulder = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER)
        right_shoulder = _get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_SHOULDER)

        if left_shoulder and right_shoulder:
            if required_facing == 'left':
                # 如果要求左侧朝向，右肩可见度不应远超左肩
                if right_shoulder.visibility > vis_threshold + 0.3 and right_shoulder.visibility > left_shoulder.visibility * 1.2:
                    return False, "请保持左侧面对相机"
            elif required_facing == 'front':
                # 如果要求正面朝向，左右肩可见度应相似
                 if abs(left_shoulder.visibility - right_shoulder.visibility) > 0.3:
                     return False, "请正面面对相机"

        return True, ""
    except Exception as e:
        print(f"姿势验证异常: {e}")
        return False, "姿势验证失败"

def _check_pose_stability(landmarks, mp_pose, exercise_type) -> Tuple[bool, str]:
    """检查姿势稳定性（身体平直、对称等）- 可选"""
    # 注意：这个检查可能过于严格，可以根据需要调整或移除
    try:
        thresholds = {
            'shoulder_diff': 0.1,
            'hip_diff': 0.1,
            'ankle_diff': 0.1,
            'shoulder_depth': 1.0,
            'hip_depth': 1.0,
            'ankle_y_diff': 0.1,
            'knee_y_diff': 0.1
        }  # 默认阈值
        
        if exercise_type == "pushup":
            left_shoulder = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER)
            right_shoulder = _get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_SHOULDER)
            left_hip = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_HIP)
            right_hip = _get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_HIP)
            left_ankle = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE)
            right_ankle = _get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_ANKLE)

            if not all([left_shoulder, right_shoulder, left_hip, right_hip, left_ankle, right_ankle]):
                return True, "" # 关键点缺失，跳过检查

            # 检查水平方向的对齐 (Y坐标差异)
            shoulder_diff = abs(left_shoulder.y - right_shoulder.y)
            hip_diff = abs(left_hip.y - right_hip.y)
            ankle_diff = abs(left_ankle.y - right_ankle.y)
            if shoulder_diff > thresholds.get('shoulder_diff', 0.1) or \
               hip_diff > thresholds.get('hip_diff', 0.1) or \
               ankle_diff > thresholds.get('ankle_diff', 0.1):
                return False, "请保持身体水平" # 更通用的提示

        elif exercise_type in ["squat", "situp", "crunch"]:
             left_shoulder = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER)
             right_shoulder = _get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_SHOULDER)
             left_hip = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_HIP)
             right_hip = _get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_HIP)

             if not all([left_shoulder, right_shoulder, left_hip, right_hip]):
                 return True, "" # 关键点缺失，跳过检查

             # 检查深度方向的对齐 (Z坐标差异) - 注意Z坐标可能不可靠
             # shoulder_depth = abs(left_shoulder.z - right_shoulder.z)
             # hip_depth = abs(left_hip.z - right_hip.z)
             # if shoulder_depth > thresholds.get('shoulder_depth', 1.0) or \
             #    hip_depth > thresholds.get('hip_depth', 1.0):
             #     return False, "请保持躯干稳定，避免扭转"

        elif exercise_type == "jumping_jack":
            left_ankle = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE)
            right_ankle = _get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_ANKLE)
            left_knee = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_KNEE)
            right_knee = _get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_KNEE)

            if not all([left_ankle, right_ankle, left_knee, right_knee]):
                 return True, "" # 关键点缺失，跳过检查

            # 检查Y坐标对称性
            ankle_y_diff = abs(left_ankle.y - right_ankle.y)
            knee_y_diff = abs(left_knee.y - right_knee.y)
            if ankle_y_diff > thresholds.get('ankle_y_diff', 0.1) or \
               knee_y_diff > thresholds.get('knee_y_diff', 0.1):
                return False, "请保持跳跃动作对称"

        return True, ""
    except Exception as e:
        print(f"稳定性检查异常: {e}")
        return True, "" # 出现异常时，默认稳定

def _calculate_angles(landmarks, mp_pose, exercise_type) -> Tuple[Optional[float], Dict[str, float]]:
    """计算主要角度和附加角度"""
    current_angle = None
    additional_angles = {}

    try:
        # 根据运动类型计算不同的角度
        if exercise_type == "squat":
            # 深蹲：计算膝关节角度，处理膝盖内扣情况
            hip = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_HIP)
            knee = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_KNEE)
            ankle = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE)
            
            if hip and knee and ankle:
                hip_pos = [hip.x, hip.y]
                knee_pos = [knee.x, knee.y]
                ankle_pos = [ankle.x, ankle.y]
                
                # 标准2D角度计算
                standard_angle = calculate_angle_2d(hip_pos, knee_pos, ankle_pos)
                
                # 检测膝盖内扣并添加调试信息，但不修改角度计算
                right_knee = _get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_KNEE)
                right_ankle = _get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_ANKLE)
                
                is_knee_valgus = False
                if right_knee and right_ankle:
                    # 检查膝盖内扣
                    left_knee_2d = [knee.x, knee.y]
                    right_knee_2d = [right_knee.x, right_knee.y]
                    left_ankle_2d = [ankle.x, ankle.y]
                    right_ankle_2d = [right_ankle.x, right_ankle.y]
                    
                    knee_dist = distance_2d(left_knee_2d, right_knee_2d)
                    ankle_dist = distance_2d(left_ankle_2d, right_ankle_2d)
                    
                    # 膝盖内扣检测阈值（保持检测，但不修改角度）
                    valgus_threshold = 0.95
                    min_ankle_dist = 0.05
                    
                    if ankle_dist > min_ankle_dist:
                        ratio = knee_dist / ankle_dist
                        is_knee_valgus = ratio < valgus_threshold
                        
                        # 添加调试输出，比较膝盖内扣时的角度
                        if is_knee_valgus:
                            print(f"[膝盖内扣检测] 膝盖距离比例: {ratio:.3f}, 角度: {standard_angle:.1f}°")
                
                # 直接使用标准角度，不进行修正
                current_angle = standard_angle
                
                # 计算髋部角度 (3D) 作为附加角度
                hip_angle = angle3(hip, knee, _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER))
                additional_angles["hip_angle"] = hip_angle
            
        elif exercise_type == "pushup":
            # 俯卧撑：计算手肘角度 (2D) 作为主要角度
            shoulder = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER)
            elbow = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ELBOW)
            wrist = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_WRIST)
            
            if shoulder and elbow and wrist:
                shoulder_pos = [shoulder.x, shoulder.y]
                elbow_pos = [elbow.x, elbow.y]
                wrist_pos = [wrist.x, wrist.y]
                current_angle = calculate_angle_2d(shoulder_pos, elbow_pos, wrist_pos)
                
                # 计算身体直线性 (3D) 作为附加角度
                hip = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_HIP)
                if hip:
                    ankle = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE)
                    if ankle:
                        body_angle = angle3(hip, shoulder, ankle)
                        additional_angles["body_angle"] = body_angle
            
        elif exercise_type in ["situp", "crunch"]:
            # 仰卧起坐/卷腹：使用肩部-臀部-膝盖的角度
            shoulder = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER)
            hip = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_HIP)
            knee = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_KNEE)
            
            if shoulder and hip and knee:
                shoulder_pos = [shoulder.x, shoulder.y]
                hip_pos = [hip.x, hip.y]
                knee_pos = [knee.x, knee.y]
                current_angle = calculate_angle_2d(shoulder_pos, hip_pos, knee_pos)
            
        elif exercise_type == "jumping_jack":
            # 开合跳：使用脚踝间距作为"角度"
            left_ankle = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_ANKLE)
            right_ankle = _get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_ANKLE)
            
            if left_ankle and right_ankle:
                ankle_width = abs(left_ankle.x - right_ankle.x)
                current_angle = ankle_width  # 在这里，使用宽度代替角度
                
                # 计算手腕间距
                left_wrist = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_WRIST)
                right_wrist = _get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_WRIST)
                
                if left_wrist and right_wrist:
                    hand_distance = distance_2d([left_wrist.x, left_wrist.y], [right_wrist.x, right_wrist.y])
                    additional_angles["hand_distance"] = hand_distance

                # 可能的附加测量：肩部宽度，用于比较上下肢协调性
                left_shoulder = _get_landmark(landmarks, mp_pose.PoseLandmark.LEFT_SHOULDER)
                right_shoulder = _get_landmark(landmarks, mp_pose.PoseLandmark.RIGHT_SHOULDER)
                if left_shoulder and right_shoulder:
                    shoulder_width = abs(left_shoulder.x - right_shoulder.x)
                    additional_angles["shoulder_width"] = shoulder_width

    except Exception as e:
        print(f"角度计算异常: {e}")

    return current_angle, additional_angles

def _analyze_exercise_motion(landmarks, mp_pose, exercise_type, stage, angle_buffer, last_angle, current_angle, additional_angles) -> Tuple[Optional[str], bool, str, float]:
    """分析动作阶段和计数逻辑"""
    new_stage = stage
    should_count = False
    feedback = ""
    smoothed_angle = current_angle if current_angle is not None else 0.0 # 默认使用当前角度

    if current_angle is None:
        return stage, False, "无法计算角度", 0.0 # 如果无法计算角度，不进行分析

    # --- 角度平滑 ---
    angle_buffer.append(current_angle)
    
    # 改进的角度平滑逻辑：
    # 1. 如果缓冲区少于3个值，直接使用当前角度，避免初期误差
    # 2. 使用较小的缓冲区减少滞后
    if len(angle_buffer) < 3:
        smoothed_angle = current_angle
        print(f"[角度调试] 缓冲区初期，使用原始角度: {current_angle:.1f}°")
    else:
        # 使用最近5帧的平均值（而不是全部10帧）
        recent_angles = list(angle_buffer)[-5:]
        smoothed_angle = sum(recent_angles) / len(recent_angles)
        print(f"[角度调试] 原始角度: {current_angle:.1f}°, 平滑角度: {smoothed_angle:.1f}°")

    # --- 为每个运动类型设置阈值 ---
    upper_threshold = 0
    lower_threshold = 0

    # 根据运动类型设置不同阈值
    if exercise_type == "squat":
        upper_threshold = 170  # 站立时膝盖角度阈值
        lower_threshold = 155  # 深蹲底部膝盖角度阈值
    elif exercise_type == "pushup":
        upper_threshold = 160  # 起始位置肘部角度阈值
        lower_threshold = 90   # 底部肘部角度阈值
    elif exercise_type in ["situp", "crunch"]:
        # upper_threshold = 120  # 起始位置躯干角度阈值
        # lower_threshold = 70   # 收缩位置躯干角度阈值
        upper_threshold = 100  # 起始位置躯干角度阈值 
        lower_threshold = 85   # 收缩位置躯干角度阈值
    elif exercise_type == "jumping_jack":
        # 开合跳阈值：脚踝宽度和手腕距离
        # 根据用户要求，将脚踝合拢阈值也根据肩宽调整
        # 从 additional_angles 中获取肩宽
        shoulder_width = additional_angles.get("shoulder_width", 0)
        # 如果获取到肩宽，则动态计算阈值，否则使用一个默认值
        if shoulder_width > 0:
            # 设置为肩宽的一个小比例，例如 0.1 倍
            ankle_closed_threshold = shoulder_width * 0.5
        else:
            ankle_closed_threshold = 0.025 # 默认值，如果无法获取肩宽
        # 根据用户要求，将脚踝分开阈值调整为肩宽的1.5倍
        
        # 如果获取到肩宽，则动态计算阈值，否则使用一个默认值
        if shoulder_width > 0:
            ankle_open_threshold = shoulder_width * 1.5
        else:
            ankle_open_threshold = 0.3 # 默认值，如果无法获取肩宽
        print(ankle_closed_threshold, ankle_open_threshold)
        hand_closed_threshold = 0.07 # 手腕合拢阈值 (适当调低)
        hand_open_threshold = 0.2   # 手腕分开阈值 (适当调低)

    try:
        # --- 开合跳定制计数逻辑 --- (新增)
        if exercise_type == "jumping_jack":
            hand_distance = additional_angles.get("hand_distance", 0)
            ankle_width = smoothed_angle # smoothed_angle 现在是脚踝宽度

            # 调试输出，便于定位问题
            print(f"[JJ调试] ankle_width={ankle_width:.3f}, hand_distance={hand_distance:.3f}, stage={stage}")

            # 定义阶段：closed (脚踝合拢, 手腕合拢/下方), open (脚踝分开, 手腕分开/上方)
            is_closed_pose = ankle_width < ankle_closed_threshold# and hand_distance < hand_closed_threshold
            is_open_pose = ankle_width > ankle_open_threshold# and hand_distance > hand_open_threshold

            stage_a, stage_b = "closed", "open"

            # 判断当前姿势属于哪个阶段
            current_stage = None
            if is_closed_pose:
                current_stage = stage_a
            elif is_open_pose:
                current_stage = stage_b
            # else: current_stage 保持 None，表示在过渡区域

            new_stage = stage # 默认保持当前阶段
            should_count = False
            feedback = ""

            # 状态机逻辑
            if stage is None: # 初始状态
                if current_stage == stage_a:
                    new_stage = stage_a
                    feedback = "已识别到起始合拢姿势，请跳跃并张开手脚"
                elif current_stage == stage_b:
                    new_stage = stage_b
                    feedback = "已识别到张开姿势，请合拢手脚回到起始"
                else:
                    feedback = "请调整到起始姿势 (手脚合拢或分开)"

            elif stage == stage_a: # 当前在 closed 阶段
                if current_stage == stage_b: # 从 closed 进入 open
                    new_stage = stage_b
                    feedback = "张开手脚，保持动作到位"
                elif current_stage == stage_a: # 保持在 closed 阶段
                    feedback = "保持合拢，准备跳跃张开"
                else: # 从 closed 进入过渡区域
                    feedback = "幅度不够，请大幅度张开手脚"

            elif stage == stage_b: # 当前在 open 阶段
                if current_stage == stage_a: # 从 open 回到 closed，完成一次动作
                    new_stage = stage_a
                    should_count = True # 在回到 closed 状态时计数
                    feedback = "标准开合跳！已计数"
                elif current_stage == stage_b: # 保持在 open 阶段
                    feedback = "保持张开，准备合拢"
                else: # 从 open 进入过渡区域
                    feedback = "幅度不够，请完全合拢手脚"

            # 如果在过渡区域，保持原阶段反馈
            if current_stage is None:
                 if stage == stage_a:
                     feedback = "幅度不够，请大幅度张开手脚"
                 elif stage == stage_b:
                     feedback = "幅度不够，请完全合拢手脚"
                 else:
                     feedback = "请调整到起始姿势..."

        # --- 其他运动类型的原有计数逻辑 --- (保留)
        else:
             # 根据运动类型调整阈值比较方式
            is_width_based = False # 其他运动类型不是基于宽度

            # 判断当前处于哪个理论区域
            in_a_zone = (smoothed_angle > upper_threshold) if not is_width_based else (smoothed_angle < upper_threshold)
            in_b_zone = (smoothed_angle < lower_threshold) if not is_width_based else (smoothed_angle > lower_threshold)
            print(f"[JJ调试] smoothed_angle={smoothed_angle:.3f}, stage={stage}")
            # 根据运动类型定制阶段名称
            if exercise_type == "squat":
                stage_a, stage_b = "stand", "squat"
            elif exercise_type == "pushup":
                stage_a, stage_b = "up", "down"
            elif exercise_type in ["situp", "crunch"]:
                stage_a, stage_b = "down", "up"
            else:
                stage_a, stage_b = "stage_a", "stage_b"

            # 根据角度区域判断阶段
            if in_a_zone:
                if stage == stage_b or stage is None: # 从 B 区回到 A 区，或初始状态
                    new_stage = stage_a
                    if exercise_type == "squat":
                        feedback = "站姿识别成功，可以下蹲"
                    elif exercise_type == "pushup":
                        feedback = "准备下压，保持手肘贴近身体"
                    elif exercise_type in ["situp", "crunch"]:
                        feedback = "准备起身，收紧腹肌"
                    else:
                        feedback = "进入起始/结束阶段"
                else: # 保持在 A 区
                    if exercise_type == "squat":
                        feedback = "准备开始深蹲"
                    elif exercise_type == "pushup":
                        feedback = "准备下压，保持身体平直"
                    elif exercise_type in ["situp", "crunch"]:
                        feedback = "收紧腹肌，准备起身"
                    else:
                        feedback = "保持起始/结束阶段"
            elif in_b_zone:
                if stage == stage_a: # 从 A 区进入 B 区，完成一次动作
                    new_stage = stage_b
                    should_count = True
                    if exercise_type == "squat":
                        feedback = "深蹲完成！"
                    elif exercise_type == "pushup":
                        feedback = "标准俯卧撑，继续保持！"
                    elif exercise_type in ["situp", "crunch"]:
                        feedback = "标准仰卧起坐！"
                    else:
                        feedback = "动作完成!"
                else: # 保持在 B 区
                    if exercise_type == "squat":
                        feedback = "下蹲姿势良好"
                    elif exercise_type == "pushup":
                        feedback = "保持住，确保身体平直"
                    elif exercise_type in ["situp", "crunch"]:
                        feedback = "保持住，充分收缩腹肌"
                    else:
                        feedback = "保持动作中间阶段"
            else: # 在中间过渡区域
                if stage == stage_a:
                    if exercise_type == "squat":
                        feedback = "继续下蹲"
                    elif exercise_type == "pushup":
                        feedback = "继续下压，保持手肘贴近身体"
                    elif exercise_type in ["situp", "crunch"]:
                        feedback = "继续用力，抬高上半身"
                    else:
                        feedback = "继续动作..."
                elif stage == stage_b:
                    if exercise_type == "squat":
                        feedback = "回到站立位置"
                    elif exercise_type == "pushup":
                        feedback = "回到起始位置，挺胸收腹"
                    elif exercise_type in ["situp", "crunch"]:
                        feedback = "慢慢放低身体，准备下一个"
                    else:
                        feedback = "返回起始/结束阶段..."
                else: # 初始状态在中间区域
                     feedback = "准备开始..."
                     new_stage = stage_a # 假设从 A 区开始

            # 检查附加角度限制 (例如俯卧撑中的身体直线要求)
            if exercise_type == "pushup" and "body_angle" in additional_angles:
                body_angle = additional_angles["body_angle"]
                if abs(body_angle - 180) >= 20:  # 身体偏离直线超过20度
                    feedback = "请保持身体平直，不要耸肩"

    except Exception as e:
        print(f"动作分析异常: {e}")
        feedback = "动作分析错误"

    return new_stage, should_count, feedback, smoothed_angle

def _check_form_errors(landmarks, mp_pose, exercise_type, hip_y_history: deque, error_buffer: dict, current_time_sec: float, detected_errors_log: dict) -> Tuple[bool, str, List[Tuple[str, Tuple[float, float], str]]]:
    """检查形态错误"""
    current_errors_details = [] # 存储 (错误文本, 标注位置, 颜色)
    form_valid = True
    feedback = ""

    try:
        # --- 通用关键点获取 ---
        lm_dict = {name: _get_landmark(landmarks, getattr(mp_pose.PoseLandmark, name, None)) 
                 for name in mp_pose.PoseLandmark.__members__}

        # --- 深蹲错误检测 ---
        if exercise_type == "squat":
            # === 膝盖检查 ===
            left_knee = lm_dict.get("LEFT_KNEE")
            right_knee = lm_dict.get("RIGHT_KNEE")
            left_ankle = lm_dict.get("LEFT_ANKLE")
            right_ankle = lm_dict.get("RIGHT_ANKLE")
            left_hip = lm_dict.get("LEFT_HIP")
            right_hip = lm_dict.get("RIGHT_HIP")
            left_shoulder = lm_dict.get("LEFT_SHOULDER")
            right_shoulder = lm_dict.get("RIGHT_SHOULDER")

            if all([left_knee, right_knee, left_ankle, right_ankle, left_hip, right_hip]):
                # 更新髋关节 Y 坐标历史
                current_hip_y = (left_hip.y + right_hip.y) / 2
                hip_y_history.append(current_hip_y)

                # 判断是否在深蹲底部附近进行检查
                should_check_knees = False
                if len(hip_y_history) == hip_y_history.maxlen:
                    highest_y = min(hip_y_history) # Y值最小的是最高点
                    lowest_y = max(hip_y_history)  # Y值最大的是最低点
                    descent_distance = current_hip_y - highest_y
                    avg_knee_y = (left_knee.y + right_knee.y) / 2
                    thigh_y_projection = avg_knee_y - current_hip_y # 大腿Y轴投影

                    # 阈值
                    desc_thresh_ratio = 1.0 / 3.0  # 下蹲深度阈值比例
                    lowest_prox_thresh = 0.03  # 接近最低点的容差
                    
                    has_descended_enough = thigh_y_projection > 0 and (descent_distance > desc_thresh_ratio * thigh_y_projection)
                    is_near_lowest = abs(current_hip_y - lowest_y) < lowest_prox_thresh

                    should_check_knees = has_descended_enough and is_near_lowest

                if should_check_knees:
                    # 使用 2D 距离检查膝盖内扣/外翻
                    left_knee_2d = [left_knee.x, left_knee.y]
                    right_knee_2d = [right_knee.x, right_knee.y]
                    left_ankle_2d = [left_ankle.x, left_ankle.y]
                    right_ankle_2d = [right_ankle.x, right_ankle.y]

                    knee_dist = distance_2d(left_knee_2d, right_knee_2d)
                    ankle_dist = distance_2d(left_ankle_2d, right_ankle_2d)

                    valgus_thresh = 0.95  # 膝盖内扣阈值
                    varus_thresh = 1.3   # 膝盖外翻阈值
                    min_ankle_dist = 0.05  # 最小脚踝距离阈值

                    if ankle_dist > min_ankle_dist:
                        ratio = knee_dist / ankle_dist
                        knee_center_pos = ((left_knee.x + right_knee.x)/2, (left_knee.y + right_knee.y)/2)
                        if ratio < valgus_thresh:
                            current_errors_details.append(("膝盖内扣", knee_center_pos, "red"))
                        elif ratio > varus_thresh:
                            current_errors_details.append(("膝盖外翻", knee_center_pos, "yellow"))

                # === 重心检查 ===
                ankle_center_x = (left_ankle.x + right_ankle.x) / 2
                hip_center_x = (left_hip.x + right_hip.x) / 2
                shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
                gravity_center_x = (hip_center_x + shoulder_center_x) / 2
                gravity_pos_y = (left_hip.y + right_hip.y) / 2
                
                gravity_offset_threshold = 0.12  # 重心偏移阈值

                if abs(gravity_center_x - ankle_center_x) > gravity_offset_threshold:
                    gravity_pos = (gravity_center_x, gravity_pos_y)
                    if gravity_center_x > ankle_center_x:
                        current_errors_details.append(("重心过于靠后", gravity_pos, "purple"))
                    else:
                        current_errors_details.append(("重心过于靠前", gravity_pos, "purple"))
        
        # --- 俯卧撑错误检测 ---
        elif exercise_type == "pushup":
            left_shoulder = lm_dict.get("LEFT_SHOULDER")
            right_shoulder = lm_dict.get("RIGHT_SHOULDER")
            left_elbow = lm_dict.get("LEFT_ELBOW")
            right_elbow = lm_dict.get("RIGHT_ELBOW")
            left_hip = lm_dict.get("LEFT_HIP")
            right_hip = lm_dict.get("RIGHT_HIP")
            
            if all([left_shoulder, right_shoulder, left_elbow, right_elbow, left_hip, right_hip]):
                # 肩部下沉检查
                shoulder_height = (left_shoulder.y + right_shoulder.y) / 2
                elbow_height = (left_elbow.y + right_elbow.y) / 2
                if shoulder_height > elbow_height:  # 肩部下沉
                    shoulder_pos = ((left_shoulder.x + right_shoulder.x)/2, shoulder_height)
                    current_errors_details.append(("肩部下沉", shoulder_pos, "red"))
                
                # 臀部下沉或抬高
                left_ankle = lm_dict.get("LEFT_ANKLE")
                if left_ankle:
                    hip_shoulder_line = abs(left_hip.y - left_shoulder.y)
                    if hip_shoulder_line > 0.12:  # 臀部下沉/抬高
                        hip_pos = ((left_hip.x + right_hip.x)/2, (left_hip.y + right_hip.y)/2)
                        if left_hip.y > left_shoulder.y:
                            current_errors_details.append(("臀部下沉", hip_pos, "yellow"))
                        else:
                            current_errors_details.append(("臀部抬高", hip_pos, "yellow"))
        
        # --- 仰卧起坐/卷腹错误检测 ---
        elif exercise_type in ["situp", "crunch"]:
            left_shoulder = lm_dict.get("LEFT_SHOULDER")
            right_shoulder = lm_dict.get("RIGHT_SHOULDER")
            left_hip = lm_dict.get("LEFT_HIP")
            right_hip = lm_dict.get("RIGHT_HIP")
            left_knee = lm_dict.get("LEFT_KNEE")
            
            if all([left_shoulder, right_shoulder, left_hip, right_hip, left_knee]):
                # 躯干扭转检查
                shoulder_hip_diff = abs(distance_2d([left_shoulder.x, left_shoulder.y], 
                                                  [right_shoulder.x, right_shoulder.y]) - 
                                      distance_2d([left_hip.x, left_hip.y], 
                                                [right_hip.x, right_hip.y]))
                if shoulder_hip_diff > 0.12:  # 躯干扭转
                    torso_pos = ((left_shoulder.x + right_shoulder.x)/2, (left_shoulder.y + left_hip.y)/2)
                    current_errors_details.append(("躯干扭转", torso_pos, "red"))
                
                # 头部前屈检查
                if left_shoulder.y > left_hip.y:  # 头部前屈
                    head_pos = (left_shoulder.x, left_shoulder.y)
                    current_errors_details.append(("头部前屈", head_pos, "yellow"))
        
        # --- 开合跳错误检测 ---
        # elif exercise_type == "jumping_jack":
        #     left_shoulder = lm_dict.get("LEFT_SHOULDER")
        #     right_shoulder = lm_dict.get("RIGHT_SHOULDER")
        #     left_ankle = lm_dict.get("LEFT_ANKLE")
        #     right_ankle = lm_dict.get("RIGHT_ANKLE")
        #     left_knee = lm_dict.get("LEFT_KNEE")
        #     right_knee = lm_dict.get("RIGHT_KNEE")
        #     left_hip = lm_dict.get("LEFT_HIP") # 获取左臀关键点
        #     right_hip = lm_dict.get("RIGHT_HIP") # 获取右臀关键点
            
            # if all([left_shoulder, right_shoulder, left_ankle, right_ankle, left_knee, right_knee]):
            #     # 动作不对称检查
            #     shoulder_diff = distance_2d([left_shoulder.x, left_shoulder.y], 
            #                               [right_shoulder.x, right_shoulder.y])
            #     ankle_diff = distance_2d([left_ankle.x, left_ankle.y], 
            #                             [right_ankle.x, right_ankle.y])
                
            #     if abs(shoulder_diff - ankle_diff) > 0.15:  # 动作不对称 (调整)
            #         center_pos = ((left_shoulder.x + right_shoulder.x)/2, 
            #                      (left_shoulder.y + right_shoulder.y)/2)
            #         current_errors_details.append(("动作不对称", center_pos, "red"))
                
                # 膝盖弯曲检查 - 使用 3D 角度更准确
                # left_knee_3d_pos = [left_knee.x, left_knee.y, left_knee.z]
                # right_knee_3d_pos = [right_knee.x, right_knee.y, right_knee.z]
                # left_ankle_3d_pos = [left_ankle.x, left_ankle.y, left_ankle.z]
                # right_ankle_3d_pos = [right_ankle.x, right_ankle.y, right_ankle.z]
                # left_shoulder_3d_pos = [left_shoulder.x, left_shoulder.y, left_shoulder.z]
                # right_shoulder_3d_pos = [right_shoulder.x, right_shoulder.y, right_shoulder.z]
                
                # 这里应使用 3D 角度，但为简化我们用 2D
                # left_leg = [left_knee.x - left_ankle.x, left_knee.y - left_ankle.y]
                # right_leg = [right_knee.x - right_ankle.x, right_knee.y - right_ankle.y]
                
                # left_thigh = [left_knee.x - left_hip.x, left_knee.y - left_hip.y] if left_hip else [0, 0]
                # right_thigh = [right_knee.x - right_hip.x, right_knee.y - right_hip.y] if right_hip else [0, 0]
                
                # 用向量的点积估算角度
                # def dot_product(v1, v2):
                #     return v1[0]*v2[0] + v1[1]*v2[1]
                
                # def vector_magnitude(v):
                #     return math.sqrt(v[0]**2 + v[1]**2)
                
                # def angle_between(v1, v2):
                #     dot = dot_product(v1, v2)
                #     mag1 = vector_magnitude(v1)
                #     mag2 = vector_magnitude(v2)
                #     if mag1 * mag2 == 0: return 180.0
                #     cos_angle = dot / (mag1 * mag2)
                #     cos_angle = max(min(cos_angle, 1.0), -1.0)  # 处理浮点误差
                #     return math.degrees(math.acos(cos_angle))
                
                # 估计膝盖角度 (腿与大腿的夹角)
                # left_knee_angle = angle_between(left_leg, left_thigh) if left_hip else 180.0
                # right_knee_angle = angle_between(right_leg, right_thigh) if right_hip else 180.0
                
                # if left_knee_angle < 155 or right_knee_angle < 155:  # 膝盖弯曲阈值 (调整)
                #     knee_pos = ((left_knee.x + right_knee.x)/2, (left_knee.y + right_knee.y)/2)
                #     current_errors_details.append(("膝盖弯曲", knee_pos, "yellow"))

        # --- 错误缓冲和最终判断 ---
        final_errors = [] # 存储确认的错误 (error_text, pos, color)
        current_error_texts = {e[0] for e in current_errors_details}

        # 增加新检测到的错误的计数
        for error_text, pos, color in current_errors_details:
            error_buffer[error_text] = error_buffer.get(error_text, 0) + 1
            if error_buffer[error_text] >= ERROR_PERSISTENCE:
                final_errors.append((error_text, pos, color))
                # 更新错误日志 - 修复：只在第一次达到阈值时计数，避免重复计数
                if error_text not in detected_errors_log:
                    detected_errors_log[error_text] = {"type": error_text, "count": 0, "first_timestamp": current_time_sec}
                # 只在刚刚达到持续阈值时计数一次，避免重复计数
                if error_buffer[error_text] == ERROR_PERSISTENCE:
                    detected_errors_log[error_text]["count"] += 1

        # 减少未检测到的错误的计数 - 修复：使用更保守的减少策略
        for error_text in list(error_buffer.keys()):
            if error_text not in current_error_texts:
                error_buffer[error_text] = max(0, error_buffer[error_text] - 1)
                if error_buffer[error_text] <= 0:
                    del error_buffer[error_text]

        if final_errors:
            form_valid = False
            feedback = "注意: " + ", ".join([e[0] for e in final_errors])
        else:
            form_valid = True
            feedback = "" # 没有稳定错误时，反馈由动作分析函数提供

        return form_valid, feedback, final_errors

    except Exception as e:
        print(f"错误检测异常: {e}")
        return True, "", [] # 异常时，默认有效，无错误


# --- 可选：添加一个简单的测试入口 ---
if __name__ == '__main__':
    print("运行 fitness_analyzer.py 测试...")
    # 选择一个测试视频和类型
    test_video = "situp.mp4" # <--- 修改为你的测试视频路径
    test_type = "situp" # <--- 修改为对应的运动类型 (squat, pushup, situp, crunch, jumping_jack)

    if not os.path.exists(test_video):
         print(f"错误：测试视频文件未找到: {test_video}")
         print("请在代码中修改 'test_video' 变量为有效的视频路径。")
    else:
        # 运行分析并显示调试窗口
        analysis_result = analyze_exercise_video(test_video, test_type, debug_show_video=True)

        print("\n--- 分析结果 ---")
        import json
        print(json.dumps(analysis_result, indent=4, ensure_ascii=False))
