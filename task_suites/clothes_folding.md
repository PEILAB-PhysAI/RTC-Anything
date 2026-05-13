<div align="center">

[![HuggingFace](https://img.shields.io/badge/%F0%9F%A4%97-HuggingFace-yellow)](https://huggingface.co/datasets/PEILAB-PhysAI/RTC-Anything)
[![lang English](https://img.shields.io/badge/lang-English-blue)](clothes_folding.md)
[![语言 简体中文](https://img.shields.io/badge/%E8%AF%AD%E8%A8%80-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-red)](clothes_folding_zh.md)

</div>

# Clothes Folding Task Suite

> Task-specific guide for robotic clothes folding with RTC Anything. For platform architecture, runtime configuration, and deployment commands, see the [main README](../README.md).

---

## 📋 Table of Contents

- [Demonstration](#-demonstration)
- [Scene Setup](#-scene-setup)
- [Data Collection](#-data-collection)
- [Folding Strategy](#-folding-strategy)
- [Troubleshooting](#-troubleshooting)

---

## 📺 Demonstration

<table align="center">
  <thead>
    <tr>
      <th align="center">Side View</th>
      <th align="center">Top View</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td align="center" width="360">
        <video src="https://github.com/PEILAB-PhysAI/RTC-Anything/releases/download/deploy_demo_videos/cloth_folding_side_view.mp4" controls width="360"></video>
      </td>
      <td align="center" width="360">
        <video src="https://github.com/PEILAB-PhysAI/RTC-Anything/releases/download/deploy_demo_videos/cloth_folding_top_view.mp4" controls width="360"></video>
      </td>
    </tr>
  </tbody>
</table>


## 🎬 Scene Setup

### Three-Camera Layout Scheme

- **High-angle Overhead View (Camera 0):** The height is approximately twice the height of joint 3 (j3) when joint 2 (j2) of the robotic arm is vertical.
- **Left Wrist View (Camera 1) + Right Wrist View (Camera 2)**

### Key Environmental Control Points

#### 🔒 Occlusion Management

- Use screens/curtains to block irrelevant background areas
- Ensure cameras only capture the active workspace
- Minimize dynamic interference (people walking, moving objects)

#### 💡 Lighting Optimization

- Use diffused, uniform lighting; for uneven lighting conditions, use blackout curtains/diffusers for homogenization
- Avoid direct light or strong directional shadows; check light distribution via real-time camera feeds to avoid glare or dark spots
- Adjust camera exposure and contrast based on lighting and garment color (see camera parameter settings in the "Data Collection" section)

#### 🪑 Workspace Table Design

- Surface Color: Light gray/beige (❌ Avoid pure white to prevent overexposure)
- Material: Matte surface, minimizing specular reflection
- Contrast: Ensure significant difference between garment color and table background

### 📸 Real Scene Demonstration

Here is our actual workspace setup, including both side and overhead views:

<div align="center">
  <img src="../assets/setting/clothes_folding_setting_side_view.jpg" height="280" />
  <img src="../assets/setting/clothes_folding_setting_top_view.jpg" height="280" />
</div>

---

## 📊 Data Collection

### ROS-based Collection Pipeline

#### 1. Topic Configuration and Time Synchronization

- **Collection Framerate**: Set an appropriate sampling rate (recommended **30Hz**) to balance data volume and computational load.
- **Data Structure**: Save as **HDF5 format**, which will be converted to **LeRobot format (version 0.3.4)** after collection.

#### 2. Camera Parameter Tuning ⚠️ Critical Step!

- **❌ Must disable Auto Exposure and Auto Exposure Priority**
- Reason: The distance between the garment and the camera changes rapidly during the folding process. Auto exposure causes sudden brightness shifts, resulting in loss spikes during training and failure of policy convergence.
- Manually adjust exposure and contrast based on lighting conditions and garment/table color
- Light-colored garments reflect light easily and require lower exposure; dark-colored garments are prone to being too dark and require appropriately increased exposure.

#### 3. Data Format and Conversion Process

- Collection Pipeline: ROS bags (raw data) → HDF5 (intermediate format with metadata) → LeRobot v0.3.4 format (training ready)

#### 4. Collection Practices

##### 🎯 Grasping Consistency Regulations

- **Correct approach**: Lower the gripper until it lightly touches the table before closing to grasp
- **Incorrect approach**: Grasping directly in mid-air
- Reason: The model can hardly distinguish between "close to table" and "mid-air" states solely based on RGB images. Inconsistent grasping heights will cause insufficient lowering of the gripper during inference, ultimately leading to grasping failures.

##### 🔄 Policy Standardization Process

- Each data collection follows a fixed three-stage process: Grasp → Flatten → Fold
- The flattening stage must guarantee policy consistency: gripper grasping positions (e.g., lowest left/right points, or top-left/bottom-right corners), tossing direction, release height, and termination conditions (e.g., both bottom corners visible simultaneously) must be unified.

---

## 🧠 Folding Strategy

### Target Feature Point Selection

- **Bottom Corners**
- **Shoulder Corners**
- **Cuffs**

### Flattening Stage Strategy

- Before the feature points are completely exposed, the gripper always grasps fixed relative positions (e.g., lowest left/right points, top-left and bottom-right corners).
- Execute a grasp → toss → release cycle until the target feature points for both arms are visible simultaneously.
- Tossing direction, amplitude, and release height must remain consistent to reduce policy randomness.

### Folding Stage Strategy

- Dynamically select strategies based on garment type (T-shirt, shirt, pants) and material (stiffness, smoothness), for example:

| Strategy Type | Operation Flow | Applicable Scenarios |
|----------|----------|----------|
| Horizontal + Vertical Folding | Grasp same-side shoulder and bottom corner → Horizontal fold → Then vertical fold | T-shirts, shirts |
| Sleeve-first Folding | Fold sleeves first → Then vertical fold → Finally horizontal fold | Garments with long sleeves |

### Adaptive Policy Selection

Different folding strategies need to be designed based on different garment types (T-shirts, shirts, pants, etc.) and material stiffness/smoothness:
- **Stiff garments**: Easy to grasp, requires fewer tosses, easier to maintain shape.
- **Soft/Smooth garments**: Requires more tosses to flatten. Attention must be paid to anti-slip when the gripper grasps, and movement speeds (like tossing) should be reduced to prevent the garment from slipping off.

---

## 🔍 Troubleshooting

| Phenomenon | Possible Cause | Solution |
|---------|---------|---------|
| Loss spikes during training | Auto-exposure enabled during collection | Disable auto-exposure, re-collect data |
| Grasping failure during deployment | Inconsistent grasping heights in training data | Enforce the "touch table then grasp" rule during collection |
| Robotic arm action jitter | Inference framerate ≠ Control loop frequency | Match the loop frequency; enable real-time chunking |
| Feature point detection failure | Insufficient lighting / low contrast | Manually adjust exposure; optimize workspace lighting |
| Garment slipping during tossing | Speed too high / insufficient gripping force | Reduce motion speed; add rubber gripper pads |

