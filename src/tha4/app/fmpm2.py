import logging
import os
import sys
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import threading

from tha4.shion.base.image_util import extract_pytorch_image_from_PIL_image, pytorch_rgba_to_numpy_image, \
    pytorch_rgb_to_numpy_image
from tha4.image_util import grid_change_to_numpy_image, resize_PIL_image

sys.path.append(os.getcwd())

import PIL.Image
import numpy
import torch
import wx

from tha4.poser.poser import Poser, PoseParameterCategory, PoseParameterGroup


class MorphCategoryControlPanel(wx.Panel):
    def __init__(self,
                 parent,
                 title: str,
                 pose_param_category: PoseParameterCategory,
                 param_groups: List[PoseParameterGroup]):
        super().__init__(parent, style=wx.SIMPLE_BORDER)
        self.pose_param_category = pose_param_category
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.SetAutoLayout(1)

        title_text = wx.StaticText(self, label=title, style=wx.ALIGN_CENTER)
        self.sizer.Add(title_text, 0, wx.EXPAND)

        self.param_groups = [group for group in param_groups if group.get_category() == pose_param_category]
        self.choice = wx.Choice(self, choices=[group.get_group_name() for group in self.param_groups])
        if len(self.param_groups) > 0:
            self.choice.SetSelection(0)
        self.choice.Bind(wx.EVT_CHOICE, self.on_choice_updated)
        self.sizer.Add(self.choice, 0, wx.EXPAND)

        self.left_slider = wx.Slider(self, minValue=-1000, maxValue=1000, value=-1000, style=wx.HORIZONTAL)
        self.sizer.Add(self.left_slider, 0, wx.EXPAND)

        self.right_slider = wx.Slider(self, minValue=-1000, maxValue=1000, value=-1000, style=wx.HORIZONTAL)
        self.sizer.Add(self.right_slider, 0, wx.EXPAND)

        self.checkbox = wx.CheckBox(self, label="Show")
        self.checkbox.SetValue(True)
        self.sizer.Add(self.checkbox, 0, wx.SHAPED | wx.ALIGN_CENTER)

        self.update_ui()
        self.sizer.Fit(self)

    def update_ui(self):
        param_group = self.param_groups[self.choice.GetSelection()]
        if param_group.is_discrete():
            self.left_slider.Enable(False)
            self.right_slider.Enable(False)
            self.checkbox.Enable(True)
        elif param_group.get_arity() == 1:
            self.left_slider.Enable(True)
            self.right_slider.Enable(False)
            self.checkbox.Enable(False)
        else:
            self.left_slider.Enable(True)
            self.right_slider.Enable(True)
            self.checkbox.Enable(False)

    def on_choice_updated(self, event: wx.Event):
        param_group = self.param_groups[self.choice.GetSelection()]
        if param_group.is_discrete():
            self.checkbox.SetValue(True)
        self.update_ui()

    def set_param_value(self, pose: List[float]):
        if len(self.param_groups) == 0:
            return
        selected_morph_index = self.choice.GetSelection()
        param_group = self.param_groups[selected_morph_index]
        param_index = param_group.get_parameter_index()
        if param_group.is_discrete():
            if self.checkbox.GetValue():
                for i in range(param_group.get_arity()):
                    pose[param_index + i] = 1.0
        else:
            param_range = param_group.get_range()
            alpha = (self.left_slider.GetValue() + 1000) / 2000.0
            pose[param_index] = param_range[0] + (param_range[1] - param_range[0]) * alpha
            if param_group.get_arity() == 2:
                alpha = (self.right_slider.GetValue() + 1000) / 2000.0
                pose[param_index + 1] = param_range[0] + (param_range[1] - param_range[0]) * alpha


class SimpleParamGroupsControlPanel(wx.Panel):
    def __init__(self, parent,
                 pose_param_category: PoseParameterCategory,
                 param_groups: List[PoseParameterGroup]):
        super().__init__(parent, style=wx.SIMPLE_BORDER)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.SetAutoLayout(1)

        self.param_groups = [group for group in param_groups if group.get_category() == pose_param_category]
        for param_group in self.param_groups:
            assert not param_group.is_discrete()
            assert param_group.get_arity() == 1

        self.sliders = []
        for param_group in self.param_groups:
            static_text = wx.StaticText(
                self,
                label="   ------------ %s ------------   " % param_group.get_group_name(), style=wx.ALIGN_CENTER)
            self.sizer.Add(static_text, 0, wx.EXPAND)
            range = param_group.get_range()
            min_value = int(range[0] * 1000)
            max_value = int(range[1] * 1000)
            slider = wx.Slider(self, minValue=min_value, maxValue=max_value, value=0, style=wx.HORIZONTAL)
            self.sizer.Add(slider, 0, wx.EXPAND)
            self.sliders.append(slider)

        self.sizer.Fit(self)

    def set_param_value(self, pose: List[float]):
        if len(self.param_groups) == 0:
            return
        for param_group_index in range(len(self.param_groups)):
            param_group = self.param_groups[param_group_index]
            slider = self.sliders[param_group_index]
            param_range = param_group.get_range()
            param_index = param_group.get_parameter_index()
            alpha = (slider.GetValue() - slider.GetMin()) * 1.0 / (slider.GetMax() - slider.GetMin())
            pose[param_index] = param_range[0] + (param_range[1] - param_range[0]) * alpha


