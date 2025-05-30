"""
语音处理工具模块 - 处理语音合成及播放功能
"""

import time
import os
import json
import base64
import hashlib
import hmac
import threading
import pygame
from urllib.parse import urlparse, urlencode
import websocket

try:
    from config import IFLYTEK_APP_ID, IFLYTEK_API_KEY, IFLYTEK_API_SECRET
except ImportError:
    # 如果无法导入，使用默认值
    IFLYTEK_APP_ID = ""
    IFLYTEK_API_KEY = ""
    IFLYTEK_API_SECRET = ""

# 初始化pygame以便播放语音
pygame.mixer.init()

def create_url():
    """
    生成科大讯飞语音合成WebSocket请求URL
    """
    if not IFLYTEK_APP_ID or not IFLYTEK_API_KEY or not IFLYTEK_API_SECRET:
        print("警告: 未设置科大讯飞API凭证，语音功能将不可用")
        return None
        
    url = 'wss://tts-api.xfyun.cn/v2/tts'
    host = urlparse(url).netloc
    path = urlparse(url).path
    
    # 生成RFC1123格式的时间戳
    now = time.strftime('%a, %d %b %Y %H:%M:%S %Z', time.localtime())
    now = now.replace('GMT', 'GMT+0800')
    
    # 拼接字符串
    signature_origin = 'host: ' + host + '\n'
    signature_origin += 'date: ' + now + '\n'
    signature_origin += 'GET ' + path + ' HTTP/1.1'
    
    # 进行hmac-sha256加密
    signature_sha = hmac.new(IFLYTEK_API_SECRET.encode('utf-8'), 
                           signature_origin.encode('utf-8'),
                           digestmod=hashlib.sha256).digest()
    
    signature_sha_base64 = base64.b64encode(signature_sha).decode()
    authorization_origin = f'api_key="{IFLYTEK_API_KEY}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode()
    
    # 将请求的鉴权参数组合为字典
    v = {
        "authorization": authorization,
        "date": now,
        "host": host
    }
    # 拼接鉴权参数，生成url
    url = url + '?' + urlencode(v)
    return url

def speak_error_async(text):
    """
    异步调用讯飞TTS API播放错误提示语音
    Args:
        text: 要合成语音的文本内容
    """
    # 新开线程处理语音请求，避免阻塞主线程
    threading.Thread(target=lambda: process_tts(text), daemon=True).start()

def process_tts(text):
    """
    处理科大讯飞TTS请求并播放语音
    Args:
        text: 要合成语音的文本内容
    """
    try:
        print(f"[语音提示]: 准备播报: {text}")
        
        if not IFLYTEK_APP_ID or not IFLYTEK_API_KEY or not IFLYTEK_API_SECRET:
            print("[语音提示]: 未配置科大讯飞API凭证，无法播放语音")
            return
            
        url = create_url()
        if not url:
            return
            
        # 创建临时音频文件路径
        temp_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "fitmirror_tts")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        output_file = os.path.join(temp_dir, f"tts_{int(time.time())}.mp3")
            
        # 构建请求参数
        common_args = {
            "app_id": IFLYTEK_APP_ID
        }
        business_args = {
            "aue": "lame",  # 音频编码，lame表示mp3格式
            "auf": "audio/L16;rate=16000",  # 音频采样率
            "vcn": "aisjiuxu",  # 男声，明显区别于女声xiaoyan
            "tte": "utf8",  # 文本编码
            "speed": 38,  # 语速恢复正常，取值范围：[0,100]
            "volume": 100,  # 增大音量，取值范围：[0,100]
            "pitch": 50,  # 音调，取值范围：[0,100]
        }
        data = {
            "common": common_args,
            "business": business_args,
            "data": {
                "text": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
                "status": 2  # 2表示完整的音频
            }
        }
        
        # 创建WebSocket连接
        ws = websocket.create_connection(url)
        ws.send(json.dumps(data))
        
        # 接收音频数据
        audio_data = b""
        while True:
            response = ws.recv()
            response = json.loads(response)
            
            # 提取音频数据
            if response["code"] == 0:
                audio_data += base64.b64decode(response["data"]["audio"])
                
                # 判断是否是最后一帧
                if response["data"]["status"] == 2:
                    break
            else:
                print(f"[语音提示]: 合成失败: {response}")
                ws.close()
                return
                
        ws.close()
        
        # 保存音频文件
        with open(output_file, "wb") as f:
            f.write(audio_data)
            
        # 播放音频
        print(f"[语音提示]: 播放语音...")
        pygame.mixer.music.load(output_file)
        pygame.mixer.music.play()
        
        # 等待播放完成
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
            
        print(f"[语音提示]: 播放完成")
        
        # 删除临时音频文件
        try:
            os.remove(output_file)
        except:
            pass
            
    except Exception as e:
        print(f"[语音提示]: 错误: {e}")