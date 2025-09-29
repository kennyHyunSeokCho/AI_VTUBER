import wx
import socket
import threading
import time
import math
import numpy as np
import os
import glob
from PIL import Image
import json
from collections import defaultdict, OrderedDict
import cv2


class iFacialMocapReceiver:
    """iFacialMocap UDP 데이터 수신 클래스"""
    
    def __init__(self, port=49983):
        self.port = port
        self.socket = None
        self.running = False
        self.latest_data = {}
        self.thread = None
        
        # 데이터 평활화를 위한 버퍼
        self.data_history = defaultdict(list)
        self.history_size = 3  # 3프레임 평균
        
        # 로깅 제한
        self.last_log_time = 0
        self.log_interval = 2.0
        
    def start(self):
        """UDP 수신 시작"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('', self.port))
            self.socket.settimeout(0.1)
            self.running = True
            self.thread = threading.Thread(target=self._receive_loop)
            self.thread.daemon = True
            self.thread.start()
            print(f"iFacialMocap receiver started on port {self.port}")
            return True
        except Exception as e:
            print(f"Failed to start iFacialMocap receiver: {e}")
            return False
    
    def stop(self):
        """UDP 수신 종료"""
        self.running = False
        if self.socket:
            self.socket.close()
        if self.thread:
            self.thread.join()
    
    def _receive_loop(self):
        """UDP 데이터 수신 루프"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(8192)
                self._parse_data(data)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    current_time = time.time()
                    if current_time - self.last_log_time > self.log_interval:
                        print(f"Error receiving data: {e}")
                        self.last_log_time = current_time
    
    def _parse_data(self, data):
        """iFacialMocap 데이터 파싱"""
        try:
            data_str = data.decode('utf-8', errors='ignore')
            parts = data_str.split('|')
            
            raw_data = {}
            
            for part in parts:
                if '=' in part:
                    self._parse_head_eye_data(part, raw_data)
                elif '-' in part and len(part) > 3:
                    try:
                        name, value_str = part.split('-', 1)
                        value = float(value_str) / 100.0
                        raw_data[name] = max(0, min(1, value))
                    except (ValueError, IndexError):
                        continue
            
            # 데이터 평활화 적용
            self._smooth_data(raw_data)
                        
        except Exception as e:
            current_time = time.time()
            if current_time - self.last_log_time > self.log_interval:
                print(f"Error parsing data: {e}")
                self.last_log_time = current_time
    
    def _smooth_data(self, raw_data):
        """데이터 평활화 - 떨림 방지"""
        for key, value in raw_data.items():
            # 히스토리에 추가
            self.data_history[key].append(value)
            if len(self.data_history[key]) > self.history_size:
                self.data_history[key].pop(0)
            
            # 평균값으로 평활화
            if len(self.data_history[key]) >= 2:
                smoothed = sum(self.data_history[key]) / len(self.data_history[key])
                self.latest_data[key] = smoothed
            else:
                self.latest_data[key] = value
    
    def _parse_head_eye_data(self, data_part, raw_data):
        """헤드와 눈 데이터 파싱"""
        try:
            sections = data_part.split('|')
            for section in sections:
                if section.startswith('=head#'):
                    head_values = section[6:].split(',')
                    if len(head_values) >= 6:
                        raw_data['head_rx'] = math.radians(float(head_values[0]))
                        raw_data['head_ry'] = math.radians(float(head_values[1]))
                        raw_data['head_rz'] = math.radians(float(head_values[2]))
                        
                elif section.startswith('rightEye#'):
                    eye_values = section[9:].split(',')
                    if len(eye_values) >= 3:
                        raw_data['rightEye_rx'] = math.radians(float(eye_values[0]))
                        raw_data['rightEye_ry'] = math.radians(float(eye_values[1]))
                        raw_data['rightEye_rz'] = math.radians(float(eye_values[2]))
                        
                elif section.startswith('leftEye#'):
                    eye_values = section[8:].split(',')
                    if len(eye_values) >= 3:
                        raw_data['leftEye_rx'] = math.radians(float(eye_values[0]))
                        raw_data['leftEye_ry'] = math.radians(float(eye_values[1]))
                        raw_data['leftEye_rz'] = math.radians(float(eye_values[2]))
                        
        except Exception:
            pass
    
    def get_latest_data(self):
        """최신 데이터 반환"""
        return self.latest_data.copy()