def convert_output_image_from_torch_to_numpy(output_image):
    if output_image.shape[2] == 2:
        h, w, c = output_image.shape
        numpy_image = torch.transpose(output_image.reshape(h * w, c), 0, 1).reshape(c, h, w)
    elif output_image.shape[0] == 4:
        numpy_image = pytorch_rgba_to_numpy_image(output_image)
    elif output_image.shape[0] == 3:
        numpy_image = pytorch_rgb_to_numpy_image(output_image)
    elif output_image.shape[0] == 1:
        c, h, w = output_image.shape
        alpha_image = torch.cat([output_image.repeat(3, 1, 1) * 2.0 - 1.0, torch.ones(1, h, w)], dim=0)
        numpy_image = pytorch_rgba_to_numpy_image(alpha_image)
    elif output_image.shape[0] == 2:
        numpy_image = grid_change_to_numpy_image(output_image, num_channels=4)
    else:
        raise RuntimeError("Unsupported # image channels: %d" % output_image.shape[0])
    numpy_image = numpy.uint8(numpy.rint(numpy_image * 255.0))
    return numpy_image


class MainFrame(wx.Frame):
    def __init__(self, poser: Poser, device: torch.device):
        super().__init__(None, wx.ID_ANY, "Poser")
        self.poser = poser
        self.dtype = self.poser.get_dtype()
        self.device = device
        self.image_size = self.poser.get_image_size()
        self.batch_size = 64

        self.wx_source_image = None
        self.torch_source_image = None

        self.main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.main_sizer)
        self.SetAutoLayout(1)
        self.init_left_panel()
        self.init_control_panel()
        self.init_right_panel()
        self.main_sizer.Fit(self)

        self.timer = wx.Timer(self, wx.ID_ANY)
        self.Bind(wx.EVT_TIMER, self.update_images, self.timer)

        save_image_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self.on_save_image, id=save_image_id)
        accelerator_table = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('S'), save_image_id)
        ])
        self.SetAcceleratorTable(accelerator_table)

        self.last_pose = None
        self.last_output_index = self.output_index_choice.GetSelection()
        self.last_output_numpy_image = None

        self.wx_source_image = None
        self.torch_source_image = None
        self.source_image_bitmap = wx.Bitmap(self.image_size, self.image_size)
        self.result_image_bitmap = wx.Bitmap(self.image_size, self.image_size)
        self.source_image_dirty = True

    def init_left_panel(self):
        self.control_panel = wx.Panel(self, style=wx.SIMPLE_BORDER, size=(self.image_size, -1))
        self.left_panel = wx.Panel(self, style=wx.SIMPLE_BORDER)
        left_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.left_panel.SetSizer(left_panel_sizer)
        self.left_panel.SetAutoLayout(1)

        self.source_image_panel = wx.Panel(self.left_panel, size=(self.image_size, self.image_size),
                                           style=wx.SIMPLE_BORDER)
        self.source_image_panel.Bind(wx.EVT_PAINT, self.paint_source_image_panel)
        self.source_image_panel.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
        left_panel_sizer.Add(self.source_image_panel, 0, wx.FIXED_MINSIZE)

        self.load_image_button = wx.Button(self.left_panel, wx.ID_ANY, "\nLoad Image\n\n")
        left_panel_sizer.Add(self.load_image_button, 1, wx.EXPAND)
        self.load_image_button.Bind(wx.EVT_BUTTON, self.load_image)

        left_panel_sizer.Fit(self.left_panel)
        self.main_sizer.Add(self.left_panel, 0, wx.FIXED_MINSIZE)

    def on_erase_background(self, event: wx.Event):
        pass

    def init_control_panel(self):
        self.control_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.control_panel.SetSizer(self.control_panel_sizer)
        self.control_panel.SetMinSize(wx.Size(256, 1))

        morph_categories = [
            PoseParameterCategory.EYEBROW,
            PoseParameterCategory.EYE,
            PoseParameterCategory.MOUTH,
            PoseParameterCategory.IRIS_MORPH
        ]
        morph_category_titles = {
            PoseParameterCategory.EYEBROW: "   ------------ Eyebrow ------------   ",
            PoseParameterCategory.EYE: "   ------------ Eye ------------   ",
            PoseParameterCategory.MOUTH: "   ------------ Mouth ------------   ",
            PoseParameterCategory.IRIS_MORPH: "   ------------ Iris morphs ------------   ",
        }
        self.morph_control_panels = {}
        for category in morph_categories:
            param_groups = self.poser.get_pose_parameter_groups()
            filtered_param_groups = [group for group in param_groups if group.get_category() == category]
            if len(filtered_param_groups) == 0:
                continue
            control_panel = MorphCategoryControlPanel(
                self.control_panel,
                morph_category_titles[category],
                category,
                self.poser.get_pose_parameter_groups())
            self.morph_control_panels[category] = control_panel
            self.control_panel_sizer.Add(control_panel, 0, wx.EXPAND)

        self.non_morph_control_panels = {}
        non_morph_categories = [
            PoseParameterCategory.IRIS_ROTATION,
            PoseParameterCategory.FACE_ROTATION,
            PoseParameterCategory.BODY_ROTATION,
            PoseParameterCategory.BREATHING
        ]
        for category in non_morph_categories:
            param_groups = self.poser.get_pose_parameter_groups()
            filtered_param_groups = [group for group in param_groups if group.get_category() == category]
            if len(filtered_param_groups) == 0:
                continue
            control_panel = SimpleParamGroupsControlPanel(
                self.control_panel,
                category,
                self.poser.get_pose_parameter_groups())
            self.non_morph_control_panels[category] = control_panel
            self.control_panel_sizer.Add(control_panel, 0, wx.EXPAND)

        # 패치 생성 버튼들 추가
        patch_buttons_panel = wx.Panel(self.control_panel)
        patch_buttons_sizer = wx.BoxSizer(wx.VERTICAL)
        patch_buttons_panel.SetSizer(patch_buttons_sizer)

        # 최적화된 버전 버튼만 유지
        self.generate_optimized_button = wx.Button(patch_buttons_panel, wx.ID_ANY, "Generate Optimized/Custom Batches")
        self.generate_optimized_button.Bind(wx.EVT_BUTTON, self.generate_combined_parameter_patches_optimized)
        patch_buttons_sizer.Add(self.generate_optimized_button, 0, wx.EXPAND)

        # GPU 배치 크기 설정 버튼
        self.batch_size_button = wx.Button(patch_buttons_panel, wx.ID_ANY, "Set Batch Size (Current: 64)")
        self.batch_size_button.Bind(wx.EVT_BUTTON, self.set_batch_size)
        patch_buttons_sizer.Add(self.batch_size_button, 0, wx.EXPAND)

        patch_buttons_sizer.Fit(patch_buttons_panel)
        self.control_panel_sizer.Add(patch_buttons_panel, 0, wx.EXPAND)

        self.control_panel_sizer.Fit(self.control_panel)
        self.main_sizer.Add(self.control_panel, 1, wx.FIXED_MINSIZE)

    def init_right_panel(self):
        self.right_panel = wx.Panel(self, style=wx.SIMPLE_BORDER)
        right_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.right_panel.SetSizer(right_panel_sizer)
        self.right_panel.SetAutoLayout(1)

        self.result_image_panel = wx.Panel(self.right_panel,
                                           size=(self.image_size, self.image_size),
                                           style=wx.SIMPLE_BORDER)
        self.result_image_panel.Bind(wx.EVT_PAINT, self.paint_result_image_panel)
        self.result_image_panel.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)
        self.output_index_choice = wx.Choice(
            self.right_panel,
            choices=[str(i) for i in range(self.poser.get_output_length())])
        self.output_index_choice.SetSelection(0)
        right_panel_sizer.Add(self.result_image_panel, 0, wx.FIXED_MINSIZE)
        right_panel_sizer.Add(self.output_index_choice, 0, wx.EXPAND)

        self.save_image_button = wx.Button(self.right_panel, wx.ID_ANY, "\nSave Image\n\n")
        right_panel_sizer.Add(self.save_image_button, 1, wx.EXPAND)
        self.save_image_button.Bind(wx.EVT_BUTTON, self.on_save_image)

        right_panel_sizer.Fit(self.right_panel)
        self.main_sizer.Add(self.right_panel, 0, wx.FIXED_MINSIZE)

    def set_batch_size(self, event: wx.Event):
        """GPU 메모리에 맞는 배치 크기 설정"""
        dialog = wx.NumberEntryDialog(
            self, 
            "Set batch size (1-64).\nLarger values = faster but more GPU memory:", 
            "Batch Size", 
            "GPU Batch Size", 
            self.batch_size, 1, 64
        )
        
        if dialog.ShowModal() == wx.ID_OK:
            self.batch_size = dialog.GetValue()
            self.batch_size_button.SetLabel(f"Set Batch Size (Current: {self.batch_size})")
            wx.MessageBox(f"Batch size set to {self.batch_size}", "Settings Updated", wx.OK | wx.ICON_INFORMATION)
        
        dialog.Destroy()

    def close_progress_dialog_safely(self, dialog):
        """Progress Dialog를 안전하게 닫기"""
        if dialog is not None:
            try:
                dialog.Update(dialog.GetRange(), "Completed!")
                wx.CallAfter(dialog.Destroy)
            except:
                try:
                    dialog.Destroy()
                except:
                    pass

    def save_patch(self, patch_image, filename, patch_type):
        """패치를 파일로 저장 (세로 절반으로 크롭 - 위쪽부터) - 빠른 저장"""
        patch_dir = f"data/{patch_type}_patches"
        os.makedirs(patch_dir, exist_ok=True)
        
        # 이미지의 위쪽 절반만 사용 (세로 0.5, 가로 1.0)
        height = patch_image.shape[0]
        cropped_image = patch_image[:height//2, :, :]  # 위에서부터 절반
        
        if len(cropped_image.shape) == 3 and cropped_image.shape[2] == 4:  # RGBA
            pil_image = PIL.Image.fromarray(cropped_image, mode='RGBA')
        else:  # RGB
            pil_image = PIL.Image.fromarray(cropped_image[:,:,:3], mode='RGB')
        
        filepath = os.path.join(patch_dir, filename)
        # PNG 압축 레벨을 낮춰서 저장 속도 향상 (compress_level: 0=무압축, 1=빠름, 9=느림)
        pil_image.save(filepath, compress_level=1, optimize=False)
        
    def save_patch_async(self, patch_image, filename, patch_type):
        """비동기로 패치 저장 (백그라운드 스레드에서 실행)"""
        try:
            self.save_patch(patch_image, filename, patch_type)
        except Exception as e:
            print(f"Error saving {filename}: {str(e)}")

    def get_current_pose(self):
        current_pose = [0.0 for i in range(self.poser.get_num_parameters())]
        for morph_control_panel in self.morph_control_panels.values():
            morph_control_panel.set_param_value(current_pose)
        for rotation_control_panel in self.non_morph_control_panels.values():
            rotation_control_panel.set_param_value(current_pose)
        return current_pose

    def find_required_parameters(self):
        """필요한 파라미터들을 찾아서 반환"""
        params = {}
        param_names = ['left_eyebrow', 'right_eyebrow', 'left_eye_wink', 'right_eye_wink', 
                       'mouth_aaa', 'head_x', 'head_y', 'neck_z']
        
        for param_group in self.poser.get_pose_parameter_groups():
            param_name = param_group.get_group_name().lower()
            
            # 파라미터 매칭 로직
            if param_group.get_category() == PoseParameterCategory.EYEBROW:
                if 'left' in param_name or param_group.get_arity() == 2:
                    if 'left_eyebrow' not in params:
                        params['left_eyebrow'] = param_group
                if 'right' in param_name or param_group.get_arity() == 2:
                    if 'right_eyebrow' not in params:
                        params['right_eyebrow'] = param_group
            
            elif param_group.get_category() == PoseParameterCategory.EYE:
                if ('wink' in param_name or 'blink' in param_name):
                    if 'left' in param_name or param_group.get_arity() == 2:
                        if 'left_eye_wink' not in params:
                            params['left_eye_wink'] = param_group
                    if 'right' in param_name or param_group.get_arity() == 2:
                        if 'right_eye_wink' not in params:
                            params['right_eye_wink'] = param_group
            
            elif param_group.get_category() == PoseParameterCategory.MOUTH:
                if 'aaa' in param_name or 'open' in param_name:
                    if 'mouth_aaa' not in params:
                        params['mouth_aaa'] = param_group
            
            elif any(keyword in param_name for keyword in ['head', 'face']):
                if 'x' in param_name and 'head_x' not in params:
                    params['head_x'] = param_group
                elif 'y' in param_name and 'head_y' not in params:
                    params['head_y'] = param_group
            
            elif 'neck' in param_name and 'z' in param_name:
                if 'neck_z' not in params:
                    params['neck_z'] = param_group
        
        # 누락된 파라미터 확인
        missing = [name for name in param_names if name not in params]
        if missing:
            wx.MessageBox(f"Missing parameters: {', '.join(missing)}", "Error", wx.OK | wx.ICON_ERROR)
            return None
        
        return params

    def create_pose_from_alphas(self, base_pose, params, alphas):
        """알파 값들로부터 포즈 생성"""
        current_pose = base_pose.copy()
        
        param_names = ['left_eyebrow', 'right_eyebrow', 'left_eye_wink', 'right_eye_wink', 
                       'mouth_aaa', 'head_x', 'head_y', 'neck_z']
        
        for i, (param_name, alpha) in enumerate(zip(param_names, alphas)):
            param = params[param_name]
            param_idx = param.get_parameter_index()
            
            if param.is_discrete():
                if alpha > 0.5:
                    for k in range(param.get_arity()):
                        current_pose[param_idx + k] = 1.0
            else:
                param_range = param.get_range()
                value = param_range[0] + (param_range[1] - param_range[0]) * alpha
                
                # 파라미터별 특별 처리
                if param_name in ['left_eyebrow', 'left_eye_wink'] and param.get_arity() == 2:
                    current_pose[param_idx + 1] = value  # 좌측
                elif param_name in ['mouth_aaa'] and param.get_arity() == 2:
                    current_pose[param_idx] = value      # 양쪽
                    current_pose[param_idx + 1] = value
                else:
                    current_pose[param_idx] = value
        
        return current_pose

    def generate_combined_parameter_patches_optimized(self, event: wx.Event):
        """최적화된 조합 파라미터 생성 - 배치 처리 및 속도 개선"""
        if self.torch_source_image is None:
            wx.MessageBox("Please load an image first!", "No Image", wx.OK | wx.ICON_WARNING)
            return

        # 사용자에게 옵션 선택하도록 하기
        options_dialog = wx.SingleChoiceDialog(
            self,
            "Choose generation mode:",
            "Generation Options",
            [
                "Quick Test (64 combinations: 4×4×4×1×1×1×1×1)",
                "Medium (1,024 combinations: 4×4×4×4×4×1×1×1)", 
                "Large (4,096 combinations: 4×4×4×4×4×4×4×1)",
                "Custom Eye-Face Config (13,310 combinations: 1×1×5×5×4×11×11×11)",
                "Full (65,536 combinations: 4×4×4×4×4×4×4×4)",
                "Custom batch size..."
            ]
        )
        
        if options_dialog.ShowModal() != wx.ID_OK:
            options_dialog.Destroy()
            return
        
        selection = options_dialog.GetSelection()
        options_dialog.Destroy()
        
        # 선택에 따른 단계 수 설정
        if selection == 0:  # Quick Test
            steps_config = [4, 4, 4, 1, 1, 1, 1, 1]
            total_combinations = 4 * 4 * 4 * 1 * 1 * 1 * 1 * 1  # 64
        elif selection == 1:  # Medium
            steps_config = [4, 4, 4, 4, 4, 1, 1, 1]
            total_combinations = 4 * 4 * 4 * 4 * 4 * 1 * 1 * 1  # 1,024
        elif selection == 2:  # Large
            steps_config = [4, 4, 4, 4, 4, 4, 4, 1]
            total_combinations = 4 * 4 * 4 * 4 * 4 * 4 * 4 * 1  # 4,096
        elif selection == 3:  # Custom Eye-Face Config
            steps_config = [1, 1, 5, 5, 4, 11, 11, 11]
            total_combinations = 1 * 1 * 5 * 5 * 4 * 11 * 11 * 11  # 13,310
        elif selection == 4:  # Full
            steps_config = [4, 4, 4, 4, 4, 4, 4, 4]
            total_combinations = 4 * 4 * 4 * 4 * 4 * 4 * 4 * 4  # 65,536
        else:  # Custom
            batch_dialog = wx.NumberEntryDialog(
                self, "Enter batch size (1-10000):", "Batch Size", "Custom Batch", 1000, 1, 10000
            )
            if batch_dialog.ShowModal() != wx.ID_OK:
                batch_dialog.Destroy()
                return
            custom_batch = batch_dialog.GetValue()
            batch_dialog.Destroy()
            
            # 커스텀 배치의 경우 랜덤 샘플링
            return self.generate_random_samples(custom_batch)

        # 파라미터 검색
        params = self.find_required_parameters()
        if not params:
            return

        # 진행 다이얼로그
        dialog = wx.ProgressDialog(
            "Generating Optimized Combined Parameters",
            f"Generating {total_combinations:,} combinations with batch processing...",
            total_combinations,
            self,
            wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE
        )

        try:
            image_count = 0
            base_pose = self.get_current_pose()
            
            # 모든 조합의 포즈를 미리 계산
            all_poses = []
            all_filenames = []
            
            # 단계별 값 계산
            step_values = []
            for i, steps in enumerate(steps_config):
                if steps == 1:
                    step_values.append([0.5])  # 중간값만 사용 (눈썹 고정용)
                else:
                    step_values.append(numpy.linspace(0, 1, steps))
            
            print(f"Generating {total_combinations:,} pose combinations...")
            print(f"Configuration: {' × '.join(map(str, steps_config))}")
            if selection == 3:
                print("Parameters: Left Eyebrow (fixed), Right Eyebrow (fixed), Left Eye (5), Right Eye (5), Mouth (4), Head X (11), Head Y (11), Neck Z (11)")
            
            # 모든 조합 생성 (메모리 효율적)
            for i1, leb_alpha in enumerate(step_values[0]):  # Left eyebrow
                for i2, reb_alpha in enumerate(step_values[1]):  # Right eyebrow
                    for i3, lew_alpha in enumerate(step_values[2]):  # Left eye wink
                        for i4, rew_alpha in enumerate(step_values[3]):  # Right eye wink
                            for i5, maa_alpha in enumerate(step_values[4]):  # Mouth AAA
                                for i6, hx_alpha in enumerate(step_values[5]):  # Head X
                                    for i7, hy_alpha in enumerate(step_values[6]):  # Head Y
                                        for i8, nz_alpha in enumerate(step_values[7]):  # Neck Z
                                            
                                            current_pose = self.create_pose_from_alphas(
                                                base_pose, params,
                                                [leb_alpha, reb_alpha, lew_alpha, rew_alpha, 
                                                 maa_alpha, hx_alpha, hy_alpha, nz_alpha]
                                            )
                                            
                                            if selection == 3:  # Custom Eye-Face Config
                                                filename = (f"eye_face_LEB{i1:01d}_REB{i2:01d}_LEW{i3:01d}_REW{i4:01d}_"
                                                          f"MAA{i5:01d}_HX{i6:02d}_HY{i7:02d}_NZ{i8:02d}.png")
                                            else:
                                                filename = (f"opt_LEB{i1:01d}_REB{i2:01d}_LEW{i3:01d}_REW{i4:01d}_"
                                                          f"MAA{i5:01d}_HX{i6:01d}_HY{i7:01d}_NZ{i8:01d}.png")
                                            
                                            all_poses.append(current_pose)
                                            all_filenames.append(filename)
                                            
                                            # 중간 진행 체크
                                            if len(all_poses) % 1000 == 0:
                                                if not dialog.Update(len(all_poses), 
                                                                   f"Prepared {len(all_poses):,} poses...")[0]:
                                                    return

            print(f"Starting batch image generation with batch size {self.batch_size}...")
            
            # ThreadPoolExecutor로 저장 작업 병렬화 (최대 4개 스레드)
            max_save_threads = 4
            executor = ThreadPoolExecutor(max_workers=max_save_threads)
            save_futures = []
            
            # 배치 처리로 이미지 생성
            for batch_start in range(0, len(all_poses), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(all_poses))
                batch_poses = all_poses[batch_start:batch_end]
                batch_filenames = all_filenames[batch_start:batch_end]
                
                # 배치를 텐서로 변환
                pose_batch = torch.stack([torch.tensor(pose, device=self.device, dtype=self.dtype) 
                                        for pose in batch_poses])
                
                # 배치 이미지 생성
                with torch.no_grad():
                    # 소스 이미지를 배치 크기만큼 복제
                    source_batch = self.torch_source_image.unsqueeze(0).repeat(len(batch_poses), 1, 1, 1)
                    
                    # 배치 처리 (poser가 배치를 지원하지 않는 경우 개별 처리)
                    output_batch = []
                    for i, pose in enumerate(pose_batch):
                        output = self.poser.pose(source_batch[i:i+1], pose, 0)[0]
                        output_batch.append(output)
                    output_batch = torch.stack(output_batch)
                
                # 배치 결과를 비동기로 저장
                folder_name = "eye_face_optimized" if selection == 3 else "combined_parameters_optimized"
                for i, (output_image, filename) in enumerate(zip(output_batch, batch_filenames)):
                    numpy_image = convert_output_image_from_torch_to_numpy(output_image.detach().cpu())
                    
                    # 백그라운드 스레드에서 저장 (GPU 연산과 병렬화)
                    future = executor.submit(self.save_patch_async, numpy_image.copy(), filename, folder_name)
                    save_futures.append(future)
                    
                    image_count += 1
                    
                    # 진행 상황 업데이트 (배치마다)
                    if image_count % (self.batch_size * 5) == 0:
                        progress_text = f"Generated {image_count:,}/{total_combinations:,} images"
                        if not dialog.Update(image_count, progress_text)[0]:
                            executor.shutdown(wait=True)  # 취소 시 모든 저장 완료 대기
                            wx.MessageBox("Generation cancelled by user.", "Cancelled", wx.OK | wx.ICON_INFORMATION)
                            return
                        wx.GetApp().Yield()
            
            # 모든 저장 작업 완료 대기
            print(f"Waiting for all {len(save_futures)} save operations to complete...")
            executor.shutdown(wait=True)

            # 완료 메시지
            self.close_progress_dialog_safely(dialog)
            if selection == 3:
                success_msg = (f"Eye-Face optimized generation completed!\n"
                             f"Total images: {image_count:,}\n"
                             f"Configuration: Eyebrows Fixed, Eyes 5×5, Mouth 4, Face 11×11×11\n"
                             f"Check data/eye_face_optimized_patches/ folder.")
            else:
                success_msg = (f"Optimized generation completed!\n"
                             f"Total images: {image_count:,}\n"
                             f"Configuration: {' × '.join(map(str, steps_config))}\n"
                             f"Check data/{folder_name}_patches/ folder.")
            
            wx.CallAfter(lambda: wx.MessageBox(success_msg, "Success", wx.OK | wx.ICON_INFORMATION))

        except Exception as e:
            print(f"Error in optimized generation: {str(e)}")
            import traceback
            traceback.print_exc()
            
            error_msg = str(e)
            wx.CallAfter(lambda msg=error_msg: wx.MessageBox(f"Error: {msg}", "Error", wx.OK | wx.ICON_ERROR))
        
        finally:
            self.close_progress_dialog_safely(dialog)

    def generate_random_samples(self, sample_count):
        """랜덤 샘플링으로 지정된 수만큼만 생성 - 빠른 저장"""
        params = self.find_required_parameters()
        if not params:
            return
        
        dialog = wx.ProgressDialog(
            "Generating Random Samples",
            f"Generating {sample_count:,} random combinations...",
            sample_count,
            self,
            wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE
        )
        
        try:
            base_pose = self.get_current_pose()
            
            # ThreadPoolExecutor로 저장 작업 병렬화
            executor = ThreadPoolExecutor(max_workers=4)
            save_futures = []
            
            for i in range(sample_count):
                # 랜덤 알파 값 생성
                random_alphas = [numpy.random.random() for _ in range(8)]
                
                current_pose = self.create_pose_from_alphas(base_pose, params, random_alphas)
                
                # 이미지 생성
                pose_tensor = torch.tensor(current_pose, device=self.device, dtype=self.dtype)
                with torch.no_grad():
                    output_image = self.poser.pose(self.torch_source_image, pose_tensor, 0)[0].detach().cpu()
                numpy_image = convert_output_image_from_torch_to_numpy(output_image)
                
                # 파일명 생성
                filename = f"random_sample_{i:06d}_{'_'.join([f'{a:.3f}' for a in random_alphas])}.png"
                
                # 비동기 저장
                future = executor.submit(self.save_patch_async, numpy_image.copy(), filename, "random_samples")
                save_futures.append(future)
                
                # 진행 상황 업데이트
                if i % 50 == 0:
                    if not dialog.Update(i, f"Generated {i}/{sample_count} samples")[0]:
                        executor.shutdown(wait=True)
                        return
                    wx.GetApp().Yield()
            
            # 모든 저장 작업 완료 대기
            print(f"Waiting for all {len(save_futures)} save operations to complete...")
            executor.shutdown(wait=True)
            
            self.close_progress_dialog_safely(dialog)
            wx.CallAfter(lambda: wx.MessageBox(
                f"Random sampling completed!\nGenerated {sample_count} samples.",
                "Success", wx.OK | wx.ICON_INFORMATION
            ))
            
        except Exception as e:
            print(f"Error in random sampling: {str(e)}")
            wx.CallAfter(lambda: wx.MessageBox(f"Error: {str(e)}", "Error", wx.OK | wx.ICON_ERROR))
        finally:
            self.close_progress_dialog_safely(dialog)

    def load_image(self, event: wx.Event):
        dir_name = "data/images"
        file_dialog = wx.FileDialog(self, "Choose an image", dir_name, "", "*.png", wx.FD_OPEN)
        if file_dialog.ShowModal() == wx.ID_OK:
            image_file_name = os.path.join(file_dialog.GetDirectory(), file_dialog.GetFilename())
            try:
                pil_image = resize_PIL_image(PIL.Image.open(image_file_name),
                                             (self.poser.get_image_size(), self.poser.get_image_size()))
                w, h = pil_image.size
                if pil_image.mode != 'RGBA':
                    self.source_image_string = "Image must have alpha channel!"
                    self.wx_source_image = None
                    self.torch_source_image = None
                else:
                    self.wx_source_image = wx.Bitmap.FromBufferRGBA(w, h, pil_image.convert("RGBA").tobytes())
                    self.torch_source_image = extract_pytorch_image_from_PIL_image(pil_image) \
                        .to(self.device).to(self.dtype)
                self.source_image_dirty = True
                self.Refresh()
                self.Update()
            except:
                message_dialog = wx.MessageDialog(self, "Could not load image " + image_file_name, "Poser", wx.OK)
                message_dialog.ShowModal()
                message_dialog.Destroy()
        file_dialog.Destroy()

    def paint_source_image_panel(self, event: wx.Event):
        wx.BufferedPaintDC(self.source_image_panel, self.source_image_bitmap)

    def paint_result_image_panel(self, event: wx.Event):
        wx.BufferedPaintDC(self.result_image_panel, self.result_image_bitmap)
        
    def draw_nothing_yet_string_to_bitmap(self, bitmap):
        dc = wx.MemoryDC()
        dc.SelectObject(bitmap)

        dc.Clear()
        font = wx.Font(wx.FontInfo(14).Family(wx.FONTFAMILY_SWISS))
        dc.SetFont(font)
        w, h = dc.GetTextExtent("Nothing yet!")
        dc.DrawText("Nothing yet!", (self.image_size - w) // 2, (self.image_size - h) // 2)

        del dc

    def update_images(self, event: wx.Event):
        current_pose = self.get_current_pose()
        if not self.source_image_dirty \
                and self.last_pose is not None \
                and self.last_pose == current_pose \
                and self.last_output_index == self.output_index_choice.GetSelection():
            return
        self.last_pose = current_pose
        self.last_output_index = self.output_index_choice.GetSelection()

        if self.torch_source_image is None:
            self.draw_nothing_yet_string_to_bitmap(self.source_image_bitmap)
            self.draw_nothing_yet_string_to_bitmap(self.result_image_bitmap)
            self.source_image_dirty = False
            self.Refresh()
            self.Update()
            return

        if self.source_image_dirty:
            dc = wx.MemoryDC()
            dc.SelectObject(self.source_image_bitmap)
            dc.Clear()
            dc.DrawBitmap(self.wx_source_image, 0, 0)
            self.source_image_dirty = False

        pose = torch.tensor(current_pose, device=self.device, dtype=self.dtype)
        output_index = self.output_index_choice.GetSelection()
        with torch.no_grad():
            start_cuda_event = torch.cuda.Event(enable_timing=True)
            end_cuda_event = torch.cuda.Event(enable_timing=True)
            start_cuda_event.record()
            start_time = time.time()

            output_image = self.poser.pose(self.torch_source_image, pose, output_index)[0].detach().cpu()

            end_time = time.time()
            end_cuda_event.record()
            torch.cuda.synchronize()
            print("cuda time (ms):", start_cuda_event.elapsed_time(end_cuda_event))
            print("elapsed time (ms):", (end_time - start_time) * 1000.0)

        numpy_image = convert_output_image_from_torch_to_numpy(output_image)
        self.last_output_numpy_image = numpy_image
        
        wx_image = wx.ImageFromBuffer(
            numpy_image.shape[0],
            numpy_image.shape[1],
            numpy_image[:, :, 0:3].tobytes(),
            numpy_image[:, :, 3].tobytes())
        wx_bitmap = wx_image.ConvertToBitmap()

        dc = wx.MemoryDC()
        dc.SelectObject(self.result_image_bitmap)
        dc.Clear()
        dc.DrawBitmap(wx_bitmap,
                      (self.image_size - numpy_image.shape[0]) // 2,
                      (self.image_size - numpy_image.shape[1]) // 2,
                      True)
        del dc

        self.Refresh()
        self.Update()

    def on_save_image(self, event: wx.Event):
        if self.last_output_numpy_image is None:
            logging.info("There is no output image to save!!!")
            return

        dir_name = "data/images"
        file_dialog = wx.FileDialog(self, "Choose an image", dir_name, "", "*.png", wx.FD_SAVE)
        if file_dialog.ShowModal() == wx.ID_OK:
            image_file_name = os.path.join(file_dialog.GetDirectory(), file_dialog.GetFilename())
            try:
                if os.path.exists(image_file_name):
                    message_dialog = wx.MessageDialog(self, f"Override {image_file_name}", "Manual Poser",
                                                      wx.YES_NO | wx.ICON_QUESTION)
                    result = message_dialog.ShowModal()
                    if result == wx.ID_YES:
                        self.save_last_numpy_image(image_file_name)
                    message_dialog.Destroy()
                else:
                    self.save_last_numpy_image(image_file_name)
            except:
                message_dialog = wx.MessageDialog(self, f"Could not save {image_file_name}", "Manual Poser", wx.OK)
                message_dialog.ShowModal()
                message_dialog.Destroy()
        file_dialog.Destroy()

    def save_last_numpy_image(self, image_file_name):
        numpy_image = self.last_output_numpy_image
        pil_image = PIL.Image.fromarray(numpy_image, mode='RGBA')
        os.makedirs(os.path.dirname(image_file_name), exist_ok=True)
        pil_image.save(image_file_name)


if __name__ == "__main__":
    device = torch.device('cuda:0')
    try:
        import tha4.poser.modes.mode_07

        poser = tha4.poser.modes.mode_07.create_poser(device)
    except RuntimeError as e:
        print(e)
        sys.exit()

    app = wx.App()
    main_frame = MainFrame(poser, device)
    main_frame.Show(True)
    main_frame.timer.Start(16)
    app.MainLoop()
