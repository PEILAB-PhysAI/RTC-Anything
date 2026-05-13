#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import time
import signal
import numpy as np
import argparse
from collections import deque
import threading

from pyAgxArm import create_agx_arm_config, AgxArmFactory

import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from utils.policy_client import PolicyClient
from utils.real_time_chunking import RealTimeChunkingBuffer

import h5py
import os
from pathlib import Path
import termios
import select
import tty
import yaml


def get_bootstrap_config_path():
    """Read --config from sys.argv before argparse builds the full CLI."""
    for index, arg in enumerate(sys.argv[1:], start=1):
        if arg == "--config" and index + 1 < len(sys.argv):
            return sys.argv[index + 1]
        if arg.startswith("--config="):
            return arg.split("=", 1)[1]
    return None


def load_config(config_path=None):
    """Load deployment config from CLI, environment, or common project locations."""
    config_candidates = []
    if config_path:
        config_candidates.append(Path(config_path))
    if os.getenv("RTC_CONFIG"):
        config_candidates.append(Path(os.environ["RTC_CONFIG"]))
    project_root = Path(__file__).resolve().parents[1]
    config_candidates.extend([
        Path.cwd() / "config.yaml",
        project_root / "configs" / "config.yaml",
        project_root / "configs" / "example_config.yaml",
    ])

    for config_path in config_candidates:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                loaded_config = yaml.safe_load(f) or {}
            print(f"[config] Loaded single-piper config from {config_path}")
            return loaded_config

    raise FileNotFoundError(
        "No config file found. Use --config, set RTC_CONFIG, or create configs/config.yaml."
    )


config = load_config(get_bootstrap_config_path())

# Rollout counters.
episode_idx_dict = config.get("episode_idx_dict", {"success": 0, "fail": 0})
outcome_count_dict = {"success": 0, "fail": 0}
success_count = 0
total_count = 0

# Asynchronous inference state.
_action_prod_thread = None
_action_stop_event = threading.Event()
_ACTION_DIM = 7

# Stop signal shared with the action producer thread.
stop_signal = threading.Event()


def save_data(images, actions, states, success, folder_type, args):
    """Save rollout data to an HDF5 file."""
    print("final长度：", len(images), len(actions), len(states))
    global episode_idx_dict
    data_size = len(actions)
    if data_size == 0:
        print("没有数据可保存(There is no data to save)")
        return

    if len(images) == 0:
        print("没有图像可保存(There are no images to save)")
        return

    image_names = list(images[0].keys())
    if not image_names:
        print("没有启用的相机可保存(No enabled cameras to save)")
        return

    data_dict = {
        "/observations/qpos": [],
        "/observations/qvel": [],
        "/observations/effort": [],
        "/action": [],
        "/base_action": [],
        "/isSuccess": [],
    }
    for image_name in image_names:
        data_dict[f"/observations/images/{image_name}"] = []

    bridge = CvBridge()

    for i, action in enumerate(actions):
        if i < len(images):
            image_dict = images[i]
            for image_name in image_names:
                data_dict[f"/observations/images/{image_name}"].append(
                    bridge.imgmsg_to_cv2(image_dict[image_name], "passthrough")
                )

        if i < len(states):
            data_dict["/observations/qpos"].append(states[i])
            data_dict["/observations/qvel"].append(np.zeros(_ACTION_DIM))
            data_dict["/observations/effort"].append(np.zeros(_ACTION_DIM))

        data_dict["/action"].append(action)
        data_dict["/isSuccess"].append(success)
        data_dict["/base_action"].append([0.0, 0.0])

    print("data_dict['/observations/qpos']:", len(data_dict["/observations/qpos"]))

    if folder_type not in episode_idx_dict:
        episode_idx_dict[folder_type] = 0
    idx = episode_idx_dict[folder_type]
    base_path = os.path.join(args.output_dir, folder_type)
    if not os.path.exists(base_path):
        os.makedirs(base_path, exist_ok=True)

    dataset_path = os.path.join(base_path, f"episode_{idx}.hdf5")

    t0 = time.time()
    with h5py.File(dataset_path, "w", rdcc_nbytes=1024**2 * 2) as root:
        root.attrs["sim"] = False
        root.attrs["compress"] = False

        obs = root.create_group("observations")
        image = obs.create_group("images")

        first_image = data_dict[f"/observations/images/{image_names[0]}"][0]
        h, w, c = first_image.shape

        for image_name in image_names:
            _ = image.create_dataset(image_name, (data_size, h, w, c), dtype="uint8", chunks=(1, h, w, c))

        _ = obs.create_dataset("qpos", (data_size, _ACTION_DIM))
        _ = obs.create_dataset("qvel", (data_size, _ACTION_DIM))
        _ = obs.create_dataset("effort", (data_size, _ACTION_DIM))
        _ = root.create_dataset("base_action", (data_size, 2))
        _ = root.create_dataset("action", (data_size, _ACTION_DIM))
        _ = root.create_dataset("isSuccess", (data_size))

        for name, array in data_dict.items():
            root[name][...] = array

    print(f"\033[32m Saving: {time.time() - t0:.1f} secs. {dataset_path} \033[0m")
    episode_idx_dict[folder_type] += 1


