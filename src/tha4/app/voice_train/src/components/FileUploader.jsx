import { useState, useRef } from 'react'
import axios from 'axios'
import './FileUploader.css'

function FileUploader({ userId, onUploadSuccess }) {
  const [selectedFiles, setSelectedFiles] = useState([])
  const [isUploading, setIsUploading] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef(null)

  // 허용 확장자 검사: mp3, m4a, wav
  const isAllowedAudio = (file) => {
    // 한글 주석: 사용자가 올린 파일 확장자를 확인하여 허용 여부 판단
    if (!file || !file.name) return false
    const name = file.name.toLowerCase()
    return name.endsWith('.mp3') || name.endsWith('.m4a') || name.endsWith('.wav')
  }

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files || [])
    const allowed = files.filter(isAllowedAudio)
    if (allowed.length !== files.length) alert('mp3, m4a, wav 파일만 업로드 가능합니다.')
    setSelectedFiles(allowed)
  }

  const handleDragEnter = (e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true) }
  const handleDragLeave = (e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false) }
  const handleDragOver = (e) => { e.preventDefault(); e.stopPropagation() }
  const handleDrop = (e) => {
    e.preventDefault(); e.stopPropagation(); setIsDragging(false)
    const files = Array.from(e.dataTransfer.files || [])
    const allowed = files.filter(isAllowedAudio)
    if (allowed.length !== files.length) alert('mp3, m4a, wav 파일만 업로드 가능합니다.')
    setSelectedFiles(allowed)
  }

  const uploadFiles = async () => {
    if (selectedFiles.length === 0) { alert('mp3, m4a 또는 wav 파일을 선택해주세요'); return }
    setIsUploading(true)
    try {
      const formData = new FormData()
      selectedFiles.forEach(file => formData.append('files', file))
      const response = await axios.post(
        `http://localhost:8000/upload-multiple?user_id=${userId}`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )
      response.data.results.forEach(result => {
        if (result.status === 'success') {
          onUploadSuccess({
            file_name: result.file_name,
            s3_keys: result.s3_keys,
            s3_prefix: response.data.s3_prefix,
            bucket: response.data.bucket
          })
        }
      })
      setSelectedFiles([])
      if (fileInputRef.current) fileInputRef.current.value = ''
      alert(`${response.data.results.length}개 파일 업로드 완료!`)
    } catch (error) {
      console.error('업로드 실패:', error)
      alert('업로드 실패: ' + (error.response?.data?.detail || error.message))
    } finally {
      setIsUploading(false)
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024, sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <div className="file-uploader">
      <div
        className={`drop-zone ${isDragging ? 'dragging' : ''}`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".mp3,.m4a,.wav,audio/mpeg,audio/x-m4a,audio/wav"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />

        <div className="big-copy">
          <div className="big-icon">⬆️</div>
          <div className="big-title">Drop Audio Here</div>
          <div className="big-sep">- or -</div>
          <div className="big-action">Click to Upload (mp3 / m4a / wav)</div>
        </div>

        {selectedFiles.length > 0 && (
          <div className="selected-files">
            <p className="file-count">{selectedFiles.length}개 오디오 파일 선택됨</p>
            <div className="file-list-preview">
              {selectedFiles.map((file, index) => (
                <div key={index} className="file-item-preview">
                  <span className="file-name-preview">{file.name}</span>
                  <span className="file-size">{formatFileSize(file.size)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="upload-actions">
        <button
          className="btn btn-ghost"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
        >
          오디오 선택
        </button>
        <button
          className="btn btn-upload-file"
          onClick={uploadFiles}
          disabled={isUploading || selectedFiles.length === 0}
        >
          {isUploading ? '업로드 중...' : '업로드'}
        </button>
        <button
          className="btn btn-clear"
          onClick={() => { setSelectedFiles([]); if (fileInputRef.current) fileInputRef.current.value = '' }}
          disabled={isUploading || selectedFiles.length === 0}
        >
          선택 취소
        </button>
      </div>
    </div>
  )
}

export default FileUploader

