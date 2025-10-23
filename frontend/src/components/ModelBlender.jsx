import { useRef, useState } from 'react'
import './ModelBlender.css'

function ModelBlender() {
  const [name, setName] = useState('')
  const [ratio, setRatio] = useState(0.5)
  const [fileA, setFileA] = useState(null)
  const [fileB, setFileB] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [downloadUrl, setDownloadUrl] = useState('')

  const inputARef = useRef(null)
  const inputBRef = useRef(null)
  const [dragA, setDragA] = useState(false)
  const [dragB, setDragB] = useState(false)

  const isPth = (f) => !!f && f.name?.toLowerCase().endsWith('.pth')

  const onPickA = (e) => {
    const f = e.target.files?.[0]
    if (f && !isPth(f)) return alert('.pth 파일만 선택하세요')
    setFileA(f || null)
  }
  const onPickB = (e) => {
    const f = e.target.files?.[0]
    if (f && !isPth(f)) return alert('.pth 파일만 선택하세요')
    setFileB(f || null)
  }

  const handleDrop = (e, which) => {
    e.preventDefault(); e.stopPropagation()
    const f = e.dataTransfer.files?.[0]
    if (f && !isPth(f)) return alert('.pth 파일만 선택하세요')
    if (which === 'A') { setFileA(f || null); setDragA(false) }
    else { setFileB(f || null); setDragB(false) }
  }

  const onSubmit = async () => {
    if (!name.trim()) return alert('모델 이름을 입력하세요')
    if (!fileA || !fileB) return alert('두 개의 .pth 파일을 선택하세요')
    setIsLoading(true); setMessage(''); setDownloadUrl('')
    try {
      const form = new FormData()
      form.append('name', name.trim())
      form.append('ratio', String(ratio))
      form.append('model_a', fileA)
      form.append('model_b', fileB)
      const res = await fetch('http://localhost:8000/blend/local', { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || '블렌딩 실패')
      setMessage(data.message || '완료')
      setDownloadUrl(`http://localhost:8000${data.download_url}`)
    } catch (e) {
      alert(e.message)
    } finally { setIsLoading(false) }
  }

  const aPct = Math.round(ratio * 100)
  const bPct = 100 - aPct

  return (
    <div className="blend-card">
      <div className="blend-title">보이스 블렌더</div>
      <div className="blend-sub">두 개의 음성 모델을 선택하고 원하는 블렌드 비율을 설정하여 새 모델로 융합하세요.</div>

      {/* 모델 이름 */}
      <div className="row">
        <label className="lbl">모델 이름</label>
        <input
          className="txt"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="새 모델의 이름을 입력"
        />
      </div>

      {/* 드래그앤드롭 - 좌(모델 B) / 우(모델 A) */}
      <div className="drop-grid">
        {/* LEFT = MODEL B */}
        <div
          className={`drop-zone ${dragB ? 'drag' : ''}`}
          onDragEnter={(e) => { e.preventDefault(); setDragB(true) }}
          onDragOver={(e) => { e.preventDefault() }}
          onDragLeave={(e) => { e.preventDefault(); setDragB(false) }}
          onDrop={(e) => handleDrop(e, 'B')}
          onClick={() => inputBRef.current?.click()}
        >
          <div className="badge">모델 B (두 번째)</div>
          <input ref={inputBRef} type="file" accept=".pth" style={{ display: 'none' }} onChange={onPickB} />
          <div className="drop-title">여기에 모델을 드래그 앤드롭하세요</div>
          <div className="drop-copy">Drop File Here</div>
          <div className="drop-sep">- or -</div>
          <div className="drop-action">Click to Upload</div>
          {fileB && <div className="picked">선택됨: {fileB.name}</div>}
        </div>
        {/* RIGHT = MODEL A */}
        <div
          className={`drop-zone ${dragA ? 'drag' : ''}`}
          onDragEnter={(e) => { e.preventDefault(); setDragA(true) }}
          onDragOver={(e) => { e.preventDefault() }}
          onDragLeave={(e) => { e.preventDefault(); setDragA(false) }}
          onDrop={(e) => handleDrop(e, 'A')}
          onClick={() => inputARef.current?.click()}
        >
          <div className="badge">모델 A (첫 번째)</div>
          <input ref={inputARef} type="file" accept=".pth" style={{ display: 'none' }} onChange={onPickA} />
          <div className="drop-title">여기에 모델을 드래그 앤드롭하세요</div>
          <div className="drop-copy">Drop File Here</div>
          <div className="drop-sep">- or -</div>
          <div className="drop-action">Click to Upload</div>
          {fileA && <div className="picked">선택됨: {fileA.name}</div>}
        </div>
      </div>

      {/* 비율 */}
      <div className="ratio-hint">왼쪽(모델 B)으로 갈수록 두 번째 모델 비중↑, 오른쪽(모델 A)으로 갈수록 첫 번째 모델 비중↑</div>
      <div className="row align">
        <label className="lbl">블렌드 비율</label>
        <input className="range" type="range" min={0} max={1} step={0.01} value={ratio} onChange={(e) => setRatio(parseFloat(e.target.value))} />
        <input className="num" type="number" min={0} max={1} step={0.01} value={ratio} onChange={(e) => setRatio(Math.min(1, Math.max(0, parseFloat(e.target.value) || 0)))} />
      </div>
      <div className="ratio-bar">
        <span>B {bPct}%</span>
        <span>A {aPct}%</span>
      </div>

      {/* 실행 / 다운로드 */}
      <div className="row gap">
        <button className="btn primary" onClick={onSubmit} disabled={isLoading}>{isLoading ? '블렌딩 중...' : '융합'}</button>
        {downloadUrl && <a className="btn" href={downloadUrl} download>모델 다운로드</a>}
      </div>

      {/* 출력 정보 */}
      <div className="row">
        <label className="lbl">출력 정보</label>
        <textarea className="out" readOnly value={message} placeholder="출력 정보가 여기 표시됩니다." />
      </div>
    </div>
  )
}

export default ModelBlender
