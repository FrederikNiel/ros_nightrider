#!/bin/bash

###################################
###        ROS 2 base setup      ###
###################################

source /opt/ros/humble/setup.bash

###################################
###      Point to OpenEB HAL     ###
###################################

unset LD_PRELOAD

export OPENEB_INSTALL=/opt/openeb
export PATH=${OPENEB_INSTALL}/bin:${PATH}
export MV_HAL_PLUGIN_PATH=${OPENEB_INSTALL}/lib/metavision/hal/plugins
export LD_LIBRARY_PATH=${OPENEB_INSTALL}/lib:/usr/local/lib:${LD_LIBRARY_PATH}
export CMAKE_PREFIX_PATH=${OPENEB_INSTALL}:${CMAKE_PREFIX_PATH}

###################################
###       Source workspace       ###
###################################

if [ -f /home/workspace/install/setup.bash ]; then
    source /home/workspace/install/setup.bash
fi

###################################
###      Interactive shell setup  ###
###################################

grep -qxF 'source /opt/ros/humble/setup.bash' ~/.bashrc || \
    echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc

grep -qxF 'export OPENEB_INSTALL=/opt/openeb' ~/.bashrc || \
    echo 'export OPENEB_INSTALL=/opt/openeb' >> ~/.bashrc

grep -qxF 'export PATH=${OPENEB_INSTALL}/bin:${PATH}' ~/.bashrc || \
    echo 'export PATH=${OPENEB_INSTALL}/bin:${PATH}' >> ~/.bashrc

grep -qxF 'export MV_HAL_PLUGIN_PATH=${OPENEB_INSTALL}/lib/metavision/hal/plugins' ~/.bashrc || \
    echo 'export MV_HAL_PLUGIN_PATH=${OPENEB_INSTALL}/lib/metavision/hal/plugins' >> ~/.bashrc

grep -qxF 'export LD_LIBRARY_PATH=${OPENEB_INSTALL}/lib:/usr/local/lib:${LD_LIBRARY_PATH}' ~/.bashrc || \
    echo 'export LD_LIBRARY_PATH=${OPENEB_INSTALL}/lib:/usr/local/lib:${LD_LIBRARY_PATH}' >> ~/.bashrc

grep -qxF 'if [ -f /home/workspace/install/setup.bash ]; then source /home/workspace/install/setup.bash; fi' ~/.bashrc || \
    echo 'if [ -f /home/workspace/install/setup.bash ]; then source /home/workspace/install/setup.bash; fi' >> ~/.bashrc

grep -qxF "alias bringup_teleop='cd /home/workspace && colcon build && source install/setup.bash && ros2 launch gorm_bringup bringup_teleop.launch.py'" ~/.bashrc || \
    echo "alias bringup_teleop='cd /home/workspace && colcon build && source install/setup.bash && ros2 launch gorm_bringup bringup_teleop.launch.py'" >> ~/.bashrc

grep -qxF "alias build='cd /home/workspace && colcon build && source install/setup.bash'" ~/.bashrc || \
    echo "alias build='cd /home/workspace && colcon build && source install/setup.bash'" >> ~/.bashrc

grep -qxF "alias camera='ros2 launch gorm_sensors cameras.launch.py'" ~/.bashrc || \
    echo "alias camera='ros2 launch gorm_sensors cameras.launch.py'" >> ~/.bashrc

grep -qxF "alias renderer='ros2 launch event_camera_renderer renderer.launch.py camera:=event_camera'" ~/.bashrc || \
    echo "alias renderer='ros2 launch event_camera_renderer renderer.launch.py camera:=event_camera'" >> ~/.bashrc

grep -qxF "alias gps='ros2 launch ublox_gps ublox_gps_node_zedf9p-launch.py'" ~/.bashrc || \
    echo "alias gps='ros2 launch ublox_gps ublox_gps_node_zedf9p-launch.py'" >> ~/.bashrc

grep -qxF "alias bringup='ros2 launch gorm_bringup bringup.launch.py'" ~/.bashrc || \
    echo "alias bringup='ros2 launch gorm_bringup bringup.launch.py'" >> ~/.bashrc

grep -qxF "alias controller='ros2 launch controller controller.launch.py'" ~/.bashrc || \
    echo "alias controller='ros2 launch controller controller.launch.py'" >> ~/.bashrc

###################################
###          Autostart           ###
###################################

if [[ "$1" == "autostart" ]]; then
    echo "Running the teleop controller in autostart mode..."
    cd /home/workspace
    colcon build
    source install/setup.bash
    ros2 launch gorm_bringup bringup_teleop.launch.py
else
    exec bash
fi
