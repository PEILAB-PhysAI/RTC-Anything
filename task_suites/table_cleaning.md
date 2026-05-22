<div align="center">

[![HuggingFace](https://img.shields.io/badge/%F0%9F%A4%97-HuggingFace-yellow)](https://huggingface.co/datasets/PEILAB-PhysAI/RTC-Anything)
[![lang English](https://img.shields.io/badge/lang-English-blue)](table_cleaning.md)
[![语言 简体中文](https://img.shields.io/badge/%E8%AF%AD%E8%A8%80-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-red)](table_cleaning_zh.md)

</div>

# Table Cleaning Task Suite

> Task-specific guide for robotic table cleaning with RTC Anything. For platform architecture, runtime configuration, and deployment commands, see the [main README](../README.md).

---

## 📋 Table of Contents

- [Demonstration](#-demonstration)
- [π0 Training Setup](#-π0-training-setup)
- [Scene Setup](#-scene-setup)
- [Data Collection](#-data-collection)
- [Cleaning Strategy](#-cleaning-strategy)
- [Troubleshooting](#-troubleshooting)

---

## 📺 Demonstration

<table align="center">
  <tr>
    <td align="center" width="360">
      <video src="https://github.com/user-attachments/assets/93bdf721-f4e2-4eb4-a72a-77992a5f19e2" controls width="360"></video>
    </td>
  </tr>
</table>

## 🤖 π0 Training Setup

We trained the π0 policy for 50,000 steps with the configuration below.

```python
TrainConfig(
    name="pi0_base_aloha_folding_full",
    model=pi0_config.Pi0Config(),
    data=LeRobotAlohaDataConfig(
      repo_id="table_cleaning",  # your datasets repo_id
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

For other task datasets, swap `repo_id` to the corresponding dataset.

---

## 🎬 Scene Setup

The scene setup, camera layout, lighting control, and workspace table requirements are consistent with the [Clothes Folding Task Suite](clothes_folding.md), so they are not repeated here.

### 📸 Real Scene Demonstration

Here is the overhead view of the actual workspace for the table cleaning task:

<div align="center">
  <img src="../assets/setting/table_cleaning_setting.jpg" height="360" />
</div>

---

## 📊 Data Collection

The data collection pipeline, ROS topic configuration, time synchronization, camera parameter tuning, data format conversion, and collection practices are consistent with the [Clothes Folding Task Suite](clothes_folding.md).

During collection, the object grasping order, placement positions in the small bucket, towel grasping method, and wiping trajectory should remain consistent across demonstrations.

---

## 🧠 Cleaning Strategy

### Task Objective

The robot first uses the left arm to pick up two objects in order and place them into the small bucket, then uses the right arm to pick up the third object and place it into the small bucket. After that, it grasps the towel, wipes the milk off the table, and ends the task.

### Standard Operation Flow

1. The left arm picks up the first object and places it into the small bucket.
2. The left arm picks up the second object and places it into the small bucket.
3. The right arm picks up the third object and places it into the small bucket.
4. The robot grasps the towel.
5. Use the towel to wipe the milk area on the table.
6. After confirming the milk area has been wiped clean, move the arm back to the ending pose to complete the task.

### Collection Consistency Guidelines

- **Fixed object order**: The grasping order of the three objects should remain consistent across all demonstrations.
- **Consistent placement position**: Each object should be stably placed into the small bucket, with consistent release height and release position.
- **Consistent towel grasping**: The towel grasping position, gripper closing timing, and lifting height should remain stable.
- **Consistent wiping trajectory**: Use a fixed wiping direction, fixed coverage area, and fixed termination condition when wiping the milk.
- **Consistent ending state**: After wiping, the robot arm should return to a unified ending pose so the model can learn the task boundary.

---

## 🔍 Troubleshooting

| Phenomenon | Possible Cause | Solution |
|------------|----------------|----------|
| Object does not land stably in the small bucket | Release height is too high, or the release position above the bucket is inconsistent | Lower the release height and standardize the release position above the bucket |
| Object grasping failure | The gripper does not stably approach the object surface, or the grasping height is inconsistent | Follow the "approach the object surface before closing" rule during collection and standardize grasping height |
| Towel slips after grasping | The grasping point is outside the stable gripping area of the towel, or gripping force is insufficient | Adjust the grasping position or gripping force, and avoid grasping only the towel edge |
| Milk is not fully wiped clean | Wiping direction, coverage area, or termination condition is inconsistent | Standardize the wiping direction and coverage area; add one overlapping wipe if needed |
| Loss spikes during training | Auto-exposure enabled during collection, or the action order changes across trajectories | Disable auto-exposure and ensure every trajectory follows the same action order |
