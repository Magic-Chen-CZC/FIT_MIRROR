import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Image,
  SafeAreaView,
  StatusBar,
  Alert,
  ActivityIndicator,
  Modal,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons'; // 需要安装 @expo/vector-icons 包
import * as ImagePicker from 'expo-image-picker'; // 需要安装 expo-image-picker 包
import * as FileSystem from 'expo-file-system'; // 需要安装 expo-file-system 包
import { WebView, WebViewMessageEvent, WebViewProps } from 'react-native-webview'; // 修改后的导入

// API配置 - 使用用户提供的IP地址
const API_BASE_URL = 'http://10.38.86.85:5000'; 

console.log(`当前平台: ${Platform.OS}, 使用API地址: ${API_BASE_URL}`);

// API请求辅助函数
const apiRequest = async (endpoint: string, method: string = 'GET', data?: any, timeout: number = 30000) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const options: RequestInit = {
      method,
      signal: controller.signal,
      headers: {}
    };

    if (data) {
      if (data instanceof FormData) {
        options.body = data;
        // 对于FormData，不要设置Content-Type，让浏览器自动设置，包含boundary
      } else {
        options.body = JSON.stringify(data);
        options.headers = {
          'Content-Type': 'application/json'
        };
      }
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API错误 (${response.status}): ${errorText}`);
    }

    return await response.json();
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('请求超时，请检查网络连接或服务器状态');
    }
    throw error;
  }
};

// 定义错误类型接口
interface ExerciseError {
  type: string;
  count: number;
  first_timestamp: number;
}

// 定义分析结果接口
interface AnalysisResult {
  success: boolean;
  message: string;
  exercise_type: string;
  counter: number;
  processed_frames?: number;
  errors_detected: ExerciseError[];
  report_path?: string; 
  uploaded_video_path?: string; 
  report_url?: string; 
}

// 运动类型中英文映射
const EXERCISE_NAMES: {[key: string]: string} = {
  "squat": "深蹲",
  "pushup": "俯卧撑",
  "situp": "仰卧起坐",
  "crunch": "卷腹",
  "jumping_jack": "开合跳",
  "plank": "平板支撑"
};

// 测试视频映射 - 使用网络视频URL
const TEST_VIDEOS: {[key: string]: string} = {
  // 这些是示例URL，您需要替换为实际可访问的视频URL
  "squat": "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
  "pushup": "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
  "situp": "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
  "jumping_jack": "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
  "plank": "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4"
};

export default function WorkoutsScreen() {
  const [openWorkout, setOpenWorkout] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedExercise, setSelectedExercise] = useState<string>('squat');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [reportHtml, setReportHtml] = useState<string | null>(null); 
  const [showReportModal, setShowReportModal] = useState(false); 

  // 从 WebViewProps 推断事件处理函数类型
  const handleWebViewError: NonNullable<WebViewProps['onError']> = (event) => {
    const { nativeEvent } = event;
    console.warn('WebView error: ', nativeEvent);
    Alert.alert("加载报告出错", `无法显示分析报告内容. ${nativeEvent.description || ''}`);
    setShowReportModal(false);
  };

  const handleWebViewHttpError: NonNullable<WebViewProps['onHttpError']> = (event) => {
    const { nativeEvent } = event;
    console.warn(
      'WebView HTTP error: ',
      nativeEvent.url,
      nativeEvent.statusCode,
      nativeEvent.description,
    );
    Alert.alert("加载报告资源出错", `报告中的部分内容可能无法加载 (HTTP ${nativeEvent.statusCode}).`);
  };

  // 请求相机和媒体库权限，并检查服务器状态
  useEffect(() => {
    // 请求权限
    const requestPermissions = async () => {
      if (Platform.OS !== 'web') {
        const { status: cameraStatus } = await ImagePicker.requestCameraPermissionsAsync();
        const { status: mediaStatus } = await ImagePicker.requestMediaLibraryPermissionsAsync();

        if (cameraStatus !== 'granted' || mediaStatus !== 'granted') {
          Alert.alert('权限不足', '需要相机和媒体库权限才能上传视频进行分析。');
        }
      }
    };

    // 检查服务器健康状态
    const checkServerHealth = async () => {
      try {
        const response = await apiRequest('/health');
        console.log('服务器状态:', response);

        if (response.agent_status !== 'available') {
          Alert.alert(
            '服务器警告',
            '动作分析功能可能不可用，请联系管理员检查服务器状态。',
            [{ text: '我知道了' }]
          );
        }
      } catch (error: any) {
        console.error('服务器健康检查失败:', error.message);
        Alert.alert(
          '连接错误',
          `无法连接到服务器 (${API_BASE_URL})，动作分析功能将不可用。请检查网络连接或服务器状态。`,
          [{ text: '我知道了' }]
        );
      }
    };

    requestPermissions();
    checkServerHealth();
  }, []);

  const toggleWorkout = (workout: string) => {
    if (openWorkout === workout) {
      setOpenWorkout(null);
    } else {
      setOpenWorkout(workout);
    }
  };

  // 打开选择视频的模态框
  const openAnalysisModal = (exercise: string) => {
    setSelectedExercise(exercise);
    setModalVisible(true);
  };

  // 从相册选择视频
  const pickVideo = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Videos, // TODO: Investigate deprecated MediaTypeOptions
        allowsEditing: true,
        quality: 1,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const videoUri = result.assets[0].uri;
        uploadVideo(videoUri);
      }
    } catch (error: any) {
      Alert.alert('错误', '选择视频时出错');
      console.error('选择视频错误:', error);
    }
  };

  // 使用相机录制视频
  const recordVideo = async () => {
    try {
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Videos, // TODO: Investigate deprecated MediaTypeOptions
        allowsEditing: true,
        quality: 1,
        videoMaxDuration: 30, // 最大录制时间30秒
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const videoUri = result.assets[0].uri;
        uploadVideo(videoUri);
      }
    } catch (error: any) {
      Alert.alert('错误', '录制视频时出错');
      console.error('录制视频错误:', error);
    }
  };

  // 上传视频到服务器进行分析
  const uploadVideo = async (videoUri: string) => {
    setIsLoading(true);
    setModalVisible(false);
    setReportHtml(null); 
    setShowReportModal(false); 

    try {
      const fileInfo = await FileSystem.getInfoAsync(videoUri);
      if (!fileInfo.exists) {
        throw new Error('文件不存在');
      }

      const formData = new FormData();
      formData.append('video', {
        uri: videoUri,
        name: 'video.mp4',
        type: 'video/mp4',
      } as any);
      formData.append('exercise_type', selectedExercise);

      console.log(`开始上传视频进行${EXERCISE_NAMES[selectedExercise] || selectedExercise}动作分析...`);
      const data: AnalysisResult = await apiRequest('/analyze-exercise', 'POST', formData, 120000); // Increased timeout to 120 seconds

      if (data.success) {
        console.log('分析成功:', data);
        setAnalysisResult(data);
        setShowResult(true);

        if (data.report_url) { 
          try {
            const reportResponse = await fetch(data.report_url);
            if (reportResponse.ok) {
              const htmlContent = await reportResponse.text();
              setReportHtml(htmlContent);
            } else {
              console.warn('无法获取报告HTML内容:', reportResponse.status);
              setReportHtml(`<html><body><h1>加载报告失败</h1><p>无法从 ${data.report_url} 加载报告内容。状态码: ${reportResponse.status}</p></body></html>`);
            }
          } catch (reportError: any) {
            console.error('加载报告内容时出错 (via report_url):', reportError.message);
            setReportHtml(`<html><body><h1>加载报告出错</h1><p>尝试从 ${data.report_url} 加载报告时发生错误: ${reportError.message}</p></body></html>`);
          }
        } else if (data.report_path) {
          console.warn(`分析结果包含 report_path (${data.report_path}) 但没有 report_url. 客户端无法直接访问此路径.`);
          setReportHtml(`<html><body><h1>报告已生成 (本地路径)</h1><p>报告文件位于服务器路径: ${data.report_path}</p><p>请联系管理员配置服务器以通过URL访问此报告，或在后续版本中实现应用内查看功能。</p></body></html>`);
        }
      } else {
        console.error('分析失败:', data.message);
        Alert.alert('分析失败', data.message || '未知错误');
      }
    } catch (error: any) {
      console.error('上传视频错误:', error.message);
      Alert.alert(
        '错误',
        error.message || '上传或分析视频时出错，请检查网络连接和服务器状态'
      );
    } finally {
      setIsLoading(false);
    }
  };

  // 使用测试视频（开发测试用）
  const useTestVideo = async (exerciseType: string) => {
    setModalVisible(false);
    setIsLoading(true);

    try {
      console.log(`准备使用测试视频进行${EXERCISE_NAMES[exerciseType] || exerciseType}动作分析...`);

      // 检查是否有对应的测试视频
      if (!TEST_VIDEOS[exerciseType]) {
        console.warn(`没有找到${exerciseType}的测试视频，将使用模拟数据`);
        simulateAnalysisResult(exerciseType);
        return;
      }

      const videoUrl = TEST_VIDEOS[exerciseType];
      console.log(`使用网络测试视频: ${videoUrl}`);

      // 创建FormData对象
      const formData = new FormData();
      formData.append('video', {
        uri: videoUrl,
        name: `${exerciseType}_test.mp4`,
        type: 'video/mp4',
      } as any);
      formData.append('exercise_type', exerciseType);

      console.log(`开始上传测试视频进行${EXERCISE_NAMES[exerciseType] || exerciseType}动作分析...`);

      try {
        // 尝试从服务器获取分析结果
        const data = await apiRequest('/analyze-exercise', 'POST', formData, 60000);

        if (data.success) {
          console.log('分析成功:', data);
          setAnalysisResult(data);
          setShowResult(true);
        } else {
          // 如果服务器分析失败，使用模拟数据
          console.log('服务器分析失败，使用模拟数据');
          simulateAnalysisResult(exerciseType);
        }
      } catch (error: any) {
        // 如果服务器请求失败，使用模拟数据
        console.log('服务器请求失败，使用模拟数据:', error.message);
        simulateAnalysisResult(exerciseType);
      }
    } catch (error: any) {
      console.error('测试视频处理错误:', error.message);
      Alert.alert('错误', `测试视频处理失败: ${error.message}`);
      // 出错时使用模拟数据
      simulateAnalysisResult(exerciseType);
    } finally {
      setIsLoading(false);
    }
  };

  // 模拟分析结果（开发测试用）
  const simulateAnalysisResult = (exerciseType: string) => {
    setModalVisible(false);
    setIsLoading(true); 
    setReportHtml(null); 
    setShowReportModal(false); 
    const mockResult: AnalysisResult = {
      success: true,
      message: "分析完成，这是模拟数据。",
      exercise_type: exerciseType,
      counter: Math.floor(Math.random() * 10) + 5,
      processed_frames: 300,
      errors_detected: [],
      report_url: 'data:text/html,<html><body><h1>模拟HTML报告</h1><p>这是一个模拟的HTML报告内容，用于测试WebView显示。</p><h2>运动: ' + exerciseType + '</h2><ul><li>错误1: 示例 (3次)</li><li>错误2: 演示 (2次)</li></ul></body></html>'
      // report_path: '/path/to/mock_server_report.html' 
    };
    const possibleErrors = {
      "squat": ["膝盖内扣", "重心过于靠前", "下蹲不够深"],
      "pushup": ["肩部下沉", "臀部抬高", "手肘角度不正确"],
      "situp": ["躯干扭转", "头部前屈", "动作不完整"],
      "jumping_jack": ["动作不对称", "膝盖弯曲", "手臂抬起不够高"],
      "plank": ["臀部抬高", "肩部下沉", "身体不平直"]
    };
    if (Math.random() > 0.5) {
      const errors = possibleErrors[exerciseType as keyof typeof possibleErrors] || [];
      if (errors.length > 0) {
        const numErrors = Math.floor(Math.random() * 2) + 1;
        for (let i = 0; i < numErrors && i < errors.length; i++) {
          mockResult.errors_detected.push({
            type: errors[i],
            count: Math.floor(Math.random() * 5) + 1,
            first_timestamp: Math.random() * 10
          });
        }
      }
    }

    // 更新模拟报告HTML以包含错误信息
    let simulatedHtml = `<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>body{font-family: sans-serif; padding: 15px;} h1{color: #333;} h2{color:#555;} ul{list-style-type: none; padding-left:0;} li{background-color:#f0f0f0; margin-bottom:5px; padding:8px; border-radius:4px;}</style></head><body><h1>模拟报告 (${EXERCISE_NAMES[exerciseType] || exerciseType})</h1><p>这是模拟生成的分析报告。</p><h2>检测到的问题:</h2>`;
    if (mockResult.errors_detected.length > 0) {
      simulatedHtml += '<ul>';
      mockResult.errors_detected.forEach(err => {
        simulatedHtml += `<li>${err.type} (出现 ${err.count} 次)</li>`;
      });
      simulatedHtml += '</ul>';
    } else {
      simulatedHtml += '<p>动作标准，未检测到明显问题！</p>';
    }
    simulatedHtml += '</body></html>';
    mockResult.report_url = `data:text/html,${encodeURIComponent(simulatedHtml)}`;

    if (mockResult.report_url) {
        setReportHtml(decodeURIComponent(mockResult.report_url.substring('data:text/html,'.length)));
    } else if (mockResult.report_path) {
        setReportHtml(`<html><body><h1>模拟报告 (${exerciseType}) - 本地路径</h1><p>报告位于模拟服务器路径: ${mockResult.report_path}</p></body></html>`);
    }
    
    setTimeout(() => { 
        setAnalysisResult(mockResult);
        setShowResult(true);
        setIsLoading(false); 
    }, 1500);
  };

  return (
    <SafeAreaView style={styles.container}>
      {isLoading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#e4dafa" />
          <Text style={styles.loadingText}>正在分析视频...</Text>
        </View>
      )}

      <ScrollView style={styles.scrollView}>
        <View style={styles.header}>
          <TouchableOpacity>
            <Ionicons name="menu" size={24} color="#1c1b1f" />
          </TouchableOpacity>
        </View>

        <Text style={styles.title}>All Workouts</Text>

        <View style={styles.searchContainer}>
          <TextInput
            style={styles.searchInput}
            placeholder="Search"
            placeholderTextColor="#676565"
          />
          <View style={styles.searchIcon}>
            <Ionicons name="search" size={20} color="#676565" />
          </View>
        </View>

        {showResult && analysisResult && (
          <View style={styles.analysisResultContainer}>
            <View style={styles.analysisResultHeader}>
              <Text style={styles.analysisResultTitle}>分析结果</Text>
              <TouchableOpacity onPress={() => setShowResult(false)}>
                <Ionicons name="close" size={24} color="#1c1b1f" />
              </TouchableOpacity>
            </View>
            <View style={styles.analysisResultContent}>
              <Text style={styles.analysisResultText}>
                运动类型: {EXERCISE_NAMES[analysisResult.exercise_type] || analysisResult.exercise_type}
              </Text>
              <Text style={styles.analysisResultText}>
                完成次数: <Text style={styles.highlightText}>{analysisResult.counter}</Text> 次
              </Text>
              {analysisResult.errors_detected && analysisResult.errors_detected.length > 0 ? (
                <View style={styles.errorsContainer}>
                  <Text style={styles.analysisResultText}>检测到的问题:</Text>
                  {analysisResult.errors_detected.map((error: ExerciseError, index: number) => (
                    <View key={index} style={styles.errorItem}>
                      <Ionicons name="alert-circle" size={16} color="#d32f2f" />
                      <Text style={styles.errorText}>{error.type} (出现 {error.count} 次)</Text>
                    </View>
                  ))}
                </View>
              ) : (
                <Text style={styles.goodResultText}>动作标准，未检测到问题！</Text>
              )}
              {/* 添加查看报告按钮 */}
              {(analysisResult.report_path || analysisResult.report_url) && reportHtml && (
                <TouchableOpacity
                  style={styles.viewReportButton}
                  onPress={() => {
                    if (reportHtml) { 
                        setShowReportModal(true); 
                    } else {
                        Alert.alert("报告不可用", "分析报告内容尚未加载或无法加载。");
                    }
                  }}
                >
                  <Ionicons name="document-text-outline" size={18} color="white" />
                  <Text style={styles.viewReportButtonText}>查看分析报告</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>
        )}

        <View style={styles.content}>
          {/* Evening Workout Card */}
          <View style={styles.section}>
            <TouchableOpacity
              style={styles.workoutCard}
              onPress={() => toggleWorkout('evening')}
            >
              <View style={styles.workoutImageContainer}>
                <Image
                  source={{ uri: 'https://via.placeholder.com/80' }}
                  style={styles.workoutImage}
                />
              </View>
              <View style={styles.workoutInfo}>
                <Text style={styles.workoutTitle}>力量训练</Text>
                <Text style={styles.workoutSubtitle}>+25 分钟</Text>
              </View>
              <View style={styles.toggleIcon}>
                <Ionicons
                  name={openWorkout === 'evening' ? 'chevron-up' : 'chevron-down'}
                  size={20}
                  color="#1c1b1f"
                />
              </View>
            </TouchableOpacity>

            {/* Evening Workout Exercises */}
            {openWorkout === 'evening' && (
              <View style={styles.exercisesList}>
                {eveningExercises.map((exercise, index) => (
                  <View key={index} style={styles.exerciseItem}>
                    <ExerciseCard
                      exercise={exercise}
                      onAnalyze={() => openAnalysisModal(exercise.type || 'squat')}
                    />
                  </View>
                ))}
              </View>
            )}
          </View>

          {/* Night Stretches Card */}
          <View style={styles.section}>
            <TouchableOpacity
              style={styles.workoutCard}
              onPress={() => toggleWorkout('night')}
            >
              <View style={styles.workoutImageContainer}>
                <Image
                  source={{ uri: 'https://via.placeholder.com/80' }}
                  style={styles.workoutImage}
                />
              </View>
              <View style={styles.workoutInfo}>
                <Text style={styles.workoutTitle}>夜间拉伸</Text>
                <Text style={styles.workoutSubtitle}>+15 分钟</Text>
              </View>
              <View style={styles.toggleIcon}>
                <Ionicons
                  name={openWorkout === 'night' ? 'chevron-up' : 'chevron-down'}
                  size={20}
                  color="#1c1b1f"
                />
              </View>
            </TouchableOpacity>

            {/* Night Stretches Exercises */}
            {openWorkout === 'night' && (
              <View style={styles.exercisesList}>
                {nightStretches.map((stretch, index) => (
                  <View key={index} style={styles.exerciseItem}>
                    <StretchCard stretch={stretch} />
                  </View>
                ))}
              </View>
            )}
          </View>
        </View>
      </ScrollView>

      {/* 视频选择模态框 */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={modalVisible}
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>选择视频来源</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)}>
                <Ionicons name="close" size={24} color="#1c1b1f" />
              </TouchableOpacity>
            </View>

            <Text style={styles.modalSubtitle}>
              选择一个视频进行{EXERCISE_NAMES[selectedExercise] || selectedExercise}动作分析
            </Text>

            <View style={styles.modalButtons}>
              <TouchableOpacity style={styles.modalButton} onPress={pickVideo}>
                <Ionicons name="images" size={24} color="#6A5ACD" />
                <Text style={styles.modalButtonText}>从相册选择</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.modalButton} onPress={recordVideo}>
                <Ionicons name="videocam" size={24} color="#6A5ACD" />
                <Text style={styles.modalButtonText}>录制新视频</Text>
              </TouchableOpacity>
            </View>

            {/* 开发测试选项 */}
            <View style={styles.devSection}>
              <Text style={styles.devSectionTitle}>开发测试选项</Text>
              <View style={styles.devButtons}>
                <TouchableOpacity
                  style={styles.devButton}
                  onPress={() => useTestVideo(selectedExercise)}
                >
                  <Ionicons name="code-working" size={20} color="#6A5ACD" />
                  <Text style={styles.devButtonText}>使用测试视频</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.devButton}
                  onPress={() => simulateAnalysisResult(selectedExercise)}
                >
                  <Ionicons name="bug" size={20} color="#6A5ACD" />
                  <Text style={styles.devButtonText}>模拟分析结果</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </View>
      </Modal>

      {/* 分析报告模态框 */}
      {analysisResult && reportHtml && showReportModal && (
        <Modal
          animationType="slide"
          transparent={false}
          visible={showReportModal} 
          onRequestClose={() => setShowReportModal(false)}
        >
          <SafeAreaView style={{ flex: 1 }}>
            <View style={styles.reportModalHeader}>
              <Text style={styles.reportModalTitle}>分析报告: {EXERCISE_NAMES[analysisResult.exercise_type] || analysisResult.exercise_type}</Text>
              <TouchableOpacity onPress={() => setShowReportModal(false)}>
                <Ionicons name="close" size={24} color="#1c1b1f" />
              </TouchableOpacity>
            </View>
            <WebView
              originWhitelist={['*']}
              source={{ html: reportHtml }} 
              style={{ flex: 1 }}
              onError={handleWebViewError} // 使用新的处理函数
              onHttpError={handleWebViewHttpError} // 使用新的处理函数
              javaScriptEnabled={true}
              domStorageEnabled={true}
              startInLoadingState={true}
              renderLoading={() => (
                <View style={{flex: 1, justifyContent: 'center', alignItems: 'center'}}>
                  <ActivityIndicator size="large" color="#6A5ACD" />
                </View>
              )}
            />
          </SafeAreaView>
        </Modal>
      )}
    </SafeAreaView>
  );
}

