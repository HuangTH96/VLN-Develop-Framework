"""
1. 通过msgpackrpc构建 server - client架构。
2. 通过port管理UE环境进程
"""
import msgpackrpc
import threading
import os
import json

# 配置UE环境的bash文件名和执行路径
env_exec_path_dict = {
    "Japanese_Street": {
        'bash_name': "Japanese_Street.sh",
        'exec_path': "/home/huangth/traveluav_envs/Japanese_Street"
    },
    "London_Street": {
        'bash_name': "London_Street.sh",
        'exec_path': "/home/huangth/traveluav_envs/London_Street"
    },
}

# 配置 AirSim 的 settings.json 文件
AIRSIM_SETTINGS_JSON = {
    "SettingsVersion": 1.2,
    "SimMode": "Multirotor",
    "PhysicsEngineName": "FastPhysicsEngine", # AirSim自己设计的UAV动力学模型

    # 录制指定相机画面
    "Recording": {
        "RecordOnMove": False,
        "RecordInterval": 0.05,
        "Folder": "/home/user/airsim_rec",
        "Enabled": False,
        "Cameras": [
            { "CameraName": "front_left",  "ImageType": 0, "PixelsAsFloat": False, "Compress": True },
            { "CameraName": "front_left",  "ImageType": 1, "PixelsAsFloat": True,  "Compress": False },
            { "CameraName": "front_right", "ImageType": 0, "PixelsAsFloat": False, "Compress": True }
        ]
    },

    # 设置PX4 UAV
    "Vehicles": {
        "px4_drone": {
            "VehicleType": "PX4Multirotor",
            "AutoCreate": True,
            # 初始位姿
            "X": 0, "Y": 0, "Z": 0,
            "Yaw": 0, "Pitch": 0, "Roll": 0,

            # 机载电脑相机，继承了通用相机参数
            "Cameras": {
                # 仿真 d435i 相机：1个RGB + 2个红外 + 1个红外投射
                # 相机名称只支持 front_center, front_left, front_right, bottom_center, back_center 
                "front_left": { 
                    "X": 0.15, "Y": -0.03, "Z": -0.5, "Pitch": 0, "Roll": 0, "Yaw": 0 ,
                    "CaptureSettings": [
                        {"ImageType": 0, "Width": 848, "Height": 480, "FOV_Degrees": 87},
                        {"ImageType": 1, "Width": 848, "Height": 480, "FOV_Degrees": 87},
                        ]},     # 模拟左IR + depth
                "front_right": { 
                    "X": 0.15, "Y": 0.03, "Z": -0.5, "Pitch": 0, "Roll": 0, "Yaw": 0,
                    "CaptureSettings": [
                        {"ImageType": 0, "Width": 848, "Height": 480, "FOV_Degrees": 87},
                    ]},     # 模拟右IR 
                "front_center": {                                                                       # 模拟RGB
                    "CaptureSettings": [
                        {"ImageType": 0, "Width": 848, "Height": 480, "FOV_Degrees": 87},
                    ],
                    "X": 0.15, "Y": 0.0575, "Z": -0.5, "Pitch": 0, "Roll": 0, "Yaw": 0 },
            },

            # 考虑模型能接受到IMU数据
            "Sensors": {
                "Imu": {
                        "SensorType": 2,
                        "Enabled" : True,
                        "AngularRandomWalk": 0.3,
                        "GyroBiasStabilityTau": 500,
                        "GyroBiasStability": 4.6,
                        "VelocityRandomWalk": 0.24,
                        "AccelBiasStabilityTau": 800,
                        "AccelBiasStability": 36
                }
            }  
        }
    }

}

"""
为运行两个UE环境，配置不同的端口号。涉及以下几个函数：

1. cleanPorts(ports: list)       准备端口
2. fromPortGetPid(port: int)    查看是否有进程占用该端口，返回pid。
3. killPID(pid: int)            通过PID杀死正在占用该端口的进程
"""

def kill_pid(port:int, pid: int):
    import signal
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"已杀死占用端口：{port}的进程，PID: {pid}")
    except Exception as e:
        print(f"无法杀死进程 {pid}: {e}")

def from_port_get_pid(port: int):
    import subprocess
    try:
        r = subprocess.run(
            ['lsof', '-t', '-i', f'TCP:{port}', '-sTCP:LISTEN'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        pids = [int(p) for p in r.stdout.split() if int(p) != os.getpid()]
        return pids[0] if pids else None
    except Exception as e:
        print(f"无法获取端口 {port} 的PID: {e}")
        return None

def clean_ports(ports: list):
    threads = []    
    def _kill_port(port):
        pid = from_port_get_pid(port)
        if pid:
            kill_pid(port, pid)

    for i, port in enumerate(ports):    # 使用多线程同时清理多个端口
        thread = threading.Thread(target=_kill_port, args=(port,), daemon=True)
        threads.append(thread)
    
    for thread in threads:      # 启动所有线程
        thread.start()
    for thread in threads:      # 等待所有线程完成
        thread.join()

    return

"""
client不直接接触UE进程，由server负责接受client的请求，处理UE进程后返回所需信息。

server核心 EventHandler 作为处理请求的对象，当客户端发送请求到服务端时，客户端调用的方法名会被分发给EventHandler里的同名方法。应具备以下功能：
1.启动环境：start_env。选场景 -> 分配端口 -> 生成 settings.json -> Popen 启动UE -> 等RPC端口就绪 -> 返回端口号
2.关闭环境：stop_env。通过端口号 -> 获取PID -> 杀死
3.GPU分配
4. settings.json 生成。为每个实例生成独立的 settings 文件

以及其他辅助功能：
1. 就绪检测： _wait_port
"""

class EventHandler(object):
    def __init__(self, ports_to_scenes: list, selected_gpu_ids: list):
        self.default_start_port = 41451
        if ports_to_scenes is None:
            # 如果没有指定端口，则为每个场景分配一个默认端口号，从 41451 开始递增
            self.ports_to_scenes = {scene: 41451 + i for i, _ in enumerate(env_exec_path_dict.keys())}
        else:
            self.ports_to_scenes = ports_to_scenes

        self.selected_gpu_ids = selected_gpu_ids
                        

    def start_env(self, env_names: list, ports: list, gpu_ids: list) -> list:
        """
        并行启动多个UE环境
        :param env_names: 场景名称列表
        :param ports: RPC端口号列表
        :param gpu_ids: GPU ID列表
        :return: 返回启动的端口号列表
        """

        # 检查输入参数
        if not env_names or not ports:
            raise ValueError("场景名称或端口号为空")

        if len(env_names) != len(ports):
            raise ValueError("场景名称和端口号数量不匹配")

        # 生成 settings.json 文件
        for env_name in env_names:
            settings_path = os.path.join(env_exec_path_dict[env_name]['exec_path'], 'settings.json')
            with open(settings_path, 'w') as f:
                json.dump(AIRSIM_SETTINGS_JSON, f, indent=4)

        # 启动UE进程
        bash_name = env_exec_path_dict[env_names]['bash_name']
        exec_path = env_exec_path_dict[env_names]['exec_path']
        bash_path = os.path.join(exec_path, bash_name)
        
        # 使用Popen启动UE进程
        process = os.popen(f"cd {exec_path} && bash {bash_name} {ports}")
        
        # 等待RPC端口就绪
        self._wait_port(ports)
        
        return ports