from fastapi import FastAPI, File, UploadFile, HTTPException, Query, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import tempfile
from typing import List, Optional, Dict, Any
import re
import time
from pydantic import BaseModel
import subprocess
import shutil

from src.config import get_settings
from src.s3_utils import upload_path, list_objects, upload_bytes, upload_file_to_key
from src.runpod_client import submit_training_job, poll_job, create_training_pod

# FastAPI 앱 생성
app = FastAPI(title="Voice Blend API", version="1.0.0")

# CORS 설정 (React 개발 서버용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()


def _sanitize_user_id(value: str) -> str:
    """영문자(a-zA-Z)만 허용. 그 외 문자는 제거. 빈 문자열이면 에러."""
    value = value or ""
    sanitized = re.sub(r"[^A-Za-z]", "", value)
    if not sanitized:
        raise HTTPException(status_code=400, detail="user_id는 영어 알파벳만 허용합니다.")
    return sanitized


def _trigger_training_background(uid: str, run: Optional[str] = None, extra: Optional[Dict[str, Any]] = None):
    """Runpod 학습 작업을 백그라운드로 트리거."""
    try:
        s3_input_prefix = f"voice_blend/{uid}/uploads/"
        s3_output_prefix = f"{settings.s3_models_prefix}{uid}/{(run or ('run'+str(int(time.time()))))}/"

        if settings.runpod_pod_image or settings.runpod_pod_template_id:
            resp = create_training_pod(uid, s3_input_prefix, s3_output_prefix, image=settings.runpod_pod_image, template_id=settings.runpod_pod_template_id, extra_env=extra)
            print(f"[Pods 제출] uid:{uid} pod_id:{resp.get('id')} in:{s3_input_prefix} out:{s3_output_prefix}")
            return

        endpoint = settings.runpod_endpoint_id
        if not endpoint:
            print(f"[학습 건너뜀] RUNPOD 설정 없음 uid:{uid}")
            return
        payload_extra = dict(extra or {})
        payload_extra.update({
            "uid": uid,
            "s3_bucket": settings.s3_bucket,
            "s3_region": settings.aws_region,
        })
        job_id = submit_training_job(endpoint, s3_input_prefix, s3_output_prefix, extra=payload_extra)
        print(f"[Endpoint 제출] uid:{uid} job:{job_id} in:{s3_input_prefix} out:{s3_output_prefix}")
    except Exception as e:
        print(f"[학습 제출 실패] uid:{uid} err:{e}")


def _get_ffmpeg_exe() -> str:
    """ffmpeg 실행파일 경로 반환. 시스템에 없으면 imageio-ffmpeg 폴백 시도.
    - 한글 주석: 우선 PATH에서 ffmpeg를 찾고, 없으면 파이썬 패키지 imageio-ffmpeg가 제공하는 바이너리를 사용
    """
    # 1) 시스템 PATH에서 ffmpeg 찾기
    path = shutil.which("ffmpeg")
    if path:
        return path
    # 2) imageio-ffmpeg 폴백
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise HTTPException(status_code=500, detail="ffmpeg 실행파일을 찾을 수 없습니다. ffmpeg를 설치하거나 imageio-ffmpeg를 추가하세요.")