interface Exercise {
  name: string;
  sets: number;
  reps: number;
  rest: number;
  image: string;
  type?: string; // 用于API请求的运动类型
}

interface Stretch {
  name: string;
  duration: number;
  image: string;
}

const eveningExercises: Exercise[] = [
  {
    name: "深蹲",
    sets: 3,
    reps: 12,
    rest: 60,
    image: "https://via.placeholder.com/80",
    type: "squat"
  },
  {
    name: "俯卧撑",
    sets: 3,
    reps: 10,
    rest: 45,
    image: "https://via.placeholder.com/80",
    type: "pushup"
  },
  {
    name: "仰卧起坐",
    sets: 3,
    reps: 15,
    rest: 45,
    image: "https://via.placeholder.com/80",
    type: "situp"
  },
  {
    name: "平板支撑",
    sets: 3,
    reps: 30,
    rest: 30,
    image: "https://via.placeholder.com/80",
    type: "plank"
  },
  {
    name: "开合跳",
    sets: 3,
    reps: 20,
    rest: 60,
    image: "https://via.placeholder.com/80",
    type: "jumping_jack"
  },
];

const nightStretches: Stretch[] = [
  {
    name: "颈部拉伸",
    duration: 30,
    image: "https://via.placeholder.com/80",
  },
  {
    name: "肩部拉伸",
    duration: 45,
    image: "https://via.placeholder.com/80",
  },
  {
    name: "腿筋拉伸",
    duration: 60,
    image: "https://via.placeholder.com/80",
  },
  {
    name: "下背部拉伸",
    duration: 45,
    image: "https://via.placeholder.com/80",
  },
  {
    name: "髋部拉伸",
    duration: 60,
    image: "https://via.placeholder.com/80",
  },
];

