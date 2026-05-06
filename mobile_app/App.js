import React, { useState, useEffect, useRef } from 'react';
import { 
  StyleSheet, 
  Text, 
  View, 
  TextInput, 
  TouchableOpacity, 
  ScrollView, 
  ActivityIndicator, 
  KeyboardAvoidingView, 
  Platform,
  Alert,
  Modal,
  FlatList
} from 'react-native';
import * as Speech from 'expo-speech';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system';
import { Mic, MicOff, Paperclip, Send, X, FileText, Languages, ThumbsUp, ThumbsDown } from 'lucide-react-native';

const BACKEND_URL = 'http://172.17.135.25:8000'; // Using your local IP

const LANGUAGES = [
  { code: 'en-US', name: 'English' },
  { code: 'hi-IN', name: 'Hindi (हिंदी)' },
  { code: 'es-ES', name: 'Spanish (Español)' },
  { code: 'fr-FR', name: 'French (Français)' },
  { code: 'de-DE', name: 'German (Deutsch)' }
];

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const [selectedLang, setSelectedLang] = useState(LANGUAGES[0]);
  const [showLangModal, setShowLangModal] = useState(false);
  const scrollViewRef = useRef();

  const speak = (text) => {
    Speech.speak(text, { language: selectedLang.code });
  };

  const pickDocument = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'text/plain', 'text/markdown'],
        copyToCacheDirectory: true,
      });

      if (!result.canceled) {
        setFile(result.assets[0]);
      }
    } catch (err) {
      Alert.alert('Error picking document', err.message);
    }
  };

  const handleSend = async () => {
    if (!input.trim() && !file) return;

    const userMsg = { 
      text: input + (file ? ` [File: ${file.name}]` : ''), 
      sender: 'user' 
    };
    
    setMessages(prev => [...prev, userMsg]);
    const currentInput = input;
    const currentFile = file;
    
    setInput('');
    setFile(null);
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('message', currentInput);
      
      if (currentFile) {
        formData.append('file', {
          uri: currentFile.uri,
          name: currentFile.name,
          type: currentFile.mimeType || 'application/octet-stream',
        });
      }

      const response = await fetch(`${BACKEND_URL}/chat`, {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const data = await response.json();
      const botMsg = { 
        text: data.response, 
        sender: 'bot', 
        id: data.message_id, 
        feedback: null 
      };
      setMessages(prev => [...prev, botMsg]);
      speak(data.response);
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { text: 'Error: Could not connect to backend.', sender: 'bot' }]);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (msgId, rating) => {
    try {
      await fetch(`${BACKEND_URL}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: msgId, rating: rating }),
      });
      setMessages(prev => prev.map(m => m.id === msgId ? { ...m, feedback: rating } : m));
    } catch (error) {
      console.error('Feedback error:', error);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>VML Enterprises Technology</Text>
        <TouchableOpacity style={styles.langButton} onPress={() => setShowLangModal(true)}>
          <Languages size={20} color="#2563eb" />
          <Text style={styles.langButtonText}>{selectedLang.code.split('-')[0].toUpperCase()}</Text>
        </TouchableOpacity>
      </View>

      <Modal
        visible={showLangModal}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setShowLangModal(false)}
      >
        <TouchableOpacity 
          style={styles.modalOverlay} 
          activeOpacity={1} 
          onPress={() => setShowLangModal(false)}
        >
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Select Language</Text>
            <FlatList
              data={LANGUAGES}
              keyExtractor={(item) => item.code}
              renderItem={({ item }) => (
                <TouchableOpacity 
                  style={[styles.langItem, selectedLang.code === item.code && styles.selectedLangItem]} 
                  onPress={() => {
                    setSelectedLang(item);
                    setShowLangModal(false);
                  }}
                >
                  <Text style={[styles.langItemText, selectedLang.code === item.code && styles.selectedLangItemText]}>
                    {item.name}
                  </Text>
                </TouchableOpacity>
              )}
            />
          </View>
        </TouchableOpacity>
      </Modal>

      <ScrollView 
        style={styles.chatContainer}
        ref={scrollViewRef}
        onContentSizeChange={() => scrollViewRef.current.scrollToEnd({ animated: true })}
      >
        {messages.map((msg, i) => (
          <View key={i} style={[
            styles.messageWrapper,
            msg.sender === 'user' ? styles.userWrapper : styles.botWrapper
          ]}>
            <View style={[
              styles.messageBubble,
              msg.sender === 'user' ? styles.userBubble : styles.botBubble
            ]}>
              <Text style={[
                styles.messageText,
                msg.sender === 'user' ? styles.userText : styles.botText
              ]}>
                {msg.text}
              </Text>
              
              {msg.sender === 'bot' && msg.id && (
                <View style={styles.feedbackRow}>
                  <TouchableOpacity onPress={() => handleFeedback(msg.id, 1)}>
                    <ThumbsUp 
                      size={16} 
                      color={msg.feedback === 1 ? '#2563eb' : '#9ca3af'} 
                      fill={msg.feedback === 1 ? '#2563eb' : 'transparent'}
                    />
                  </TouchableOpacity>
                  <TouchableOpacity onPress={() => handleFeedback(msg.id, -1)}>
                    <ThumbsDown 
                      size={16} 
                      color={msg.feedback === -1 ? '#ef4444' : '#9ca3af'} 
                      fill={msg.feedback === -1 ? '#ef4444' : 'transparent'}
                    />
                  </TouchableOpacity>
                </View>
              )}
            </View>
          </View>
        ))}
        {loading && (
          <View style={styles.botWrapper}>
            <View style={[styles.messageBubble, styles.botBubble]}>
              <ActivityIndicator size="small" color="#666" />
            </View>
          </View>
        )}
      </ScrollView>

      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        <View style={styles.inputArea}>
          {file && (
            <View style={styles.filePreview}>
              <FileText size={16} color="#2563eb" />
              <Text style={styles.fileName} numberOfLines={1}>{file.name}</Text>
              <TouchableOpacity onPress={() => setFile(null)}>
                <X size={16} color="#2563eb" />
              </TouchableOpacity>
            </View>
          )}
          
          <View style={styles.inputRow}>
            <TouchableOpacity style={styles.iconButton} onPress={pickDocument}>
              <Paperclip size={24} color="#666" />
            </TouchableOpacity>

            <TextInput
              style={styles.input}
              placeholder="Type your message..."
              value={input}
              onChangeText={setInput}
              multiline
            />

            <TouchableOpacity 
              style={[styles.sendButton, (!input.trim() && !file) && styles.disabledSend]} 
              onPress={handleSend}
              disabled={loading || (!input.trim() && !file)}
            >
              <Send size={24} color="#fff" />
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f3f4f6',
  },
  header: {
    paddingTop: 50,
    paddingBottom: 20,
    paddingHorizontal: 20,
    backgroundColor: '#fff',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2563eb',
  },
  langButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#eff6ff',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 15,
    gap: 5,
  },
  langButtonText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#2563eb',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    maxHeight: '50%',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 15,
    textAlign: 'center',
  },
  langItem: {
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
  },
  selectedLangItem: {
    backgroundColor: '#eff6ff',
  },
  langItemText: {
    fontSize: 16,
    color: '#4b5563',
  },
  selectedLangItemText: {
    color: '#2563eb',
    fontWeight: 'bold',
  },
  chatContainer: {
    flex: 1,
    padding: 15,
  },
  messageWrapper: {
    marginBottom: 15,
    flexDirection: 'row',
  },
  userWrapper: {
    justifyContent: 'flex-end',
  },
  botWrapper: {
    justifyContent: 'flex-start',
  },
  messageBubble: {
    padding: 12,
    borderRadius: 20,
    maxWidth: '80%',
  },
  userBubble: {
    backgroundColor: '#2563eb',
  },
  botBubble: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  messageText: {
    fontSize: 16,
    lineHeight: 22,
  },
  userText: {
    color: '#fff',
  },
  botText: {
    color: '#1f2937',
  },
  feedbackRow: {
    flexDirection: 'row',
    gap: 15,
    marginTop: 8,
    paddingTop: 5,
    borderTopWidth: 1,
    borderTopColor: '#f3f4f6',
  },
  inputArea: {
    padding: 15,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  filePreview: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#eff6ff',
    padding: 8,
    borderRadius: 8,
    marginBottom: 10,
    gap: 8,
  },
  fileName: {
    flex: 1,
    fontSize: 14,
    color: '#1e40af',
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 10,
  },
  iconButton: {
    padding: 8,
  },
  input: {
    flex: 1,
    backgroundColor: '#f9fafb',
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 20,
    paddingHorizontal: 15,
    paddingVertical: 8,
    fontSize: 16,
    maxHeight: 100,
  },
  sendButton: {
    backgroundColor: '#2563eb',
    width: 44, height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  disabledSend: {
    backgroundColor: '#93c5fd',
  }
});
