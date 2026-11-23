# Notes

## `server.py`
1. 配置仿真环境路径：`env_exec_path_dict`
2. 构建AirSim的 settings.json 文件：`AIRSIM_SETTINGS_JSON`
3. 围绕端口，管理运行UE环境的进程：`kill_pid`、`from_port_get_pid` 和 `clean_ports`
4. 构建仿真环境调度服务器**server**，用msgpackrpc对外提供接口，供 `client.py` 使用
5. EventHandler
