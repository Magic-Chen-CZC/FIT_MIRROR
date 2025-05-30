<<<<<<< HEAD
# FitMirror - 智能健身助手

FitMirror 是一个智能健身助手应用，结合了 React Native 前端和 Python 后端，提供运动姿势分析、健身聊天助手等功能。

## 项目结构

项目由两个主要部分组成：

### 1. 前端 (FitMirrorApp)

基于 React Native 和 TypeScript 开发的移动应用，包含以下主要功能和文件：

- **主页 (HomeScreen.tsx)**: 应用首页，显示健身概览和快捷入口
- **搜索 (SearchScreen.tsx)**: 搜索功能，用于查找运动和健身内容
- **运动 (WorkoutsScreen.tsx)**: 运动列表和姿势分析功能，核心功能模块
- **聊天 (ChatScreen.tsx)**: 与 AI 健身助手交流，提供健身建议和指导
- **相册 (GalleryScreen.tsx)**: 查看健身记录和分析历史
- **应用入口 (App.tsx)**: 应用主入口，配置导航和全局样式

主要文件结构：
```
FitMirrorApp/
├── App.tsx              # 应用入口
├── HomeScreen.tsx       # 主页
├── SearchScreen.tsx     # 搜索页面
├── WorkoutsScreen.tsx   # 运动分析页面
├── ChatScreen.tsx       # AI 聊天页面
├── GalleryScreen.tsx    # 相册页面
├── assets/              # 静态资源文件夹
│   └── squat_test.mp4   # 测试视频
├── package.json         # 项目依赖配置
└── tsconfig.json        # TypeScript 配置
```

### 2. 后端 (FitMirror_Backend)

基于 Python 和 Flask 开发的 API 服务器，提供以下功能和文件：

- **聊天 API**: 基于 LangChain 和通义千问大模型的健身助手
- **动作分析 API**: 使用 OpenCV 和 MediaPipe 进行运动姿势分析
- **健康检查 API**: 监控服务器和 AI 模型状态

主要文件结构：
```
FitMirror_Backend/
├── api_server.py         # API 服务器主入口
├── agent_react.py        # LangChain Agent 实现
├── fitness_analyzer.py   # 健身动作分析核心逻辑
├── tools.py              # 工具函数集合
├── image_utils.py        # 图像处理工具
├── voice_utils.py        # 语音处理工具
├── training_stats.py     # 训练数据统计
├── config.py             # 配置文件
├── requirements.txt      # 依赖列表
├── .env                  # 环境变量配置
├── knowledge_base/       # 知识库文件夹
│   └── Strength_Training_Basics.md  # 力量训练基础知识
└── uploads/              # 上传文件临时存储
```

## 准备工作

### 环境要求

#### 前端环境

- Node.js (v14+)
- npm 或 yarn
- React Native 环境
- Android Studio (用于 Android 开发)
- Xcode (用于 iOS 开发，仅 macOS)

#### 前端依赖包

主要依赖：
- react
- react-native
- expo
- @react-navigation/native
- @react-navigation/bottom-tabs
- @expo/vector-icons
- expo-image-picker
- expo-file-system
- expo-asset
- typescript

#### 后端环境

- Python 3.9+
- 通义千问 API 密钥 (DASHSCOPE_API_KEY)
- 必要的 Python 包 (见 requirements.txt)

#### 后端依赖包

主要依赖：
- **LangChain 相关**:
  - langchain
  - langchain-community
  - langchain-core
  - dashscope (通义千问 API 客户端)

- **向量存储与嵌入**:
  - faiss-cpu (或 GPU 版本，如果有兼容的 GPU)
  - tiktoken

- **文档处理**:
  - pypdf

- **健身分析核心依赖**:
  - mediapipe (用于姿势估计)
  - opencv-python (图像处理)
  - numpy (数值计算)

- **Web 服务器**:
  - flask (Web 框架)
  - flask-cors (跨域资源共享)

- **工具库**:
  - pydantic (数据验证)
  - python-dotenv (环境变量管理)
  - pygame (用于音频反馈)

### 安装步骤

#### 1. 克隆项目

```bash
git clone <项目仓库URL>
cd FitMirror
```

#### 2. 设置后端

```bash
cd FitMirror_Backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 如果需要手动安装依赖
pip install langchain langchain-community langchain-core dashscope
pip install faiss-cpu tiktoken pypdf
pip install mediapipe opencv-python numpy
pip install flask flask-cors
pip install pydantic python-dotenv pygame

# 创建 .env 文件并添加必要的环境变量
echo "DASHSCOPE_API_KEY=your_api_key_here" > .env
```

#### 3. 设置前端

```bash
cd ../FitMirrorApp

# 安装所有依赖
npm install
# 或
yarn install

# 如果需要手动安装核心依赖
npm install react react-native expo
npm install @react-navigation/native @react-navigation/bottom-tabs
npm install @expo/vector-icons expo-image-picker expo-file-system expo-asset
npm install typescript @types/react

# 启动 Expo 开发服务器
npx expo start
```

## 运行项目

### 启动后端服务器

```bash
cd FitMirror_Backend
python api_server.py
```

服务器将在 http://localhost:5000 上运行，提供以下 API 端点：

- `/health`: 健康检查
- `/chat`: 聊天 API
- `/analyze-exercise`: 运动分析 API

### 启动前端应用

```bash
cd FitMirrorApp
npm start
# 或
yarn start
```

这将启动 Expo 开发服务器，您可以：

