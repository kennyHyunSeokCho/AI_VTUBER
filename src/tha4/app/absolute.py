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
        """데이터 평활화 - 떨림 방지"""
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
    """통합 균형 매칭을 위한 이미지 관리자 - absolute-2.py의 눈 인식 적용"""
    
    def __init__(self, images_base_dir="data", max_cache_size=300):
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
        """순차적 매칭 - 눈→입→헤드 순서로 단계별 매칭"""
        
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
        """순차적 단계별 매칭 - 눈→입→헤드 순서로 정확한 매칭"""
        
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
        """눈 표정 필터링 - 정확한 매칭"""
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
        """눈 표정 필터링 - 완화된 매칭"""
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
        """입 표정 필터링"""
        jo_target = target_key[4]
        mouth_candidates = []
        
        for key in candidates:
            jo = key[4]
            if abs(jo - jo_target) <= 1:
                mouth_candidates.append(key)
        
        return mouth_candidates if mouth_candidates else candidates
    
    def _filter_by_head(self, target_key, candidates):
        """헤드 각도 필터링"""
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
        """최종 후보 중 가장 가까운 것 선택"""
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
        """모캡 데이터를 파라미터로 변환 - absolute-2.py의 민감한 눈 인식 적용"""
        
        def sensitivity_convert(value, param_type='general'):
            """민감도 기반 변환"""
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
        
        # 눈 깜빡임 - 좌우 반전 수정
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
        
        # 디버깅
        current_time = time.time()
        if current_time - self.last_eye_debug > self.eye_debug_interval:
            if ewl_value > 0.01 or ewr_value > 0.01:
                print(f"Eye: L={ewl_value:.3f}->EWL{ewl}, R={ewr_value:.3f}->EWR{ewr}")
            self.last_eye_debug = current_time
        
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
        """헤드 회전 변환"""
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
        """NZ(기울기) 변환"""
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
        """이미지 로드"""
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
    
    def get_cache_stats(self):
        return {
            'indexed_count': len(self.image_paths),
            'cached_count': len(self.image_cache),
        }


class FixedOverlay(wx.Frame):
    
    def __init__(self, parent_app):
        super().__init__(None, title="VTuber-Overlay-For-OBS", 
                         style=wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP)
        
        self.parent_app = parent_app
        self.SetSize(450, 500)
        
        display = wx.GetDisplaySize()
        self.SetPosition((display[0] - 500, 50))
        
        self.current_avatar = None
        self.current_bitmap = None
        
        self.init_ui()
        
        self.update_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_update_timer)
        self.update_timer.Start(33)
        
        self.stay_top_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.stay_on_top, self.stay_top_timer)  
        self.stay_top_timer.Start(500)
        
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
    def init_ui(self):
        panel = wx.Panel(self)
        panel.SetBackgroundColour(wx.Colour(0, 255, 0))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.status_label = wx.StaticText(panel, label="VTuber Overlay Ready")
        self.status_label.SetForegroundColour(wx.Colour(255, 255, 255))
        font = self.status_label.GetFont()
        font.SetPointSize(12)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        self.status_label.SetFont(font)
        
        self.avatar_panel = wx.Panel(panel, size=(400, 400))
        self.avatar_panel.SetBackgroundColour(wx.Colour(0, 255, 0))
        self.avatar_panel.Bind(wx.EVT_PAINT, self.on_paint_avatar)
        
        button_panel = wx.Panel(panel)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.close_btn = wx.Button(button_panel, label="Close", size=(60, 30))
        self.smaller_btn = wx.Button(button_panel, label="Smaller", size=(60, 30))  
        self.bigger_btn = wx.Button(button_panel, label="Bigger", size=(60, 30))
        
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
        if self.IsShown():
            self.Raise()
    
    def on_update_timer(self, event):
        if (self.parent_app and hasattr(self.parent_app, 'current_avatar') and
            self.parent_app.current_avatar != self.current_avatar):
            
            self.current_avatar = self.parent_app.current_avatar
            self.current_bitmap = None
            self.avatar_panel.Refresh()
            
        if hasattr(self.parent_app, 'timer') and self.parent_app.timer.IsRunning():
            self.status_label.SetLabel("VTuber Active - Enhanced Eye Tracking")
        else:
            self.status_label.SetLabel("VTuber Stopped")
    
    def on_paint_avatar(self, event):
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
            dc.DrawText("Waiting for Avatar...", 50, 180)
    
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
        self.Hide()
        if hasattr(self.parent_app, 'overlay_btn'):
            self.parent_app.overlay_btn.SetLabel("Show Overlay")
    
    def on_close(self, event):
        self.Hide()
        if hasattr(self.parent_app, 'overlay_btn'):
            self.parent_app.overlay_btn.SetLabel("Show Overlay")
    
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


