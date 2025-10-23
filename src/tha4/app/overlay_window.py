#!/usr/bin/env python3
"""
VTuber Overlay - absolute_perfect.py 기반
독립 실행 버전
"""

import wx
import socket
import threading
import time
import math
import os
import glob
from PIL import Image
from collections import defaultdict, OrderedDict

class iFacialMocapReceiver:
    """iFacialMocap UDP 데이터 수신"""
    
    def __init__(self, port=49983):
        self.port = port
        self.socket = None
        self.running = False
        self.latest_data = {}
        self.thread = None
        
        self.data_history = defaultdict(list)
        self.history_size = 3
        
        self.last_log_time = 0
        self.log_interval = 2.0
        
        self.received_params = set()
        
    def start(self):
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
        self.running = False
        if self.socket:
            self.socket.close()
        if self.thread:
            self.thread.join()
    
    def _receive_loop(self):
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
                        
                        if name not in self.received_params:
                            self.received_params.add(name)
                            print(f"✓ New parameter detected: {name}")
                            
                    except (ValueError, IndexError):
                        continue
            
            self._smooth_data(raw_data)
                        
        except Exception as e:
            current_time = time.time()
            if current_time - self.last_log_time > self.log_interval:
                print(f"Error parsing data: {e}")
                self.last_log_time = current_time
    
    def _smooth_data(self, raw_data):
        for key, value in raw_data.items():
            self.data_history[key].append(value)
            if len(self.data_history[key]) > self.history_size:
                self.data_history[key].pop(0)
            
            if len(self.data_history[key]) >= 2:
                smoothed = sum(self.data_history[key]) / len(self.data_history[key])
                self.latest_data[key] = smoothed
            else:
                self.latest_data[key] = value
    
    def _parse_head_eye_data(self, data_part, raw_data):
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
        return self.latest_data.copy()


