from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Iterable, List, Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from .config import get_settings, ensure_trailing_slash


# 전역 세션/클라이언트 생성 (재사용)
_settings = get_settings()
_session = boto3.session.Session(
	aws_access_key_id=_settings.aws_access_key_id,
	aws_secret_access_key=_settings.aws_secret_access_key,
	region_name=_settings.aws_region,
)
_s3 = _session.resource("s3", config=Config(signature_version="s3v4"))
_client = _session.client("s3", config=Config(signature_version="s3v4"))
_bucket = _s3.Bucket(_settings.s3_bucket)


def upload_path(path: str | Path, prefix: str) -> List[str]:
	"""
	로컬 경로(파일/폴더)를 S3로 업로드.
	- prefix는 S3 상의 디렉터리(예: voice_blend/uploads/user1/)
	- 반환: 업로드된 S3 키 목록
	"""
	prefix = ensure_trailing_slash(prefix)
	path = Path(path)
	keys: List[str] = []
	if path.is_file():
		key = prefix + path.name
		_bucket.upload_file(str(path), key)
		keys.append(key)
		return keys

	for file in path.rglob("*"):
		if file.is_file():
			rel = file.relative_to(path)
			key = prefix + str(rel).replace(os.sep, "/")
			_bucket.upload_file(str(file), key)
			keys.append(key)
	return keys


def upload_bytes(data: bytes, key: str) -> str:
	"""바이트 데이터를 지정 키로 업로드하고 키를 반환."""
	_client.put_object(Bucket=_settings.s3_bucket, Key=key, Body=data)
	return key


def upload_file_to_key(path: str | Path, key: str) -> str:
	"""로컬 파일을 지정된 키로 업로드."""
	_bucket.upload_file(str(path), key)
	return key


def list_objects(prefix: str) -> List[str]:
	"""지정 프리픽스 하위의 객체 키들을 반환."""
	prefix = ensure_trailing_slash(prefix)
	keys: List[str] = []
	for obj in _bucket.objects.filter(Prefix=prefix):
		if obj.key.endswith("/"):
			continue
		keys.append(obj.key)
	return keys


def wait_for_artifacts(prefix: str, exts: Iterable[str], timeout_sec: int = 7200, poll_sec: int = 15) -> List[str]:
	"""
	특정 프리픽스에서 주어진 확장자 파일(.pth, .index 등)이 생성될 때까지 대기.
	- timeout_sec: 최대 대기 시간(초)
	- poll_sec: 폴링 주기(초)
	- 반환: 발견된 키 목록
	"""
	prefix = ensure_trailing_slash(prefix)
	end = time.time() + timeout_sec

	exts = {e.lower() for e in exts}
	found: List[str] = []
	while time.time() < end:
		keys = list_objects(prefix)
		found = [k for k in keys if any(k.lower().endswith(e) for e in exts)]
		if found:
			return found
		time.sleep(poll_sec)
	return found


def download_prefix(prefix: str, out_dir: str | Path = "downloads") -> List[Path]:
	"""프리픽스 하위의 모든 파일을 로컬 폴더로 다운로드."""
	prefix = ensure_trailing_slash(prefix)
	out = Path(out_dir)
	out.mkdir(parents=True, exist_ok=True)
	paths: List[Path] = []
	for key in list_objects(prefix):
		dst = out / Path(key).name
		_bucket.download_file(key, str(dst))
		paths.append(dst)
	return paths


def download_object_to_path(key: str, dst_path: str | Path) -> Path:
	"""단일 S3 객체를 지정 경로로 다운로드하고 경로를 반환."""
	dst = Path(dst_path)
	dst.parent.mkdir(parents=True, exist_ok=True)
	_bucket.download_file(key, str(dst))
	return dst


def object_exists(key: str) -> bool:
	try:
		_client.head_object(Bucket=_settings.s3_bucket, Key=key)
		return True
	except ClientError as e:
		if e.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
			return False
		raise


def healthcheck(prefix: str | None = None) -> bool:
	"""
	S3 연결/권한 확인을 위한 경량 헬스체크.
	- 버킷 존재/권한: head_bucket
	- 쓰기/읽기/삭제: 임시 텍스트 객체 생성 후 삭제
	"""
	import uuid

	pfx = ensure_trailing_slash(prefix or _settings.s3_data_prefix)
	key = f"{pfx}healthcheck-{uuid.uuid4().hex}.txt"

	# 버킷 접근 가능 여부
	_client.head_bucket(Bucket=_settings.s3_bucket)

	# 쓰기
	_client.put_object(Bucket=_settings.s3_bucket, Key=key, Body=b"ok")

	# 읽기 (head)
	_client.head_object(Bucket=_settings.s3_bucket, Key=key)

	# 삭제
	_client.delete_object(Bucket=_settings.s3_bucket, Key=key)
	return True
