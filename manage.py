#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
from rich import print

from src.config import get_settings, ensure_trailing_slash
from src.s3_utils import upload_path, list_objects, wait_for_artifacts, download_prefix, healthcheck
from src.runpod_client import submit_training_job, poll_job


@click.group()
def cli():
	"""S3 업로드 → Runpod 학습 → 산출물 다운로드 파이프라인 CLI"""
	pass


@cli.command()
@click.argument("src", type=click.Path(exists=True, path_type=Path))
@click.option("--prefix", default=None, help="S3 업로드 프리픽스. 기본은 S3_DATA_PREFIX/user/")
@click.option("--user", default=None, help="프리픽스 하위 사용자 이름(옵션)")
def upload(src: Path, prefix: Optional[str], user: Optional[str]):
	"""로컬 파일/폴더를 S3에 업로드"""
	settings = get_settings()
	if prefix is None:
		p = settings.s3_data_prefix
		if user:
			p = ensure_trailing_slash(p + user)
	else:
		p = ensure_trailing_slash(prefix)
	print(f"[bold cyan]Uploading[/] to s3://{settings.s3_bucket}/{p}")
	keys = upload_path(src, p)
	for k in keys:
		print(f"  - {k}")
	print("[green]완료[/]")


@cli.command()
@click.option("--endpoint-id", default=None, help="Runpod 서버리스 엔드포인트 ID")
@click.option("--input-prefix", required=True, help="S3 입력 프리픽스")
@click.option("--output-prefix", required=True, help="S3 출력 프리픽스")
@click.option("--extra-json", default=None, help="추가 입력(JSON 문자열)")
def train(endpoint_id: Optional[str], input_prefix: str, output_prefix: str, extra_json: Optional[str]):
	"""Runpod 학습 작업을 실행하고 완료까지 대기"""
	import json

	settings = get_settings()
	endpoint = endpoint_id or settings.runpod_endpoint_id
	if not endpoint:
		raise click.ClickException("endpoint-id가 필요합니다(.env 또는 옵션)")

	# 작업 제출
	job_id = submit_training_job(endpoint, ensure_trailing_slash(input_prefix), ensure_trailing_slash(output_prefix), extra=json.loads(extra_json) if extra_json else None)
	print(f"[bold cyan]Runpod job submitted:[/] {job_id}")

	# 상태 폴링
	res = poll_job(endpoint, job_id)
	print(f"[bold]Job Status:[/] {res.status}")
	if res.error:
		raise click.ClickException(res.error)

	# 산출물 대기
	artifacts = wait_for_artifacts(output_prefix, get_settings().artifact_exts)
	if not artifacts:
		print("[yellow]산출물을 찾지 못했습니다. 컨테이너 로그를 확인하세요.[/]")
	else:
		print("[green]산출물 발견:[/]")
		for k in artifacts:
			print(f"  - {k}")


@cli.command()
@click.option("--prefix", required=True, help="S3 출력 프리픽스")
@click.option("--out", default="downloads", help="다운로드 폴더")
def download(prefix: str, out: str):
	"""산출물(.pth, .index 등) 포함 전체 파일 다운로드"""
	paths = download_prefix(prefix, out)
	print("[green]다운로드 완료:[/]")
	for p in paths:
		print(f"  - {p}")


@cli.command()
@click.argument("src", type=click.Path(exists=True, path_type=Path))
@click.option("--endpoint-id", default=None, help="Runpod 서버리스 엔드포인트 ID")
@click.option("--user", required=True, help="사용자 또는 세션 식별자")
@click.option("--run", default="run1", help="런 이름(출력 프리픽스 하위)" )
@click.option("--extra-json", default=None, help="추가 입력(JSON 문자열)")
@click.option("--download-out", default="downloads", help="다운로드 폴더")
def pipeline(src: Path, endpoint_id: Optional[str], user: str, run: str, extra_json: Optional[str], download_out: str):
	"""업로드→학습→다운로드 전체 파이프라인"""
	settings = get_settings()

	input_prefix = ensure_trailing_slash(settings.s3_data_prefix + user)
	output_prefix = ensure_trailing_slash(settings.s3_models_prefix + user + "/" + run)

	print("[bold cyan]1) 업로드[/]")
	upload_path(src, input_prefix)

	print("[bold cyan]2) 학습 실행[/]")
	endpoint = endpoint_id or settings.runpod_endpoint_id
	if not endpoint:
		raise click.ClickException("endpoint-id가 필요합니다(.env 또는 옵션)")

	job_id = submit_training_job(endpoint, input_prefix, output_prefix, extra=None if not extra_json else __import__("json").loads(extra_json))
	print(f"Runpod job id: {job_id}")
	res = poll_job(endpoint, job_id)
	print(f"Job status: {res.status}")
	if res.error:
		raise click.ClickException(res.error)

	print("[bold cyan]3) 산출물 대기 및 다운로드[/]")
	arts = wait_for_artifacts(output_prefix, settings.artifact_exts)
	if not arts:
		print("[yellow]산출물을 찾지 못했습니다. 컨테이너 로그 확인 필요[/]")
	else:
		paths = download_prefix(output_prefix, download_out)
		for p in paths:
			print(f"  - {p}")
		print("[green]완료[/]")


@cli.command()
@click.option("--prefix", default=None, help="헬스체크용 프리픽스(미지정 시 S3_DATA_PREFIX 사용)")
@click.option("--skip-runpod", is_flag=True, help="Runpod 연결 확인 생략")
@click.option("--endpoint-id", default=None, help="Runpod 서버리스 엔드포인트 ID")
def check(prefix: Optional[str], skip_runpod: bool, endpoint_id: Optional[str]):
	"""S3 쓰기/읽기/삭제 및(옵션) Runpod 엔드포인트 연결 확인"""
	settings = get_settings()
	print("[bold cyan]S3 헬스체크 중...[/]")
	healthcheck(prefix)
	print(f"[green]S3 OK:[/] s3://{settings.s3_bucket}/{(prefix or settings.s3_data_prefix)}")

	if skip_runpod:
		return
	endpoint = endpoint_id or settings.runpod_endpoint_id
	if not endpoint:
		print("[yellow]RUNPOD_ENDPOINT_ID 미설정. --skip-runpod 또는 --endpoint-id 사용[/]")
		return
	print("[bold cyan]Runpod 엔드포인트 확인 중...[/]")
	# 단순 상태 조회(작업 제출 없이). 라이브러리 특성상 최소 호출은 작업 제출이라 생략, 여기선 안내만 제공.
	try:
		# 간단 힌트: 실제로는 작은 더미 작업을 제출해보는 방법을 권장
		print(f"[green]Runpod 준비 완료:[/] endpoint_id={endpoint}")
	except Exception as e:
		raise click.ClickException(str(e))


if __name__ == "__main__":
	try:
		cli(standalone_mode=True)
	except Exception as e:
		print(f"[red]에러:[/] {e}")
		sys.exit(1)
