"""
训练统计模块 - 处理训练数据记录和报告生成
"""
import time
import os
import datetime
import json
import base64
from io import BytesIO
from voice_utils import speak_error_async
import shutil # 新增导入

# 尝试导入绘图库
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import numpy as np
    from matplotlib.patches import Polygon
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("警告：matplotlib 未安装，无法生成雷达图")

try:
    from config import ERROR_COOLDOWN, EXERCISE_NAMES
except ImportError:
    ERROR_COOLDOWN = 2.0
    EXERCISE_NAMES = {
        "squat": "深蹲",
        "crunch": "卷腹",
        "situp": "仰卧起坐",
        "jumping_jack": "开合跳",
        "pushup": "俯卧撑"
    }

# 尝试导入大模型API
try:
    from dashscope import Generation
    from dashscope.api_entities.dashscope_response import Role
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False

class TrainingStats:
    def __init__(self, exercise_type):
        self.exercise_type = exercise_type
        self.start_time = time.time()
        self.error_records = []
        self.total_count = 0
        self.error_summary = {}
        self.last_error_types = set()
        self.last_speak_time = 0
        self.error_cooldown = ERROR_COOLDOWN
        self.frame_count = 0
        self.user_name = "健身爱好者"
        
        # 新增：动作质量维度数据
        self.quality_metrics = {
            "standard_scores": [],     # 标准度得分（每次动作）
            "stability_scores": [],    # 稳定性得分
            "depth_scores": [],        # 动作深度得分
            "frequency_data": []       # 频率数据（时间戳）
        }

        # 根据运动类型设置报告目录
        exercise_name = EXERCISE_NAMES.get(self.exercise_type, "未知运动")
        report_folder = f"{exercise_name}训练报告"
        self.report_dir = os.path.join(os.path.expanduser("~"), "Desktop", report_folder)
        if not os.path.exists(self.report_dir):
            os.makedirs(self.report_dir, exist_ok=True)

    def add_record(self, errors):
        """记录错误，在新的错误类型出现时更新统计，并根据冷却时间决定是否语音播报"""
        self.frame_count += 1
        current_time = time.time()
        # 修改点：确保 error_text 在加入集合前去除首尾空格
        current_error_types = {error_text.strip() for error_text, _, _ in errors} if errors else set()

        # print(f"--- Frame {self.frame_count} (Time: {current_time:.2f}) ---")
        # print(f"  Incoming errors: {current_error_types if current_error_types else 'None'}")
        # print(f"  Last frame errors: {self.last_error_types if self.last_error_types else 'None'}")

        newly_appeared_error_types = current_error_types - self.last_error_types

        if newly_appeared_error_types:
            # print(f"  New errors detected: {newly_appeared_error_types}")
            for error_type in newly_appeared_error_types: # error_type 已经是 .strip() 过的
                # 更新错误统计
                self.error_summary[error_type] = self.error_summary.get(error_type, 0) + 1
                self.error_records.append({
                    "timestamp": current_time - self.start_time,
                    "error_type": error_type, 
                    "frame": self.frame_count
                })
                
                # 语音播报新增错误，并考虑冷却时间
                if current_time - self.last_speak_time > self.error_cooldown:
                    spoken_error_message = error_type 
                    if error_type == "膝盖内扣":
                        spoken_error_message = "膝盖内扣，请保持膝盖与脚尖同向"
                    
                    # print(f"  Attempting to speak error: {spoken_error_message}")
                    speak_error_async(spoken_error_message)
                    self.last_speak_time = current_time
                # else:
                    # print(f"  Speak error cooldown active for: {error_type}")

        # self.last_error_types 现在存储的是去除空格后的错误类型集合
        self.last_error_types = current_error_types

    def update_count(self):
        """更新总动作次数"""
        self.total_count += 1
        # 记录动作完成时间（用于频率计算）
        self.quality_metrics["frequency_data"].append(time.time() - self.start_time)

    def add_quality_metrics(self, standard_score=85, stability_score=80, depth_score=75):
        """添加动作质量指标数据"""
        self.quality_metrics["standard_scores"].append(standard_score)
        self.quality_metrics["stability_scores"].append(stability_score)
        self.quality_metrics["depth_scores"].append(depth_score)

    def calculate_quality_dimensions(self):
        """计算四个质量维度的综合得分"""
        # 标准度：基于错误率计算
        error_rate = sum(self.error_summary.values()) / self.total_count * 100 if self.total_count > 0 else 0
        standard_score = max(60, 100 - error_rate * 2)  # 错误率越低，标准度越高
        
        # 稳定性：基于动作一致性（模拟计算）
        if self.quality_metrics["stability_scores"]:
            stability_score = sum(self.quality_metrics["stability_scores"]) / len(self.quality_metrics["stability_scores"])
        else:
            # 基于错误类型数量计算
            error_types_count = len(self.error_summary)
            stability_score = max(60, 95 - error_types_count * 10)
        
        # 动作深度：基于运动类型和完成质量
        if self.quality_metrics["depth_scores"]:
            depth_score = sum(self.quality_metrics["depth_scores"]) / len(self.quality_metrics["depth_scores"])
        else:
            # 基于总体表现估算
            depth_score = min(90, max(65, standard_score - 5))
        
        # 动作频率：基于训练时长和动作次数
        training_duration = (time.time() - self.start_time) / 60  # 分钟
        if training_duration > 0 and self.total_count > 0:
            frequency_per_min = self.total_count / training_duration
            
            # 根据运动类型设置理想频率范围
            ideal_frequencies = {
                "squat": (8, 12),      # 每分钟8-12个
                "pushup": (6, 10),     # 每分钟6-10个
                "situp": (10, 15),     # 每分钟10-15个
                "crunch": (12, 18),    # 每分钟12-18个
                "jumping_jack": (20, 30) # 每分钟20-30个
            }
            
            ideal_min, ideal_max = ideal_frequencies.get(self.exercise_type, (8, 12))
            
            if ideal_min <= frequency_per_min <= ideal_max:
                frequency_score = 90
            elif frequency_per_min < ideal_min:
                frequency_score = max(60, 90 - (ideal_min - frequency_per_min) * 5)
            else:
                frequency_score = max(60, 90 - (frequency_per_min - ideal_max) * 3)
        else:
            frequency_score = 75  # 默认值
        
        return {
            "standard": round(standard_score, 1),
            "stability": round(stability_score, 1),
            "depth": round(depth_score, 1),
            "frequency": round(frequency_score, 1)
        }

    def generate_radar_chart(self, quality_scores):
        """生成雷达图并返回base64编码的图片"""
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        try:
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 雷达图数据
            categories = ['标准度', '稳定性', '动作深度', '动作频率']
            values = [
                quality_scores["standard"],
                quality_scores["stability"], 
                quality_scores["depth"],
                quality_scores["frequency"]
            ]
            
            # 闭合雷达图
            values += values[:1]
            angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
            angles += angles[:1]
            
            # 创建图形
            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
            
            # 绘制雷达图
            ax.plot(angles, values, 'o-', linewidth=2, color='#667eea', label='当前表现')
            ax.fill(angles, values, alpha=0.25, color='#667eea')
            
            # 绘制参考线（优秀水平）
            excellent_values = [90] * len(categories) + [90]
            ax.plot(angles, excellent_values, '--', linewidth=1, color='#28a745', alpha=0.7, label='优秀水平')
            
            # 设置标签
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, fontsize=12)
            
            # 设置径向轴
            ax.set_ylim(0, 100)
            ax.set_yticks([20, 40, 60, 80, 100])
            ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=10)
            ax.grid(True)
            
            # 添加图例
            ax.legend(loc='upper right', bbox_to_anchor=(1.1, 1.0)) # 修改了 bbox_to_anchor 的 x 值从 1.3 到 1.1
            
            # 添加标题
            plt.title(f'{EXERCISE_NAMES.get(self.exercise_type, "运动")}动作质量分析', 
                     fontsize=16, fontweight='bold', pad=20)
            
            # 保存为base64字符串
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            plt.close()
            return image_base64
            
        except Exception as e:
            print(f"生成雷达图时出错: {e}")
            return None

    def _generate_ai_suggestions(self, summary_data):
        """使用大模型生成个性化训练建议"""
        if not DASHSCOPE_AVAILABLE:
            return self._get_default_suggestions(summary_data)
        
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            return self._get_default_suggestions(summary_data)
        
        try:
            exercise_name = summary_data["exercise_name"]
            error_list = list(self.error_summary.keys())
            total_count = summary_data["total_count"]
            overall_score = summary_data["overall_score"]
            
            # 构建提示词
            prompt = f"""作为专业健身教练，请为用户的{exercise_name}训练提供个性化建议。

训练数据：
- 完成次数：{total_count}个
- 综合评分：{overall_score}分
- 检测到的错误：{', '.join(error_list) if error_list else '无明显错误'}

请生成以下内容（用JSON格式返回）：
1. error_analysis: 针对检测到的错误进行分析（如果没有错误，说明动作标准）
2. beginner_suggestions: 3-4个适合初学者的改进建议
3. advanced_suggestions: 3-4个进阶训练建议
4. form_tips: 2-3个关键的动作要点提醒

要求：
- 建议要具体、实用、专业
- 语言要友好鼓励
- 针对检测到的具体错误给出解决方案
- 如果没有错误，要给予肯定并提供进阶建议"""

            messages = [
                {'role': Role.SYSTEM, 'content': '你是一位专业的健身教练，擅长分析用户的训练数据并提供个性化的健身建议。'},
                {'role': Role.USER, 'content': prompt}
            ]

            response = Generation.call(
                model='qwen-plus',
                messages=messages,
                api_key=api_key,
                result_format='message'
            )

            if response.status_code == 200:
                ai_response = response.output.choices[0].message.content
                print(f"AI生成的建议: {ai_response}")
                
                # 尝试解析JSON格式的回复
                try:
                    import json
                    # 提取JSON部分
                    if '```json' in ai_response:
                        json_start = ai_response.find('```json') + 7
                        json_end = ai_response.find('```', json_start)
                        json_content = ai_response[json_start:json_end].strip()
                    elif '{' in ai_response and '}' in ai_response:
                        json_start = ai_response.find('{')
                        json_end = ai_response.rfind('}') + 1
                        json_content = ai_response[json_start:json_end]
                    else:
                        # 如果没有JSON格式，使用默认建议
                        return self._get_default_suggestions(summary_data)
                    
                    suggestions = json.loads(json_content)
                    return suggestions
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"解析AI回复失败: {e}")
                    # 解析失败时，尝试从文本中提取建议
                    return self._parse_text_suggestions(ai_response, summary_data)
            else:
                print(f"AI API调用失败: {response.status_code}")
                return self._get_default_suggestions(summary_data)
                
        except Exception as e:
            print(f"生成AI建议时出错: {e}")
            return self._get_default_suggestions(summary_data)

    def _parse_text_suggestions(self, ai_response, summary_data):
        """从AI的文本回复中解析建议"""
        try:
            # 简单的文本解析逻辑
            lines = ai_response.split('\n')
            suggestions = {
                "error_analysis": "",
                "beginner_suggestions": [],
                "advanced_suggestions": [],
                "form_tips": []
            }
            
            current_section = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if '错误分析' in line or 'error_analysis' in line.lower():
                    current_section = 'error_analysis'
                elif '初学者' in line or 'beginner' in line.lower():
                    current_section = 'beginner_suggestions'
                elif '进阶' in line or 'advanced' in line.lower():
                    current_section = 'advanced_suggestions'
                elif '要点' in line or 'form_tips' in line.lower():
                    current_section = 'form_tips'
                elif line.startswith(('-', '•', '1.', '2.', '3.', '4.')):
                    if current_section and current_section != 'error_analysis':
                        clean_line = line.lstrip('-•1234567890. ')
                        if clean_line:
                            suggestions[current_section].append(clean_line)
                elif current_section == 'error_analysis' and not line.startswith(('初学者', '进阶', '要点')):
                    suggestions['error_analysis'] += line + ' '
            
            # 确保每个列表至少有一些内容
            if not suggestions['beginner_suggestions']:
                suggestions['beginner_suggestions'] = self._get_default_suggestions(summary_data)['beginner_suggestions']
            if not suggestions['advanced_suggestions']:
                suggestions['advanced_suggestions'] = self._get_default_suggestions(summary_data)['advanced_suggestions']
            if not suggestions['form_tips']:
                suggestions['form_tips'] = self._get_default_suggestions(summary_data)['form_tips']
                
            return suggestions
        except Exception as e:
            print(f"解析文本建议失败: {e}")
            return self._get_default_suggestions(summary_data)

    def _get_default_suggestions(self, summary_data):
        """获取默认的训练建议（当AI不可用时）"""
        exercise_type = summary_data["exercise_type"]
        overall_score = summary_data["overall_score"]
        error_list = list(self.error_summary.keys())
        
        # 生成错误分析
        if error_list:
            error_analysis = f"检测到以下问题：{', '.join(error_list)}。这些是常见的技术错误，通过针对性练习可以改善。"
        else:
            error_analysis = "本次训练未检测到明显错误，动作标准程度良好。继续保持这种标准，并可以考虑增加训练强度。"
        
        suggestions = {
            "error_analysis": error_analysis,
            "beginner_suggestions": [],
            "advanced_suggestions": [],
            "form_tips": []
        }
        
        if exercise_type == "squat":
            suggestions["beginner_suggestions"] = [
                "从浅蹲开始，逐渐增加下蹲深度",
                "保持膝盖与脚尖方向一致，避免内扣",
                "可以背靠墙练习，确保重心稳定",
                "控制下蹲和起立的速度，注重动作质量"
            ]
            suggestions["advanced_suggestions"] = [
                "尝试负重深蹲，增加训练强度",
                "练习单腿深蹲，提升平衡能力",
                "增加深蹲变式：相扑深蹲、跳跃深蹲",
                "结合其他下肢训练动作，形成训练组合"
            ]
            suggestions["form_tips"] = [
                "保持核心收紧，避免身体前倾",
                "下蹲时重心放在脚跟，而非脚尖",
                "呼吸要配合动作：下蹲吸气，起立呼气"
            ]
        elif exercise_type == "pushup":
            suggestions["beginner_suggestions"] = [
                "可以从膝盖俯卧撑开始练习",
                "注意保持身体平直，避免塌腰",
                "控制下降和上升的速度",
                "逐渐增加训练次数和组数"
            ]
            suggestions["advanced_suggestions"] = [
                "尝试钻石俯卧撑，增强三头肌力量",
                "增加俯卧撑变式：宽距、窄距俯卧撑",
                "可以负重训练或单手俯卧撑",
                "结合其他上肢训练动作"
            ]
            suggestions["form_tips"] = [
                "手掌位置在肩膀正下方",
                "保持身体一条直线",
                "手肘贴近身体，不要过度外展"
            ]
        # ...existing default suggestions for other exercises...
        
        return suggestions

    def export_report(self, filename=None, template_path="squat_analysis_report.html"):
        """
        导出HTML格式的训练报告
        """
        summary_data = self.get_summary()
        exercise_name = summary_data["exercise_name"]
        overall_score = summary_data["overall_score"]
        report_datetime = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M")

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        if filename is None:
            filename = f"{exercise_name}_训练报告_{timestamp}.html"

        full_filename = os.path.join(self.report_dir, filename)

        try:
            # 生成AI建议
            ai_suggestions = self._generate_ai_suggestions(summary_data)
            
            # 计算质量维度得分
            quality_scores = self.calculate_quality_dimensions()
            summary_data["quality_scores"] = quality_scores
            
            # 生成雷达图
            radar_chart_base64 = self.generate_radar_chart(quality_scores)
            
            # ---- 新增：读取并编码 shendun.jpg 为 Base64 ----
            muscle_activation_image_base64 = None
            try:
                shendun_jpg_path = os.path.join(os.path.dirname(__file__), "picture", "shendun.jpg")
                if os.path.exists(shendun_jpg_path):
                    with open(shendun_jpg_path, "rb") as image_file:
                        muscle_activation_image_base64 = base64.b64encode(image_file.read()).decode()
                    print(f"DEBUG: Successfully encoded {shendun_jpg_path} to Base64.")
                else:
                    print(f"DEBUG: Image file not found at {shendun_jpg_path}")
            except Exception as e:
                print(f"DEBUG: Error encoding {shendun_jpg_path}: {e}")
            # ---- 结束新增代码 ----

            # 尝试读取HTML模板
            template_full_path = os.path.join(os.path.dirname(__file__), template_path)
            if os.path.exists(template_full_path):
                with open(template_full_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # 替换基本信息
                html_content = html_content.replace("健身爱好者", self.user_name)
                html_content = html_content.replace("2025年05月27日 20:00", report_datetime)
                html_content = html_content.replace("82", str(overall_score))
                
                # 替换训练概况数据
                html_content = self._replace_training_overview(html_content, summary_data)

                # ---- 修改：插入肌群激活图 (Base64) ----
                if muscle_activation_image_base64:
                    muscle_img_tag = f'<img src="data:image/jpeg;base64,{muscle_activation_image_base64}" alt="肌群激活分析图" class="muscle-chart" />'
                    html_content = html_content.replace('<!-- MUSCLE_ACTIVATION_IMAGE_PLACEHOLDER -->', muscle_img_tag)
                    print("DEBUG: Muscle activation image (Base64) inserted into HTML.")
                else:
                    html_content = html_content.replace('<!-- MUSCLE_ACTIVATION_IMAGE_PLACEHOLDER -->', '<p>肌群激活分析图无法加载</p>')
                    print("DEBUG: Placeholder for muscle activation image used due to missing Base64 data.")
                # ---- 结束修改 ----
                
                # 插入雷达图
                if radar_chart_base64:
                    radar_img_tag = f'<img src="data:image/png;base64,{radar_chart_base64}" alt="动作质量雷达图" class="radar-chart" />'
                else:
                    radar_img_tag = '<p>无法生成雷达图，请确保已安装matplotlib</p>'
                
                # 替换雷达图容器
                html_content = html_content.replace(
                    '<div class="radar-chart-container">',
                    f'<div class="radar-chart-container">{radar_img_tag}'
                )
                
                # 替换错误诊断内容
                error_content = self._generate_error_diagnosis_html(ai_suggestions)
                html_content = self._replace_section_content(html_content, "关键错误诊断", error_content)
                
                # 替换训练建议内容
                suggestions_content = self._generate_suggestions_html(ai_suggestions)
                html_content = self._replace_section_content(html_content, "个性化训练建议", suggestions_content)
                
                # 替换动作质量分析
                quality_content = self._generate_quality_analysis_html(summary_data)
                html_content = self._replace_section_content(html_content, "动作质量分析", quality_content)
                
                with open(full_filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                print(f"HTML报告已生成: {full_filename}")
                return full_filename
            else:
                print(f"HTML模板不存在: {template_full_path}，生成纯文本报告")
                return self._export_text_report(filename, fallback=True)
                
        except Exception as e:
            print(f"生成HTML报告时出错: {e}")
            import traceback
            traceback.print_exc()
            return self._export_text_report(filename, fallback=True)

    def _replace_training_overview(self, html_content, summary_data):
        """替换训练概况数据"""
        training_duration = summary_data['training_duration']
        total_count = summary_data['total_count']
        error_count = summary_data['error_count']
        accuracy = 100 - summary_data['error_rate']
        
        # 替换统计数据
        html_content = html_content.replace('<div class="stat-value">15</div>', f'<div class="stat-value">{total_count}</div>')
        html_content = html_content.replace('<div class="stat-value">5.2</div>', f'<div class="stat-value">{training_duration}</div>')
        html_content = html_content.replace('<div class="stat-value">3</div>', f'<div class="stat-value">{error_count}</div>')
        html_content = html_content.replace('<div class="stat-value">80%</div>', f'<div class="stat-value">{accuracy:.0f}%</div>')
        
        return html_content

    def _generate_error_diagnosis_html(self, ai_suggestions):
        """生成错误诊断的HTML内容"""
        error_analysis = ai_suggestions.get("error_analysis", "")
        
        if not self.error_summary:
            return '''            <div class="list-item normal-pain">✅ 本次训练未检测到明显错误，动作标准！</div>
            <div class="list-item normal-pain">✅ 继续保持这种标准，可以考虑增加训练强度</div>'''
        
        html = f'            <div class="error-analysis-summary">{error_analysis}</div>\n'
        
        for error_type in self.error_summary.keys(): # 修改：只遍历错误类型，不显示次数
            html += f'            <div class="list-item abnormal-pain">⚠️ {error_type}</div>\n' # 修改：移除 {count}
        
        return html

    def _generate_quality_analysis_html(self, summary_data):
        """生成动作质量分析的HTML内容"""
        if not self.error_summary:
            return '''            <div class="list-item normal-pain">✅ 动作标准程度：优秀</div>
            <div class="list-item normal-pain">✅ 运动节奏：良好</div>
            <div class="list-item normal-pain">✅ 技术稳定性：稳定</div>'''
        
        html = ""
        # 根据具体错误类型生成对应的质量分析
        for error_type in self.error_summary.keys():
            if "膝盖" in error_type:
                html += '            <div class="list-item abnormal-pain">⚠️ 膝关节控制需要改进</div>\n'
            elif "重心" in error_type:
                html += '            <div class="list-item abnormal-pain">⚠️ 重心稳定性有待提升</div>\n'
            elif "肩部" in error_type:
                html += '            <div class="list-item abnormal-pain">⚠️ 肩部姿态需要调整</div>\n'
            elif "躯干" in error_type:
                html += '            <div class="list-item abnormal-pain">⚠️ 躯干稳定性需要加强</div>\n'
        
        # 添加一些正面的质量评价
        overall_score = summary_data["overall_score"]
        if overall_score >= 85:
            html += '            <div class="list-item normal-pain">✅ 整体动作完成度较高</div>\n'
        elif overall_score >= 70:
            html += '            <div class="list-item">⚡ 动作基础良好，有改进空间</div>\n'
        
        return html

    def _generate_suggestions_html(self, ai_suggestions):
        """生成训练建议的HTML内容"""
        html = ""
        
        # 退阶方案（初学者建议）
        beginner_suggestions = ai_suggestions.get("beginner_suggestions", [])
        html += '        <div class="suggestion-title">【退阶方案】</div>\n'
        html += '        <div class="list-container">\n'
        for suggestion in beginner_suggestions:
            html += f'            <div class="list-item">📚 {suggestion}</div>\n'
        html += '        </div>\n\n'
        
        # 进阶方案
        advanced_suggestions = ai_suggestions.get("advanced_suggestions", [])
        html += '        <div class="suggestion-title">【进阶方案】</div>\n'
        html += '        <div class="list-container">\n'
        for suggestion in advanced_suggestions:
            html += f'            <div class="list-item">🚀 {suggestion}</div>\n'
        html += '        </div>\n\n'
        
        # 关键要点提醒
        form_tips = ai_suggestions.get("form_tips", [])
        if form_tips:
            html += '        <div class="suggestion-title">【关键要点提醒】</div>\n'
            html += '        <div class="list-container">\n'
            for tip in form_tips:
                html += f'            <div class="list-item">💡 {tip}</div>\n'
            html += '        </div>\n'
        
        return html

    def _replace_section_content(self, html_content, section_title, new_content):
        """替换HTML中指定section的内容"""
        # 查找section标题
        section_start = html_content.find(f'<div class="section-title">{section_title}</div>')
        if section_start == -1:
            return html_content
        
        # 查找该section的list-container
        container_start = html_content.find('<div class="list-container">', section_start)
        if container_start == -1:
            return html_content
        
        container_end = html_content.find('</div>', container_start) + 6
        
        # 替换内容
        before = html_content[:container_start]
        after = html_content[container_end:]
        
        new_section = f'<div class="list-container">\n{new_content}        </div>'
        
        return before + new_section + after

    # ...existing methods...
    
    def get_summary(self):
        """获取训练摘要数据"""
        exercise_name = EXERCISE_NAMES.get(self.exercise_type, "未知运动")
        training_duration = (time.time() - self.start_time) / 60
        total_error_occurrences = sum(self.error_summary.values())
        error_rate = total_error_occurrences / self.total_count * 100 if self.total_count > 0 else 0 # 添加 else 0

        capped_error_rate = min(error_rate, 100.0)
        
        return {
            "exercise_name": exercise_name,
            "training_duration": round(training_duration, 1),
            "total_count": self.total_count,
            "error_count": len(self.error_records),
            "error_rate": round(capped_error_rate, 1),
            "overall_score": round((
                self.calculate_quality_dimensions().get("standard", 0) +
                self.calculate_quality_dimensions().get("stability", 0) +
                self.calculate_quality_dimensions().get("depth", 0) +
                self.calculate_quality_dimensions().get("frequency", 0)
            ) / 4, 1)
        }