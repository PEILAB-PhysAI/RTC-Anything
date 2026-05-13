![Title](assets/images/title.png)
<div align="center">

[![HuggingFace](https://img.shields.io/badge/%F0%9F%A4%97-HuggingFace-yellow)](https://huggingface.co/datasets/PEILAB-PhysAI/RTC-Anything)
[![lang English](https://img.shields.io/badge/lang-English-blue)](README.md)
[![语言 简体中文](https://img.shields.io/badge/%E8%AF%AD%E8%A8%80-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-red)](README_zh.md)

</div>

> 一个面向 **Agilex Cobot Magic** 和 **单臂 Piper** 机器人的通用 real-time chunking 运行时，用于跨任务套件和模型后端部署具身智能策略。

## 概览

RTC Anything 为 Agilex 机器人平台上的具身策略部署提供了一套实用运行框架。它将任务相关配置与运行时解耦，因此每个 task suite 都可以独立定义任务指令、相机布局、初始位姿、rollout 保存行为和策略后端配置。

当前运行时围绕以下能力设计：

- **机器人平台**：Agilex Cobot Magic 双臂机器人和单臂 Piper 机器人。
- **策略后端**：默认使用 OpenPI 兼容的 websocket 推理；也可以通过可替换的 `PolicyClient` 适配自定义模型服务器或本地推理。
- **观测流水线**：同步 ROS 相机流和机器人状态，并转换后发送给策略后端。
- **控制循环**：通过 real-time chunking 融合重叠的动作 chunk，让真机执行更平滑。
- **Rollout 数据**：可选保存 HDF5，记录图像、状态、动作和成功标签，便于调试或后续数据集转换。

用于策略学习与训练的**训练数据**已在 Hugging Face 公开：[**PEILAB-PhysAI/RTC-Anything**](https://huggingface.co/datasets/PEILAB-PhysAI/RTC-Anything)。

## 任务套件

| 任务 | 类别 | 指南 |
|------|------|------|
| 衣物折叠 | 柔性物体操作 | [打开指南](task_suites/clothes_folding_zh.md) |
| 物体清扫 | 工具辅助物体操作 | [打开指南](task_suites/object_sweeping_zh.md) |
| 桌面清洁 | 桌面清洁 | [打开指南](task_suites/table_cleaning_zh.md) |

任务套件演示：

<div align="center">

<table>
  <thead>
    <tr>
      <th align="center">衣物折叠 · 侧视视角</th>
      <th align="center">衣物折叠 · 俯视视角</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td align="center" width="360">
        <video src="https://github.com/user-attachments/assets/9da8969b-33eb-425f-8e7c-d13dddeb2977" controls width="360"></video>
      </td>
      <td align="center" width="360">
        <video src="https://github.com/user-attachments/assets/1eb4c65c-a268-4490-8635-ebf53ad5059a" controls width="360"></video>
      </td>
    </tr>
    <tr>
      <td colspan="2" align="center">
        <p><strong>衣物折叠</strong><br><a href="task_suites/clothes_folding_zh.md">打开指南</a></p>
      </td>
    </tr>
    <tr>
      <td align="center" width="360">
        <video src="https://github.com/user-attachments/assets/cc3c1982-cf7f-499e-a01f-fbe8d6db2f00" controls width="360"></video>
        <p align="center"><strong>物体清扫</strong><br><a href="task_suites/object_sweeping_zh.md">打开指南</a></p>
      </td>
      <td align="center" width="360">
        <video src="https://github.com/user-attachments/assets/93bdf721-f4e2-4eb4-a72a-77992a5f19e2" controls width="360"></video>
        <p align="center"><strong>桌面清洁</strong><br><a href="task_suites/table_cleaning_zh.md">打开指南</a></p>
      </td>
    </tr>
  </tbody>
</table>

</div>

## 特性

| 能力 | 说明 |
|------|------|
| **Agilex 机器人支持** | 支持 **Cobot Magic** 双臂部署和 **单臂 Piper** 部署；Cobot Magic 被视为 dual-Piper 机器人配置。 |
| **模型无关部署** | 通过轻量策略客户端，将任务观测连接到可替换的策略后端。 |
| **任务套件** | 将任务指令、相机、初始位姿和 rollout 设置组织为可复用的任务套件。 |
| **Real-Time Chunking 运行** | 通过动作 chunk 缓冲和在线重叠预测融合，让真机动作更平滑。 |
| **ROS 传感器桥接** | 同步机器人侧相机流和状态观测，用于真实世界闭环部署。 |
| **配置驱动 Rollout** | 使用 YAML 配置机器人通道、安全阈值、控制频率、初始位姿和数据输出路径。 |
| **Rollout 数据记录** | 以 HDF5 格式记录部署 episode，便于调试、评估和后续数据集转换。 |

## 硬件与软件

| 组件 | 支持配置 |
|------|----------|
| **机器人** | Agilex Cobot Magic 双臂机器人、Agilex 单臂 Piper |
| **相机** | 通过 ROS 图像 topic 配置 front/high 相机和 wrist 相机 |
| **GPU** | Nvidia RTX 4090 24GB |
| **末端执行器** | 通过 `pyAgxArm` 控制 Agilex 夹爪 |
| **机器人控制** | 使用 `pyAgxArm` 直接控制，并支持速度与加速度限制配置 |
| **推理客户端** | `PolicyClient` 适配器，默认连接 OpenPI 兼容 websocket server |

软件栈：

- ROS Noetic 用于图像采集和相机同步。
- 默认使用 **Python 3.11**（见 `requires-python` 与 `.python-version`）。
- `pyAgxArm` 用于 Agilex 机械臂和夹爪控制。
- 默认使用 OpenPI 兼容客户端推理。
- 使用 HDF5 保存部署轨迹。

## 环境配置

本仓库以 **Python 3.11** 为默认版本。使用 `uv sync` 安装核心依赖；若要启用可选的 OpenPI 兼容后端，请安装 dependency group `openpi`（见下方步骤 3）。

1. 先按照 AgileX 平台文档完成机械臂 ROS 部署。

由于本项目部署在松灵 AgileX 机器人平台上，请先参考官方 [Cobot Magic 使用资料](https://agilexsupport.yuque.com/staff-hso6mo/toh64r)，完成机器人侧 ROS 环境配置，并确认机械臂驱动可以正常运行。

2. 如果尚未安装 `uv`，先安装 `uv`。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. 创建 Python 环境。

```bash
uv sync
source .venv/bin/activate
git clone https://github.com/agilexrobotics/pyAgxArm
git clone https://github.com/Physical-Intelligence/openpi #可选
uv pip install -e ./pyAgxArm ./openpi


4. 准备运行时配置。

```bash
cp configs/example_config.yaml configs/config.yaml
```

然后根据你的机器人通道、相机选择、相机 observation 名称、初始位姿、任务指令、`server_host`、`server_port` 和 `save_rollout` 修改 `configs/config.yaml`。

5. 部署前检查机器人和相机连接。

- 确认 Agilex 机械臂 CAN 接口可用，并且与配置中的通道一致。
- 确认已启用相机对应的 ROS topic 正在发布图像。
- 确认策略 server 已在配置的 `server_host` 和 `server_port` 上运行。

## 运行时架构

RTC Anything 保持各个部署组件松耦合：

| 模块 | 职责 |
|------|------|
| `src/dual_piper_deploy.py` | Cobot Magic 双臂部署主循环 |
| `src/single_piper_deploy.py` | 单臂 Piper 部署主循环 |
| `src/utils/policy_client.py` | 策略后端适配器，提供 `update_observation()`、`get_action()` 和 `reset()` |
| `src/utils/real_time_chunking.py` | 线程安全的 real-time chunking 缓冲和加权动作融合 |
| `configs/example_config.yaml` | 机器人、相机、server、安全阈值和日志设置的示例配置 |

部署流程：

1. 从 YAML 加载机器人、相机、server 和任务配置。
2. 将机器人移动到配置的初始位姿。
3. 等待操作者确认开始。
4. 启动异步策略 producer 线程。
5. 根据同步后的 ROS 图像、机器人状态和任务 prompt 构造 observation。
6. 请求策略后端生成动作 chunk。
7. 使用 real-time chunking 融合可用动作 chunk。
8. 在机器人上执行动作，并可选保存 rollout 数据。
9. 停止 producer，调用 `PolicyClient.reset()`，进入下一个 episode。

## Real-Time Chunking

Real-time chunking 通过保存历史预测的动作 chunk 来提升真机 rollout 的平滑性。在每个控制步，所有覆盖当前 timestep 的 chunk 都会用指数权重融合，新的预测权重更高，同时保留旧预测带来的平滑效果。

关键配置字段：

```yaml
action_chunk_size: 50
exp_weight_factor: 0.3
rtc_debug: false
```

如果动作滞后，可以减小 `action_chunk_size` 或提高近期预测权重；如果动作抖动，可以减小 `exp_weight_factor`。

## 配置

从 `configs/example_config.yaml` 开始，创建自己的配置文件，例如 `configs/config.yaml`。

重要配置组：

- **机器人连接**：`left_channel`、`right_channel`、`single_channel`、`bitrate`。
- **运动限制**：`speed_pct`、`max_linear_vel`、`max_angular_vel`、`max_linear_acc`、`max_angular_acc`。
- **策略 server**：`server_host`、`server_port`。
- **相机选择（双臂 `dual_piper_deploy.py`）**：`use_front`、`use_wrist`、`use_left_wrist`、`use_right_wrist`。
- **相机选择（单臂 `single_piper_deploy.py`）**：`use_front`、`use_wrist`（仅 front + wrist 两路 RGB）。
- **ROS topic（双臂）**：配置块 `ros_topics_dual`（`img_front_topic`、`img_left_topic`、`img_right_topic` 及对应 depth）。
- **ROS topic（单臂）**：配置块 `ros_topics_single`（`img_front_topic`、`img_wrist_topic` 及对应 depth）。
- **相机 observation 名称**：`front_camera_name`、`wrist_camera_name`、`left_wrist_camera_name`、`right_wrist_camera_name`。
- **任务指令**：`instruction`。
- **初始位姿**：`left_init_position`、`right_init_position`、`single_init_position`。
- **安全检查**：`action_safety_threshold`、`state_safety_threshold`。
- **Rollout 日志**：`save_rollout`、`output_dir`、`episode_idx_dict`。

提醒：只有当一个 action chunk 覆盖的执行时间大于一次策略推理耗时时，real-time chunking 才能稳定发挥作用。chunk 覆盖时间为 `action_chunk_size / rospy_rate`。例如 `rospy_rate: 100`、`action_chunk_size: 50` 时，一个 chunk 覆盖 `50 / 100 = 0.5s`，也就是 `500ms`；如果一次策略推理约为 `80ms`，producer 就有足够时间在当前 chunk 消耗完之前生成下一段动作。

当 `save_rollout` 关闭时，运行时仍会读取相机图像和机器人状态用于策略推理，但不会缓存或保存 rollout episode。

## 快速开始

```bash
# Cobot Magic 双臂部署
uv run src/dual_piper_deploy.py --config configs/config.yaml

# 单臂 Piper 部署
uv run src/single_piper_deploy.py --config configs/config.yaml

# 关闭 rollout 日志，但仍向 server 发送相机图像和状态
uv run src/dual_piper_deploy.py --config configs/config.yaml --no-save-rollout
```

策略后端默认使用配置中的 `server_host` 和 `server_port`。也可以通过命令行覆盖：

```bash
uv run src/dual_piper_deploy.py --config configs/config.yaml --host localhost --port 8000
```

## 构建你自己的模型后端

RTC Anything 的设计目标是让机器人运行时不绑定到某一种策略实现。要支持不同的模型 server、本地推理运行时，或未来新的策略架构，可以直接定制 `src/utils/policy_client.py`。

部署脚本只依赖三个方法：

- `update_observation(obs)`：从运行时接收原始相机图像、机器人状态和任务指令。
- `get_action()`：返回用于 real-time chunking 和机器人执行的下一段动作 chunk。
- `reset()`：在每个 episode 结束时清理后端侧的 episode 状态。

只要自定义的 `PolicyClient` 保持这个接口，`src/dual_piper_deploy.py` 和 `src/single_piper_deploy.py` 就可以复用同一套 RTC、相机、安全检查和 rollout 日志流水线，同时接入你自己的模型后端。

## 参考资料

- [Real-Time Action Chunking with Large Models](https://www.pi.website/research/real_time_chunking)
- [LeRobot: 开源机器人学习框架](https://github.com/huggingface/lerobot)
- [AgileX pyAgxArm 文档](https://github.com/agilexrobotics/pyAgxArm)
