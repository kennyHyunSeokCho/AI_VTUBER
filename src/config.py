from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

# 환경변수 로드 (.env 사용)
load_dotenv()


@dataclass
class Settings:
	"""런타임 설정 값을 보관하는 데이터 클래스."""
	aws_access_key_id: str
	aws_secret_access_key: str
	aws_region: str
	s3_bucket: str
	s3_data_prefix: str
	s3_models_prefix: str
	runpod_api_key: str
	runpod_endpoint_id: str | None
	artifact_exts: List[str]
	# Pods 관련 (옵션)
	runpod_pod_template_id: str | None
	runpod_pod_image: str | None
	# 외부 학습 트리거 URL (옵션)
	external_train_url: str | None

	def s3_uri(self, prefix: str) -> str:
		"""S3 프리픽스를 s3 URI 형태로 변환."""
		prefix = ensure_trailing_slash(prefix)
		return f"s3://{self.s3_bucket}/{prefix}"


def ensure_trailing_slash(prefix: str) -> str:
	# 프리픽스는 항상 슬래시로 끝나도록 강제
	return prefix if prefix.endswith("/") else prefix + "/"


def _parse_artifact_exts(raw: str | None) -> List[str]:
	# 확장자 목록을 쉼표 구분으로 파싱 (점 포함/미포함 모두 허용)
	if not raw:
		return [".pth", ".index"]
	exts: List[str] = []
	for token in raw.split(","):
		t = token.strip()
		if not t:
			continue
		if not t.startswith('.'):
			t = '.' + t
		exts.append(t)
	return exts or [".pth", ".index"]


def get_settings() -> Settings:
	"""환경변수에서 설정을 읽어 Settings로 반환."""
	return Settings(
		aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
		aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
		aws_region=os.getenv("AWS_DEFAULT_REGION", "ap-northeast-2"),
		s3_bucket=os.getenv("S3_BUCKET_NAME", ""),
		s3_data_prefix=ensure_trailing_slash(os.getenv("S3_DATA_PREFIX", "voice_blend/uploads/")),
		s3_models_prefix=ensure_trailing_slash(os.getenv("S3_MODELS_PREFIX", "voice_blend/models/")),
		runpod_api_key=os.getenv("RUNPOD_API_KEY", ""),
		runpod_endpoint_id=os.getenv("RUNPOD_ENDPOINT_ID"),
		artifact_exts=_parse_artifact_exts(os.getenv("ARTIFACT_EXTS")),
		runpod_pod_template_id=os.getenv("RUNPOD_POD_TEMPLATE_ID"),
		runpod_pod_image=os.getenv("RUNPOD_POD_IMAGE"),
		external_train_url=os.getenv("EXTERNAL_TRAIN_URL", "https://n7f2zix4pkmdgk-8000.proxy.runpod.net/train"),
	)
