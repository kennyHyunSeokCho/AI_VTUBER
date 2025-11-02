import os
from collections import OrderedDict
from pathlib import Path
import torch


def _extract(ckpt):
    """Applio 호환: ckpt['model']가 있을 때 가중치만 추출"""
    a = ckpt["model"]
    opt = OrderedDict()
    opt["weight"] = {}
    for key in a.keys():
        if "enc_q" in key:
            continue
        opt["weight"][key] = a[key]
    return opt


def _get_sr_value(ckpt) -> str:
    """체크포인트에서 샘플레이트를 최대한 안전하게 추출.
    - 우선 'sr' 키, 없으면 'config' 내부 탐색, 그래도 없으면 48000으로 폴백
    """
    if isinstance(ckpt, dict) and "sr" in ckpt:
        return str(ckpt["sr"]).lower().replace("k", "000")
    cfg = ckpt.get("config") if isinstance(ckpt, dict) else None
    sr_candidates = {"sr", "sample_rate", "sampling_rate"}
    if isinstance(cfg, dict):
        for k in sr_candidates:
            if k in cfg:
                return str(cfg[k]).lower().replace("k", "000")
    if isinstance(cfg, (list, tuple)):
        for item in cfg:
            if isinstance(item, (int, float)) and int(item) in (32000, 40000, 44100, 48000):
                return str(int(item))
            if isinstance(item, str) and item.endswith("k"):
                try:
                    return str(int(item[:-1]) * 1000)
                except Exception:
                    pass
    return "48000"


def blend_voices(name: str, path1: str, path2: str, ratio: float):
    """두 개의 RVC .pth를 선형 보간으로 블렌딩.
    - 한글 주석: Applio rvc/train/process/model_blender.py 로직을 반영
    """
    try:
        message = f"Model {path1} and {path2} are merged with alpha {ratio}."
        ckpt1 = torch.load(path1, map_location="cpu", weights_only=True)
        ckpt2 = torch.load(path2, map_location="cpu", weights_only=True)

        sr1 = _get_sr_value(ckpt1)
        sr2 = _get_sr_value(ckpt2)
        if sr1 != sr2:
            return f"샘플레이트 불일치: {sr1} vs {sr2}. 동일해야 블렌딩 가능합니다.", None

        cfg = ckpt1.get("config", {})
        cfg_f0 = ckpt1.get("f0", True)
        cfg_version = ckpt1.get("version", "v2")
        cfg_sr = sr1
        vocoder = ckpt1.get("vocoder", "HiFi-GAN")

        # 가중치 사전으로 정규화
        if "model" in ckpt1:
            ckpt1 = _extract(ckpt1)
        if isinstance(ckpt1, dict) and "weight" in ckpt1:
            ckpt1 = ckpt1["weight"]
        if "model" in ckpt2:
            ckpt2 = _extract(ckpt2)
        if isinstance(ckpt2, dict) and "weight" in ckpt2:
            ckpt2 = ckpt2["weight"]

        if sorted(list(ckpt1.keys())) != sorted(list(ckpt2.keys())):
            k1, k2 = set(ckpt1.keys()), set(ckpt2.keys())
            only1 = list(k1 - k2)[:5]
            only2 = list(k2 - k1)[:5]
            return (
                "Fail to merge the models. The model architectures are not the same.\n"
                f"diff-only-in-A: {only1} (…){' ' if only1 else ''}"
                f"diff-only-in-B: {only2} (…)",
                None,
            )

        # 추가: 공통 키의 shape가 다른 경우 안내
        shape_mismatch = []
        for key in set(ckpt1.keys()) & set(ckpt2.keys()):
            try:
                if hasattr(ckpt1[key], "shape") and hasattr(ckpt2[key], "shape"):
                    if tuple(ckpt1[key].shape) != tuple(ckpt2[key].shape) and key != "emb_g.weight":
                        shape_mismatch.append((key, tuple(ckpt1[key].shape), tuple(ckpt2[key].shape)))
            except Exception:
                pass
        if shape_mismatch:
            sample = shape_mismatch[:5]
            return (
                "Fail to merge the models. Tensor shapes differ.\n"
                + "\n".join([f"{k}: {s1} vs {s2}" for k, s1, s2 in sample])
                + ("\n…" if len(shape_mismatch) > 5 else ""),
                None,
            )

        opt = OrderedDict()
        opt["weight"] = {}
        for key in ckpt1.keys():
            if key == "emb_g.weight" and ckpt1[key].shape != ckpt2[key].shape:
                min_shape0 = min(ckpt1[key].shape[0], ckpt2[key].shape[0])
                opt["weight"][key] = (
                    ratio * (ckpt1[key][:min_shape0].float())
                    + (1 - ratio) * (ckpt2[key][:min_shape0].float())
                ).half()
            else:
                opt["weight"][key] = (
                    ratio * (ckpt1[key].float()) + (1 - ratio) * (ckpt2[key].float())
                ).half()

        opt["config"] = cfg
        opt["sr"] = cfg_sr
        opt["f0"] = cfg_f0
        opt["version"] = cfg_version
        opt["info"] = message
        opt["vocoder"] = vocoder

        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        out_path = logs_dir / f"{name}.pth"
        torch.save(opt, out_path)

        # 한글 주석: 사용자 로컬 다운로드 폴더에도 복사 저장 (macOS/일반 환경)
        try:
            downloads_dir = Path.home() / "Downloads"
            downloads_dir.mkdir(parents=True, exist_ok=True)
            dst_path = downloads_dir / f"{name}.pth"
            if str(dst_path) != str(out_path):
                import shutil
                shutil.copyfile(out_path, dst_path)
        except Exception:
            # 복사 실패는 치명적이지 않으므로 무시 (서버 경로에 있는 파일은 유지)
            pass

        return message, str(out_path)
    except Exception as error:
        return f"An error occurred blending the models: {error}", None