class UnifiedImageManager:
    """통합 균형 매칭을 위한 이미지 관리자"""
    
    def __init__(self, images_base_dir=None, max_cache_size=300):
        # 환경변수에서 data 경로 가져오기
        if images_base_dir is None:
            env_data_path = os.environ.get('VTUBER_DATA_PATH')
            if env_data_path:
                images_base_dir = env_data_path
            else:
                # 상대 경로
                script_dir = os.path.dirname(os.path.abspath(__file__))
                images_base_dir = os.path.join(script_dir, '../../../data')
        
        self.images_base_dir = images_base_dir
        self.image_cache = OrderedDict()
        self.image_paths = {}
        self.max_cache_size = max_cache_size
        
        self.fallback_search_enabled = True
        self.sensitivity = 0.5
        
        self.last_debug_time = 0
        self.debug_interval = 3.0
        self.last_matched_key = None
        self.last_search_method = ""
        
        self.last_eye_debug = 0
        self.eye_debug_interval = 1.0
        
        self.last_avatar_image = None
        
        print(f"Data path: {self.images_base_dir}")
        self.index_image_paths()
        self._create_sorted_keys()
        
    def index_image_paths(self):
        print("Indexing images for enhanced eye recognition...")
        start_time = time.time()
        
        image_dir = os.path.join(self.images_base_dir, "eye_face_optimized_patches")
        if not os.path.exists(image_dir):
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
        
        patterns = ["eye_face_*.png", "opt_*.png"]
        
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
        print(f"Enhanced eye recognition system ready!")
        
    def _parse_filename(self, filename):
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
        self.sorted_keys = sorted(list(self.image_paths.keys()))
        print(f"Created sorted key index with {len(self.sorted_keys)} entries")
        
    def get_best_avatar_image(self, mocap_data):
        head_rx = abs(mocap_data.get('head_rx', 0))
        head_ry = abs(mocap_data.get('head_ry', 0))
        head_rz = abs(mocap_data.get('head_rz', 0))
        
        if head_rx < 0.05 and head_ry < 0.05 and head_rz < 0.05:
            mocap_data_corrected = mocap_data.copy()
            mocap_data_corrected['head_rx'] = 0.0
            mocap_data_corrected['head_ry'] = 0.0  
            mocap_data_corrected['head_rz'] = 0.0
            mocap_data = mocap_data_corrected
        
        params = self._convert_mocap_to_params(mocap_data)
        param_key = tuple(params)
        
        img = self._load_image_if_needed(param_key)
        if img:
            self.last_matched_key = param_key
            self.last_search_method = "EXACT MATCH"
            self.last_avatar_image = img
            return img
        
        if self.fallback_search_enabled:
            best_match = self._find_sequential_best_match(param_key)
            if best_match:
                img = self._load_image_if_needed(best_match)
                if img:
                    self.last_matched_key = best_match
                    self.last_search_method = "SEQUENTIAL MATCH"
                    self.last_avatar_image = img
                    return img
        
        if self.last_avatar_image:
            self.last_search_method = "PREVIOUS"
            return self.last_avatar_image
        
        default_key = (0, 0, 0, 0, 0, 5, 5, 5)
        img = self._load_image_if_needed(default_key)
        if img:
            self.last_matched_key = default_key
            self.last_search_method = "DEFAULT"
            self.last_avatar_image = img
        return img
    
    def _find_sequential_best_match(self, target_key):
        eye_candidates = self._filter_by_eyes(target_key)
        
        if not eye_candidates:
            eye_candidates = self._filter_by_eyes_relaxed(target_key)
        
        if eye_candidates:
            mouth_candidates = self._filter_by_mouth(target_key, eye_candidates)
        else:
            mouth_candidates = []
        
        final_candidates = []
        if mouth_candidates:
            final_candidates = self._filter_by_head(target_key, mouth_candidates)
        
        if final_candidates:
            return self._select_closest_match(target_key, final_candidates)
        elif mouth_candidates:
            return self._select_closest_match(target_key, mouth_candidates)
        elif eye_candidates:
            return self._select_closest_match(target_key, eye_candidates)
        else:
            return None
    
    def _filter_by_eyes(self, target_key):
        ebl_target, ebr_target, ewl_target, ewr_target = target_key[0:4]
        candidates = []
        
        for key in self.sorted_keys:
            ebl, ebr, ewl, ewr = key[0:4]
            
            if (abs(ebl - ebl_target) <= 1 and 
                abs(ebr - ebr_target) <= 1 and
                abs(ewl - ewl_target) <= 1 and
                abs(ewr - ewr_target) <= 1):
                candidates.append(key)
        
        return candidates
    
    def _filter_by_eyes_relaxed(self, target_key):
        ebl_target, ebr_target, ewl_target, ewr_target = target_key[0:4]
        candidates = []
        
        for key in self.sorted_keys:
            ebl, ebr, ewl, ewr = key[0:4]
            
            if (abs(ebl - ebl_target) <= 2 and 
                abs(ebr - ebr_target) <= 2 and
                abs(ewl - ewl_target) <= 2 and
                abs(ewr - ewr_target) <= 2):
                candidates.append(key)
        
        return candidates
    
    def _filter_by_mouth(self, target_key, candidates):
        jo_target = target_key[4]
        mouth_candidates = []
        
        for key in candidates:
            jo = key[4]
            if abs(jo - jo_target) <= 1:
                mouth_candidates.append(key)
        
        return mouth_candidates if mouth_candidates else candidates
    
    def _filter_by_head(self, target_key, candidates):
        hx_target, hy_target, bl_target = target_key[5:8]
        head_candidates = []
        
        for key in candidates:
            hx, hy, bl = key[5:8]
            
            if (abs(hx - hx_target) <= 2 and 
                abs(hy - hy_target) <= 2 and
                abs(bl - bl_target) <= 2):
                head_candidates.append(key)
        
        return head_candidates if head_candidates else candidates
    
    def _select_closest_match(self, target_key, candidates):
        if not candidates:
            return None
            
        if len(candidates) == 1:
            return candidates[0]
        
        min_distance = float('inf')
        best_match = None
        
        for candidate in candidates:
            distance = sum((target_key[i] - candidate[i]) ** 2 for i in range(8))
            if distance < min_distance:
                min_distance = distance
                best_match = candidate
        
        return best_match
    
    def _convert_mocap_to_params(self, mocap_data):
        def sensitivity_convert(value, param_type='general'):
            base_thresholds = {
                'eye': [0.02, 0.25, 0.7],
                'eyebrow': [0.05, 0.3, 0.6],
                'jaw': [0.05, 0.3, 0.75],
                'general': [0.05, 0.35, 0.7]
            }
            
            thresholds = base_thresholds.get(param_type, base_thresholds['general'])
            
            sensitivity_factor = self.sensitivity
            adjusted_thresholds = []
            for threshold in thresholds:
                if sensitivity_factor < 0.5:
                    adjusted = threshold * (1 + (0.5 - sensitivity_factor))
                else:
                    adjusted = threshold * (1 - (sensitivity_factor - 0.5) * 0.8)
                adjusted_thresholds.append(max(0.01, min(0.95, adjusted)))
            
            for i, threshold in enumerate(adjusted_thresholds):
                if value < threshold:
                    return i
            return 3
        
        # 눈썹
        ebl_sources = ['eyeWide_L', 'browInnerUp', 'browOuterUp_L', 'browDown_L']
        ebr_sources = ['eyeWide_R', 'browInnerUp', 'browOuterUp_R', 'browDown_R']
        
        ebl_value = 0
        for source in ebl_sources:
            if source in mocap_data:
                ebl_value = max(ebl_value, mocap_data[source])
        
        ebr_value = 0
        for source in ebr_sources:
            if source in mocap_data:
                ebr_value = max(ebr_value, mocap_data[source])
        
        ebl = sensitivity_convert(ebl_value, 'eyebrow')
        ebr = sensitivity_convert(ebr_value, 'eyebrow')
        
        # 눈 깜빡임
        ewl_value = 0
        ewl_sources = ['eyeBlink_R', 'eyeBlinkRight', 'EyeBlinkRight', 'eyeblink_R']
        for source in ewl_sources:
            if source in mocap_data:
                ewl_value = max(ewl_value, mocap_data[source])
        
        ewr_value = 0
        ewr_sources = ['eyeBlink_L', 'eyeBlinkLeft', 'EyeBlinkLeft', 'eyeblink_L']
        for source in ewr_sources:
            if source in mocap_data:
                ewr_value = max(ewr_value, mocap_data[source])
        
        ewl = sensitivity_convert(ewl_value, 'eye')
        ewr = sensitivity_convert(ewr_value, 'eye')
        
        # 입
        jaw_value = 0
        jaw_sources = ['jawOpen', 'JawOpen', 'mouthOpen']
        for source in jaw_sources:
            if source in mocap_data:
                jaw_value = max(jaw_value, mocap_data[source])
        
        jo = sensitivity_convert(jaw_value, 'jaw')
        
        # 헤드
        hx = self._convert_head_rotation_11x11(mocap_data.get('head_rx', 0), 'rx')
        hy = self._convert_head_rotation_11x11(mocap_data.get('head_ry', 0), 'ry')
        bl = self._convert_body_lean_11x11(mocap_data.get('head_rz', 0))
        
        return [ebl, ebr, ewl, ewr, jo, hx, hy, bl]
    
    def _convert_head_rotation_11x11(self, head_rotation_rad, axis):
        max_rad = 0.6981
        
        if axis == 'rx':
            normalized = max(-1, min(1, -head_rotation_rad / max_rad))
        else:
            normalized = max(-1, min(1, head_rotation_rad / max_rad))
        
        thresholds = [0.12, 0.24, 0.35, 0.45, 0.55, 0.65, 0.74, 0.82, 0.89, 0.95]
        
        abs_norm = abs(normalized)
        
        if abs_norm < thresholds[0]:
            result = 5
        else:
            for i, threshold in enumerate(thresholds):
                if abs_norm < threshold:
                    if axis == 'ry':
                        result = (5 + (i + 1)) if normalized > 0 else (5 - (i + 1))
                    else:
                        result = (5 - (i + 1)) if normalized > 0 else (5 + (i + 1))
                    break
            else:
                if axis == 'ry':
                    result = 10 if normalized > 0 else 0
                else:
                    result = 0 if normalized > 0 else 10
        
        return max(0, min(10, result))
    
    def _convert_body_lean_11x11(self, head_rz_rad):
        max_rad = 0.4363
        normalized = max(-1, min(1, head_rz_rad / max_rad))
        
        thresholds = [0.18, 0.36, 0.53, 0.68, 0.83, 0.98, 1.11, 1.23, 1.34, 1.43]
        
        abs_norm = abs(normalized)
        
        if abs_norm < thresholds[0]:
            return 5
        else:
            for i, threshold in enumerate(thresholds):
                if abs_norm < threshold:
                    return (5 + (i + 1)) if normalized > 0 else (5 - (i + 1))
            return 10 if normalized > 0 else 0
    
    def _load_image_if_needed(self, param_key):
        if param_key in self.image_cache:
            self.image_cache.move_to_end(param_key)
            return self.image_cache[param_key]
        
        if param_key in self.image_paths:
            try:
                img = Image.open(self.image_paths[param_key]).convert('RGBA')
                
                self.image_cache[param_key] = img
                self.image_cache.move_to_end(param_key)
                
                while len(self.image_cache) > self.max_cache_size:
                    oldest_key = next(iter(self.image_cache))
                    del self.image_cache[oldest_key]
                
                return img
            except Exception:
                pass
        
        return None


