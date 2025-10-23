import { useState } from 'react'
import FileUploader from './components/FileUploader'
import ModelBlender from './components/ModelBlender'
import './App.css'

function App() {
  const [userId, setUserId] = useState('')
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [selectedFileName, setSelectedFileName] = useState('')

  // 인덱스 찾기용 별도 입력값 (기본값 비움)
  const [indexUserId, setIndexUserId] = useState('')

  const handleUploadSuccess = (result) => {
    setUploadedFiles((prev) => [
      ...prev,
      { file_name: result.file_name, s3_prefix: result.s3_prefix, bucket: result.bucket },
    ])
  }

  const fetchIndexes = async (uid) => {
    const res = await fetch(`http://localhost:8000/models/indexes?user_id=${encodeURIComponent(uid)}`)
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail || '조회 실패')
    return data
  }

  const sanitize = (val) => val.replace(/[^A-Za-z]/g, '')

  const onClickFindIndexes = async () => {
    try {
      const uid = sanitize(indexUserId)
      if (!uid) throw new Error('사용자 ID는 영어 알파벳만 입력해주세요.')
      const data = await fetchIndexes(uid)
      alert(`Index 파일 ${data.indexes.length}개\n` + data.indexes.map((k) => `- ${k}`).join('\n'))
    } catch (e) {
      alert('조회 실패: ' + e.message)
    }
  }

  return (
    <div className="app">
      <div className="container">
        <header className="header">
          <h1>음성 학습</h1>
          <p>학습을 위한 오디오 업로드</p>
        </header>

        {/* 업로드용 사용자 ID */}
        <div className="user-input">
          <label htmlFor="userId">사용자 ID</label>
          <input
            id="userId"
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            onBlur={() => setUserId(sanitize(userId))}
            placeholder="영어 알파벳만 입력해주세요 (특수문자 불가)"
          />
        </div>

        {/* 업로드 드롭존 패널 */}
        <FileUploader
          userId={userId}
          onUploadSuccess={handleUploadSuccess}
        />

        {/* 음성 모델 인덱스 찾기 패널 */}
        <div className="panel">
          <div className="panel-title">음성 모델 index 찾기</div>
          <div className="panel-row">
            <label htmlFor="indexUserId">사용자 ID</label>
            <input
              id="indexUserId"
              type="text"
              value={indexUserId}
              onChange={(e) => setIndexUserId(e.target.value)}
              onBlur={() => setIndexUserId(sanitize(indexUserId))}
              placeholder="영어 알파벳만 입력해주세요 (특수문자 불가)"
            />
            <button className="btn btn-secondary" onClick={onClickFindIndexes}>찾기</button>
          </div>
        </div>

        {/* 모델 블렌딩 패널 */}
        <ModelBlender />
      </div>
    </div>
  )
}

export default App

