"""
健身动作识别系统配置文件
"""

# 科大讯飞语音合成API配置
IFLYTEK_APP_ID = "6061e2ba"  # 需要填写你的科大讯飞AppID
IFLYTEK_API_KEY = "448b0e4c05e3df7ec02a9ed791229e4d"  # 需要填写你的科大讯飞APIKey 
IFLYTEK_API_SECRET = "MWNkMzdkMWUwYjRjZjRjOWE2MWI0NTgy"  # 需要填写你的科大讯飞APISecret

# 错误检测配置
ERROR_PERSISTENCE = 3  # 错误持续次数阈值，只有连续检测到ERROR_PERSISTENCE次才报告
ERROR_COOLDOWN = 0.5  # 错误记录冷却时间，避免重复记录相似错误

# 视频处理配置
PROCESS_EVERY_N_FRAMES = 1  # 每隔多少帧处理一次，设为1表示每帧都处理
MAX_BUFFER_SIZE = 10  # 角度缓冲区大小，用于平滑处理
ANGLE_THRESHOLD = 5.0  # 角度变化阈值，防止微小抖动导致状态变化

# UI配置
SCREEN_WIDTH = 1920  # 假定普通屏幕分辨率
SCREEN_HEIGHT = 1080
DISPLAY_SCALE = 0.8  # 显示窗口占屏幕的比例

# 颜色映射
COLOR_MAP = {
    "red": (0, 0, 255),
    "yellow": (0, 255, 255),
    "orange": (0, 165, 255),
    "purple": (255, 0, 255),
    "green": (0, 255, 0),
    "blue": (255, 0, 0)
}

# 运动类型映射
EXERCISE_NAMES = {
    "squat": "深蹲",
    "crunch": "卷腹",
    "situp": "仰卧起坐",
    "jumping_jack": "开合跳",
    "pushup": "俯卧撑"
}