class UnifiedImageManager:
    """통합 균형 매칭을 위한 이미지 관리자 - 5×5×4×11×11×11 지원"""
    
    def __init__(self, images_base_dir="data", max_cache_size=300):
        self.images_base_dir = images_base_dir
        self.image_cache = OrderedDict()
        self.image_paths = {}
        self.max_cache_size = max_cache_size
        
        # 매칭 설정
        self.fallback_search_enabled = True
        self.sensitivity = 0.5  # 0.2~0.8 범위
        
        # 디버깅
        self.last_debug_time = 0
        self.debug_interval = 3.0
        self.last_matched_key = None
        self.last_search_method = ""
        
        # 인덱싱
        self.index_image_paths()
        self._create_sorted_keys()
        
    def index_image_paths(self):
        """이미지 파일 경로 인덱싱 - 5×5×4×11×11×11 지원"""
        print("Indexing images for 5×5×4×11×11×11 support...")
        start_time = time.time()
        
        image_dir = os.path.join(self.images_base_dir, "eye_face_optimized_patches")
        if not os.path.exists(image_dir):
            # 대안 경로들 시도
            alt_dirs = [
                os.path.join(self.images_base_dir, "combined_parameters_optimized_patches"),
                os.path.join(self.images_base_dir, "eye_face_patches")
            ]
            for alt_dir in alt_dirs:
                if os.path.exists(alt_dir):
                    image_dir = alt_dir
                    break
            else:
                print(f"Images directory not found: {image_dir}")
                return
        
        patterns = [
            "eye_face_*.png",  # 새로운 5×5×4×11×11×11 패턴
            "opt_*.png",       # 기존 패턴들
        ]
        
        files = []
        for pattern in patterns:
            pattern_files = glob.glob(os.path.join(image_dir, pattern))
            if pattern_files:
                files.extend(pattern_files)
        
        indexed_count = 0
        for file_path in files:
            filename = os.path.basename(file_path)
            try:
                params = self._parse_filename(filename)
                if params:
                    param_key = (
                        params.get('EBL', 0), params.get('EBR', 0),
                        params.get('EWL', 0), params.get('EWR', 0),
                        params.get('JO', 0), params.get('HX', 0),
                        params.get('HY', 0), params.get('BL', 0)
                    )
                    self.image_paths[param_key] = file_path
                    indexed_count += 1
                    
            except Exception as e:
                continue
        
        elapsed = time.time() - start_time
        print(f"Indexed {indexed_count} images in {elapsed:.2f}s")
        print(f"5×5×4×11×11×11 configuration: Eyes(0-4×0-4), Mouth(0-3), Head(0-10×0-10×0-10)")
        
    def _parse_filename(self, filename):
        """파일명 파싱 - 5×5×4×11×11×11 지원"""
        # eye_face_ 패턴과 기존 opt_ 패턴 모두 지원
        if filename.startswith('eye_face_'):
            name_part = filename.replace('eye_face_', '').replace('.png', '')
        else:
            name_part = filename.replace('opt_', '').replace('.png', '')
        
        parts = name_part.split('_')
        
        params = {}
        for part in parts:
            try:
                if part.startswith('EBL') or part.startswith('LEB'):
                    params['EBL'] = int(part[3:])
                elif part.startswith('EBR') or part.startswith('REB'):
                    params['EBR'] = int(part[3:])
                elif part.startswith('EWL') or part.startswith('LEW'):
                    params['EWL'] = int(part[3:])
                elif part.startswith('EWR') or part.startswith('REW'):
                    params['EWR'] = int(part[3:])
                elif part.startswith('JO') or part.startswith('MAA'):
                    params['JO'] = int(part[2:] if part.startswith('JO') else part[3:])
                elif part.startswith('BL') or part.startswith('NZ'):
                    params['BL'] = int(part[2:])
                elif part.startswith('HX'):
                    params['HX'] = int(part[2:])
                elif part.startswith('HY'):
                    params['HY'] = int(part[2:])
            except (ValueError, IndexError):
                continue
                
        required_params = ['EBL', 'EBR', 'EWL', 'EWR', 'JO', 'HX', 'HY', 'BL']
        return params if all(param in params for param in required_params) else None
    
    def _create_sorted_keys(self):
        """정렬된 키 리스트 생성"""
        self.sorted_keys = sorted(list(self.image_paths.keys()))
        print(f"Created sorted key index with {len(self.sorted_keys)} entries")
        
    def get_best_avatar_image(self, mocap_data):
        """순차적 매칭 - 눈→입→헤드 순서로 단계별 매칭 (5×5×4×11×11×11 지원)"""
        
        # **우측 편향 방지**: 매우 작은 헤드 움직임은 강제로 중앙으로
        head_rx = abs(mocap_data.get('head_rx', 0))
        head_ry = abs(mocap_data.get('head_ry', 0))
        head_rz = abs(mocap_data.get('head_rz', 0))
        
        if head_rx < 0.05 and head_ry < 0.05 and head_rz < 0.05:
            # 강제로 중앙 헤드로 설정
            mocap_data_corrected = mocap_data.copy()
            mocap_data_corrected['head_rx'] = 0.0
            mocap_data_corrected['head_ry'] = 0.0  
            mocap_data_corrected['head_rz'] = 0.0
            mocap_data = mocap_data_corrected
        
        # 파라미터 변환 (5×5×4×11×11×11 지원)
        params = self._convert_mocap_to_params(mocap_data)
        param_key = tuple(params)
        
        # 1단계: 완전 정확한 매치
        img = self._load_image_if_needed(param_key)
        if img:
            self.last_matched_key = param_key
            self.last_search_method = "EXACT MATCH"
            return img
        
        # 2단계: 순차적 단계별 매칭 (눈→입→헤드 순서)
        if self.fallback_search_enabled:
            best_match = self._find_sequential_best_match(param_key)
            if best_match:
                img = self._load_image_if_needed(best_match)
                if img:
                    self.last_matched_key = best_match
                    self.last_search_method = "SEQUENTIAL MATCH"
                    return img
        
        # 3단계: 기본 이미지 - **정면 중앙으로 수정 (5×5×4×11×11×11 중심값)**
        default_key = (0, 0, 0, 0, 0, 5, 5, 5)  # EBL0_EBR0_EWL0_EWR0_JO0_HX5_HY5_NZ5 (정면, 보통 숨쉬기)
        img = self._load_image_if_needed(default_key)
        if img:
            self.last_matched_key = default_key
            self.last_search_method = "DEFAULT"
        else:
            # 백업 기본값들 시도 (다양한 중심값들)
            backup_keys = [
                (0, 0, 0, 0, 0, 5, 5, 0),  # NZ0 (안 숨쉬기)
                (0, 0, 0, 0, 0, 5, 5, 3),  # NZ3 (약간 숨쉬기)
                (0, 0, 0, 0, 0, 5, 5, 7),  # NZ7 (많이 숨쉬기)
                (1, 1, 0, 0, 0, 5, 5, 5),  # 약간 다른 표정
                (0, 0, 1, 1, 0, 5, 5, 5),  # 눈 깜빡임
                (0, 0, 0, 0, 1, 5, 5, 5),  # 입 열기
            ]
            for backup_key in backup_keys:
                img = self._load_image_if_needed(backup_key)
                if img:
                    self.last_matched_key = backup_key
                    self.last_search_method = "BACKUP_DEFAULT"
                    break
        return img
    
    def _find_sequential_best_match(self, target_key):
        """순차적 단계별 매칭 - 눈→입→헤드 순서로 정확한 매칭"""
        
        # 1단계: 눈 표정 우선 매칭 (EBL, EBR, EWL, EWR) - 5×5 지원
        eye_candidates = self._filter_by_eyes(target_key)
        
        if not eye_candidates:
            # 눈 매칭 실패시 눈 파라미터 완화
            eye_candidates = self._filter_by_eyes_relaxed(target_key)
        
        # 2단계: 입 표정 매칭 (JO - jawOpen) - 4단계 지원
        if eye_candidates:
            mouth_candidates = self._filter_by_mouth(target_key, eye_candidates)
        else:
            mouth_candidates = []
        
        # 3단계: 헤드 각도 매칭 (HX, HY, BL) - 11×11×11 지원
        final_candidates = []
        if mouth_candidates:
            final_candidates = self._filter_by_head(target_key, mouth_candidates)
        
        # 최종 선택: 가장 가까운 것
        if final_candidates:
            best_match = self._select_closest_match(target_key, final_candidates)
            return best_match
        elif mouth_candidates:
            # 헤드 매칭 실패시 입까지만 매칭된 것 선택
            best_match = self._select_closest_match(target_key, mouth_candidates)
            return best_match
        elif eye_candidates:
            # 입 매칭 실패시 눈까지만 매칭된 것 선택  
            best_match = self._select_closest_match(target_key, eye_candidates)
            return best_match
        else:
            return None
    
    def _filter_by_eyes(self, target_key):
        """눈 표정 필터링 - 5×5 지원"""
        ebl_target, ebr_target, ewl_target, ewr_target = target_key[0:4]
        candidates = []
        
        for key in self.sorted_keys:
            ebl, ebr, ewl, ewr = key[0:4]
            
            # 정확한 눈 매칭 (차이 ±1 허용)
            if (abs(ebl - ebl_target) <= 1 and 
                abs(ebr - ebr_target) <= 1 and
                abs(ewl - ewl_target) <= 1 and 
                abs(ewr - ewr_target) <= 1):
                candidates.append(key)
        
        return candidates
    
    def _filter_by_eyes_relaxed(self, target_key):
        """눈 표정 필터링 - 완화된 매칭"""
        ebl_target, ebr_target, ewl_target, ewr_target = target_key[0:4]
        candidates = []
        
        for key in self.sorted_keys:
            ebl, ebr, ewl, ewr = key[0:4]
            
            # 완화된 눈 매칭 (차이 ±2 허용)
            if (abs(ebl - ebl_target) <= 2 and 
                abs(ebr - ebr_target) <= 2 and
                abs(ewl - ewl_target) <= 2 and 
                abs(ewr - ewr_target) <= 2):
                candidates.append(key)
        
        return candidates
    
    def _filter_by_mouth(self, target_key, candidates):
        """입 표정 필터링 - 4단계 지원"""
        jo_target = target_key[4]
        mouth_candidates = []
        
        for key in candidates:
            jo = key[4]
            
            # 입 매칭 (차이 ±1 허용)
            if abs(jo - jo_target) <= 1:
                mouth_candidates.append(key)
        
        return mouth_candidates if mouth_candidates else candidates
    
    def _filter_by_head(self, target_key, candidates):
        """헤드 각도 필터링 - 11×11×11 지원"""
        hx_target, hy_target, bl_target = target_key[5:8]
        head_candidates = []
        
        for key in candidates:
            hx, hy, bl = key[5:8]
            
            # 헤드 매칭 (11×11×11에서 차이 ±2 허용)
            if (abs(hx - hx_target) <= 2 and 
                abs(hy - hy_target) <= 2 and
                abs(bl - bl_target) <= 2):
                head_candidates.append(key)
        
        return head_candidates if head_candidates else candidates
    
    def _select_closest_match(self, target_key, candidates):
        """최종 후보 중 가장 가까운 것 선택"""
        if not candidates:
            return None
            
        if len(candidates) == 1:
            return candidates[0]
        
        # 유클리드 거리로 가장 가까운 것 선택
        min_distance = float('inf')
        best_match = None
        
        for candidate in candidates:
            distance = sum((target_key[i] - candidate[i]) ** 2 for i in range(8))
            if distance < min_distance:
                min_distance = distance
                best_match = candidate
        
        return best_match
    
    def _convert_mocap_to_params(self, mocap_data):
        """모캡 데이터를 파라미터로 변환 - 5×5×4×11×11×11 지원"""
        
        def sensitivity_convert(value, param_type='general', steps=4):
            """민감도 기반 변환 - 단계 수 조정 가능"""
            base_thresholds = {
                'eye': [0.02, 0.25, 0.5, 0.75],      # 5단계용 (0,1,2,3,4)
                'eyebrow': [0.05, 0.3, 0.6, 0.8],    # 5단계용
                'jaw': [0.15, 0.45, 0.75],           # 4단계용 (0,1,2,3)
                'general': [0.05, 0.35, 0.7]
            }
            
            # 단계 수에 따라 임계값 조정
            if steps == 5:  # 눈용 (0,1,2,3,4)
                thresholds = base_thresholds.get(param_type, base_thresholds['eye'])
            elif steps == 4:  # 입용 (0,1,2,3)
                thresholds = base_thresholds.get(param_type, base_thresholds['jaw'])
            else:
                thresholds = base_thresholds.get(param_type, base_thresholds['general'])
            
            # 민감도 조정
            sensitivity_factor = self.sensitivity
            adjusted_thresholds = []
            for threshold in thresholds:
                if sensitivity_factor < 0.5:
                    adjusted = threshold * (1 + (0.5 - sensitivity_factor))
                else:
                    adjusted = threshold * (1 - (sensitivity_factor - 0.5) * 0.8)
                adjusted_thresholds.append(max(0.01, min(0.95, adjusted)))
            
            # 변환
            for i, threshold in enumerate(adjusted_thresholds):
                if value < threshold:
                    return i
            return steps - 1  # 최대값
        
        # **눈썹 표정 매핑 수정** - 5단계 지원
        ebl_sources = [
            'eyeWide_L', 'browInnerUp', 'browOuterUp_L', 'browDown_L'  # 왼쪽 눈썹 관련
        ]
        ebr_sources = [
            'eyeWide_R', 'browInnerUp', 'browOuterUp_R', 'browDown_R'  # 오른쪽 눈썹 관련
        ]
        
        # EBL (왼쪽 눈썹) - 5단계 (0,1,2,3,4)
        ebl_value = 0
        for source in ebl_sources:
            if source in mocap_data:
                ebl_value = max(ebl_value, mocap_data[source])
        ebl = sensitivity_convert(ebl_value, 'eyebrow', steps=5)
        
        # EBR (오른쪽 눈썹) - 5단계 (0,1,2,3,4)
        ebr_value = 0
        for source in ebr_sources:
            if source in mocap_data:
                ebr_value = max(ebr_value, mocap_data[source])
        ebr = sensitivity_convert(ebr_value, 'eyebrow', steps=5)
        
        # 눈 깜빡임 - 5단계 (0,1,2,3,4)
        ewl = sensitivity_convert(mocap_data.get('eyeBlink_L', 0), 'eye', steps=5)
        ewr = sensitivity_convert(mocap_data.get('eyeBlink_R', 0), 'eye', steps=5)
        
        # 입 - 4단계 (0,1,2,3)
        jo = sensitivity_convert(mocap_data.get('jawOpen', 0), 'jaw', steps=4)
        
        # 헤드 회전 - 11단계 (0,1,2,3,4,5,6,7,8,9,10)
        hx = self._convert_head_rotation_11x11(mocap_data.get('head_rx', 0), 'rx')
        hy = self._convert_head_rotation_11x11(mocap_data.get('head_ry', 0), 'ry')
        bl = self._convert_body_lean_11x11(mocap_data.get('head_rz', 0))
        
        return [ebl, ebr, ewl, ewr, jo, hx, hy, bl]
    
    def _convert_head_rotation_11x11(self, head_rotation_rad, axis):
        """헤드 회전 변환 - 11×11×11 지원 (0,1,2,3,4,5,6,7,8,9,10)"""
        max_rad = 0.6981  # 40도
        
        if axis == 'rx':
            normalized = max(-1, min(1, -head_rotation_rad / max_rad))
        else:  # 'ry'
            normalized = max(-1, min(1, head_rotation_rad / max_rad))
        
        # 민감도 적용 임계값들 (11단계)
        sensitivity_factor = self.sensitivity
        if sensitivity_factor < 0.5:
            # 덜 민감하게 - 중립 범위 넓게
            thresholds = [0.18, 0.32, 0.44, 0.55, 0.65, 0.74, 0.82, 0.88, 0.93, 0.97]
        else:
            # 더 민감하게
            thresholds = [0.12, 0.24, 0.35, 0.45, 0.55, 0.65, 0.74, 0.82, 0.89, 0.95]
        
        abs_norm = abs(normalized)
        
        # **11단계 매핑: 0,1,2,3,4,5,6,7,8,9,10 (중앙값 5)**
        if abs_norm < thresholds[0]:
            result = 5  # 중앙 (정면)
        else:
            # 점진적 단계 매핑
            for i, threshold in enumerate(thresholds):
                if abs_norm < threshold:
                    if axis == 'ry':  # 좌우 회전
                        if normalized > 0:
                            result = 5 + (i + 1)  # 6,7,8,9,10 (오른쪽)
                        else:
                            result = 5 - (i + 1)  # 4,3,2,1,0 (왼쪽)
                    else:  # 상하
                        if normalized > 0:
                            result = 5 - (i + 1)  # 4,3,2,1,0 (위)
                        else:
                            result = 5 + (i + 1)  # 6,7,8,9,10 (아래)
                    break
            else:
                # 극한 회전
                if axis == 'ry':
                    result = 10 if normalized > 0 else 0
                else:
                    result = 0 if normalized > 0 else 10
        
        # 범위 제한
        return max(0, min(10, result))
    
    def _convert_body_lean_11x11(self, head_rz_rad):
        """NZ(기울기) 변환 - 11×11×11 지원 (iFacialMocap 호환)"""
        max_rad = 0.4363  # 25도
        normalized = max(-1, min(1, head_rz_rad / max_rad))
        
        # 11단계 임계값
        thresholds = [0.12, 0.24, 0.35, 0.45, 0.55, 0.65, 0.74, 0.82, 0.89, 0.95]
        thresholds = [t * (1.5 - self.sensitivity * 0.5) for t in thresholds]
        
        abs_norm = abs(normalized)
        
        # 11단계 매핑 (중심값 5)
        if abs_norm < thresholds[0]:
            return 5  # 중앙
        else:
            for i, threshold in enumerate(thresholds):
                if abs_norm < threshold:
                    if normalized > 0:
                        return 5 + (i + 1)  # 6,7,8,9,10
                    else:
                        return 5 - (i + 1)  # 4,3,2,1,0
            # 극한값
            return 10 if normalized > 0 else 0
    
    def _load_image_if_needed(self, param_key):
        """이미지 로드 (캐시 활용)"""
        # 캐시 확인
        if param_key in self.image_cache:
            self.image_cache.move_to_end(param_key)
            return self.image_cache[param_key]
        
        # 파일에서 로드
        if param_key in self.image_paths:
            try:
                img = Image.open(self.image_paths[param_key]).convert('RGBA')
                
                # 캐시에 추가
                self.image_cache[param_key] = img
                self.image_cache.move_to_end(param_key)
                
                # 캐시 크기 관리
                while len(self.image_cache) > self.max_cache_size:
                    oldest_key = next(iter(self.image_cache))
                    del self.image_cache[oldest_key]
                
                return img
            except Exception:
                pass
        
        return None
    
    def get_cache_stats(self):
        """캐시 통계"""
        return {
            'indexed_count': len(self.image_paths),
            'cached_count': len(self.image_cache),
        }