class RosOperator:
    def __init__(self, args):
        self.img_front_deque = None
        self.img_wrist_deque = None
        self.img_front = None
        self.img_wrist = None
        self.img_front_depth_deque = None
        self.img_wrist_depth_deque = None
        self.bridge = None
        self.args = args
        self.init()
        self.init_ros()

    def init(self):
        self.bridge = CvBridge()
        self.img_front_deque = deque()
        self.img_wrist_deque = deque()
        self.img_front_depth_deque = deque()
        self.img_wrist_depth_deque = deque()

    def get_frame(self):
        active_deques = []
        if self.args.use_front:
            active_deques.append(self.img_front_deque)
        if self.args.use_wrist:
            active_deques.append(self.img_wrist_deque)
        if not active_deques:
            raise ValueError("At least one camera must be enabled for single-arm deployment.")
        if any(len(image_deque) == 0 for image_deque in active_deques):
            return False

        frame_time = min(image_deque[-1].header.stamp.to_sec() for image_deque in active_deques)
        if any(image_deque[-1].header.stamp.to_sec() < frame_time for image_deque in active_deques):
            return False

        frame = {}
        if self.args.use_front:
            while self.img_front_deque[0].header.stamp.to_sec() < frame_time:
                self.img_front_deque.popleft()
            frame["front"] = self.bridge.imgmsg_to_cv2(self.img_front_deque.popleft(), "passthrough")

        if self.args.use_wrist:
            while self.img_wrist_deque[0].header.stamp.to_sec() < frame_time:
                self.img_wrist_deque.popleft()
            frame["wrist"] = self.bridge.imgmsg_to_cv2(self.img_wrist_deque.popleft(), "passthrough")

        return frame

    def img_front_callback(self, msg):
        if len(self.img_front_deque) >= 2000:
            self.img_front_deque.popleft()
        self.img_front_deque.append(msg)
        self.img_front = msg

    def img_wrist_callback(self, msg):
        if len(self.img_wrist_deque) >= 2000:
            self.img_wrist_deque.popleft()
        self.img_wrist_deque.append(msg)
        self.img_wrist = msg

    def img_front_depth_callback(self, msg):
        if len(self.img_front_depth_deque) >= 2000:
            self.img_front_depth_deque.popleft()
        self.img_front_depth_deque.append(msg)

    def img_wrist_depth_callback(self, msg):
        if len(self.img_wrist_depth_deque) >= 2000:
            self.img_wrist_depth_deque.popleft()
        self.img_wrist_depth_deque.append(msg)

    def get_latest_image_messages(self):
        """Return latest ROS image messages keyed by configured policy camera names."""
        images = {}
        if self.args.use_front and self.img_front is not None:
            images[config.get("front_camera_name", "cam_high")] = self.img_front
        if self.args.use_wrist and self.img_wrist is not None:
            images[config.get("wrist_camera_name", "cam_wrist")] = self.img_wrist
        return images

    def init_ros(self):
        rospy.init_node("joint_state_publisher", anonymous=True)
        if self.args.use_front:
            rospy.Subscriber(self.args.img_front_topic, Image, self.img_front_callback, queue_size=1000, tcp_nodelay=True)
        if self.args.use_wrist:
            rospy.Subscriber(self.args.img_wrist_topic, Image, self.img_wrist_callback, queue_size=1000, tcp_nodelay=True)
        if self.args.use_depth_image:
            rospy.Subscriber(self.args.img_front_depth_topic, Image, self.img_front_depth_callback, queue_size=1000, tcp_nodelay=True)
            rospy.Subscriber(self.args.img_wrist_depth_topic, Image, self.img_wrist_depth_callback, queue_size=1000, tcp_nodelay=True)