function ExerciseCard({ exercise, onAnalyze }: { exercise: Exercise, onAnalyze?: () => void }) {
  return (
    <View style={styles.card}>
      <View style={styles.cardImageContainer}>
        <Image
          source={{ uri: exercise.image }}
          style={styles.cardImage}
        />
      </View>
      <View style={styles.cardInfo}>
        <Text style={styles.cardTitle}>{exercise.name}</Text>
        <Text style={styles.cardSubtitle}>
          {exercise.sets} 组 • {exercise.reps} {exercise.name === "平板支撑" ? "秒" : "次"}
        </Text>
      </View>
      <View style={styles.cardActions}>
        <View style={styles.cardTag}>
          <Text style={styles.cardTagText}>休息 {exercise.rest}秒</Text>
        </View>
        {onAnalyze && (
          <TouchableOpacity
            style={styles.analyzeButton}
            onPress={onAnalyze}
          >
            <Ionicons name="videocam" size={16} color="white" />
            <Text style={styles.analyzeButtonText}>分析</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

function StretchCard({ stretch }: { stretch: Stretch }) {
  return (
    <View style={styles.card}>
      <View style={styles.cardImageContainer}>
        <Image
          source={{ uri: stretch.image }}
          style={styles.cardImage}
        />
      </View>
      <View style={styles.cardInfo}>
        <Text style={styles.cardTitle}>{stretch.name}</Text>
        <Text style={styles.cardSubtitle}>保持 {stretch.duration} 秒</Text>
      </View>
      <View style={styles.cardTag}>
        <Text style={styles.cardTagText}>{stretch.duration}秒</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f8f8',
    paddingTop: StatusBar.currentHeight,
  },
  scrollView: {
    flex: 1,
    padding: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: '600',
    marginBottom: 16,
    color: '#1c1b1f',
  },
  searchContainer: {
    position: 'relative',
    marginBottom: 24,
  },
  searchInput: {
    width: '100%',
    backgroundColor: 'white',
    borderRadius: 25,
    padding: 12,
    paddingLeft: 40,
    borderWidth: 1,
    borderColor: '#d9d9d9',
  },
  searchIcon: {
    position: 'absolute',
    left: 12,
    top: '50%',
    transform: [{ translateY: -10 }],
  },
  content: {
    marginBottom: 20,
  },
  section: {
    marginBottom: 32,
  },
  workoutCard: {
    backgroundColor: '#e4dafa',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
  },
  workoutImageContainer: {
    width: 80,
    height: 80,
    marginRight: 16,
    borderRadius: 8,
    overflow: 'hidden',
  },
  workoutImage: {
    width: '100%',
    height: '100%',
  },
  workoutInfo: {
    flex: 1,
  },
  workoutTitle: {
    fontSize: 20,
    fontWeight: '500',
    color: '#1c1b1f',
  },
  workoutSubtitle: {
    fontSize: 14,
    color: '#676565',
  },
  toggleIcon: {
    padding: 4,
    backgroundColor: 'white',
    borderRadius: 20,
  },
  exercisesList: {
    marginTop: 12,
  },
  exerciseItem: {
    marginBottom: 12,
  },
  card: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
  },
  cardImageContainer: {
    width: 64,
    height: 64,
    marginRight: 16,
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cardImage: {
    width: 50,
    height: 50,
  },
  cardInfo: {
    flex: 1,
  },
  cardTitle: {
    fontWeight: '500',
  },
  cardSubtitle: {
    fontSize: 14,
    color: '#676565',
  },
  cardActions: {
    alignItems: 'flex-end',
  },
  cardTag: {
    backgroundColor: '#f5f5f5',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
    marginBottom: 8,
  },
  cardTagText: {
    fontSize: 14,
  },
  analyzeButton: {
    backgroundColor: '#6A5ACD',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    flexDirection: 'row',
    alignItems: 'center',
  },
  analyzeButtonText: {
    color: 'white',
    fontSize: 14,
    marginLeft: 4,
  },
  viewReportButton: {
    backgroundColor: '#007bff',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 12,
  },
  viewReportButtonText: {
    color: 'white',
    fontSize: 14,
    marginLeft: 8,
  },

  // 模态框样式
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    width: '100%',
    maxWidth: 400,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#1c1b1f',
  },
  modalSubtitle: {
    fontSize: 16,
    color: '#676565',
    marginBottom: 20,
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  modalButton: {
    alignItems: 'center',
    padding: 16,
    borderRadius: 8,
    backgroundColor: '#f5f5f5',
    width: '45%',
  },
  modalButtonText: {
    marginTop: 8,
    color: '#1c1b1f',
    fontWeight: '500',
  },

  // 加载样式
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  loadingText: {
    color: 'white',
    marginTop: 12,
    fontSize: 16,
  },

  // 分析结果样式
  analysisResultContainer: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  analysisResultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  analysisResultTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1c1b1f',
  },
  analysisResultContent: {
    paddingVertical: 8,
  },
  analysisResultText: {
    fontSize: 16,
    marginBottom: 8,
    color: '#1c1b1f',
  },
  highlightText: {
    fontWeight: '700',
    color: '#6A5ACD',
  },
  errorsContainer: {
    marginTop: 8,
  },
  errorItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
    backgroundColor: '#ffebee',
    padding: 8,
    borderRadius: 8,
  },
  errorText: {
    marginLeft: 8,
    color: '#d32f2f',
  },
  goodResultText: {
    color: '#4caf50',
    fontWeight: '500',
    fontSize: 16,
    marginTop: 8,
  },
  reportModalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    backgroundColor: 'white',
  },
  reportModalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1c1b1f',
  },

  // 开发测试选项样式
  devSection: {
    marginTop: 20,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    paddingTop: 16,
  },
  devSectionTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#757575',
    marginBottom: 12,
    textAlign: 'center',
  },
  devButtons: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  devButton: {
    alignItems: 'center',
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#f5f5f5',
    width: '45%',
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderStyle: 'dashed',
  },
  devButtonText: {
    marginTop: 6,
    color: '#757575',
    fontSize: 13,
  },
});