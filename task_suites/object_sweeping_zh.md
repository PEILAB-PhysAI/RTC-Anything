<div align="center">

[![HuggingFace](https://img.shields.io/badge/%F0%9F%A4%97-HuggingFace-yellow)](https://huggingface.co/datasets/PEILAB-PhysAI/RTC-Anything)
[![lang English](https://img.shields.io/badge/lang-English-blue)](object_sweeping.md)
[![语言 简体中文](https://img.shields.io/badge/%E8%AF%AD%E8%A8%80-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-red)](object_sweeping_zh.md)

</div>

# 物体清扫任务套件

> RTC Anything 的机器人物体清扫任务指南。平台架构、运行时配置和部署命令请参考[主 README](../README_zh.md)。

---

## 📋 目录

- [效果演示](#-效果演示)
- [训练配置](#-训练配置)
- [场景搭建](#-场景搭建)
- [数据采集](#-数据采集)
- [清扫策略](#-清扫策略)
- [常见问题排查](#-常见问题排查)

---

## 📺 效果演示

<table align="center">
  <tr>
    <td align="center" width="360">
      <video src="https://github.com/user-attachments/assets/cc3c1982-cf7f-499e-a01f-fbe8d6db2f00" controls width="360"></video>
    </td>
  </tr>
</table>

---

## 🤖 训练配置

基于 `pi0_base` 权重，我们使用以下 TrainConfig 训练了 **50,000** 步。

```python
TrainConfig(
    name="pi0_base_aloha_robotwin_full",
    model=pi0_config.Pi0Config(),
    data=LeRobotAlohaDataConfig(
      repo_id="object_sweeping",  # your datasets repo_id
      adapt_to_pi=False,
      repack_transforms=_transforms.Group(inputs=[
        _transforms.RepackTransform({
          "images": {
            "cam_high": "observation.images.cam_high",
            "cam_left_wrist": "observation.images.cam_left_wrist",
            "cam_right_wrist": "observation.images.cam_right_wrist",
          },
          "state": "observation.state",
          "actions": "action",
          "prompt": "prompt",
        })
      ]),
      base_config=DataConfig(
        #local_files_only=True,  # Set to True for local-only datasets.
        prompt_from_task=True,  # Set to True for prompt by task_name
      )
    ),
    optimizer=_optimizer.AdamW(clip_gradient_norm=1.0),
    batch_size=32,  # the total batch_size not pre_gpu batch_size
    weight_loader=weight_loaders.CheckpointWeightLoader("gs://openpi-assets/checkpoints/pi0_base/params"),
    num_train_steps=50000,
    log_interval=1,
    fsdp_devices=2,
  )
```

如果用于其他任务，把 `repo_id` 替换成对应任务的数据集即可。

---

## 🎬 场景搭建

场景搭建、相机布局、光照控制和工作台要求与[衣物折叠任务套件](clothes_folding_zh.md)保持一致，此处不再赘述。

### 📸 真实场景展示

以下是物体清扫任务的真实工作空间俯视视角：

<div align="center">
  <img src="../assets/setting/object_sweeping_setting.jpg" height="360" />
</div>

---

## 📊 数据采集

数据采集流程、ROS topic 配置、时间同步、相机参数调节、数据格式转换和采集规范与[衣物折叠任务套件](clothes_folding_zh.md)保持一致。

采集时需要保证每条轨迹遵循一致的任务顺序和动作边界，避免因物体顺序、工具起始姿态或归位方式不一致导致策略学习困难。

---

## 🧠 清扫策略

### 任务目标

机器人需要先夹起铲子和刷子，按照固定顺序将桌面上的 5 个物体扫入铲子，再将铲子中的物品倒入左侧篮子，最后将铲子和刷子归位并结束任务。

### 标准操作流程

1. 左右机械臂分别夹起铲子和刷子。
2. 按预设顺序依次清扫桌面上的 5 个物体。
3. 将每个物体扫入铲子内，并确保物体稳定落入铲子区域。
4. 将装有物品的铲子移动到左侧篮子上方。
5. 翻转或倾斜铲子，将铲子中的物品倒入左侧篮子。
6. 将铲子和刷子放回初始位置。
7. 双臂回到结束姿态，任务完成。

### 采集一致性要点

- **固定清扫顺序**：5 个物体的清扫顺序在所有 demonstration 中保持一致。
- **工具姿态一致**：夹起铲子和刷子时，抓取位置、闭合时机和抬升高度应保持稳定。
- **扫入判定一致**：每个物体都应完整进入铲子后再执行下一个清扫动作。
- **倒入动作一致**：铲子移动到篮子上方后再倾倒，避免在移动过程中提前滑落。

---

## 🔍 常见问题排查

| 现象 | 可能原因 | 解决方案 |
|------|----------|----------|
| 物体没有完全进入铲子 | 刷子与桌面接触高度不一致，或清扫方向、力度不稳定 | 调整刷子接触高度，统一清扫方向和力度 |
| 铲子内物体移动时滑落 | 铲子移动速度过快，或铲面姿态变化过大 | 降低铲子移动速度，并保持铲面姿态稳定 |
| 倒入篮子失败 | 铲子未到达篮子上方就开始倾倒，或倾倒角度不一致 | 确认铲子到达篮子上方后再倾倒，并统一倾倒角度 |
| 工具归位不稳定 | 归位位置或释放高度不一致 | 统一归位位置和释放高度，避免释放时工具弹开或偏移 |
| 训练 loss spike | 采集时开启了自动曝光，或不同轨迹的任务顺序不一致 | 关闭自动曝光，并确保每条轨迹遵循固定任务顺序 |
