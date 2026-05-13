![Title](assets/images/title.png)
<div align="center">

[![HuggingFace](https://img.shields.io/badge/%F0%9F%A4%97-HuggingFace-yellow)](https://huggingface.co/datasets/PEILAB-PhysAI/RTC-Anything)
[![lang English](https://img.shields.io/badge/lang-English-blue)](README.md)
[![语言 简体中文](https://img.shields.io/badge/%E8%AF%AD%E8%A8%80-%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87-red)](README_zh.md)

</div>

> A universal **real-time chunking** runtime for deploying embodied intelligence policies on **Agilex Cobot Magic** and **single-arm Piper** robots across task suites and model backends.

## Overview

RTC Anything provides a practical runtime framework for embodied policy deployment on Agilex robot platforms. It decouples task-specific configuration from the runtime, so each task suite can independently define task instructions, camera layout, initial poses, rollout saving behavior, and policy backend settings.

The current runtime is built around:

- **Robot platforms**: Agilex Cobot Magic dual-arm robots and single-arm Piper robots.
- **Policy backends**: OpenPI-compatible websocket inference by default; a replaceable `PolicyClient` can adapt to custom model servers or local inference.
- **Observation pipeline**: Synchronized ROS camera streams and robot state, converted and sent to the policy backend.
- **Control loop**: Real-time chunking fuses overlapping action chunks for smoother on-robot execution.
- **Rollout data**: Optional HDF5 logging stores images, state, actions, and success labels for debugging or downstream dataset conversion.

The **training dataset** used for embodied policy learning in these setups is publicly available on Hugging Face: [**PEILAB-PhysAI/RTC-Anything**](https://huggingface.co/datasets/PEILAB-PhysAI/RTC-Anything).

## Task suites

| Task | Category | Guide |
|------|----------|-------|
| Clothes folding | Deformable manipulation | [Open guide](task_suites/clothes_folding.md) |
| Object sweeping | Tool-mediated manipulation | [Open guide](task_suites/object_sweeping.md) |
| Table cleaning | Table cleaning | [Open guide](task_suites/table_cleaning.md) |

Task suite demos:

<div align="center">

<table>
  <thead>
    <tr>
      <th align="center">Clothes folding · Side view</th>
      <th align="center">Clothes folding · Top view</th>
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
        <p><strong>Clothes folding</strong><br><a href="task_suites/clothes_folding.md">Guide</a></p>
      </td>
    </tr>
    <tr>
      <td align="center" width="360">
        <video src="https://github.com/user-attachments/assets/cc3c1982-cf7f-499e-a01f-fbe8d6db2f00" controls width="360"></video>
        <p align="center"><strong>Object sweeping</strong><br><a href="task_suites/object_sweeping.md">Guide</a></p>
      </td>
      <td align="center" width="360">
        <video src="https://github.com/user-attachments/assets/93bdf721-f4e2-4eb4-a72a-77992a5f19e2" controls width="360"></video>
        <p align="center"><strong>Table cleaning</strong><br><a href="task_suites/table_cleaning.md">Guide</a></p>
      </td>
    </tr>
  </tbody>
</table>

</div>

## Features

| Capability | Description |
|------------|-------------|
| **Agilex robot support** | **Cobot Magic** dual-arm deployment and **single-arm Piper** deployment; Cobot Magic is treated as a dual-Piper robot configuration. |
| **Model-agnostic deployment** | Lightweight policy client connects task observations to interchangeable policy backends. |
| **Task suites** | Task instructions, cameras, initial poses, and rollout settings are organized as reusable task suites. |
| **Real-time chunking runtime** | Action chunk buffering and online fusion of overlapping predictions for smoother physical execution. |
| **ROS sensor bridge** | Synchronizes robot-side camera streams and state observations for real-world closed-loop deployment. |
| **Config-driven rollouts** | YAML configures robot channels, safety thresholds, control rate, initial poses, and output paths. |
| **Rollout recording** | Deployment episodes saved in HDF5 for debugging, evaluation, and dataset conversion. |

## Hardware and software

| Component | Supported setup |
|-----------|----------------|
| **Robot** | Agilex Cobot Magic dual-arm robot, Agilex single-arm Piper |
| **Cameras** | Front/high and wrist cameras via configurable ROS image topics |
| **GPU** | Nvidia RTX 4090 24GB |
| **End effector** | Agilex gripper via `pyAgxArm` |
| **Robot control** | Direct `pyAgxArm` control with configurable velocity and acceleration limits |
| **Inference client** | `PolicyClient` adapter, default OpenPI-compatible websocket server |

Software stack:

- ROS Noetic for image capture and camera synchronization.
- Python >= 3.11.
- `pyAgxArm` for Agilex arms and gripper control.
- OpenPI-compatible client inference by default.
- HDF5 for deployment trajectory logging.

## Environment setup

The repository targets **Python 3.11** (`requires-python` / `.python-version`). Run `uv sync` for the core runtime. To add the optional OpenPI-compatible backend, use the `openpi` dependency group (see step 3 below).

1. Complete arm-side ROS setup following the AgileX platform documentation.

This project targets the AgileX robot stack. Refer to the official [Cobot Magic guide](https://agilexsupport.yuque.com/staff-hso6mo/toh64r), finish ROS configuration on the robot side, and confirm the arm drivers run normally.

2. Install `uv` if you do not already have it.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Create the Python environment.

```bash
uv sync
source .venv/bin/activate
git clone https://github.com/agilexrobotics/pyAgxArm
git clone https://github.com/Physical-Intelligence/openpi  # optional
uv pip install -e ./pyAgxArm ./openpi


4. Prepare the runtime configuration.

```bash
cp configs/example_config.yaml configs/config.yaml
```

Edit `configs/config.yaml` for robot channels, camera selection, observation key names, initial poses, task instruction, `server_host`, `server_port`, and `save_rollout`.

5. Pre-deployment checks.

- Agilex CAN interfaces are available and match the configured channels.
- ROS topics for enabled cameras publish images.
- The policy server is running at `server_host` / `server_port`.

## Runtime architecture

RTC Anything keeps deployment components loosely coupled:

| Module | Responsibility |
|--------|------------------|
| `src/dual_piper_deploy.py` | Cobot Magic dual-arm deployment main loop |
| `src/single_piper_deploy.py` | Single-arm Piper deployment main loop |
| `src/utils/policy_client.py` | Policy backend adapter: `update_observation()`, `get_action()`, and `reset()` |
| `src/utils/real_time_chunking.py` | Thread-safe real-time chunking buffer and weighted fusion |
| `configs/example_config.yaml` | Example YAML for robot, camera, server, safety, and logging |

Deployment workflow:

1. Load robot, camera, server, and task settings from YAML.
2. Move the robot(s) to the configured initial poses.
3. Wait for operator confirmation before starting inference.
4. Start the asynchronous policy producer thread.
5. Build observations from synchronized ROS images, robot state, and task prompt.
6. Request action chunks from the policy backend.
7. Fuse overlapping chunks via real-time chunking.
8. Execute on hardware and optionally log rollout data.
9. Stop the producer, call `PolicyClient.reset()`, then move on to the next episode.

## Real-time chunking

Real-time chunking improves on-robot smoothness by retaining a history of predicted action chunks. At each step, chunks that cover the current timestep are fused with exponential weights—new predictions weigh more while older ones still smooth jitter.

Key settings:

```yaml
action_chunk_size: 50
exp_weight_factor: 0.3
rtc_debug: false
```

If motion lags, reduce `action_chunk_size` or emphasize recent predictions more. If motion jitters, reduce `exp_weight_factor`.

## Configuration

Start from `configs/example_config.yaml` and create your own file, for example `configs/config.yaml`.

Important groups:

- **Robot connection**: `left_channel`, `right_channel`, `single_channel`, `bitrate`.
- **Motion limits**: `speed_pct`, `max_linear_vel`, `max_angular_vel`, `max_linear_acc`, `max_angular_acc`.
- **Policy server**: `server_host`, `server_port`.
- **Camera selection (`dual_piper_deploy.py`)**: `use_front`, `use_wrist`, `use_left_wrist`, `use_right_wrist`.
- **Camera selection (`single_piper_deploy.py`)**: `use_front`, `use_wrist` (front + wrist RGB only).
- **ROS topics (dual arm)**: `ros_topics_dual` (`img_front_topic`, `img_left_topic`, `img_right_topic`, and depth variants).
- **ROS topics (single arm)**: `ros_topics_single` (`img_front_topic`, `img_wrist_topic`, and depth variants).
- **Camera observation names**: `front_camera_name`, `wrist_camera_name`, `left_wrist_camera_name`, `right_wrist_camera_name`.
- **Task instruction**: `instruction`.
- **Initial poses**: `left_init_position`, `right_init_position`, `single_init_position`.
- **Safety checks**: `action_safety_threshold`, `state_safety_threshold`.
- **Rollout logging**: `save_rollout`, `output_dir`, `episode_idx_dict`.

Note: chunking behaves best when chunk duration exceeds one inference latency. Duration is `action_chunk_size / rospy_rate`. Example: `rospy_rate: 100`, `action_chunk_size: 50` → chunk covers **0.5 s** (**500 ms**); if inference is ~80 ms, the producer can supply the next chunk before the current one is depleted.

When `save_rollout` is off, cameras and state still feed the policy, but rollout buffers and HDF5 saving are skipped.

## Quick Start

```bash
# Cobot Magic dual-arm deployment
uv run src/dual_piper_deploy.py --config configs/config.yaml

# Single-arm Piper deployment
uv run src/single_piper_deploy.py --config configs/config.yaml

# Disable rollout logging; still streams images/state to the server
uv run src/dual_piper_deploy.py --config configs/config.yaml --no-save-rollout
```

Defaults come from `server_host` and `server_port` in the YAML. Override on the CLI if needed:

```bash
uv run src/dual_piper_deploy.py --config configs/config.yaml --host localhost --port 8000
```

## Build your own backend

RTC Anything avoids locking the runtime to a single policy implementation. Customize `src/utils/policy_client.py` to target another model server, local runtime, or future architecture.

The deploy scripts rely on exactly three hooks:

- `update_observation(obs)` — raw camera frames, robot state, and task prompt from the runtime.
- `get_action()` — next action chunk for real-time chunking and execution.
- `reset()` — clear backend-side episode bookkeeping when an episode finishes.

Preserve this surface and both `dual_piper_deploy.py` and `single_piper_deploy.py` reuse the RTC, vision, safety, and rollout pipelines with your backend.



## References

- [Real-Time Action Chunking with Large Models](https://www.pi.website/research/real_time_chunking)
- [LeRobot: open-source robotics learning framework](https://github.com/huggingface/lerobot)
- [AgileX pyAgxArm docs](https://github.com/agilexrobotics/pyAgxArm)