class FixedOverlay(wx.Frame):
    """수정된 오버레이 - 제대로 닫히고 사라지지 않음"""
    
    def __init__(self, parent_app):
        super().__init__(None, title="VTuber-Overlay-For-OBS", 
                         style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)
        
        self.parent_app = parent_app
        self.SetSize(450, 500)
        
        # 화면 우측에 배치
        display = wx.GetDisplaySize()
        self.SetPosition((display[0] - 500, 50))
        
        # 현재 아바타
        self.current_avatar = None
        self.current_bitmap = None
        
        self.init_ui()
        
        # 타이머들
        self.update_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_update_timer)
        self.update_timer.Start(33)  # 30fps
        
        # 상단 유지 (덜 공격적)
        self.stay_top_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.stay_on_top, self.stay_top_timer)  
        self.stay_top_timer.Start(500)  # 0.5초마다
        
        # 이벤트 바인딩
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
        print("Fixed overlay created - 5×5×4×11×11×11 configuration")
        
    def init_ui(self):
        """UI 생성"""
        panel = wx.Panel(self)
        panel.SetBackgroundColour(wx.Colour(0, 255, 0))  # 크로마키 녹색
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 상태 표시
        self.status_label = wx.StaticText(panel, label="VTuber Overlay Ready - 5×5×4×11×11×11")
        self.status_label.SetForegroundColour(wx.Colour(255, 255, 255))
        font = self.status_label.GetFont()
        font.SetPointSize(12)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        self.status_label.SetFont(font)
        
        # 아바타 표시 영역
        self.avatar_panel = wx.Panel(panel, size=(400, 400))
        self.avatar_panel.SetBackgroundColour(wx.Colour(0, 255, 0))
        self.avatar_panel.Bind(wx.EVT_PAINT, self.on_paint_avatar)
        
        # 컨트롤 버튼들
        button_panel = wx.Panel(panel)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.close_btn = wx.Button(button_panel, label="Close", size=(60, 30))
        self.smaller_btn = wx.Button(button_panel, label="Smaller", size=(60, 30))  
        self.bigger_btn = wx.Button(button_panel, label="Bigger", size=(60, 30))
        
        # 버튼 이벤트 바인딩
        self.close_btn.Bind(wx.EVT_BUTTON, self.on_close_button)
        self.smaller_btn.Bind(wx.EVT_BUTTON, self.on_smaller)
        self.bigger_btn.Bind(wx.EVT_BUTTON, self.on_bigger)
        
        button_sizer.Add(self.close_btn, 0, wx.ALL, 2)
        button_sizer.Add(self.smaller_btn, 0, wx.ALL, 2)
        button_sizer.Add(self.bigger_btn, 0, wx.ALL, 2)
        button_panel.SetSizer(button_sizer)
        
        sizer.Add(self.status_label, 0, wx.ALL | wx.CENTER, 10)
        sizer.Add(self.avatar_panel, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(button_panel, 0, wx.CENTER | wx.ALL, 5)
        
        panel.SetSizer(sizer)
    
    def stay_on_top(self, event):
        """적당히 상단 유지"""
        if self.IsShown():
            self.Raise()
    
    def on_update_timer(self, event):
        """아바타 업데이트"""
        if (self.parent_app and hasattr(self.parent_app, 'current_avatar') and
            self.parent_app.current_avatar != self.current_avatar):
            
            self.current_avatar = self.parent_app.current_avatar
            self.current_bitmap = None
            self.avatar_panel.Refresh()
            
        # 상태 업데이트
        if hasattr(self.parent_app, 'timer') and self.parent_app.timer.IsRunning():
            self.status_label.SetLabel("VTuber Active - 5×5×4×11×11×11 Tracking")
        else:
            self.status_label.SetLabel("VTuber Stopped - 5×5×4×11×11×11 Ready")
    
    def on_paint_avatar(self, event):
        """아바타 그리기"""
        dc = wx.PaintDC(self.avatar_panel)
        dc.SetBackground(wx.Brush(wx.Colour(0, 255, 0)))
        dc.Clear()
        
        if self.current_avatar:
            try:
                if not self.current_bitmap:
                    self.current_bitmap = self.create_wx_bitmap()
                
                if self.current_bitmap:
                    panel_size = self.avatar_panel.GetSize()
                    bitmap_size = self.current_bitmap.GetSize()
                    
                    x = (panel_size[0] - bitmap_size[0]) // 2
                    y = (panel_size[1] - bitmap_size[1]) // 2
                    
                    dc.DrawBitmap(self.current_bitmap, x, y, True)
                    
            except Exception as e:
                dc.SetTextForeground(wx.Colour(255, 255, 255))
                dc.DrawText(f"Error: {e}", 10, 10)
        else:
            dc.SetTextForeground(wx.Colour(255, 255, 255))
            dc.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            dc.DrawText("Waiting for Avatar...", 50, 160)
            dc.DrawText("5×5×4×11×11×11 Mode", 50, 180)
            dc.DrawText("Start VTuber Mode", 50, 200)
    
    def create_wx_bitmap(self):
        """PIL 이미지를 wx.Bitmap으로 변환"""
        if not self.current_avatar:
            return None
            
        try:
            panel_size = self.avatar_panel.GetSize()
            max_size = min(panel_size[0] - 20, panel_size[1] - 20)
            
            img_size = self.current_avatar.size
            scale = min(max_size / img_size[0], max_size / img_size[1])
            
            if scale < 1:
                new_size = (int(img_size[0] * scale), int(img_size[1] * scale))
                resized_img = self.current_avatar.resize(new_size, Image.LANCZOS)
            else:
                resized_img = self.current_avatar
            
            wx_image = wx.Image(resized_img.size[0], resized_img.size[1], 
                               resized_img.convert('RGB').tobytes())
            
            if resized_img.mode == 'RGBA':
                wx_image.SetAlpha(resized_img.getchannel('A').tobytes())
            
            return wx.Bitmap(wx_image)
            
        except Exception:
            return None
    
    def on_close_button(self, event):
        """닫기 버튼 클릭 - 그냥 숨기기"""
        self.Hide()
        if hasattr(self.parent_app, 'overlay_btn'):
            self.parent_app.overlay_btn.SetLabel("Show Overlay")
    
    def on_close(self, event):
        """창 닫기 이벤트 - 항상 숨기기만 하고 절대 파괴하지 않음"""
        self.Hide()
        if hasattr(self.parent_app, 'overlay_btn'):
            self.parent_app.overlay_btn.SetLabel("Show Overlay")
    
    def on_smaller(self, event):
        """크기 줄이기"""
        current_size = self.GetSize()
        new_size = (max(300, int(current_size[0] * 0.9)), 
                   max(350, int(current_size[1] * 0.9)))
        self.SetSize(new_size)
        self.Layout()
    
    def on_bigger(self, event):
        """크기 늘리기"""
        current_size = self.GetSize()
        new_size = (min(800, int(current_size[0] * 1.1)), 
                   min(900, int(current_size[1] * 1.1)))
        self.SetSize(new_size)
        self.Layout()


class VTuberMainFrame(wx.Frame):
    """메인 컨트롤 프레임 - 5×5×4×11×11×11 지원"""
    
    def __init__(self):
        super().__init__(None, title="VTuber Controller - 5×5×4×11×11×11 Configuration", size=(700, 500))
        
        # 페이스 트래킹 시스템
        self.mocap_receiver = iFacialMocapReceiver()
        self.image_manager = UnifiedImageManager()
        self.current_avatar = None
        
        self.init_ui()
        
        # 수정된 오버레이
        self.overlay_frame = FixedOverlay(self)
        
        # 타이머
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        
        # 성능 측정
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.fps = 0
        self.last_ui_update = 0
        
    def init_ui(self):
        """메인 UI"""
        panel = wx.Panel(self)
        
        # 타이틀
        title = wx.StaticText(panel, label="VTuber Controller - 5×5×4×11×11×11 Configuration")
        font = title.GetFont()
        font.SetPointSize(14)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(font)
        
        # 버튼들
        self.start_btn = wx.Button(panel, label="Start VTuber Mode", size=(150, 40))
        self.overlay_btn = wx.Button(panel, label="Show Overlay", size=(150, 40))
        
        self.start_btn.Bind(wx.EVT_BUTTON, self.on_start_stop)
        self.overlay_btn.Bind(wx.EVT_BUTTON, self.on_toggle_overlay)
        
        # 상태 표시
        self.status_text = wx.StaticText(panel, label="Status: Stopped")
        self.fps_text = wx.StaticText(panel, label="FPS: 0")
        
        # 설정들
        sens_label = wx.StaticText(panel, label="민감도:")
        self.sensitivity_slider = wx.Slider(panel, value=50, minValue=20, maxValue=80,
                                          style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        
        self.unified_cb = wx.CheckBox(panel, label="Sequential Matching (Eyes→Mouth→Head)")
        self.unified_cb.SetValue(True)
        
        chroma_label = wx.StaticText(panel, label="크로마키 색상:")
        self.chroma_choice = wx.Choice(panel, choices=["녹색 (권장)", "파란색", "검정색", "투명"])
        self.chroma_choice.SetSelection(0)
        
        # 파라미터 표시
        self.param_display = wx.StaticText(panel, label="Parameters: Ready")
        
        # 안내 정보
        info_text = """5×5×4×11×11×11 Configuration:
- Eyes: 5×5 levels (Left/Right Eyebrow + Left/Right Wink)
- Mouth: 4 levels (Jaw Open)
- Head: 11×11×11 levels (X/Y/Z rotation)

Features:
- Enhanced head rotation precision (11 steps vs 5)
- Improved eye expression range (5 steps vs 4)
- Optimized sequential matching algorithm
- Fixed overlay window behavior

Usage:
1. Start VTuber Mode
2. Show Overlay
3. Use OBS Window Capture: 'VTuber-Overlay-For-OBS'
4. Apply green screen filter in OBS"""
        
        info_ctrl = wx.StaticText(panel, label=info_text)
        
        # 레이아웃
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(self.start_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.overlay_btn, 0, wx.ALL, 5)
        
        status_sizer = wx.BoxSizer(wx.HORIZONTAL)
        status_sizer.Add(self.status_text, 1, wx.ALL, 5)
        status_sizer.Add(self.fps_text, 0, wx.ALL, 5)
        
        sens_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sens_sizer.Add(sens_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        sens_sizer.Add(self.sensitivity_slider, 1, wx.EXPAND | wx.ALL, 5)
        
        chroma_sizer = wx.BoxSizer(wx.HORIZONTAL)
        chroma_sizer.Add(chroma_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        chroma_sizer.Add(self.chroma_choice, 0, wx.ALL, 5)
        
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 10)
        sizer.Add(btn_sizer, 0, wx.ALL | wx.CENTER, 10)
        sizer.Add(status_sizer, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(sens_sizer, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.unified_cb, 0, wx.ALL, 5)
        sizer.Add(chroma_sizer, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.param_display, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(info_ctrl, 1, wx.ALL | wx.EXPAND, 10)
        
        panel.SetSizer(sizer)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
    def on_start_stop(self, event):
        """VTuber 모드 시작/중지"""
        if not self.timer.IsRunning():
            if self.mocap_receiver.start():
                self.timer.Start(33)  # 30fps
                self.start_btn.SetLabel("Stop VTuber Mode")
                self.start_btn.SetBackgroundColour(wx.Colour(200, 100, 100))
                self.status_text.SetLabel("Status: Running (30fps) - 5×5×4×11×11×11")
            else:
                wx.MessageBox("iFacialMocap 연결 실패!", "Connection Error", wx.OK | wx.ICON_ERROR)
        else:
            self.timer.Stop()
            self.mocap_receiver.stop()
            self.start_btn.SetLabel("Start VTuber Mode")
            self.start_btn.SetBackgroundColour(wx.Colour(100, 200, 100))
            self.status_text.SetLabel("Status: Stopped")
    
    def on_toggle_overlay(self, event):
        """오버레이 표시/숨김 - RuntimeError 방지"""
        try:
            # 오버레이가 삭제되었는지 확인
            if self.overlay_frame and self.overlay_frame.IsShown():
                self.overlay_frame.Hide()
                self.overlay_btn.SetLabel("Show Overlay")
            else:
                # 오버레이가 삭제되었거나 숨겨진 경우
                if not self.overlay_frame:
                    # 새로 생성
                    self.overlay_frame = FixedOverlay(self)
                self.overlay_frame.Show()
                self.overlay_frame.Raise()
                self.overlay_btn.SetLabel("Hide Overlay")
        except (RuntimeError, AttributeError):
            # C++ 객체가 삭제된 경우 새로 생성
            self.overlay_frame = FixedOverlay(self)
            self.overlay_frame.Show()
            self.overlay_frame.Raise()
            self.overlay_btn.SetLabel("Hide Overlay")
    
    def on_timer(self, event):
        """메인 타이머 루프"""
        # 설정 업데이트
        self.image_manager.fallback_search_enabled = self.unified_cb.GetValue()
        sensitivity = self.sensitivity_slider.GetValue() / 100.0
        self.image_manager.sensitivity = sensitivity
        
        # 모캡 데이터 가져오기
        mocap_data = self.mocap_receiver.get_latest_data()
        
        # 아바타 선택 (5×5×4×11×11×11 알고리즘)
        new_avatar = self.image_manager.get_best_avatar_image(mocap_data)
        if new_avatar:
            self.current_avatar = new_avatar
        
        # UI 업데이트 (5fps로 제한)
        current_time = time.time()
        if current_time - self.last_ui_update > 0.2:
            self.update_ui(mocap_data)
            self.last_ui_update = current_time
        
        # FPS 계산
        self.frame_count += 1
        if current_time - self.last_fps_time >= 1.0:
            self.fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
    
    def update_ui(self, mocap_data):
        """UI 상태 업데이트"""
        self.fps_text.SetLabel(f"FPS: {self.fps:.1f}")
        
        if mocap_data:
            params = self.image_manager._convert_mocap_to_params(mocap_data)
            param_str = f"EBL{params[0]}_EBR{params[1]}_EWL{params[2]}_EWR{params[3]}_JO{params[4]}_HX{params[5]:02d}_HY{params[6]:02d}_NZ{params[7]:02d}"
            
            if self.image_manager.last_matched_key:
                key = self.image_manager.last_matched_key  
                matched_str = f"EBL{key[0]}_EBR{key[1]}_EWL{key[2]}_EWR{key[3]}_JO{key[4]}_HX{key[5]:02d}_HY{key[6]:02d}_NZ{key[7]:02d}"
                method = self.image_manager.last_search_method
                self.param_display.SetLabel(f"Target: {param_str}\nMatched: {matched_str}\nMethod: {method}")
            else:
                self.param_display.SetLabel(f"Target: {param_str}\nMatched: None")
    
    def on_close(self, event):
        """프로그램 종료 - 오버레이도 강제 종료"""
        self.timer.Stop()
        self.mocap_receiver.stop()
        
        # 오버레이 종료 - 타이머 먼저 중지
        if hasattr(self, 'overlay_frame'):
            try:
                if hasattr(self.overlay_frame, 'update_timer'):
                    self.overlay_frame.update_timer.Stop()
                if hasattr(self.overlay_frame, 'stay_top_timer'):
                    self.overlay_frame.stay_top_timer.Stop()
                self.overlay_frame.Destroy()
            except (RuntimeError, AttributeError):
                pass  # 이미 삭제된 경우 무시
        
        self.Destroy()


class VTuberApp(wx.App):
    def OnInit(self):
        self.main_frame = VTuberMainFrame()
        self.main_frame.Show()
        return True


if __name__ == "__main__":
    app = VTuberApp()
    app.MainLoop()