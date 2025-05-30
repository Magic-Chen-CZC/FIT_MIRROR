"""
图像处理工具模块 - 处理图像渲染和分析功能
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def calculate_angle(a, b, c):
    """计算三个点形成的角度。
    
    Args:
        a: 第一个点的坐标 [x, y]
        b: 角度顶点的坐标 [x, y]
        c: 第三个点的坐标 [x, y]
    
    Returns:
        float: 角度值（0-180度）
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    calculated_angle = np.abs(radians*180.0/np.pi)

    if calculated_angle > 180.0:
        calculated_angle = 360 - calculated_angle

    return calculated_angle

def cv2AddChineseText(img, text, position, textColor=(0, 255, 0), textSize=30):
    """在图片上添加中文文字"""
    if isinstance(img, np.ndarray):
        img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    
    draw = ImageDraw.Draw(img)
    try:
        # 首先尝试使用项目目录中的字体文件
        fontStyle = ImageFont.truetype("simhei.ttf", textSize, encoding="utf-8")
    except IOError:
        # 如果失败，尝试使用系统字体
        try:
            fontStyle = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", textSize, encoding="utf-8")
        except IOError:
            # 如果仍然失败，使用默认字体
            fontStyle = ImageFont.load_default()
            print("[警告] 无法加载指定字体，使用默认字体")
    
    draw.text(position, text, textColor, font=fontStyle)
    
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

def draw_error_annotations(image, error_annotations, color_map=None):
    """在图像上绘制错误标注
    
    Args:
        image: 输入图像
        error_annotations: 错误标注列表，每项为(错误文本, 错误位置, 错误颜色)
        color_map: 颜色映射字典
        
    Returns:
        绘制了错误标注的图像
    """
    if color_map is None:
        color_map = {
            "red": (0, 0, 255),
            "yellow": (0, 255, 255),
            "orange": (0, 165, 255),
            "purple": (255, 0, 255)
        }
        
    h, w, _ = image.shape
    for error_text, error_pos, error_color in error_annotations:
        pos_x = int(error_pos[0] * w)
        pos_y = int(error_pos[1] * h)
        
        # 创建半透明背景
        overlay = image.copy()
        # 绘制标注框和文字
        cv2.rectangle(overlay,
                    (pos_x - 160, pos_y - 80),
                    (pos_x + 120, pos_y),
                    color_map[error_color],
                    -1)
        # 设置透明度
        image = cv2.addWeighted(overlay, 0.4, image, 0.6, 0)
        # 添加文字
        image = cv2AddChineseText(image, error_text, (pos_x - 150, pos_y - 70),
                                (255, 255, 255), 60)
        
        # 绘制指向线
        cv2.line(image,
                (pos_x, pos_y),
                (pos_x, pos_y + 20),
                color_map[error_color],
                2)
    
    return image

def draw_skeleton_lines(image, landmarks, mp_pose, exercise_type):
    """根据运动类型在图像上绘制骨骼线
    
    Args:
        image: 输入图像
        landmarks: 关键点坐标
        mp_pose: MediaPipe Pose对象
        exercise_type: 运动类型
        
    Returns:
        绘制了骨骼线的图像
    """
    h, w, _ = image.shape
    
    if exercise_type == "squat":
        # 深蹲：绘制髋关节-膝盖-脚踝线
        hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
               landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
        knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
                landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
        ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
        
        knee_point = (int(knee[0] * w), int(knee[1] * h))
        hip_point = (int(hip[0] * w), int(hip[1] * h))
        ankle_point = (int(ankle[0] * w), int(ankle[1] * h))
        
        cv2.line(image, knee_point, hip_point, (0, 0, 255), 3)
        cv2.line(image, knee_point, ankle_point, (0, 0, 255), 3)
        
    elif exercise_type == "pushup":
        # 俯卧撑：绘制肩膀-肘部-手腕线
        shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                  landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
        elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
        wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
        
        shoulder_point = (int(shoulder[0] * w), int(shoulder[1] * h))
        elbow_point = (int(elbow[0] * w), int(elbow[1] * h))
        wrist_point = (int(wrist[0] * w), int(wrist[1] * h))
        
        cv2.line(image, elbow_point, shoulder_point, (0, 0, 255), 3)
        cv2.line(image, elbow_point, wrist_point, (0, 0, 255), 3)
        
    elif exercise_type in ["situp", "crunch"]:
        # 仰卧起坐/卷腹：绘制肩膀-臀部-膝盖线
        shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                  landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
        hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
              landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
        knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
               landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
        
        shoulder_point = (int(shoulder[0] * w), int(shoulder[1] * h))
        hip_point = (int(hip[0] * w), int(hip[1] * h))
        knee_point = (int(knee[0] * w), int(knee[1] * h))
        
        cv2.line(image, hip_point, shoulder_point, (0, 0, 255), 3)  # 躯干线
        cv2.line(image, hip_point, knee_point, (0, 255, 0), 3)  # 腿部参考线
        
    elif exercise_type == "jumping_jack":
        # 开合跳：绘制肩膀线和脚踝线
        left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                        landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
        right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                         landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
        left_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                     landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
        right_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x,
                      landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]
        
        left_shoulder_point = (int(left_shoulder[0] * w), int(left_shoulder[1] * h))
        right_shoulder_point = (int(right_shoulder[0] * w), int(right_shoulder[1] * h))
        left_ankle_point = (int(left_ankle[0] * w), int(left_ankle[1] * h))
        right_ankle_point = (int(right_ankle[0] * w), int(right_ankle[1] * h))
        
        cv2.line(image, left_shoulder_point, right_shoulder_point, (0, 0, 255), 3)  # 肩部线
        cv2.line(image, left_ankle_point, right_ankle_point, (0, 255, 0), 3)  # 脚踝线
    
    return image

