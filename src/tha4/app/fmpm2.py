import logging
import os
import sys
import time
from typing import List

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
        self.batch_size = 32  # 기본 배치 크기

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

        # 눈 패치 생성 버튼
        self.generate_eye_button = wx.Button(patch_buttons_panel, wx.ID_ANY, "Generate Eye Patches")
        self.generate_eye_button.Bind(wx.EVT_BUTTON, self.generate_eye_patches)
        patch_buttons_sizer.Add(self.generate_eye_button, 0, wx.EXPAND)

        # 아이브로우 패치 생성 버튼
        self.generate_eyebrow_button = wx.Button(patch_buttons_panel, wx.ID_ANY, "Generate Eyebrow Patches")
        self.generate_eyebrow_button.Bind(wx.EVT_BUTTON, self.generate_eyebrow_patches)
        patch_buttons_sizer.Add(self.generate_eyebrow_button, 0, wx.EXPAND)

        # 입 패치 생성 버튼
        self.generate_mouth_button = wx.Button(patch_buttons_panel, wx.ID_ANY, "Generate Mouth Patches")
        self.generate_mouth_button.Bind(wx.EVT_BUTTON, self.generate_mouth_patches)
        patch_buttons_sizer.Add(self.generate_mouth_button, 0, wx.EXPAND)

        # 헤드/넥 조합 패치 생성 버튼
        self.generate_head_neck_button = wx.Button(patch_buttons_panel, wx.ID_ANY, "Generate Head+Neck Combinations")
        self.generate_head_neck_button.Bind(wx.EVT_BUTTON, self.generate_head_neck_combinations)
        patch_buttons_sizer.Add(self.generate_head_neck_button, 0, wx.EXPAND)

        # 기존 조합 버튼 (4x4x4x4x4x4x4x4 = 65K)
        self.generate_combined_button = wx.Button(patch_buttons_panel, wx.ID_ANY, "Generate Combined Parameters (65K)")
        self.generate_combined_button.Bind(wx.EVT_BUTTON, self.generate_combined_parameter_patches)
        patch_buttons_sizer.Add(self.generate_combined_button, 0, wx.EXPAND)

        # 최적화된 버전 버튼 추가
        self.generate_optimized_button = wx.Button(patch_buttons_panel, wx.ID_ANY, "Generate Optimized/Custom Batches")
        self.generate_optimized_button.Bind(wx.EVT_BUTTON, self.generate_combined_parameter_patches_optimized)
        patch_buttons_sizer.Add(self.generate_optimized_button, 0, wx.EXPAND)

        # GPU 배치 크기 설정 버튼
        self.batch_size_button = wx.Button(patch_buttons_panel, wx.ID_ANY, "Set Batch Size (Current: 32)")
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

    def get_param_groups_by_category(self, category):
        """카테고리별 파라미터 그룹 가져오기"""
        param_groups = []
        for param_group in self.poser.get_pose_parameter_groups():
            if param_group.get_category() == category:
                param_groups.append(param_group)
        return param_groups

    def get_head_neck_parameters(self):
        """헤드 X, 헤드 Y, 넥 Z 파라미터 찾기"""
        head_x_param = None
        head_y_param = None
        neck_z_param = None
        
        for param_group in self.poser.get_pose_parameter_groups():
            param_name = param_group.get_group_name().lower()
            
            # 헤드 X 파라미터 찾기
            if any(keyword in param_name for keyword in ['head', 'face']) and 'x' in param_name:
                head_x_param = param_group
                print(f"Found Head X parameter: {param_group.get_group_name()}")
            
            # 헤드 Y 파라미터 찾기
            elif any(keyword in param_name for keyword in ['head', 'face']) and 'y' in param_name:
                head_y_param = param_group
                print(f"Found Head Y parameter: {param_group.get_group_name()}")
            
            # 넥 Z 파라미터 찾기
            elif 'neck' in param_name and 'z' in param_name:
                neck_z_param = param_group
                print(f"Found Neck Z parameter: {param_group.get_group_name()}")
        
        return head_x_param, head_y_param, neck_z_param

    def save_patch(self, patch_image, filename, patch_type):
        """패치를 파일로 저장"""
        patch_dir = f"data/{patch_type}_patches"
        os.makedirs(patch_dir, exist_ok=True)
        
        if len(patch_image.shape) == 3 and patch_image.shape[2] == 4:  # RGBA
            pil_image = PIL.Image.fromarray(patch_image, mode='RGBA')
        else:  # RGB
            pil_image = PIL.Image.fromarray(patch_image[:,:,:3], mode='RGB')
        
        filepath = os.path.join(patch_dir, filename)
        pil_image.save(filepath)
        print(f"{patch_type} patch saved: {filepath}")

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
                "Custom Eye-Face Config (13,310 combinations: 1×1×5×5×4×11×11×11)",  # 새로 추가
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
        elif selection == 3:  # Custom Eye-Face Config (새로운 설정)
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
                
                # 배치 결과 저장
                folder_name = "eye_face_optimized" if selection == 3 else "combined_parameters_optimized"
                for i, (output_image, filename) in enumerate(zip(output_batch, batch_filenames)):
                    numpy_image = convert_output_image_from_torch_to_numpy(output_image.detach().cpu())
                    self.save_patch(numpy_image, filename, folder_name)
                    
                    image_count += 1
                    
                    # 진행 상황 업데이트 (배치마다)
                    if image_count % (self.batch_size * 5) == 0:
                        progress_text = f"Generated {image_count:,}/{total_combinations:,} images"
                        if not dialog.Update(image_count, progress_text)[0]:
                            wx.MessageBox("Generation cancelled by user.", "Cancelled", wx.OK | wx.ICON_INFORMATION)
                            return
                        wx.GetApp().Yield()

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
        """랜덤 샘플링으로 지정된 수만큼만 생성"""
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
                self.save_patch(numpy_image, filename, "random_samples")
                
                # 진행 상황 업데이트
                if i % 50 == 0:
                    if not dialog.Update(i, f"Generated {i}/{sample_count} samples")[0]:
                        return
                    wx.GetApp().Yield()
            
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

    def generate_combined_parameter_patches(self, event: wx.Event):
        """모든 파라미터 조합으로 전체 이미지 생성 (4×4×4×4×4×4×4×4 = 65,536개)"""
        if self.torch_source_image is None:
            wx.MessageBox("Please load an image first!", "No Image", wx.OK | wx.ICON_WARNING)
            return

        # 필요한 파라미터들 찾기
        left_eyebrow_param = None
        right_eyebrow_param = None
        left_eye_wink_param = None
        right_eye_wink_param = None
        mouth_aaa_param = None
        head_x_param = None
        head_y_param = None
        neck_z_param = None

        # 파라미터 검색
        for param_group in self.poser.get_pose_parameter_groups():
            param_name = param_group.get_group_name().lower()
            
            # 왼쪽 눈썹
            if param_group.get_category() == PoseParameterCategory.EYEBROW:
                if 'left' in param_name or param_group.get_arity() == 2:
                    if left_eyebrow_param is None:
                        left_eyebrow_param = param_group
                        print(f"Found Left Eyebrow: {param_group.get_group_name()}")
            
            # 오른쪽 눈썹 (arity가 2인 경우 같은 파라미터 사용)
            if param_group.get_category() == PoseParameterCategory.EYEBROW:
                if 'right' in param_name or param_group.get_arity() == 2:
                    if right_eyebrow_param is None:
                        right_eyebrow_param = param_group
                        print(f"Found Right Eyebrow: {param_group.get_group_name()}")
            
            # 왼쪽 눈 윙크
            if param_group.get_category() == PoseParameterCategory.EYE:
                if ('wink' in param_name or 'blink' in param_name) and ('left' in param_name or param_group.get_arity() == 2):
                    if left_eye_wink_param is None:
                        left_eye_wink_param = param_group
                        print(f"Found Left Eye Wink: {param_group.get_group_name()}")
            
            # 오른쪽 눈 윙크
            if param_group.get_category() == PoseParameterCategory.EYE:
                if ('wink' in param_name or 'blink' in param_name) and ('right' in param_name or param_group.get_arity() == 2):
                    if right_eye_wink_param is None:
                        right_eye_wink_param = param_group
                        print(f"Found Right Eye Wink: {param_group.get_group_name()}")
            
            # 입 AAA 모양
            if param_group.get_category() == PoseParameterCategory.MOUTH:
                if 'aaa' in param_name or 'open' in param_name:
                    if mouth_aaa_param is None:
                        mouth_aaa_param = param_group
                        print(f"Found Mouth AAA: {param_group.get_group_name()}")
            
            # 헤드 X
            if any(keyword in param_name for keyword in ['head', 'face']) and 'x' in param_name:
                if head_x_param is None:
                    head_x_param = param_group
                    print(f"Found Head X: {param_group.get_group_name()}")
            
            # 헤드 Y
            if any(keyword in param_name for keyword in ['head', 'face']) and 'y' in param_name:
                if head_y_param is None:
                    head_y_param = param_group
                    print(f"Found Head Y: {param_group.get_group_name()}")
            
            # 넥 Z
            if 'neck' in param_name and 'z' in param_name:
                if neck_z_param is None:
                    neck_z_param = param_group
                    print(f"Found Neck Z: {param_group.get_group_name()}")

        # 파라미터 검증
        required_params = [
            ("Left Eyebrow", left_eyebrow_param),
            ("Right Eyebrow", right_eyebrow_param),
            ("Left Eye Wink", left_eye_wink_param),
            ("Right Eye Wink", right_eye_wink_param),
            ("Mouth AAA", mouth_aaa_param),
            ("Head X", head_x_param),
            ("Head Y", head_y_param),
            ("Neck Z", neck_z_param)
        ]
        
        missing_params = [name for name, param in required_params if param is None]
        
        if missing_params:
            wx.MessageBox(
                f"Missing parameters: {', '.join(missing_params)}\n"
                f"Please check if these parameters exist in your model.",
                "Parameters Not Found",
                wx.OK | wx.ICON_ERROR
            )
            return

        # 총 조합 수: 4×4×4×4×4×4×4×4 = 65,536
        total_combinations = 4 * 4 * 4 * 4 * 4 * 4 * 4 * 4
        
        # 진행 다이얼로그
        dialog = wx.ProgressDialog(
            "Generating Combined Parameter Images",
            f"Generating {total_combinations:,} combinations...",
            total_combinations,
            self,
            wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE
        )

        image_count = 0
        base_pose = self.get_current_pose()

        try:
            # 파라미터 인덱스 가져오기
            left_eyebrow_idx = left_eyebrow_param.get_parameter_index()
            right_eyebrow_idx = right_eyebrow_param.get_parameter_index()
            left_eye_wink_idx = left_eye_wink_param.get_parameter_index()
            right_eye_wink_idx = right_eye_wink_param.get_parameter_index()
            mouth_aaa_idx = mouth_aaa_param.get_parameter_index()
            head_x_idx = head_x_param.get_parameter_index()
            head_y_idx = head_y_param.get_parameter_index()
            neck_z_idx = neck_z_param.get_parameter_index()

            # 파라미터 범위 가져오기
            left_eyebrow_range = left_eyebrow_param.get_range()
            right_eyebrow_range = right_eyebrow_param.get_range()
            left_eye_wink_range = left_eye_wink_param.get_range() if not left_eye_wink_param.is_discrete() else [0, 1]
            right_eye_wink_range = right_eye_wink_param.get_range() if not right_eye_wink_param.is_discrete() else [0, 1]
            mouth_aaa_range = mouth_aaa_param.get_range()
            head_x_range = head_x_param.get_range()
            head_y_range = head_y_param.get_range()
            neck_z_range = neck_z_param.get_range()

            # 각 파라미터의 단계별 값 계산 (4단계씩)
            left_eyebrow_steps = numpy.linspace(0, 1, 4)
            right_eyebrow_steps = numpy.linspace(0, 1, 4)
            left_eye_wink_steps = numpy.linspace(0, 1, 4)
            right_eye_wink_steps = numpy.linspace(0, 1, 4)
            mouth_aaa_steps = numpy.linspace(0, 1, 4)
            head_x_steps = numpy.linspace(0, 1, 4)
            head_y_steps = numpy.linspace(0, 1, 4)
            neck_z_steps = numpy.linspace(0, 1, 4)

            # 중첩 루프로 모든 조합 생성
            for i1, leb_alpha in enumerate(left_eyebrow_steps):
                for i2, reb_alpha in enumerate(right_eyebrow_steps):
                    for i3, lew_alpha in enumerate(left_eye_wink_steps):
                        for i4, rew_alpha in enumerate(right_eye_wink_steps):
                            for i5, maa_alpha in enumerate(mouth_aaa_steps):
                                for i6, hx_alpha in enumerate(head_x_steps):
                                    for i7, hy_alpha in enumerate(head_y_steps):
                                        for i8, nz_alpha in enumerate(neck_z_steps):
                                            
                                            # 현재 조합의 파라미터 값 계산
                                            current_pose = base_pose.copy()
                                            
                                            # 왼쪽 눈썹
                                            if left_eyebrow_param.get_arity() == 2:
                                                current_pose[left_eyebrow_idx + 1] = left_eyebrow_range[0] + (left_eyebrow_range[1] - left_eyebrow_range[0]) * leb_alpha
                                            else:
                                                current_pose[left_eyebrow_idx] = left_eyebrow_range[0] + (left_eyebrow_range[1] - left_eyebrow_range[0]) * leb_alpha
                                            
                                            # 오른쪽 눈썹
                                            if right_eyebrow_param.get_arity() == 2:
                                                current_pose[right_eyebrow_idx] = right_eyebrow_range[0] + (right_eyebrow_range[1] - right_eyebrow_range[0]) * reb_alpha
                                            else:
                                                current_pose[right_eyebrow_idx] = right_eyebrow_range[0] + (right_eyebrow_range[1] - right_eyebrow_range[0]) * reb_alpha
                                            
                                            # 왼쪽 눈 윙크
                                            if left_eye_wink_param.is_discrete():
                                                if lew_alpha > 0.5:  # 50% 이상이면 ON
                                                    for k in range(left_eye_wink_param.get_arity()):
                                                        current_pose[left_eye_wink_idx + k] = 1.0
                                            else:
                                                if left_eye_wink_param.get_arity() == 2:
                                                    current_pose[left_eye_wink_idx + 1] = left_eye_wink_range[0] + (left_eye_wink_range[1] - left_eye_wink_range[0]) * lew_alpha
                                                else:
                                                    current_pose[left_eye_wink_idx] = left_eye_wink_range[0] + (left_eye_wink_range[1] - left_eye_wink_range[0]) * lew_alpha
                                            
                                            # 오른쪽 눈 윙크
                                            if right_eye_wink_param.is_discrete():
                                                if rew_alpha > 0.5:  # 50% 이상이면 ON
                                                    for k in range(right_eye_wink_param.get_arity()):
                                                        current_pose[right_eye_wink_idx + k] = 1.0
                                            else:
                                                if right_eye_wink_param.get_arity() == 2:
                                                    current_pose[right_eye_wink_idx] = right_eye_wink_range[0] + (right_eye_wink_range[1] - right_eye_wink_range[0]) * rew_alpha
                                                else:
                                                    current_pose[right_eye_wink_idx] = right_eye_wink_range[0] + (right_eye_wink_range[1] - right_eye_wink_range[0]) * rew_alpha
                                            
                                            # 입 AAA
                                            if mouth_aaa_param.get_arity() == 2:
                                                # 대각선으로 변화
                                                current_pose[mouth_aaa_idx] = mouth_aaa_range[0] + (mouth_aaa_range[1] - mouth_aaa_range[0]) * maa_alpha
                                                current_pose[mouth_aaa_idx + 1] = mouth_aaa_range[0] + (mouth_aaa_range[1] - mouth_aaa_range[0]) * maa_alpha
                                            else:
                                                current_pose[mouth_aaa_idx] = mouth_aaa_range[0] + (mouth_aaa_range[1] - mouth_aaa_range[0]) * maa_alpha
                                            
                                            # 헤드 X
                                            current_pose[head_x_idx] = head_x_range[0] + (head_x_range[1] - head_x_range[0]) * hx_alpha
                                            
                                            # 헤드 Y
                                            current_pose[head_y_idx] = head_y_range[0] + (head_y_range[1] - head_y_range[0]) * hy_alpha
                                            
                                            # 넥 Z
                                            current_pose[neck_z_idx] = neck_z_range[0] + (neck_z_range[1] - neck_z_range[0]) * nz_alpha
                                            
                                            # 이미지 생성
                                            pose_tensor = torch.tensor(current_pose, device=self.device, dtype=self.dtype)
                                            with torch.no_grad():
                                                output_image = self.poser.pose(self.torch_source_image, pose_tensor, 0)[0].detach().cpu()
                                            numpy_image = convert_output_image_from_torch_to_numpy(output_image)
                                            
                                            # 파일명 생성
                                            filename = (f"combined_LEB{i1:01d}_REB{i2:01d}_LEW{i3:01d}_REW{i4:01d}_"
                                                      f"MAA{i5:01d}_HX{i6:01d}_HY{i7:01d}_NZ{i8:01d}_"
                                                      f"{leb_alpha:.2f}_{reb_alpha:.2f}_{lew_alpha:.2f}_{rew_alpha:.2f}_"
                                                      f"{maa_alpha:.2f}_{hx_alpha:.2f}_{hy_alpha:.2f}_{nz_alpha:.2f}.png")
                                            
                                            # 전체 이미지 저장
                                            self.save_patch(numpy_image, filename, "combined_parameters")
                                            
                                            image_count += 1
                                            
                                            # 진행 상황 업데이트 (100개마다)
                                            if image_count % 100 == 0:
                                                progress_text = f"Generated {image_count:,}/{total_combinations:,} combinations"
                                                if not dialog.Update(image_count, progress_text)[0]:
                                                    wx.MessageBox("Generation cancelled by user.", "Cancelled", wx.OK | wx.ICON_INFORMATION)
                                                    return
                                                wx.GetApp().Yield()

            # 완료 메시지
            self.close_progress_dialog_safely(dialog)
            wx.CallAfter(lambda: wx.MessageBox(
                f"All combined parameter images generated successfully!\n"
                f"Total images: {image_count:,}\n"
                f"Combinations: 4×4×4×4×4×4×4×4 = {total_combinations:,}\n"
                f"Parameters: Left Eyebrow, Right Eyebrow, Left Eye Wink, Right Eye Wink, Mouth AAA, Head X, Head Y, Neck Z\n"
                f"Check data/combined_parameters_patches/ folder.",
                "Success",
                wx.OK | wx.ICON_INFORMATION
            ))

        except Exception as e:
            print(f"Error generating combined parameter images: {str(e)}")
            import traceback
            traceback.print_exc()
            
            error_msg = str(e)
            wx.CallAfter(lambda msg=error_msg: wx.MessageBox(f"Error generating combined images: {msg}", "Error", wx.OK | wx.ICON_ERROR))
        
        finally:
            self.close_progress_dialog_safely(dialog)

    def generate_head_neck_combinations(self, event: wx.Event):
        """헤드 X, 헤드 Y, 넥 Z의 모든 조합 패치 생성 (총 1000장)"""
        if self.torch_source_image is None:
            wx.MessageBox("Please load an image first!", "No Image", wx.OK | wx.ICON_WARNING)
            return

        # 헤드/넥 파라미터 찾기
        head_x_param, head_y_param, neck_z_param = self.get_head_neck_parameters()
        
        if not all([head_x_param, head_y_param, neck_z_param]):
            missing_params = []
            if not head_x_param:
                missing_params.append("Head X")
            if not head_y_param:
                missing_params.append("Head Y")
            if not neck_z_param:
                missing_params.append("Neck Z")
            
            wx.MessageBox(
                f"Missing parameters: {', '.join(missing_params)}\nPlease check parameter names.",
                "Parameters Not Found",
                wx.OK | wx.ICON_ERROR
            )
            return

        # 파라미터 정보 출력
        print(f"Head X: {head_x_param.get_group_name()}, Index: {head_x_param.get_parameter_index()}, Range: {head_x_param.get_range()}")
        print(f"Head Y: {head_y_param.get_group_name()}, Index: {head_y_param.get_parameter_index()}, Range: {head_y_param.get_range()}")
        print(f"Neck Z: {neck_z_param.get_group_name()}, Index: {neck_z_param.get_parameter_index()}, Range: {neck_z_param.get_range()}")

        # 전체 이미지를 패치로 사용할 영역 정의
        full_image_region = {
            'x': 0,
            'y': 0,
            'w': self.image_size,
            'h': self.image_size,
            'side': 'full'
        }

        # 총 패치 수: 10 × 10 × 10 = 1000
        total_patches = 10 * 10 * 10
        
        # 진행 다이얼로그
        dialog = wx.ProgressDialog(
            "Generating Head+Neck Combination Patches",
            "Generating all combinations of Head X, Head Y, and Neck Z...",
            total_patches,
            self,
            wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE
        )

        patch_count = 0
        base_pose = self.get_current_pose()

        try:
            # 파라미터 범위 가져오기
            head_x_range = head_x_param.get_range()
            head_y_range = head_y_param.get_range()
            neck_z_range = neck_z_param.get_range()
            
            head_x_index = head_x_param.get_parameter_index()
            head_y_index = head_y_param.get_parameter_index()
            neck_z_index = neck_z_param.get_parameter_index()

            # 0~1 범위를 10단계로 나누기
            steps = numpy.linspace(0, 1, 10)
            
            for i, head_x_alpha in enumerate(steps):
                for j, head_y_alpha in enumerate(steps):
                    for k, neck_z_alpha in enumerate(steps):
                        # 현재 조합에 대한 파라미터 값 계산
                        head_x_value = head_x_range[0] + (head_x_range[1] - head_x_range[0]) * head_x_alpha
                        head_y_value = head_y_range[0] + (head_y_range[1] - head_y_range[0]) * head_y_alpha
                        neck_z_value = neck_z_range[0] + (neck_z_range[1] - neck_z_range[0]) * neck_z_alpha
                        
                        # 포즈 설정
                        current_pose = base_pose.copy()
                        current_pose[head_x_index] = head_x_value
                        current_pose[head_y_index] = head_y_value
                        current_pose[neck_z_index] = neck_z_value
                        
                        # 이미지 생성
                        pose_tensor = torch.tensor(current_pose, device=self.device, dtype=self.dtype)
                        with torch.no_grad():
                            output_image = self.poser.pose(self.torch_source_image, pose_tensor, 0)[0].detach().cpu()
                        numpy_image = convert_output_image_from_torch_to_numpy(output_image)
                        
                        # 전체 이미지를 패치로 저장
                        patch = numpy_image[
                            full_image_region['y']:full_image_region['y']+full_image_region['h'],
                            full_image_region['x']:full_image_region['x']+full_image_region['w']
                        ]
                        
                        # 파일명 생성: head_neck_X{i:02d}_Y{j:02d}_Z{k:02d}_{head_x_alpha:.2f}_{head_y_alpha:.2f}_{neck_z_alpha:.2f}.png
                        filename = f"head_neck_X{i:02d}_Y{j:02d}_Z{k:02d}_{head_x_alpha:.2f}_{head_y_alpha:.2f}_{neck_z_alpha:.2f}.png"
                        self.save_patch(patch, filename, "head_neck_combinations")
                        
                        patch_count += 1
                        
                        # 진행 상황 업데이트
                        progress_text = f"Generated {filename} ({patch_count}/{total_patches})"
                        dialog.Update(patch_count, progress_text)
                        wx.GetApp().Yield()
                        
                        # 중단 요청 확인
                        if not dialog.Update(patch_count)[0]:
                            wx.MessageBox("Patch generation cancelled by user.", "Cancelled", wx.OK | wx.ICON_INFORMATION)
                            return

            # 완료 메시지
            self.close_progress_dialog_safely(dialog)
            wx.CallAfter(lambda: wx.MessageBox(
                f"All Head+Neck combination patches generated successfully!\n"
                f"Total patches: {patch_count}\n"
                f"Combinations: Head X (10) × Head Y (10) × Neck Z (10) = 1000\n"
                f"Check data/head_neck_combinations_patches/ folder.",
                "Success",
                wx.OK | wx.ICON_INFORMATION
            ))

        except Exception as e:
            print(f"Error generating head+neck combination patches: {str(e)}")
            import traceback
            traceback.print_exc()
            
            error_msg = str(e)
            wx.CallAfter(lambda msg=error_msg: wx.MessageBox(f"Error generating head+neck patches: {msg}", "Error", wx.OK | wx.ICON_ERROR))
        
        finally:
            self.close_progress_dialog_safely(dialog)

    def generate_patches_for_category(self, category, regions, patch_type):
        """특정 카테고리의 모든 파라미터에 대해 패치 생성"""
        if self.torch_source_image is None:
            wx.MessageBox("Please load an image first!", "No Image", wx.OK | wx.ICON_WARNING)
            return

        param_groups = self.get_param_groups_by_category(category)
        if not param_groups:
            wx.MessageBox(f"No {patch_type} parameters found!", "Error", wx.OK | wx.ICON_ERROR)
            return

        # 총 패치 수 계산
        total_patches = 0
        for param_group in param_groups:
            if param_group.is_discrete():
                total_patches += 2 * len(regions)  # on/off × 영역 수
            else:
                if param_group.get_arity() == 1:
                    total_patches += 10 * len(regions)  # 10단계 × 영역 수
                elif param_group.get_arity() == 2:
                    if patch_type == "mouth":
                        total_patches += 10  # 입은 1개 영역만
                    else:
                        total_patches += 20  # 좌우 각각 10단계

        # 진행 다이얼로그
        dialog = wx.ProgressDialog(
            f"Generating {patch_type.title()} Patches",
            f"Generating patches for {patch_type} parameters...",
            total_patches,
            self,
            wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE
        )

        patch_count = 0
        base_pose = self.get_current_pose()

        try:
            for param_group in param_groups:
                param_name = param_group.get_group_name()
                if 'wink' in param_name.lower():
                    param_name = param_name.lower().replace('wink', 'blink')
                param_index = param_group.get_parameter_index()
                param_arity = param_group.get_arity()
                is_discrete = param_group.is_discrete()

                print(f"Processing {patch_type} parameter: {param_name}")

                if is_discrete:
                    # discrete 파라미터: OFF/ON
                    for state_value in [0.0, 1.0]:
                        state_name = "off" if state_value == 0.0 else "on"
                        
                        current_pose = base_pose.copy()
                        for i in range(param_arity):
                            current_pose[param_index + i] = state_value
                        
                        # 이미지 생성
                        pose_tensor = torch.tensor(current_pose, device=self.device, dtype=self.dtype)
                        with torch.no_grad():
                            output_image = self.poser.pose(self.torch_source_image, pose_tensor, 0)[0].detach().cpu()
                        numpy_image = convert_output_image_from_torch_to_numpy(output_image)
                        
                        # 각 영역별 패치 저장
                        for region in regions:
                            patch = numpy_image[
                                region['y']:region['y']+region['h'],
                                region['x']:region['x']+region['w']
                            ]
                            safe_name = param_name.replace(" ", "_").replace("/", "_")
                            filename = f"{safe_name}_{region['side']}_{state_name}.png"
                            self.save_patch(patch, filename, patch_type)
                            
                            patch_count += 1
                            dialog.Update(patch_count, f"Generated {filename}")
                            wx.GetApp().Yield()

                elif param_arity == 1:
                    # 단일 파라미터: 10단계
                    param_range = param_group.get_range()
                    for i, alpha in enumerate(numpy.linspace(0, 1, 10)):
                        value = param_range[0] + (param_range[1] - param_range[0]) * alpha
                        
                        current_pose = base_pose.copy()
                        current_pose[param_index] = value
                        
                        # 이미지 생성
                        pose_tensor = torch.tensor(current_pose, device=self.device, dtype=self.dtype)
                        with torch.no_grad():
                            output_image = self.poser.pose(self.torch_source_image, pose_tensor, 0)[0].detach().cpu()
                        numpy_image = convert_output_image_from_torch_to_numpy(output_image)
                        
                        # 각 영역별 패치 저장
                        for region in regions:
                            patch = numpy_image[
                                region['y']:region['y']+region['h'],
                                region['x']:region['x']+region['w']
                            ]
                            safe_name = param_name.replace(" ", "_").replace("/", "_")
                            filename = f"{safe_name}_{region['side']}_step{i:02d}_{alpha:.2f}.png"
                            self.save_patch(patch, filename, patch_type)
                            
                            patch_count += 1
                            dialog.Update(patch_count, f"Generated {filename}")
                            wx.GetApp().Yield()

                elif param_arity == 2:
                    param_range = param_group.get_range()
                    
                    if patch_type == "mouth":
                        # 입: 대각선으로 10단계
                        for i, alpha in enumerate(numpy.linspace(0, 1, 10)):
                            value1 = param_range[0] + (param_range[1] - param_range[0]) * alpha
                            value2 = param_range[0] + (param_range[1] - param_range[0]) * alpha
                            
                            current_pose = base_pose.copy()
                            current_pose[param_index] = value1
                            current_pose[param_index + 1] = value2
                            
                            # 이미지 생성
                            pose_tensor = torch.tensor(current_pose, device=self.device, dtype=self.dtype)
                            with torch.no_grad():
                                output_image = self.poser.pose(self.torch_source_image, pose_tensor, 0)[0].detach().cpu()
                            numpy_image = convert_output_image_from_torch_to_numpy(output_image)
                            
                            # 입 패치 저장
                            region = regions[0]  # 입은 1개 영역만
                            patch = numpy_image[
                                region['y']:region['y']+region['h'],
                                region['x']:region['x']+region['w']
                            ]
                            safe_name = param_name.replace(" ", "_").replace("/", "_")
                            filename = f"{safe_name}_step{i:02d}_{alpha:.2f}.png"
                            self.save_patch(patch, filename, patch_type)
                            
                            patch_count += 1
                            dialog.Update(patch_count, f"Generated {filename}")
                            wx.GetApp().Yield()
                    
                    else:
                        # 눈/아이브로우: 좌우 각각 10단계
                        left_region = regions[0]
                        right_region = regions[1]
                        
                        # 좌측 변화
                        for i, alpha in enumerate(numpy.linspace(0, 1, 10)):
                            left_value = param_range[0] + (param_range[1] - param_range[0]) * alpha
                            
                            current_pose = base_pose.copy()
                            current_pose[param_index + 1] = left_value  # 좌측
                            current_pose[param_index] = param_range[0]  # 우측 기본값
                            
                            # 이미지 생성
                            pose_tensor = torch.tensor(current_pose, device=self.device, dtype=self.dtype)
                            with torch.no_grad():
                                output_image = self.poser.pose(self.torch_source_image, pose_tensor, 0)[0].detach().cpu()
                            numpy_image = convert_output_image_from_torch_to_numpy(output_image)
                            
                            # 좌측 패치만 저장
                            patch = numpy_image[
                                left_region['y']:left_region['y']+left_region['h'],
                                left_region['x']:left_region['x']+left_region['w']
                            ]
                            safe_name = param_name.replace(" ", "_").replace("/", "_")
                            filename = f"{safe_name}_left_step{i:02d}_{alpha:.2f}.png"
                            self.save_patch(patch, filename, patch_type)
                            
                            patch_count += 1
                            dialog.Update(patch_count, f"Generated {filename}")
                            wx.GetApp().Yield()
                        
                        # 우측 변화
                        for i, alpha in enumerate(numpy.linspace(0, 1, 10)):
                            right_value = param_range[0] + (param_range[1] - param_range[0]) * alpha
                            
                            current_pose = base_pose.copy()
                            current_pose[param_index] = right_value  # 우측
                            current_pose[param_index + 1] = param_range[0]  # 좌측 기본값
                            
                            # 이미지 생성
                            pose_tensor = torch.tensor(current_pose, device=self.device, dtype=self.dtype)
                            with torch.no_grad():
                                output_image = self.poser.pose(self.torch_source_image, pose_tensor, 0)[0].detach.cpu()
                            numpy_image = convert_output_image_from_torch_to_numpy(output_image)
                            
                            # 우측 패치만 저장
                            patch = numpy_image[
                                right_region['y']:right_region['y']+right_region['h'],
                                right_region['x']:right_region['x']+right_region['w']
                            ]
                            safe_name = param_name.replace(" ", "_").replace("/", "_")
                            filename = f"{safe_name}_right_step{i:02d}_{alpha:.2f}.png"
                            self.save_patch(patch, filename, patch_type)
                            
                            patch_count += 1
                            dialog.Update(patch_count, f"Generated {filename}")
                            wx.GetApp().Yield()

            # 완료 메시지
            self.close_progress_dialog_safely(dialog)
            wx.CallAfter(lambda: wx.MessageBox(
                f"All {patch_type} patches generated successfully!\n"
                f"Total patches: {patch_count}\n"
                f"Parameters processed: {len(param_groups)}\n"
                f"Check data/{patch_type}_patches/ folder.",
                "Success",
                wx.OK | wx.ICON_INFORMATION
            ))

        except Exception as e:
            print(f"Error generating {patch_type} patches: {str(e)}")
            import traceback
            traceback.print_exc()
            
            error_msg = str(e)
            wx.CallAfter(lambda msg=error_msg: wx.MessageBox(f"Error generating {patch_type} patches: {msg}", "Error", wx.OK | wx.ICON_ERROR))
        
        finally:
            self.close_progress_dialog_safely(dialog)

    def generate_eye_patches(self, event: wx.Event):
        """눈 패치 생성"""
        left_region = {'x': 216, 'y': 138, 'w': 36, 'h': 17, 'side': 'left'}
        right_region = {'x': 260, 'y': 138, 'w': 36, 'h': 17, 'side': 'right'}
        regions = [left_region, right_region]
        self.generate_patches_for_category(PoseParameterCategory.EYE, regions, "eye")

    def generate_eyebrow_patches(self, event: wx.Event):
        """아이브로우 패치 생성"""
        left_region = {'x': 215, 'y': 115, 'w': 41, 'h': 15, 'side': 'left'}
        right_region = {'x': 256, 'y': 115, 'w': 45, 'h': 15, 'side': 'right'}
        regions = [left_region, right_region]
        self.generate_patches_for_category(PoseParameterCategory.EYEBROW, regions, "eyebrow")

    def generate_mouth_patches(self, event: wx.Event):
        """입 패치 생성"""
        mouth_region = {'x': 240, 'y': 165, 'w': 30, 'h': 20, 'side': 'center'}
        regions = [mouth_region]
        self.generate_patches_for_category(PoseParameterCategory.MOUTH, regions, "mouth")

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