def _convert_to_wav_bytes(file_bytes: bytes, input_suffix: str) -> bytes:
    """주어진 바이트(원본 확장자 참고)를 ffmpeg로 WAV 바이트로 변환.
    - 항상 WAV로 변환하여 일관성 보장
    - ffmpeg 표준 출력 사용 대신 임시 파일로 안전하게 처리
    """
    ffmpeg_exe = _get_ffmpeg_exe()
    # 입력 임시 파일 생성
    with tempfile.NamedTemporaryFile(delete=False, suffix=input_suffix) as in_f:
        in_f.write(file_bytes)
        in_path = Path(in_f.name)
    # 출력 임시 파일 경로
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as out_f:
        out_path = Path(out_f.name)
    try:
        # 단순 변환 (채널/샘플레이트는 원본 유지). 필요 시 -ac/-ar 옵션으로 표준화 가능
        proc = subprocess.run([
            ffmpeg_exe, '-y', '-hide_banner', '-loglevel', 'error',
            '-i', str(in_path), str(out_path)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        wav_bytes = out_path.read_bytes()
        return wav_bytes
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
        raise HTTPException(status_code=500, detail=f"오디오 변환 실패: {err}")
    finally:
        # 임시 파일 정리
        try:
            in_path.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            out_path.unlink(missing_ok=True)
        except Exception:
            pass


@app.get("/")
async def root():
    return {"status": "ok", "message": "Voice Blend API is running"}


@app.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    user_id: str = "default",
    background_tasks: BackgroundTasks = None,
):
    # 허용 확장자: mp3, m4a, wav, webm (최종 저장은 WAV)
    allowed_extensions = {".mp3", ".m4a", ".wav", ".webm"}
    orig_name = Path(file.filename).name
    file_ext = Path(orig_name).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="지원하지 않는 형식입니다. mp3/m4a/wav 파일을 업로드하세요.")
    user_id_clean = _sanitize_user_id(user_id)

    # 최종 저장 파일명은 무조건 {uid}.wav
    target = f"{user_id_clean}.wav"

    try:
        # 업로드 파일을 WAV로 변환
        content = await file.read()
        wav_bytes = _convert_to_wav_bytes(content, input_suffix=file_ext)

        key = f"voice_blend/{user_id_clean}/uploads/{target}"
        uploaded_key = upload_bytes(wav_bytes, key)

        # 업로드 직후 Runpod 학습 자동 트리거 (백그라운드)
        if background_tasks is not None:
            background_tasks.add_task(_trigger_training_background, user_id_clean)

        debug_msg = f"[업로드 완료] uid:{user_id_clean} bucket:{settings.s3_bucket} key:{uploaded_key}"
        print(debug_msg)

        return JSONResponse(status_code=200, content={
            "message": "업로드 성공",
            "file_name": target,
            "s3_keys": [uploaded_key],
            "s3_prefix": f"voice_blend/{user_id_clean}/uploads/",
            "bucket": settings.s3_bucket,
            "user_id": user_id_clean,
            "debug": debug_msg,
            "training": "SUBMITTED" if settings.runpod_endpoint_id else "SKIPPED",
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")


@app.post("/upload-multiple")
async def upload_multiple_audio(
    files: List[UploadFile] = File(...),
    user_id: str = "default",
    background_tasks: BackgroundTasks = None,
):
    if not files:
        raise HTTPException(status_code=400, detail="파일이 없습니다")
    # 허용 확장자: mp3, m4a, wav (최종 저장은 WAV)
    allowed_extensions = {".mp3", ".m4a", ".wav"}
    uploaded_results = []
    user_id_clean = _sanitize_user_id(user_id)
    try:
        s3_prefix = f"voice_blend/{user_id_clean}/uploads/"
        uploaded_keys_all: List[str] = []
        for idx, file in enumerate(files):
            orig_name = Path(file.filename).name
            file_ext = Path(orig_name).suffix.lower()
            if file_ext not in allowed_extensions:
                uploaded_results.append({
                    "file_name": orig_name,
                    "status": "error",
                    "message": f"지원하지 않는 파일 형식: {file_ext} (허용: mp3/m4a/wav)"
                })
                continue
            # WAV로 변환 후 저장
            content = await file.read()
            wav_bytes = _convert_to_wav_bytes(content, input_suffix=file_ext)
            target = f"{user_id_clean}.wav" if idx == 0 else f"{user_id_clean}_{idx+1}.wav"
            key = s3_prefix + target
            uploaded_key = upload_bytes(wav_bytes, key)
            uploaded_keys_all.append(uploaded_key)
            uploaded_results.append({
                "file_name": target,
                "status": "success",
                "s3_keys": [uploaded_key]
            })

        # 업로드 직후 Runpod 학습 자동 트리거 (백그라운드)
        if background_tasks is not None:
            background_tasks.add_task(_trigger_training_background, user_id_clean)

        debug_msg = f"[업로드 완료] uid:{user_id_clean} bucket:{settings.s3_bucket} count:{len(uploaded_keys_all)} first_key:{uploaded_keys_all[0] if uploaded_keys_all else '-'}"
        print(debug_msg)

        return JSONResponse(status_code=200, content={
            "message": f"{len(uploaded_results)}개 파일 업로드 완료",
            "results": uploaded_results,
            "s3_prefix": s3_prefix,
            "bucket": settings.s3_bucket,
            "user_id": user_id_clean,
            "debug": debug_msg,
            "training": "SUBMITTED" if settings.runpod_endpoint_id else "SKIPPED",
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")


class TrainRequest(BaseModel):
    user_id: str
    run: Optional[str] = "run1"
    endpoint_id: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    wait: bool = False


@app.post("/train")
async def start_training(req: TrainRequest):
    """
    Runpod 학습 작업을 시작. 프롬프트에 전달되는 입력 예:
    {
      uid, s3_bucket, s3_region, s3_input_prefix, s3_output_prefix, ...extra
    }
    """
    uid = _sanitize_user_id(req.user_id)
    endpoint = req.endpoint_id or settings.runpod_endpoint_id
    if not endpoint:
        raise HTTPException(status_code=400, detail="RUNPOD_ENDPOINT_ID가 필요합니다(.env 또는 요청에 지정)")

    s3_input_prefix = f"voice_blend/{uid}/uploads/"
    # 산출물은 models/{uid}/{run}/ 하위에 저장한다고 가정
    s3_output_prefix = f"{settings.s3_models_prefix}{uid}/{req.run or 'run1'}/"

    payload_extra = dict(req.extra or {})
    payload_extra.update({
        "uid": uid,
        "s3_bucket": settings.s3_bucket,
        "s3_region": settings.aws_region,
    })

    job_id = submit_training_job(endpoint, s3_input_prefix, s3_output_prefix, extra=payload_extra)

    if req.wait:
        res = poll_job(endpoint, job_id)
        return {
            "endpoint_id": endpoint,
            "job_id": job_id,
            "status": res.status,
            "output": res.output,
            "error": res.error,
            "s3_input_prefix": s3_input_prefix,
            "s3_output_prefix": s3_output_prefix,
        }

    return {
        "endpoint_id": endpoint,
        "job_id": job_id,
        "status": "SUBMITTED",
        "s3_input_prefix": s3_input_prefix,
        "s3_output_prefix": s3_output_prefix,
        "sent_payload": {
            "uid": uid,
            "s3_bucket": settings.s3_bucket,
            "s3_region": settings.aws_region,
        }
    }


@app.get("/models/indexes")
async def list_user_indexes(user_id: str = Query(..., description="사용자 UID")):
    user_id_clean = _sanitize_user_id(user_id)
    try:
        prefix = f"{settings.s3_models_prefix}{user_id_clean}/"
        keys = list_objects(prefix)
        index_keys = [k for k in keys if k.lower().endswith('.index')]
        return {"bucket": settings.s3_bucket, "prefix": prefix, "indexes": index_keys, "user_id": user_id_clean}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    try:
        from src.s3_utils import healthcheck
        healthcheck()
        return {"status": "healthy", "s3": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"S3 연결 실패: {str(e)}")


# ---------------- 모델 블렌딩 (로컬 CPU) ----------------

try:
	from model_blender.backend.logic import blend_voices as local_blend
except Exception:
	local_blend = None


@app.post("/blend/local")
async def blend_local(
	name: str = Form(...),
	ratio: float = Form(...),
	model_a: UploadFile = File(...),
	model_b: UploadFile = File(...),
):
	"""두 개의 .pth를 업로드 받아 로컬에서 블렌딩하고 파일명을 반환."""
	if local_blend is None:
		raise HTTPException(status_code=500, detail="model_blender 로직을 불러올 수 없습니다.")
	# 임시 저장
	with tempfile.NamedTemporaryFile(delete=False, suffix=".pth") as f1:
		f1.write(await model_a.read())
		p1 = Path(f1.name)
	with tempfile.NamedTemporaryFile(delete=False, suffix=".pth") as f2:
		f2.write(await model_b.read())
		p2 = Path(f2.name)
	# 로컬 블렌딩 실행
	msg, out_path = local_blend(name=name, path1=str(p1), path2=str(p2), ratio=ratio)
	if not out_path:
		raise HTTPException(status_code=400, detail=msg)
	filename = Path(out_path).name
	return {
		"message": msg,
		"filename": filename,
		"download_url": f"/blend/download?filename={filename}",
	}


@app.get("/blend/download")
async def download_blended_model(filename: str = Query(..., description="logs 폴더 내 파일명(.pth)")):
	"""블렌딩 산출물 다운로드. logs 폴더 하위만 허용."""
	if not filename.lower().endswith(".pth"):
		raise HTTPException(status_code=400, detail=".pth 파일만 다운로드 가능합니다")
	logs_dir = Path("logs")
	file_path = logs_dir / Path(filename).name
	if not file_path.exists():
		raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
	return FileResponse(path=str(file_path), media_type="application/octet-stream", filename=file_path.name)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

