from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import runpod

from .config import get_settings


@dataclass
class RunpodJobResult:
	status: str
	output: Dict[str, Any] | None
	error: str | None


_settings = get_settings()
runpod.api_key = _settings.runpod_api_key


def submit_training_job(endpoint_id: str, s3_input_prefix: str, s3_output_prefix: str, extra: Optional[Dict[str, Any]] = None) -> str:
	"""
	Runpod 서버리스 엔드포인트에 학습 작업 제출.
	- 반환: job_id
	"""
	payload = {
		"s3_input_prefix": s3_input_prefix,
		"s3_output_prefix": s3_output_prefix,
	}
	if extra:
		payload.update(extra)

	res = runpod.endpoint.run(
		endpoint_id=endpoint_id,
		input=payload,
	)
	# res is dict: { 'id': '...', 'status': 'IN_QUEUE', ... }
	return res["id"]


def poll_job(endpoint_id: str, job_id: str, timeout_sec: int = 7200, poll_sec: int = 10) -> RunpodJobResult:
	"""작업 완료까지 상태를 폴링하여 결과를 반환."""
	end = time.time() + timeout_sec
	while time.time() < end:
		info = runpod.endpoint.get_job(endpoint_id=endpoint_id, job_id=job_id)
		status = (info or {}).get("status", "UNKNOWN")
		if status in {"COMPLETED", "FAILED", "CANCELLED"}:
			output = (info or {}).get("output")
			error = None
			if status != "COMPLETED":
				error = str(output)
			return RunpodJobResult(status=status, output=output if status == "COMPLETED" else None, error=error)
		time.sleep(poll_sec)
	return RunpodJobResult(status="TIMEOUT", output=None, error="timeout")


# ---------------- Pods API ----------------

def create_training_pod(uid: str, s3_input_prefix: str, s3_output_prefix: str, image: Optional[str] = None, template_id: Optional[str] = None, extra_env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
	"""
	Runpod Pods로 배치 컨테이너를 생성. 환경변수로 학습 파라미터를 전달.
	반환: Pod 생성 응답(dict)
	"""
	from runpod import pods

	image_to_use = image or _settings.runpod_pod_image
	env_vars = {
		"AWS_ACCESS_KEY_ID": _settings.aws_access_key_id,
		"AWS_SECRET_ACCESS_KEY": _settings.aws_secret_access_key,
		"AWS_DEFAULT_REGION": _settings.aws_region,
		"S3_BUCKET": _settings.s3_bucket,
		"S3_REGION": _settings.aws_region,
		"UID": uid,
		"S3_INPUT_PREFIX": s3_input_prefix,
		"S3_OUTPUT_PREFIX": s3_output_prefix,
	}
	if extra_env:
		env_vars.update(extra_env)

	if template_id or _settings.runpod_pod_template_id:
		resp = pods.create_pod_from_template(
			template_id=template_id or _settings.runpod_pod_template_id,
			environment_variables=env_vars,
		)
	else:
		# 직접 이미지로 생성 (리소스 사양은 Runpod 계정 기본/템플릿에 의존)
		resp = pods.create_pod(
			image_name=image_to_use,
			environment_variables=env_vars,
		)
	return resp