class InferController:
    def __init__(self, host="localhost", port=8000):
        self.client = None
        self.host = host
        self.port = port
        self.channel = config.get("single_channel", config.get("left_channel", "can0"))
        self.bitrate = config.get("bitrate", 1000000)

        self.speed_pct = config.get("speed_pct", 15)
        self.max_linear_vel = config.get("max_linear_vel", 0.5)
        self.max_angular_vel = config.get("max_angular_vel", 0.1)
        self.max_linear_acc = config.get("max_linear_acc", 0.1)
        self.max_angular_acc = config.get("max_angular_acc", 0.05)

        self.arm = None
        self.gripper = None

        self.instruction = config.get("instruction", "fold the cloth")

        self.ACTION_CHUNK_SIZE = config.get("action_chunk_size", 50)
        self.rtc = RealTimeChunkingBuffer(
            chunk_size=self.ACTION_CHUNK_SIZE,
            exp_weight_factor=config.get("exp_weight_factor", 0.3),
            debug=config.get("rtc_debug", False),
        )

        self.INIT_POSITION = np.asarray(
            config.get("single_init_position", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.05]),
            dtype=np.float32,
        )

        self.ACTION_SAFETY_THRESHOLD = config.get("action_safety_threshold", 1.5)
        self.STATE_SAFETY_THRESHOLD = config.get("state_safety_threshold", 0.3)

    def connect_arm(self):
        """Connect the Piper arm, initialize the gripper, and enable motion."""
        print("连接机械臂(connect arm)...")
        try:
            cfg = create_agx_arm_config(
                robot="piper",
                comm="can",
                channel=self.channel,
                bitrate=self.bitrate,
            )
            self.arm = AgxArmFactory.create_arm(cfg)
            self.gripper = self.arm.init_effector(self.arm.OPTIONS.EFFECTOR.AGX_GRIPPER)
            self.arm.connect()

            time.sleep(0.5)
            if not self.arm.is_ok():
                raise Exception("机械臂连接状态检查失败(connection status check failed)")

            self.arm.set_flange_vel_acc_limits(
                max_linear_vel=self.max_linear_vel,
                max_angular_vel=self.max_angular_vel,
                max_linear_acc=self.max_linear_acc,
                max_angular_acc=self.max_angular_acc,
                timeout=1.0,
            )
            self.arm.set_speed_percent(self.speed_pct)

            enabled = False
            for _ in range(5):
                if self.arm.enable():
                    enabled = True
                    break
                time.sleep(0.5)
            if not enabled:
                raise Exception("机械臂 使能超时(enable timeout)")

            print("连接成功(connect successfully)\n")
            return True

        except Exception as e:
            print(f"连接错误：{e}")
            return False

    def get_status_and_state(self):
        """Return 6 joint positions plus gripper value as a 7D state."""
        state = np.zeros(_ACTION_DIM, dtype=np.float32)
        try:
            ja = self.arm.get_joint_angles()
            if ja is not None:
                state[0:6] = ja.msg
            if self.gripper:
                gs = self.gripper.get_gripper_status()
                if gs is not None:
                    state[6] = gs.msg.value
        except Exception as e:
            print(f"状态读取异常(status reading error)：{e}")
        return state

    def move(self, position_state):
        """Send a 7D joint-plus-gripper action."""
        joint_position = position_state[0:6].tolist()
        gripper_position = max(0.0, min(float(position_state[6]), 0.1))
        try:
            self.arm.move_js(joint_position)
            self.gripper.move_gripper(width=gripper_position, force=1.0)
            time.sleep(0.02)
        except Exception as e:
            print(f"移动失败(move failed)：{e}")

    def move_initial(self, position_state):
        """Move smoothly to the configured initial pose."""
        n = 50
        target = np.asarray(position_state, dtype=np.float32)
        left_arm_position = target[0:6].tolist()
        gripper_position = max(0.0, min(float(target[6]), 0.1))
        traj = np.linspace(self.get_status_and_state()[0:6], np.asarray(left_arm_position, dtype=np.float32), n)
        try:
            for i in range(n):
                print(traj[i])
                self.arm.move_js(traj[i].tolist())
                self.gripper.move_gripper(width=gripper_position, force=1.0)
                time.sleep(0.02)
        except Exception as e:
            print(f"移动失败(move failed)：{e}")

    def run(self, ros_operator, args):
        global success_count, total_count, outcome_count_dict, stop_signal

        if not self.connect_arm():
            return False
        print(self.arm.get_firmware())

        self.client = PolicyClient(self.host, self.port)
        if not self.client:
            return False

        while True:
            save_states = []
            save_actions = []
            save_images = []

            stop_signal.clear()
            _action_stop_event.clear()

            rospy_rate = config.get("rospy_rate", 100)
            rate = rospy.Rate(rospy_rate)
            rate.sleep()
            initial_position = self.INIT_POSITION.copy()
            self.move_initial(initial_position)

            self.rtc.clear()

            input("按回车键开始模型推理(Press Enter to start model inference)...")

            global _action_prod_thread
            _action_prod_thread = threading.Thread(target=self._action_producer_loop, args=(ros_operator,), daemon=True)
            _action_prod_thread.start()

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setcbreak(fd)

            t = 0
            last_action = initial_position
            st = time.time()
            try:
                while not rospy.is_shutdown() and not stop_signal.is_set():
                    self.rtc.set_control_time(t)
                    action = self.rtc.get_action(t)
                    if action is None or len(action) == 0:
                        print(f"[WAITING] Waiting for action...")
                        rate.sleep()
                        continue
                    rate.sleep()

                    prev_curr_l1 = np.mean(np.abs(np.array(action) - last_action))
                    if prev_curr_l1 > self.ACTION_SAFETY_THRESHOLD:
                        print(f"\033[31m 安全检查失败：动作变化过大(Safety check failed: Action change too much) {prev_curr_l1:.3f}\033[0m")
                        break

                    current_state = self.get_status_and_state()
                    prev_state_l1 = np.mean(np.abs(current_state - action))
                    if prev_state_l1 > self.STATE_SAFETY_THRESHOLD:
                        print(f"\033[31m 安全检查失败：状态差异过大(Safety check failed: State difference too large) {prev_state_l1:.3f}\033[0m")
                        break

                    last_action = np.array(action)

                    if args.save_rollout:
                        image_dict = ros_operator.get_latest_image_messages()
                        if image_dict:
                            save_images.append(image_dict)
                            save_actions.append(action.copy())
                            save_states.append(current_state.copy())
                            print("保存长度：", len(save_images), len(save_actions), len(save_states))

                    print(self.rtc.get_control_time(), t)
                    print("待执行(Pending execution) action_chunk:", action)
                    try:
                        self.move(action)
                        rate.sleep()
                    except Exception as e:
                        print(f"执行异常(Execute error)：{e}")

                    t += 1
                    rate.sleep()

                    r, w, x = select.select([sys.stdin], [], [], 0)
                    if r:
                        key = sys.stdin.read(1)
                        if key == " ":
                            print("\n结束单次测试()(End of this episode)\n")
                            ed = time.time()
                            cost_time = ed - st
                            print(f"本次耗时(cost time): {cost_time:.2f}s, {t}steps")
                            print(t / cost_time, " steps/s")
                            break

            except Exception as e:
                print(f"\nerror：{e}")
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                termios.tcflush(fd, termios.TCIFLUSH)

            stop_signal.set()
            _action_stop_event.set()
            if _action_prod_thread is not None and _action_prod_thread.is_alive():
                _action_prod_thread.join(timeout=2.0)

            user_input = input("Success? Enter 'y' or 'n': ")
            success = True if user_input.lower() == "y" else False

            if success:
                success_count += 1
                outcome_count_dict["success"] += 1
            else:
                outcome_count_dict["fail"] += 1
            total_count += 1

            if args.save_rollout:
                user_input = input("Save this episode? Enter 'y'(success/fail), or 'n'(no): ")
                save = False
                folder_type = ""

                if user_input.lower() == "y":
                    save = True
                    if success:
                        folder_type = "success"
                    else:
                        folder_type = "fail"
                elif user_input.lower() == "n":
                    save = False

                if save:
                    save_data(save_images, save_actions, save_states, success, folder_type, args)
            else:
                print("[rollout] save_rollout=false; rollout buffers and HDF5 saving are disabled.")
            self.client.reset()

            try:
                success_rate = success_count / total_count * 100
            except Exception:
                success_rate = 0.0

            print("\n" + "=" * 50)
            print("当前测试次数(present rollout episodes):", total_count)
            print("此次是否成功(success?):", "是" if success else "否")
            print("当前成功率(success rate):", f"{success_rate:.2f}%")
            print("当前成功次数(present successful episodes):", outcome_count_dict["success"])
            print("当前失败次数(present failed episodes):", outcome_count_dict["fail"])
            print("总测试次数(total episodes):", total_count)
            print("=" * 50 + "\n")

            continue_input = input("继续下一次测试？(Continue to next episode?) Enter 'y' or 'n': ")
            if continue_input.lower() != "y":
                break

        self._cleanup()

    def _action_producer_loop(self, ros_operator):
        rospy_rate = config.get("rospy_rate", 100)
        rate = rospy.Rate(rospy_rate)
        print_flag_local = True
        while not _action_stop_event.is_set() and not rospy.is_shutdown() and not stop_signal.is_set():
            cursor = self.rtc.get_control_time()
            generation = self.rtc.get_generation()
            already_inferred = self.rtc.has_chunk(cursor)

            if already_inferred:
                rate.sleep()
                continue
            result = ros_operator.get_frame()
            if not isinstance(result, dict) or not result:
                if print_flag_local:
                    print("async syn fail")
                    print_flag_local = False
                rate.sleep()
                continue
            print_flag_local = True

            images = {}
            if "front" in result:
                images[config.get("front_camera_name", "cam_high")] = result["front"]
            if "wrist" in result:
                images[config.get("wrist_camera_name", "cam_wrist")] = result["wrist"]
            obs = {
                "images": images,
                "state": self.get_status_and_state(),
                "prompt": self.instruction,
            }
            self.client.update_observation(obs)

            try:
                action_chunk = self.client.get_action()
                action_chunk = action_chunk[: self.ACTION_CHUNK_SIZE]
                self.rtc.enqueue(action_chunk, cursor, generation=generation)
            except Exception as e:
                print(f"Inference error: {e}")
            rate.sleep()

    def _cleanup(self):
        print("\n正在退出(Exiting)...")
        _action_stop_event.set()

        if _action_prod_thread is not None and _action_prod_thread.is_alive():
            _action_prod_thread.join(timeout=2.0)
            print("producer线程已停止(producer thread stopped).")

        print("Inference stopped.")


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", action="store", type=str, default=None, required=False, help="Path to YAML deployment config.")
    parser.add_argument("--host", action="store", type=str, default=config.get("server_host", "localhost"), required=False, help="Model server host.")
    parser.add_argument("--port", action="store", type=int, default=config.get("server_port", 8000), required=False, help="Model server port.")
    parser.add_argument(
        "--save-rollout",
        dest="save_rollout",
        action=argparse.BooleanOptionalAction,
        default=config.get("save_rollout", True),
        required=False,
        help="Enable image/state/action buffering and HDF5 rollout saving.",
    )
    parser.add_argument("--use-front", dest="use_front", action=argparse.BooleanOptionalAction, default=config.get("use_front", True), required=False, help="Enable front/high camera.")
    parser.add_argument("--use-wrist", dest="use_wrist", action=argparse.BooleanOptionalAction, default=config.get("use_wrist", True), required=False, help="Enable wrist camera.")
    _topics = config.get("ros_topics_single", {}) or {}
    _img_wrist = _topics.get("img_wrist_topic") or _topics.get("img_left_topic", "/camera_wrist/color/image_raw")
    _img_wrist_depth = _topics.get("img_wrist_depth_topic") or _topics.get("img_left_depth_topic", "/camera_wrist/depth/image_raw")
    parser.add_argument("--img_front_topic", action="store", type=str,
                        default=_topics.get("img_front_topic", "/camera_h/color/image_raw"), required=False)
    parser.add_argument("--img_wrist_topic", action="store", type=str,
                        default=_img_wrist, required=False)
    parser.add_argument("--img_front_depth_topic", action="store", type=str,
                        default=_topics.get("img_front_depth_topic", "/camera_h/depth/image_raw"), required=False)
    parser.add_argument("--img_wrist_depth_topic", action="store", type=str,
                        default=_img_wrist_depth, required=False)
    parser.add_argument(
        "--use-depth-image",
        "--use_depth_image",
        dest="use_depth_image",
        action=argparse.BooleanOptionalAction,
        default=config.get("use_depth_image", False),
        required=False,
    )
    parser.add_argument("--output_dir", action="store", type=str, default=config.get("output_dir", "./"), required=False)
    args, unknown = parser.parse_known_args()
    return args


def main():
    def signal_handler(sig, frame):
        print("\n收到中断信号，正在清理(Receive interrupt signal, cleaning up)...")
        global stop_signal, _action_stop_event
        stop_signal.set()
        _action_stop_event.set()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    args = get_arguments()
    ros_operator = RosOperator(args)
    try:
        controller = InferController(host=args.host, port=args.port)
        controller.run(ros_operator, args)
    finally:
        pass


if __name__ == "__main__":
    main()
