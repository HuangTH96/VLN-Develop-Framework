# 按层次划分各个方法

层	                                    |           内容
算法	                                | action_point、projector
翻译（依赖 AirSim 约定，不依赖 API）	    | action_space
通用机制	                             | 队列线程、wait_for_queue_empty、主循环逻辑
平台（真正调用 AirSim）	                   | _execute_action、起飞降落、capture_airsim_image、读相机信息
胶水	                                 | process_spatial_command、controller 持有 projector 和 action_space