def draw_ui_elements(image, counter, angle, feedback, progress=None, hip_pixel_distance=0):
    """在图像上绘制UI元素（仅保留计数和结束按钮）"""
    # 根据臀部像素距离动态计算文本大小
    # 目标是人越大（臀部像素距离越大）尺寸越小，人越小（臀部像素距离越小）尺寸越大
    # 使用一个反比例关系，例如：字体大小 = K / 臀部像素距离 + C
    # 我们可以尝试一个简单的反比例模型： font_size = K / hip_pixel_distance + C
    # 假设当臀部距离很小时（例如 50 像素），字体接近最大值 80
    # 当臀部距离很大时（例如 400 像素），字体接近最小值 20
    # 我们可以尝试一个线性映射： hip_pixel_distance -> font_size
    # (50, 80), (400, 20)
    # 斜率 m = (20 - 80) / (400 - 50) = -60 / 350 ≈ -0.17
    # 截距 c = 80 - (-0.17) * 50 = 80 + 8.5 = 88.5
    # font_size = -0.17 * hip_pixel_distance + 88.5

    max_font_size_limit = 80 # 字体大小上限
    min_font_size_limit = 20 # 字体大小下限

    # 使用线性反比关系
    scaling_factor = -0.17
    base_offset = 88.5

    if hip_pixel_distance > 0:
        dynamic_font_size = int(base_offset + hip_pixel_distance * scaling_factor)
        # 限制字体大小在合理范围内
        font_size = max(min_font_size_limit, min(max_font_size_limit, dynamic_font_size))
    else:
        font_size = 30 # 如果无法获取臀部距离，使用默认大小

    # 绘制圆形背景
    center_x = 200 # 圆心X坐标
    center_y = 200 # 圆心Y坐标
    radius = int(font_size * 1.5) # 半径根据字体大小调整
    background_color = (128, 128, 128) # 灰色背景
    cv2.circle(image, (center_x, center_y), radius, background_color, -1)

    # 显示 COUNTER 文字
    counter_text = "COUNTER"
    counter_font_size = max(15, int(font_size * 0.7)) # COUNTER文字大小
    # 计算文本大小以居中 (近似)
    # 注意：cv2.getTextSize 对于中文字符可能不准确，这里先用一个近似值或假设
    # 更精确的做法可能需要依赖PIL或其他库，或者预估一个偏移量
    counter_text_size, _ = cv2.getTextSize(counter_text, cv2.FONT_HERSHEY_SIMPLEX, counter_font_size/30, 2) # 使用OpenCV字体估算大小
    counter_text_x = center_x - counter_text_size[0] // 2 + 37
    counter_text_y = center_y - int(radius * 0.5) 
    image = cv2AddChineseText(image, counter_text, (counter_text_x, counter_text_y), (255, 255, 255), counter_font_size)

    # 显示计数
    count_str = f"{counter}"
    count_font_size = font_size # 计数数字使用动态计算的字体大小
    count_text_size, _ = cv2.getTextSize(count_str, cv2.FONT_HERSHEY_SIMPLEX, count_font_size/30, 2) # 使用OpenCV字体估算大小
    count_text_x = center_x - count_text_size[0] // 2 + 5
    count_text_y = center_y + count_text_size[1] // 2 - 20# 调整Y位置使其在圆心下方
    image = cv2AddChineseText(image, count_str, (count_text_x, count_text_y), (255, 255, 255), count_font_size)

    # 不再显示角度、动作指导、进度等内容
    # 保留结束按钮
    h, w, _ = image.shape
    button_width = int(font_size * 3.4)  #120
    button_height = int(font_size * 1) #40
    button_x = 30
    button_y = h - 100
    overlay = image.copy()
    cv2.rectangle(overlay, 
                (button_x, button_y), 
                (button_x + button_width, button_y + button_height),
                (0, 0, 200),
                -1)
    image = cv2.addWeighted(overlay, 0.7, image, 0.3, 0)
    image = cv2AddChineseText(image, "结束分析", (button_x + 25, button_y + 12), (255, 255, 255), counter_font_size)
    button_rect = (button_x, button_y, button_x + button_width, button_y + button_height)
    return image, button_rect