- 在 Android 模拟器上运行应用
- 在 iOS 模拟器上运行应用 (仅 macOS)
- 在真实设备上通过 Expo Go 应用运行

## 测试

### 测试后端 API

可以使用 curl 或 Postman 测试后端 API：

```bash
# 健康检查
curl -X GET http://localhost:5000/health

# 聊天 API
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "请给我一些深蹲的建议"}'

# 运动分析 API (使用模拟数据)
curl -X POST http://localhost:5000/analyze-exercise \
  -F "exercise_type=squat" \
  -F "use_mock=true"
```

### 测试前端应用

#### 测试聊天功能

1. 打开应用，导航到"聊天"选项卡
2. 输入健身相关问题，如"如何正确做深蹲？"
3. 等待 AI 助手回复

#### 测试运动分析功能

1. 打开应用，导航到"运动"选项卡
2. 点击"力量训练"展开运动列表
3. 点击某个运动旁边的"分析"按钮
4. 在弹出的模态框中选择视频来源：
   - **从相册选择**: 从设备相册选择视频
   - **录制新视频**: 使用相机录制新视频
   - **使用测试视频**: 使用预设的测试视频
   - **模拟分析结果**: 生成模拟的分析结果

### 使用本地视频进行测试

有几种方法可以使用本地电脑上的视频进行测试：

#### 方法 1: 使用 ADB 推送视频到模拟器

```bash
adb push C:\路径\到\视频.mp4 /sdcard/Download/
```

然后在应用中点击"从相册选择"，导航到 Download 文件夹找到视频。

#### 方法 2: 使用模拟器的拖放功能

直接将视频文件从电脑拖放到模拟器窗口，然后在应用中访问该文件。

## 常见问题与故障排除

### 后端连接问题

#### 症状
- 前端应用显示"无法连接到服务器"错误
- API 请求超时或失败
- 健康检查 API 返回错误

#### 解决方案
- 确保后端服务器正在运行：`python api_server.py`
- 检查 API 地址配置是否正确：
  - Android 模拟器访问本机服务器应使用 `10.0.2.2` 而不是 `localhost`
  - iOS 模拟器可以使用 `localhost`
- 检查防火墙设置，确保端口 5000 未被阻止
- 尝试使用 `curl http://localhost:5000/health` 测试服务器是否响应
- 检查后端日志中的错误信息

### 视频上传问题

#### 症状
- 上传视频时应用崩溃或卡住
- 服务器返回 400 或 500 错误
- 视频上传成功但分析失败

#### 解决方案
- 确保视频格式为 MP4，编码为 H.264
- 视频大小不应超过 100MB（服务器限制）
- 检查应用是否有相机和媒体库权限：
  ```javascript
  const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (status !== 'granted') {
    Alert.alert('需要权限', '请在设置中允许应用访问媒体库');
  }
  ```
- 尝试使用较小的测试视频
- 检查 `uploads` 目录是否存在且可写
- 查看服务器日志中的详细错误信息

### AI 聊天功能不可用

#### 症状
- 聊天消息发送后没有响应
- 服务器返回 503 错误
- 健康检查显示 `agent_status: "unavailable"`

#### 解决方案
- 确保已设置 DASHSCOPE_API_KEY 环境变量：
  ```bash
  # Linux/macOS
  export DASHSCOPE_API_KEY=your_api_key_here

  # Windows
  set DASHSCOPE_API_KEY=your_api_key_here
  ```
- 检查 `.env` 文件是否正确配置并位于正确位置
- 确认 API 密钥有效且未过期
- 检查网络连接，确保可以访问通义千问 API
- 查看后端日志中的详细错误信息：
  ```bash
  # 查找与 Agent 相关的错误
  grep "Agent" api_server.log
  ```
- 尝试重启后端服务器

### MediaPipe 或 OpenCV 相关问题

#### 症状
- 导入 MediaPipe 或 OpenCV 时出现错误
- 视频分析时崩溃
- 姿势检测不准确

#### 解决方案
- 确保已安装正确版本的依赖：
  ```bash
  pip install mediapipe==0.8.10 opencv-python==4.5.5.64
  ```
- 对于 Windows 用户，可能需要安装 Visual C++ 运行时
- 确保视频分辨率适中（太高可能导致性能问题）
- 检查 Python 版本兼容性（建议使用 Python 3.9）
- 如果姿势检测不准确，尝试调整 `fitness_analyzer.py` 中的检测参数

## 开发者指南

### 添加新的运动类型

1. 在 `WorkoutsScreen.tsx` 中的 `EXERCISE_NAMES` 对象中添加新的运动类型：
   ```typescript
   const EXERCISE_NAMES: {[key: string]: string} = {
     // 现有运动类型
     "new_exercise": "新运动名称",
   };
   ```

2. 在 `api_server.py` 中的 `valid_exercise_types` 列表中添加新的运动类型：
   ```python
   valid_exercise_types = ["squat", "pushup", "situp", "crunch", "jumping_jack", "plank", "new_exercise"]
   ```

3. 在 `fitness_analyzer.py` 中实现新运动类型的分析逻辑

### 自定义 AI 助手

1. 修改 `agent_react.py` 中的提示词模板
2. 在 `knowledge_base` 文件夹中添加新的知识文档
3. 更新 `rag_setup.py` 中的文档加载逻辑

## 许可证

[添加许可证信息]
=======
# FIT_MIRROR
>>>>>>> 7bcd292098472c8e154be2f5ad89fb0fb051f2e7
