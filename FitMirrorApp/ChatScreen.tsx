import React, { useState, useRef, useEffect } from 'react';
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
  KeyboardAvoidingView,
  Platform,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

// 定义聊天消息类型接口
interface ChatMessage {
  id: number;
  sender: string;
  message: string;
  timestamp: string;
  isError?: boolean;
  isWarning?: boolean;
  isLoading?: boolean;
  renderAsPlainText?: boolean;
}

// API配置
const API_BASE_URL = 'http://10.0.2.2:5000'; // 安卓模拟器访问本机的地址
// const API_BASE_URL = 'http://localhost:5000'; // iOS模拟器访问本机的地址

export default function ChatScreen() {
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [apiAvailable, setApiAvailable] = useState(true);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([
    {
      id: 1,
      sender: 'bot',
      message: '你好！我是你的健身助手，可以为你提供健身指导和建议。请问你需要什么帮助？',
      timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
    }
  ]);

  // 使用 useRef 替代 this
  const scrollViewRef = useRef<ScrollView>(null);

  // 检查API服务器是否可用
  useEffect(() => {
    const checkApiStatus = async () => {
      try {
        console.log(`尝试连接API服务器: ${API_BASE_URL}/health`);
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        console.log('API服务器健康检查响应:', data);

        setApiAvailable(data.agent_status === 'available');

        if (data.agent_status !== 'available') {
          console.warn('FitMirror Agent不可用，聊天功能可能受限');

          // 添加一条系统消息，告知用户聊天功能受限
          const systemMessage = {
            id: chatHistory.length + 1,
            sender: 'bot',
            message: '⚠️ 注意：FitMirror Agent当前不可用，聊天功能受限。您仍然可以使用动作分析功能。',
            timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}),
            isWarning: true
          };

          setChatHistory(prev => [...prev, systemMessage]);
        }
      } catch (error) {
        console.error('API服务器连接失败:', error);
        setApiAvailable(false);

        // 添加一条系统消息，告知用户连接失败
        const errorMessage = {
          id: chatHistory.length + 1,
          sender: 'bot',
          message: '⚠️ 无法连接到FitMirror服务器，请确保服务器已启动并且网络连接正常。聊天功能暂时不可用，但您可以尝试使用动作分析功能。',
          timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}),
          isError: true
        };

        setChatHistory(prev => [...prev, errorMessage]);

        Alert.alert(
          '连接失败',
          '无法连接到FitMirror服务器，请确保服务器已启动并且网络连接正常。',
          [{ text: '确定' }]
        );
      }
    };

    checkApiStatus();
  }, []);

  const sendMessage = async () => {
    if (message.trim() === '') return;

    // 如果API不可用，显示提示
    if (!apiAvailable) {
      Alert.alert(
        '服务不可用',
        'FitMirror服务器当前不可用，请稍后再试。',
        [{ text: '确定' }]
      );
      return;
    }

    // 添加用户消息到聊天历史
    const userMessage = message.trim();
    const newMessage = {
      id: chatHistory.length + 1,
      sender: 'user',
      message: userMessage,
      timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
    };

    setChatHistory(prev => [...prev, newMessage]);
    setMessage('');

    // 添加临时的"正在输入"消息
    const tempId = chatHistory.length + 2;
    const loadingMessage = {
      id: tempId,
      sender: 'bot',
      message: '正在思考...',
      timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}),
      isLoading: true
    };

    setChatHistory(prev => [...prev, loadingMessage]);
    setIsLoading(true);

    try {
      // 调用后端API
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage
        })
      });

      const data = await response.json();

      // 移除临时的加载消息
      setChatHistory(prev => prev.filter(msg => msg.id !== tempId));

      if (data.success) {
        // 添加AI回复
        const botReply = {
          id: tempId,
          sender: 'bot',
          message: data.message,
          timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
        };

        setChatHistory(prev => [...prev, botReply]);
      } else {
        // 处理错误
        const errorMessage = data.message || '未知错误';
        // 确保错误消息不包含Markdown格式，避免渲染问题
        const sanitizedErrorMessage = errorMessage.replace(/[*_#`]/g, '');

        const errorReply = {
          id: tempId,
          sender: 'bot',
          message: `抱歉，处理您的请求时出现问题: ${sanitizedErrorMessage}`,
          timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}),
          isError: true,
          renderAsPlainText: true
        };

        setChatHistory(prev => [...prev, errorReply]);
      }
    } catch (error) {
      // 移除临时的加载消息
      setChatHistory(prev => prev.filter(msg => msg.id !== tempId));

      // 添加错误消息，确保不包含Markdown格式
      const errorReply = {
        id: tempId,
        sender: 'bot',
        message: '抱歉，连接服务器时出现问题，请检查网络连接或稍后再试。',
        timestamp: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}),
        isError: true,
        // 设置为用户消息类型，这样就不会尝试渲染Markdown
        renderAsPlainText: true
      };

      setChatHistory(prev => [...prev, errorReply]);
      console.error('API请求失败:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity>
          <Ionicons name="menu" size={24} color="#1c1b1f" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>健身助手</Text>
        <TouchableOpacity>
          <Ionicons name="information-circle-outline" size={24} color="#1c1b1f" />
        </TouchableOpacity>
      </View>

      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={styles.content}
        keyboardVerticalOffset={100}
      >
        <ScrollView
          style={styles.chatContainer}
          contentContainerStyle={styles.chatContent}
          ref={scrollViewRef}
          onContentSizeChange={() => {
            if (scrollViewRef.current) {
              scrollViewRef.current.scrollToEnd({ animated: true });
            }
          }}
        >
          {chatHistory.map((chat) => (
            <View
              key={chat.id}
              style={[
                styles.messageBubble,
                chat.sender === 'user' ? styles.userBubble : styles.botBubble
              ]}
            >
              {chat.sender === 'bot' && (
                <View style={styles.botAvatarContainer}>
                  <View style={styles.botAvatar}>
                    <Ionicons name="fitness" size={20} color="white" />
                  </View>
                </View>
              )}
              <View style={[
                styles.messageContent,
                chat.sender === 'user' ? styles.userMessageContent : styles.botMessageContent,
                chat.isError ? styles.errorMessageContent : null,
                chat.isWarning ? styles.warningMessageContent : null
              ]}>
                {chat.isLoading ? (
                  <View style={styles.loadingContainer}>
                    <ActivityIndicator size="small" color="#6A5ACD" />
                    <Text style={[styles.messageText, styles.botText, styles.loadingText]}>
                      {chat.message}
                    </Text>
                  </View>
                ) : (
                  <Text style={[
                    styles.messageText,
                    chat.sender === 'user' ? styles.userText : styles.botText,
                    chat.isError ? styles.errorText : null,
                    chat.isWarning ? styles.warningText : null
                  ]}>
                    {/* 简单处理Markdown格式，将常见的Markdown标记替换为空格 */}
                    {chat.message.replace(/(\*\*|__)(.*?)\1/g, '$2')  // 处理粗体
                              .replace(/(\*|_)(.*?)\1/g, '$2')        // 处理斜体
                              .replace(/^(#+)\s+(.*)$/gm, '$2')       // 处理标题
                              .replace(/^[-*+]\s+(.*)$/gm, '• $1')    // 处理无序列表
                              .replace(/^(\d+)\.\s+(.*)$/gm, '$1. $2') // 处理有序列表
                    }
                  </Text>
                )}
                <Text style={styles.timestamp}>{chat.timestamp}</Text>
              </View>
            </View>
          ))}
        </ScrollView>

        <View style={styles.inputContainer}>
          <View style={styles.inputWrapper}>
            <TextInput
              style={styles.input}
              placeholder="输入你的问题..."
              value={message}
              onChangeText={setMessage}
              multiline
            />
            <TouchableOpacity style={styles.sendButton} onPress={sendMessage}>
              <Ionicons name="send" size={20} color="white" />
            </TouchableOpacity>
          </View>

          <View style={styles.suggestionContainer}>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              <TouchableOpacity style={styles.suggestionChip}>
                <Text style={styles.suggestionText}>如何减脂？</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.suggestionChip}>
                <Text style={styles.suggestionText}>增肌饮食</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.suggestionChip}>
                <Text style={styles.suggestionText}>初学者训练计划</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.suggestionChip}>
                <Text style={styles.suggestionText}>每日热身动作</Text>
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f8f8',
    paddingTop: StatusBar.currentHeight,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    backgroundColor: 'white',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1c1b1f',
  },
  content: {
    flex: 1,
  },
  chatContainer: {
    flex: 1,
    padding: 16,
  },
  chatContent: {
    flexGrow: 1,
    paddingBottom: 16,
  },
  messageBubble: {
    flexDirection: 'row',
    marginBottom: 16,
    maxWidth: '80%',
  },
  userBubble: {
    alignSelf: 'flex-end',
  },
  botBubble: {
    alignSelf: 'flex-start',
  },
  botAvatarContainer: {
    marginRight: 8,
    alignItems: 'center',
    justifyContent: 'flex-start',
    paddingTop: 4,
  },
  botAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#e4dafa',
    alignItems: 'center',
    justifyContent: 'center',
  },
  messageContent: {
    borderRadius: 16,
    padding: 12,
  },
  userMessageContent: {
    backgroundColor: '#e4dafa',
    borderTopRightRadius: 0,
  },
  botMessageContent: {
    backgroundColor: 'white',
    borderTopLeftRadius: 0,
  },
  errorMessageContent: {
    backgroundColor: '#ffebee',
    borderTopLeftRadius: 0,
  },
  warningMessageContent: {
    backgroundColor: '#fff8e1',
    borderTopLeftRadius: 0,
  },
  userText: {
    color: '#1c1b1f',
  },
  botText: {
    color: '#1c1b1f',
  },
  errorText: {
    color: '#d32f2f',
  },
  warningText: {
    color: '#ff8f00',
  },

  messageText: {
    fontSize: 15,
    lineHeight: 20,
  },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  loadingText: {
    marginLeft: 8,
    fontStyle: 'italic',
  },
  timestamp: {
    fontSize: 11,
    color: '#676565',
    alignSelf: 'flex-end',
    marginTop: 4,
  },
  inputContainer: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  input: {
    flex: 1,
    backgroundColor: '#f1f1f1',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    maxHeight: 100,
  },
  sendButton: {
    backgroundColor: '#e4dafa',
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },
  suggestionContainer: {
    marginTop: 12,
  },
  suggestionChip: {
    backgroundColor: '#f1f1f1',
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginRight: 8,
  },
  suggestionText: {
    fontSize: 13,
    color: '#676565',
  },
});