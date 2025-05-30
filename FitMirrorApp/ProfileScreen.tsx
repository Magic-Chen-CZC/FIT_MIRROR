import React, { useState, useCallback } from 'react';
import { 
  View, Text, StyleSheet, FlatList, TouchableOpacity, 
  ActivityIndicator, SafeAreaView, Button, Modal, Alert
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import WebView from 'react-native-webview'; // Import WebView directly
import { type WebViewProps } from 'react-native-webview'; // Import WebViewProps for event types

// Define event types based on WebViewProps if not directly exportable
type WebViewErrorEvent = WebViewProps['onError'] extends ((event: infer E) => void) | undefined ? E : never;
type WebViewHttpErrorEvent = WebViewProps['onHttpError'] extends ((event: infer E) => void) | undefined ? E : never;

// 更新的报告数据结构以匹配后端
interface Report {
  filename: string;
  exercise_type: string;
  date_str: string;
  report_url: string; // 虽然暂时不用来显示详情，但保留以备后用
  timestamp: number;
}

// !! 重要: 请将 YOUR_COMPUTER_IP_ADDRESS 替换为你运行后端服务器的电脑的局域网IP地址 !!
// 例如: const API_BASE_URL = 'http://192.168.1.101:5000';
const API_BASE_URL = 'http://10.38.86.85:5000'; 

const ProfileScreen = () => {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [isReportModalVisible, setIsReportModalVisible] = useState(false);
  const [currentReportUrl, setCurrentReportUrl] = useState<string | null>(null);
  const [isWebViewLoading, setIsWebViewLoading] = useState(false); 

  const fetchReports = useCallback(async () => {
    setLoading(true);
    console.log("ProfileScreen: Fetching reports...");
    try {
      const response = await fetch(`${API_BASE_URL}/get-analysis-reports`);
      if (!response.ok) {
        const errorText = await response.text();
        console.error("ProfileScreen: HTTP error!", response.status, errorText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      // 确保后端返回的是 { success: boolean, reports: Report[] } 结构
      const responseData = await response.json(); 
      if (responseData && responseData.success && Array.isArray(responseData.reports)) {
        setReports(responseData.reports);
        console.log("ProfileScreen: Reports fetched successfully - ", responseData.reports.length, "reports");
      } else {
        // 如果responseData.reports不是数组或者responseData.success为false
        console.error("ProfileScreen: Invalid data structure received or request not successful", responseData);
        setReports([]); // 清空或设置为一个明确的空状态
      }
    } catch (error) {
      console.error("ProfileScreen: Failed to fetch reports:", error);
      setReports([]); // 出错时清空报告或显示错误提示
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchReports();
      return () => {
        // Optional cleanup logic
      };
    }, [fetchReports])
  );

  const handleReportItemPress = (report: Report) => {
    console.log("Report item pressed:", report.filename, "url:", report.report_url);
    if (report.report_url) {
      setCurrentReportUrl(report.report_url);
      setIsReportModalVisible(true);
    } else {
      Alert.alert("无法打开报告", "此报告没有可用的URL。");
    }
  };

  const handleWebViewError = (event: WebViewErrorEvent) => {
    const { nativeEvent } = event;
    console.warn('WebView error: ', nativeEvent);
    Alert.alert("加载报告出错", `无法显示分析报告内容. ${nativeEvent.description || nativeEvent.code || ''}`);
  };

  const handleWebViewHttpError = (event: WebViewHttpErrorEvent) => {
    const { nativeEvent } = event;
    console.warn(
      'WebView HTTP error: ',
      nativeEvent.url,
      nativeEvent.statusCode,
      nativeEvent.description,
    );
    Alert.alert("加载报告资源出错", `报告中的部分内容可能无法加载 (HTTP ${nativeEvent.statusCode}).`);
  };


  const renderReportItem = ({ item }: { item: Report }) => (
    <TouchableOpacity style={styles.reportItem} onPress={() => handleReportItemPress(item)}>
      <View style={styles.reportIconContainer}>
        <Ionicons name="document-text-outline" size={24} color="#6A5ACD" />
      </View>
      <View style={styles.reportTextContainer}>
        <Text style={styles.reportTitle}>{item.exercise_type || '运动报告'}</Text>
        <Text style={styles.reportDate}>{item.date_str}</Text>
        {/* 可以考虑显示文件名或其他摘要信息 */}
        <Text style={styles.reportSummary} numberOfLines={1} ellipsizeMode="middle">{item.filename}</Text>
      </View>
      <Ionicons name="chevron-forward-outline" size={24} color="#C0C0C0" />
    </TouchableOpacity>
  );

  if (loading && reports.length === 0) {
    return (
      <SafeAreaView style={styles.centeredContainer}>
        <ActivityIndicator size="large" color="#6A5ACD" />
        <Text style={styles.loadingText}>加载报告中...</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}> 
      <Text style={styles.header}>我的运动报告</Text>
      <FlatList
        data={reports}
        renderItem={renderReportItem}
        keyExtractor={item => item.filename}
        ListEmptyComponent={
          <View style={styles.centeredContainer}> 
            <Text style={styles.emptyText}>暂无运动报告</Text>
            {!loading && <Button title="刷新列表" onPress={fetchReports} color="#6A5ACD" />} 
          </View>
        }
        contentContainerStyle={reports.length === 0 ? styles.emptyListContainer : {}}
        onRefresh={fetchReports} 
        refreshing={loading}    
      />

      {currentReportUrl && (
        <Modal
          animationType="slide"
          transparent={false}
          visible={isReportModalVisible}
          onRequestClose={() => {
            setIsReportModalVisible(false);
            setCurrentReportUrl(null); 
          }}
        >
          <SafeAreaView style={styles.modalSafeArea}>
            <View style={styles.reportModalHeader}>
              <Text style={styles.reportModalTitle}>分析报告</Text>
              <TouchableOpacity onPress={() => {
                setIsReportModalVisible(false);
                setCurrentReportUrl(null);
              }}>
                <Ionicons name="close" size={28} color="#333" />
              </TouchableOpacity>
            </View>
            <WebView
              source={{ uri: currentReportUrl }}
              style={{ flex: 1 }}
              originWhitelist={['*']}
              onLoadStart={() => setIsWebViewLoading(true)}
              onLoadEnd={() => setIsWebViewLoading(false)}
              onError={handleWebViewError}
              onHttpError={handleWebViewHttpError}
              javaScriptEnabled={true}
              domStorageEnabled={true}
              startInLoadingState={true}
              renderLoading={() => (
                <View style={styles.webViewLoadingContainer}>
                  <ActivityIndicator size="large" color="#6A5ACD" />
                  <Text>正在加载报告...</Text>
                </View>
              )}
            />
            {isWebViewLoading && (
              <View style={styles.webViewLoadingOverlay}>
                <ActivityIndicator size="large" color="#6A5ACD" />
                <Text>请稍候...</Text>
              </View>
            )}
          </SafeAreaView>
        </Modal>
      )}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f0f2f5',
    // paddingTop: 50, // SafeAreaView 会处理顶部空间,可以移除或调整
  },
  centeredContainer: { // 新增样式，用于居中显示加载或空状态
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f0f2f5',
  },
  emptyListContainer: { // 新增样式，确保空列表提示也居中
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: { // 新增加载文本样式
    marginTop: 10,
    fontSize: 16,
    color: '#555',
  },
  header: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginLeft: 20,
    marginBottom: 20,
  },
  reportItem: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 15,
    marginHorizontal: 20,
    marginBottom: 15,
    flexDirection: 'row',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  reportIconContainer: {
    marginRight: 15,
    backgroundColor: '#e6e0ff', // 淡紫色背景
    padding: 10,
    borderRadius: 25, // 圆形
  },
  reportTextContainer: {
    flex: 1,
  },
  reportTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  reportDate: {
    fontSize: 12,
    color: '#777',
    marginTop: 2,
  },
  reportSummary: { // 更新了样式以更好显示文件名
    fontSize: 12,
    color: '#888', // 调整颜色使其不那么突出
    marginTop: 4,
  },
  emptyText: {
    textAlign: 'center',
    marginTop: 50,
    fontSize: 16,
    color: '#777',
  },
  // Styles for Report Modal
  modalSafeArea: {
    flex: 1,
    backgroundColor: 'white', // Or your app's background color
  },
  reportModalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 15,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    backgroundColor: 'white',
  },
  reportModalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  webViewLoadingContainer: { // For renderLoading prop
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  webViewLoadingOverlay: { // For overlay during webview loading if needed
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
  },
});

export default ProfileScreen;
