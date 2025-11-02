import { useState } from 'react'
import FileUploader from './components/FileUploader'
import ModelBlender from './components/ModelBlender'
import './App.css'

function App() {
  const [userId, setUserId] = useState('')
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [selectedFileName, setSelectedFileName] = useState('')

  // 모델 파일 조회용 입력값
  const [indexUserId, setIndexUserId] = useState('')
  const [modelFiles, setModelFiles] = useState({ indexes: [], pths: [], prefix: '', bucket: '', user_id: '' })
  const [isDownloading, setIsDownloading] = useState(false)
  const [progress, setProgress] = useState(0) // 0~100
  const [downloadSummary, setDownloadSummary] = useState('')

  const handleUploadSuccess = (result) => {
    setUploadedFiles((prev) => [
      ...prev,
      { file_name: result.file_name, s3_prefix: result.s3_prefix, bucket: result.bucket },
    ])
  }

  const fetchFiles = async (uid) => {
    const res = await fetch(`/api/models/files?user_id=${encodeURIComponent(uid)}`)
    const data = await res.json()
    if (!res.ok) throw new Error(data?.detail || '조회 실패')
    return data
  }

  const sanitize = (val) => val.replace(/[^A-Za-z0-9]/g, '')

  const downloadByKey = async (key) => {
    // 한글 주석: presign → 실패 시 백엔드 프록시(download)로 폴백
    try {
      const res = await fetch(`/api/models/presign?key=${encodeURIComponent(key)}`, { cache: 'no-store' })
      if (!res.ok) throw new Error('presign-failed')
      const { url } = await res.json()
      const a = document.createElement('a')
      a.href = url
      a.download = (key.split('/').pop() || 'model')
      a.rel = 'noopener'
      document.body.appendChild(a)
      a.click()
      a.remove()
    } catch (_) {
      const url = `/api/models/download?key=${encodeURIComponent(key)}`
      const a = document.createElement('a')
      a.href = url
      a.download = (key.split('/').pop() || 'model')
      a.rel = 'noopener'
      document.body.appendChild(a)
      a.click()
      a.remove()
    }
    await new Promise((r) => setTimeout(r, 120))
  }

  const onClickFindIndexes = async () => {
    try {
      const uid = sanitize(indexUserId)
      if (!uid) throw new Error('사용자 ID를 입력해주세요')
      const data = await fetchFiles(uid)
      setModelFiles(data)
      // 한글 주석: ZIP으로 묶어 단건 다운로드 (브라우저 자동 다운로드 제한 회피)
      setIsDownloading(true)
      setProgress(0)
      setDownloadSummary('')
      try {
        const url = `/api/models/archive?user_id=${encodeURIComponent(uid)}`
        const res = await fetch(url)
        if (!res.ok || !res.body) throw new Error('아카이브 생성/다운로드 실패')
        const total = Number(res.headers.get('content-length') || 0)
        const reader = res.body.getReader()
        const chunks = []
        let received = 0
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          chunks.push(value)
          received += value.byteLength
          if (total > 0) setProgress(Math.min(100, Math.round((received / total) * 100)))
        }
        const blob = new Blob(chunks, { type: 'application/zip' })
        const dlUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = dlUrl
        a.download = `${uid}_models.zip`
        a.rel = 'noopener'
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(dlUrl)
        setDownloadSummary(`다운로드 완료: index ${data.indexes?.length || 0}개, pth ${data.pths?.length || 0}개 (zip)`) 
      } finally {
        setIsDownloading(false)
        setTimeout(() => setProgress(0), 500)
      }
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
            placeholder="영어/숫자만 입력 가능"
          />
        </div>

        {/* 업로드 드롭존 패널 */}
        <FileUploader
          userId={userId}
          onUploadSuccess={handleUploadSuccess}
        />

        {/* 음성 모델 파일 찾기 패널 */}
        <div className="panel">
          <div className="panel-title">음성 모델 파일 찾기</div>
          <div className="panel-row">
            <label htmlFor="indexUserId">사용자 ID</label>
            <input
              id="indexUserId"
              type="text"
              value={indexUserId}
              onChange={(e) => setIndexUserId(e.target.value)}
              onBlur={() => setIndexUserId(sanitize(indexUserId))}
              placeholder="영어/숫자만 입력 가능"
            />
            <button className="btn btn-secondary" onClick={onClickFindIndexes} disabled={isDownloading}>
              {isDownloading ? '다운로드 중...' : '찾기'}
            </button>
          </div>
          {(isDownloading || !!downloadSummary) && (
            <div className="select-section">
              <div className="select-header">다운로드 상태</div>
              {isDownloading && (
                <div className="select-desc">{progress > 0 ? `${progress}%` : '준비 중...'}</div>
              )}
              {!isDownloading && !!downloadSummary && (
                <div className="select-desc">{downloadSummary}</div>
              )}
            </div>
          )}
        </div>

        {/* 모델 블렌딩 패널 */}
        <ModelBlender />
      </div>
    </div>
  )
}

export default App

