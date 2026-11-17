import json, os, subprocess,tempfile,time,socket
import cv2
import numpy as np
import pytest
import airsim

import server as srv

ENV="Japanese_Street"
API_PORT=41451

# ---------- 1. 纯单元测试：不需要启动 UE ----------
"""
验证 clean_ports 函数能杀掉占用端口的进程
"""
def test_clean_ports_kills_listener():
    port = 45678
    p = subprocess.Popen(["python", "-m", "http.server", str(port)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # 启动一个简易http服务，监听45678
    time.sleep(1)

    assert srv.from_port_get_pid(port) is not None  # 确定能检查到端口正在被占用
    srv.clean_ports([port])                         # 确定能正确杀死该段口

    time.sleep(1)
    assert srv.from_port_get_pid(port) is None      # 确认端口已被释放
    p.wait(timeout=5)


# ---------- 2. 集成测试：真正启动 UE + AirSim ----------

def _wait_port(port, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        with socket.socket() as s:
            s.settimeout(1)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(2)
    return False


@pytest.fixture(scope="module")
def airsim_env():
    srv.clean_ports([API_PORT])
    cfg = srv.env_exec_path_dict[ENV]

    settings = dict(srv.AIRSIM_SETTINGS_JSON)
    settings["ApiServerPort"] = API_PORT
    # 只测相机/渲染时用 SimpleFlight，避免依赖 PX4 SITL
    settings["Vehicles"]["px4_drone"]["VehicleType"] = "SimpleFlight"

    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(settings, f); f.close()

    proc = subprocess.Popen(
        ["bash", cfg["bash_name"], f"-settings={f.name}", "-RenderOffScreen"],
        cwd=cfg["exec_path"],
        stdout=open("ue.log", "w"), stderr=subprocess.STDOUT,
    )
    try:
        assert _wait_port(API_PORT), "UE 未在超时内起来，查看 ue.log"
        yield proc
    finally:
        proc.terminate()
        proc.wait(timeout=30)
        srv.clean_ports([API_PORT])
        os.unlink(f.name)


@pytest.fixture(scope="module")
def client(airsim_env):
    c = airsim.MultirotorClient(port=API_PORT)
    c.confirmConnection()
    return c

def test_images(client):
    """ 测试RGB-D图像的解析度 """
    rs = client.simGetImages([
        airsim.ImageRequest("front_left", airsim.ImageType.Scene, False, False),
        airsim.ImageRequest("front_left", airsim.ImageType.DepthPlanar, True),
        airsim.ImageRequest("front_center", airsim.ImageType.Scene, False, False),
        airsim.ImageRequest("front_right", airsim.ImageType.Scene, False, False)
    ])
    
    rgb, depth, rgb_c, rgb_r = rs
    assert (rgb.width, rgb.height) == (depth.width, depth.height) == (rgb_c.width, rgb_c.height) == (848, 480)

    d = airsim.get_pfm_array(depth)
    assert np.isfinite(d).all()
    assert 0 < d.mean() < 1000

def test_imu(client):
    imu = client.getImuData()
    assert imu.linear_acceleration is not None

def test_takeoff(client):
    client.enableApiControl(True)
    client.armDisarm(True)
    client.takeoffAsync().join()
    z = client.getMultirotorState().kinematics_estimated.position.z_val
    assert z < -0.5                            # NED，向上为负
    # print(f"takeoff z={z:.2f}")