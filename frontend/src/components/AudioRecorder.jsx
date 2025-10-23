import { useState, useRef } from 'react'
import axios from 'axios'
import './AudioRecorder.css'

function AudioRecorder({ userId, onUploadSuccess }) {
  const [isRecording, setIsRecording] = useState(false)
  const [audioURL, setAudioURL] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const timerRef = useRef(null)

  // 녹음 시작
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }
      
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        const url = URL.createObjectURL(audioBlob)
        setAudioURL(url)
        
        // 스트림 정리
        stream.getTracks().forEach(track => track.stop())
      }
      
      mediaRecorder.start()
      setIsRecording(true)
      setRecordingTime(0)
      
      // 타이머 시작
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1)
      }, 1000)
      
    } catch (error) {
      console.error('녹음 시작 실패:', error)
      alert('마이크 접근 권한이 필요합니다.')
    }
  }

  // 녹음 정지
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      clearInterval(timerRef.current)
    }
  }

  // S3 업로드
  const uploadToS3 = async () => {
    if (!audioURL) return
    
    setIsUploading(true)
    
    try {
      // Blob 생성
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
      
      // FormData 생성
      const formData = new FormData()
      const fileName = `recording_${Date.now()}.webm`
      formData.append('file', audioBlob, fileName)
      
      // API 호출
      const response = await axios.post(
        `http://localhost:8000/upload?user_id=${userId}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      )
      
      // 성공 처리
      onUploadSuccess(response.data)
      
      // 초기화
      setAudioURL('')
      audioChunksRef.current = []
      setRecordingTime(0)
      
      alert('업로드 성공!')
      
    } catch (error) {
      console.error('업로드 실패:', error)
      alert('업로드 실패: ' + (error.response?.data?.detail || error.message))
    } finally {
      setIsUploading(false)
    }
  }

  // 시간 포맷팅
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="audio-recorder">
      <h3>🎤 음성 녹음</h3>
      
      <div className="recorder-controls">
        {!isRecording && !audioURL && (
          <button className="btn btn-record" onClick={startRecording}>
            녹음 시작
          </button>
        )}
        
        {isRecording && (
          <>
            <div className="recording-indicator">
              <span className="pulse"></span>
              <span className="time">{formatTime(recordingTime)}</span>
            </div>
            <button className="btn btn-stop" onClick={stopRecording}>
              녹음 정지
            </button>
          </>
        )}
        
        {audioURL && !isRecording && (
          <div className="audio-preview">
            <audio src={audioURL} controls />
            <div className="preview-actions">
              <button 
                className="btn btn-upload" 
                onClick={uploadToS3}
                disabled={isUploading}
              >
                {isUploading ? '업로드 중...' : 'S3에 업로드'}
              </button>
              <button 
                className="btn btn-reset" 
                onClick={() => setAudioURL('')}
                disabled={isUploading}
              >
                다시 녹음
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default AudioRecorder