class FixedOverlay(wx.Frame):
    """오버레이 윈도우 - 단독 실행"""
    
    def __init__(self):
        super().__init__(None, title="VTuber-Overlay-For-OBS", 
                         style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)
        
        self.SetSize(450, 500)
        
        # 창 투명도 설정 (크로마키 개선)
        self.SetTransparent(255)
        
        display = wx.GetDisplaySize()
        self.SetPosition((display[0] - 500, 50))
        
        self.current_avatar = None
        self.current_bitmap = None
        
        # FPS 카운터
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.fps = 0
        
        # 데이터 수신 초기화
        self.mocap_receiver = iFacialMocapReceiver()
        self.image_manager = UnifiedImageManager()
        
        self.init_ui()
        
        # iFacialMocap 시작
        if not self.mocap_receiver.start():
            wx.MessageBox("iFacialMocap connection failed!", "Connection Error", wx.OK | wx.ICON_ERROR)
        
        # 업데이트 타이머 - 60 FPS
        self.update_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_update_timer)
        self.update_timer.Start(16)  # 16ms = ~60 FPS
        
        # 상단 유지 타이머
        self.stay_top_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.stay_on_top, self.stay_top_timer)  
        self.stay_top_timer.Start(500)
        
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
    def init_ui(self):
        panel = wx.Panel(self)
        # 크로마키를 위한 순수 초록색 (RGB: 0, 255, 0)
        chroma_green = wx.Colour(0, 255, 0)
        panel.SetBackgroundColour(chroma_green)
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 상태 라벨 (크로마키 배경)
        status_panel = wx.Panel(panel)
        status_panel.SetBackgroundColour(chroma_green)
        status_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.status_label = wx.StaticText(status_panel, label="VTuber Overlay - FPS: 0.0")
        self.status_label.SetForegroundColour(wx.Colour(255, 255, 255))
        font = self.status_label.GetFont()
        font.SetPointSize(10)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        self.status_label.SetFont(font)
        
        status_sizer.Add(self.status_label, 1, wx.ALL | wx.CENTER, 5)
        status_panel.SetSizer(status_sizer)
        
        # 아바타 패널 (크로마키 배경)
        self.avatar_panel = wx.Panel(panel, size=(400, 400))
        self.avatar_panel.SetBackgroundColour(chroma_green)
        self.avatar_panel.Bind(wx.EVT_PAINT, self.on_paint_avatar)
        
        # 버튼 패널 (크로마키 배경)
        button_panel = wx.Panel(panel)
        button_panel.SetBackgroundColour(chroma_green)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 버튼들 - 작지만 보이게
        self.close_btn = wx.Button(button_panel, label="✕", size=(40, 30))
        self.smaller_btn = wx.Button(button_panel, label="−", size=(40, 30))  
        self.bigger_btn = wx.Button(button_panel, label="+", size=(40, 30))
        
        # 버튼 색상 - 반투명 느낌
        btn_bg = wx.Colour(30, 30, 30)
        self.close_btn.SetBackgroundColour(wx.Colour(180, 0, 0))
        self.close_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.smaller_btn.SetBackgroundColour(btn_bg)
        self.smaller_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.bigger_btn.SetBackgroundColour(btn_bg)
        self.bigger_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        
        # 버튼 폰트 크기
        btn_font = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.close_btn.SetFont(btn_font)
        self.smaller_btn.SetFont(btn_font)
        self.bigger_btn.SetFont(btn_font)
        
        # 버튼 이벤트
        self.close_btn.Bind(wx.EVT_BUTTON, self.on_close_button)
        self.smaller_btn.Bind(wx.EVT_BUTTON, self.on_smaller)
        self.bigger_btn.Bind(wx.EVT_BUTTON, self.on_bigger)
        
        button_sizer.Add(self.smaller_btn, 0, wx.ALL, 3)
        button_sizer.Add(self.bigger_btn, 0, wx.ALL, 3)
        button_sizer.Add(self.close_btn, 0, wx.ALL, 3)
        button_panel.SetSizer(button_sizer)
        
        # 메인 레이아웃에 추가
        main_sizer.Add(status_panel, 0, wx.EXPAND | wx.ALL, 0)
        main_sizer.Add(self.avatar_panel, 1, wx.EXPAND | wx.ALL, 0)
        main_sizer.Add(button_panel, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        
        panel.SetSizer(main_sizer)
        self.Layout()
    
    def stay_on_top(self, event):
        if self.IsShown():
            self.Raise()
    
    def on_update_timer(self, event):
        # 모캡 데이터 받아서 아바타 업데이트
        mocap_data = self.mocap_receiver.get_latest_data()
        
        if mocap_data:
            new_avatar = self.image_manager.get_best_avatar_image(mocap_data)
            if new_avatar and new_avatar != self.current_avatar:
                self.current_avatar = new_avatar
                self.current_bitmap = None
                self.avatar_panel.Refresh()
        
        # FPS 계산
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
            
            # 상태 라벨 업데이트
            self.status_label.SetLabel(f"VTuber Overlay - FPS: {self.fps:.1f}")
            self.status_label.Refresh()
    
    def on_paint_avatar(self, event):
        dc = wx.PaintDC(self.avatar_panel)
        # 크로마키 순수 초록 (RGB: 0, 255, 0)
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
                pass  # 에러 메시지 표시 안 함 (크로마키 방해)
        else:
            # 대기 중 메시지 - 작게 표시
            dc.SetTextForeground(wx.Colour(255, 255, 255))
            dc.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            text = "Waiting..."
            text_width, text_height = dc.GetTextExtent(text)
            panel_size = self.avatar_panel.GetSize()
            x = (panel_size[0] - text_width) // 2
            y = (panel_size[1] - text_height) // 2
            dc.DrawText(text, x, y)
    
    def create_wx_bitmap(self):
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
        self.on_close(event)
    
    def on_close(self, event):
        print("Closing VTuber Overlay...")
        self.update_timer.Stop()
        self.stay_top_timer.Stop()
        self.mocap_receiver.stop()
        self.Destroy()
        
        # 앱 완전 종료
        wx.GetApp().ExitMainLoop()
        import sys
        sys.exit(0)
    
    def on_smaller(self, event):
        current_size = self.GetSize()
        new_size = (max(300, int(current_size[0] * 0.9)), 
                   max(350, int(current_size[1] * 0.9)))
        self.SetSize(new_size)
        self.Layout()
    
    def on_bigger(self, event):
        current_size = self.GetSize()
        new_size = (min(800, int(current_size[0] * 1.1)), 
                   min(900, int(current_size[1] * 1.1)))
        self.SetSize(new_size)
        self.Layout()


class VTuberApp(wx.App):
    def OnInit(self):
        self.frame = FixedOverlay()
        self.frame.Show()
        return True


if __name__ == "__main__":
    print("\n" + "="*50)
    print("🎭 VTuber Overlay (wxPython)")
    print("="*50 + "\n")
    
    app = VTuberApp()
    app.MainLoop()