class VTuberMainFrame(wx.Frame):
    
    def __init__(self):
        super().__init__(None, title="VTuber Controller - Enhanced Eye Recognition", size=(700, 580))
        
        self.mocap_receiver = iFacialMocapReceiver()
        self.image_manager = UnifiedImageManager()
        self.current_avatar = None
        
        self.init_ui()
        
        self.overlay_frame = FixedOverlay(self)
        
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer)
        
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.fps = 0
        self.last_ui_update = 0
        
    def init_ui(self):
        panel = wx.Panel(self)
        
        title = wx.StaticText(panel, label="VTuber Controller - Enhanced Eye Recognition")
        font = title.GetFont()
        font.SetPointSize(14)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(font)
        
        self.start_btn = wx.Button(panel, label="Start VTuber Mode", size=(150, 40))
        self.overlay_btn = wx.Button(panel, label="Show Overlay", size=(150, 40))
        
        self.start_btn.Bind(wx.EVT_BUTTON, self.on_start_stop)
        self.overlay_btn.Bind(wx.EVT_BUTTON, self.on_toggle_overlay)
        
        self.status_text = wx.StaticText(panel, label="Status: Stopped")
        self.fps_text = wx.StaticText(panel, label="FPS: 0")
        
        self.eye_debug_text = wx.StaticText(panel, label="Eye Blink: L=0.000(EWL0) R=0.000(EWR0)")
        self.eye_debug_text.SetForegroundColour(wx.Colour(0, 100, 200))
        font_eye = self.eye_debug_text.GetFont()
        font_eye.SetPointSize(11)
        font_eye.SetWeight(wx.FONTWEIGHT_BOLD)
        self.eye_debug_text.SetFont(font_eye)
        
        sens_label = wx.StaticText(panel, label="Sensitivity:")
        self.sensitivity_slider = wx.Slider(panel, value=50, minValue=20, maxValue=80,
                                          style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        
        chroma_label = wx.StaticText(panel, label="Chroma Key:")
        self.chroma_choice = wx.Choice(panel, choices=["Green", "Blue", "Black"])
        self.chroma_choice.SetSelection(0)
        
        self.param_display = wx.StaticText(panel, label="Parameters: Ready")
        
        info_text = """Enhanced Eye Recognition System:
- Very sensitive eye blink detection (0.02 threshold)
- Multi-source eye parameter fusion
- Smooth 3-frame averaging to reduce jitter
- Sequential matching: Eyes -> Mouth -> Head
- Fixed left/right eye mirroring issue

Just start and blink naturally!"""
        
        info_ctrl = wx.StaticText(panel, label=info_text)
        
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
        sizer.Add(self.eye_debug_text, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(sens_sizer, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(chroma_sizer, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.param_display, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(info_ctrl, 1, wx.ALL | wx.EXPAND, 10)
        
        panel.SetSizer(sizer)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
    def on_start_stop(self, event):
        if not self.timer.IsRunning():
            if self.mocap_receiver.start():
                self.timer.Start(33)
                self.start_btn.SetLabel("Stop VTuber Mode")
                self.start_btn.SetBackgroundColour(wx.Colour(200, 100, 100))
                self.status_text.SetLabel("Status: Running - Enhanced Eye Tracking")
                print("\nEnhanced eye recognition active!")
            else:
                wx.MessageBox("iFacialMocap connection failed!", "Connection Error", wx.OK | wx.ICON_ERROR)
        else:
            self.timer.Stop()
            self.mocap_receiver.stop()
            self.start_btn.SetLabel("Start VTuber Mode")
            self.start_btn.SetBackgroundColour(wx.Colour(100, 200, 100))
            self.status_text.SetLabel("Status: Stopped")
    
    def on_toggle_overlay(self, event):
        try:
            if self.overlay_frame and self.overlay_frame.IsShown():
                self.overlay_frame.Hide()
                self.overlay_btn.SetLabel("Show Overlay")
            else:
                if not self.overlay_frame:
                    self.overlay_frame = FixedOverlay(self)
                self.overlay_frame.Show()
                self.overlay_frame.Raise()
                self.overlay_btn.SetLabel("Hide Overlay")
        except (RuntimeError, AttributeError):
            self.overlay_frame = FixedOverlay(self)
            self.overlay_frame.Show()
            self.overlay_frame.Raise()
            self.overlay_btn.SetLabel("Hide Overlay")
    
    def on_timer(self, event):
        sensitivity = self.sensitivity_slider.GetValue() / 100.0
        self.image_manager.sensitivity = sensitivity
        
        mocap_data = self.mocap_receiver.get_latest_data()
        
        new_avatar = self.image_manager.get_best_avatar_image(mocap_data)
        if new_avatar:
            self.current_avatar = new_avatar
        
        current_time = time.time()
        if current_time - self.last_ui_update > 0.2:
            self.update_ui(mocap_data)
            self.last_ui_update = current_time
        
        self.frame_count += 1
        if current_time - self.last_fps_time >= 1.0:
            self.fps = self.frame_count / (current_time - self.last_fps_time)
            self.frame_count = 0
            self.last_fps_time = current_time
    
    def update_ui(self, mocap_data):
        self.fps_text.SetLabel(f"FPS: {self.fps:.1f}")
        
        if mocap_data:
            ewl_sources = ['eyeBlink_R', 'eyeBlinkRight', 'EyeBlinkRight', 'eyeblink_R']
            ewr_sources = ['eyeBlink_L', 'eyeBlinkLeft', 'EyeBlinkLeft', 'eyeblink_L']
            
            ewl_raw = 0
            for src in ewl_sources:
                if src in mocap_data:
                    ewl_raw = max(ewl_raw, mocap_data[src])
            
            ewr_raw = 0
            for src in ewr_sources:
                if src in mocap_data:
                    ewr_raw = max(ewr_raw, mocap_data[src])
            
            params = self.image_manager._convert_mocap_to_params(mocap_data)
            ewl_level = params[2]
            ewr_level = params[3]
            
            self.eye_debug_text.SetLabel(f"Eye: L={ewl_raw:.3f}(EWL{ewl_level}) R={ewr_raw:.3f}(EWR{ewr_level})")
            
            param_str = f"EBL{params[0]}_EBR{params[1]}_EWL{params[2]}_EWR{params[3]}_JO{params[4]}_HX{params[5]:02d}_HY{params[6]:02d}_NZ{params[7]:02d}"
            
            if self.image_manager.last_matched_key:
                key = self.image_manager.last_matched_key  
                matched_str = f"EBL{key[0]}_EBR{key[1]}_EWL{key[2]}_EWR{key[3]}_JO{key[4]}_HX{key[5]:02d}_HY{key[6]:02d}_NZ{key[7]:02d}"
                method = self.image_manager.last_search_method
                self.param_display.SetLabel(f"Target: {param_str}\nMatched: {matched_str}\nMethod: {method}")
            else:
                self.param_display.SetLabel(f"Target: {param_str}\nMatched: None")
    
    def on_close(self, event):
        self.timer.Stop()
        self.mocap_receiver.stop()
        
        if hasattr(self, 'overlay_frame'):
            try:
                if hasattr(self.overlay_frame, 'update_timer'):
                    self.overlay_frame.update_timer.Stop()
                if hasattr(self.overlay_frame, 'stay_top_timer'):
                    self.overlay_frame.stay_top_timer.Stop()
                self.overlay_frame.Destroy()
            except (RuntimeError, AttributeError):
                pass
        
        self.Destroy()


class VTuberApp(wx.App):
    def OnInit(self):
        self.main_frame = VTuberMainFrame()
        self.main_frame.Show()
        return True


if __name__ == "__main__":
    app = VTuberApp()
    app.MainLoop()
