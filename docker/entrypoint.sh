#!/bin/bash

# Source ROS 2 environment
source /opt/ros/humble/setup.bash

busybox devmem 0x0c303000 32 0x0000C400
busybox devmem 0x0c303008 32 0x0000C458
busybox devmem 0x0c303010 32 0x0000C400
busybox devmem 0x0c303018 32 0x0000C458

modprobe can
modprobe can_raw
modprobe mttcan

ip link set down can0
ip link set down can1

ip link set can0 type can bitrate 1000000 
ip link set can1 type can bitrate 1000000 

ip link set up can0
ip link set up can1

# Add ROS 2 sourcing to bashrc so it's available in all new shells
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "source /home/ros2_ws/install/setup.bash" >> ~/.bashrc
echo "export PATH=/opt/openeb/bin:$PATH" >> ~/.bashrc
source ~/.bashrc
echo "alias bringup_teleop='cd /home/workspace && colcon build && source install/setup.bash && ros2 launch gorm_bringup bringup_teleop.launch.py'" >> ~/.bashrc
echo "alias build='cd /home/workspace && colcon build && source install/setup.bash'" >> ~/.bashrc
echo "alias camera='ros2 launch gorm_sensors cameras.launch.py'" >> ~/.bashrc
echo "alias gps='ros2 launch ublox_gps ublox_gps_node_zedf9p-launch.py'" >> ~/.bashrc
echo "alias bringup='ros2 launch gorm_bringup bringup.launch.py'" >> ~/.bashrc

if [[ $1 == "autostart" ]]
then
    # If the first argument is "autostart", run the controller launch file
    echo "Running the teleop controller in autostart mode..."
    
    # Source the workspace setup file
    #source /home/zed_ros2_ws/install/setup.bash
    
    # Build the workspace
    cd /home/workspace
    colcon build
    source install/setup.bash
    ros2 launch gorm_bringup bringup_teleop.launch.py

	bash

else
    alias controller="ros2 launch controller controller.launch.py"
    # Add ROS 2 sourcing to bashrc so it's available in all new shells
    echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
	bash
fi

