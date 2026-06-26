# Dockerfile for ros_event_camera
# Single-stage image containing all dependencies and application setup

ARG L4T_VERSION_MAJOR
ARG L4T_VERSION_MINOR
ARG L4T_VERSION_PATCH
ARG L4T_VERSION=${L4T_VERSION_MAJOR}.${L4T_VERSION_MINOR}.${L4T_VERSION_PATCH}
ARG WORKSPACE_DIR=/home/workspace
ARG WORKSPACE_SRC=/home/workspace/src
ARG OPENEB_SRC=/opt/openeb-src
ARG OPENEB_BUILD=/opt/openeb-src/build
ARG OPENEB_INSTALL=/opt/openeb

#####################################
###         BASE STAGE            ###
#####################################

FROM nvcr.io/nvidia/l4t-jetpack:r${L4T_VERSION} AS base

# Re-declare build args after FROM so they are available at runtime during build steps
ARG DEBIAN_FRONTEND=noninteractive
ARG WORKSPACE_DIR
ARG WORKSPACE_SRC
ARG OPENEB_SRC
ARG OPENEB_BUILD
ARG OPENEB_INSTALL

ENV WORKSPACE_DIR=${WORKSPACE_DIR}
ENV WORKSPACE_SRC=${WORKSPACE_SRC}

###################################
###         Install ROS         ###
###################################

# Update system locale
RUN apt-get update && apt-get install -y locales && \
    locale-gen en_US en_US.UTF-8 && \
    update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

ENV LANG=en_US.UTF-8
ENV PYTHONIOENCODING=utf-8

# Set Python3 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# 
RUN apt install software-properties-common -y && \
    add-apt-repository universe
    
# Add the ROS 2 GPG key with apt.
RUN apt update && apt install curl -y && \
    curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

# Add the repository to your sources list.
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" > /etc/apt/sources.list.d/ros2.list

RUN apt update && apt upgrade -y && \
    apt install ros-humble-desktop python3-rosdep -y

# Install pip3 
RUN apt-get update && apt-get install -y python3-pip

#####################################
###         Install PyTorch       ###
#####################################



# Fix NumPy compatibility issue with PyTorch - install specific compatible version
#RUN pip3 install --force-reinstall 
#numpy==1.24.3

###################################
###     Install       ###
###################################

#ARG cuSPARSELt_URL=https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/arm64/cuda-keyring_1.1-1_all.deb
#ARG cuSPARSELt_DEB=cuda-keyring_1.1-1_all.deb

#RUN wget --quiet --show-progress --progress=bar:force:noscroll --no-check-certificate ${cuSPARSELt_URL} -O ${cuSPARSELt_DEB} && \
#    dpkg -i cuda-keyring_1.1-1_all.deb && \
#    rm ${cuSPARSELt_DEB} && \
#    apt-get update && \
#    apt-get -y install libcusparselt0 libcusparselt-dev

#####################################
###     Open EB Visialisation     ###
#####################################

# (placeholder for OpenEB install steps)
# Install USB and camera dependencies
RUN apt-get install -y libopencv-dev && \
    apt-get install -y libboost-all-dev && \
    apt-get install -y libusb-1.0-0-dev && \
    apt-get install -y libprotobuf-dev && \
    apt-get install -y protobuf-compiler

# Install visiualization dependencies
RUN apt-get install -y libhdf5-dev && \
    apt-get install -y hdf5-tools && \
    apt-get install -y libglew-dev && \
    apt-get install -y libglfw3-dev && \
    apt-get install -y libcanberra-gtk3-module && \
    apt-get install -y ffmpeg

# USB/debugging utilities
RUN apt-get update && apt-get install -y usbutils psmisc

###################################
###   Open EB pip packages      ###
###################################

# Fix NumPy compatibility issue with OpenCV and OpenEB
RUN pip3 install --force-reinstall numpy==1.23.4

RUN pip3 install opencv-python==4.5.5.64 && \
    pip3 install sk-video==1.1.10 && \
    pip3 install fire==0.4.0 && \
    pip3 install h5py==3.7.0 && \
    pip3 install pandas && \
    pip3 install scipy

#Install pybind 11 for OpenEB

RUN apt-get update && apt-get install -y unzip

RUN wget https://github.com/pybind/pybind11/archive/v2.13.6.zip && \
    unzip v2.13.6.zip && \
    cd pybind11-2.13.6 && \
    mkdir build && \
    cd build && \
    cmake .. -DPYBIND11_TEST=OFF && \
    cmake --build . && \
    cmake --build . --target install

#####################################
###           Open EB             ###
#####################################

# Install and build OpenEB
RUN apt-get update && apt-get install -y git

RUN git clone https://github.com/atdtu/openeb.git ${OPENEB_SRC} && \
    mkdir -p ${OPENEB_BUILD} && \
    cd ${OPENEB_BUILD} && \
    cmake ${OPENEB_SRC} -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
    -DCOMPILE_PYTHON3_BINDINGS=ON -DCMAKE_INSTALL_PREFIX=${OPENEB_INSTALL} && \
    cmake --build . --config Release -j$(nproc) && \
    cmake --build . --target install

ENV LD_LIBRARY_PATH=${OPENEB_INSTALL}/lib:/usr/local/lib:${LD_LIBRARY_PATH}
ENV HDF5_PLUGIN_PATH=/usr/local/hdf5/lib/plugin:${HDF5_PLUGIN_PATH}
ENV PYTHONPATH=${OPENEB_BUILD}/py3:${OPENEB_SRC}/sdk/modules/core/python/pypkg:${OPENEB_SRC}/sdk/modules/base/python/pypkg:${OPENEB_SRC}/sdk/modules/ui/python/pypkg:${OPENEB_SRC}/utils/python:${PYTHONPATH}

# Register OpenEB libraries with ldconfig so the dynamic linker finds them
RUN echo "${OPENEB_INSTALL}/lib" > /etc/ld.so.conf.d/openeb.conf && ldconfig

###################################
###      Point to OpenEB HAL     ###
###################################

# Make ROS/metavision_driver use the OpenEB install that was built in this image.
# This is required for IDS/uEye EVS cameras because the HAL plugin is installed
# under /opt/openeb, not /usr/lib/ids/...
ENV MV_HAL_PLUGIN_PATH=${OPENEB_INSTALL}/lib/metavision/hal/plugins
ENV LD_LIBRARY_PATH=${OPENEB_INSTALL}/lib:/usr/local/lib:${LD_LIBRARY_PATH}
ENV CMAKE_PREFIX_PATH=${OPENEB_INSTALL}:${CMAKE_PREFIX_PATH}

# Register OpenEB libraries with the dynamic linker
RUN echo "${OPENEB_INSTALL}/lib" > /etc/ld.so.conf.d/openeb.conf && ldconfig

# Optional sanity check during build: fail early if IDS HAL plugin is missing
RUN test -f ${OPENEB_INSTALL}/lib/metavision/hal/plugins/libueye_evs_hal_plugin.so

###################################
###       ROS Event Camera      ###
###################################

# Install ROS build tools and dependencies needed by metavision_driver
RUN apt-get update && apt-get install -y \
    git \
    python3-colcon-common-extensions \
    python3-rosdep \
    ros-humble-ament-cmake \
    ros-humble-ament-cmake-clang-format \
    ros-humble-ament-cmake-copyright \
    ros-humble-ament-cmake-cppcheck \
    ros-humble-ament-cmake-lint-cmake \
    ros-humble-ament-cmake-pep257 \
    ros-humble-ament-cmake-uncrustify \
    ros-humble-ament-cmake-xmllint \
    ros-humble-event-camera-msgs \
    && rm -rf /var/lib/apt/lists/*

# Build ROS event-camera packages from source
RUN mkdir -p ${WORKSPACE_DIR}/src && \
    cd ${WORKSPACE_DIR}/src && \
    git clone --branch master --single-branch \
      https://github.com/ros-event-camera/metavision_driver.git && \
    git clone --branch master --single-branch \
      https://github.com/ros-event-camera/event_camera_renderer.git && \
    sed -i 's/const int qsize = 1000;/const int qsize = 1;/' \
      event_camera_renderer/src/renderer.cpp && \
    sed -i \
      's/const auto qosProf = rclcpp::SystemDefaultsQoS();/const auto qosProf = rclcpp::QoS(rclcpp::KeepLast(1)).best_effort().durability_volatile();/' \
      event_camera_renderer/src/renderer.cpp && \
    sed -i \
      's/const auto qosProf = rmw_qos_profile_default;/auto qosProf = rmw_qos_profile_sensor_data; qosProf.depth = 1;/' \
      event_camera_renderer/src/renderer.cpp

RUN /bin/bash -c "source /opt/ros/humble/setup.bash && \
    export LD_LIBRARY_PATH=${OPENEB_INSTALL}/lib:/usr/local/lib:\${LD_LIBRARY_PATH} && \
    export CMAKE_PREFIX_PATH=${OPENEB_INSTALL}:\${CMAKE_PREFIX_PATH} && \
    export MV_HAL_PLUGIN_PATH=${OPENEB_INSTALL}/lib/metavision/hal/plugins && \
    cd ${WORKSPACE_DIR} && \
    colcon build --symlink-install \
      --packages-select metavision_driver \
      --cmake-args \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_PREFIX_PATH=${OPENEB_INSTALL}"


###################################
###         pip packages        ###
###################################

# Install pip and Python packages
RUN apt-get update && apt-get install -y python3-pip && \
    pip3 install setuptools Cython wheel colcon-common-extensions canopen Jetson.GPIO && \
    pip3 install zenoh==0.4.0

RUN apt-get install busybox && apt-get install iproute2 -y && \
    apt-get install net-tools -y

#RUN pip3 install tritonclient[all]

#####################################
###         Install EXTRAS       ###
#####################################

RUN apt-get update && apt-get install -y ros-humble-rosbridge-server ros-humble-rmw-zenoh-cpp

    # xeyes

RUN apt-get update && apt-get install -y x11-apps

#Zenoh UDP
RUN apt-get update && apt-get install -y ros-humble-rmw-zenoh-cpp

    ### tmux -only 1 ssh session at a time.
RUN apt-get update && apt-get install -y tmux

# Clean up
RUN rm -rf /var/lib/apt/lists/*

###################################
###    Copy and Build Rover SW   ###
###################################

# Create workspace directory
RUN mkdir -p ${WORKSPACE_DIR}

# Copy the source code
COPY ./src ${WORKSPACE_SRC}

# Set working directory
WORKDIR ${WORKSPACE_DIR}

# Install dependencies for the rover software
RUN /bin/bash -c "apt-get update && \
    source /opt/ros/humble/setup.bash && \
    if [ -f ${ROS2_WRAPPER_FOLDER}/install/setup.bash ]; then \
        source ${ROS2_WRAPPER_FOLDER}/install/setup.bash; \
    fi && \
    rosdep init || true && \
    rosdep update && \
    rosdep install --from-paths src --ignore-src -r -y --rosdistro humble"

# Build the rover software
RUN /bin/bash -c "source /opt/ros/humble/setup.bash && \
    if [ -f ${ROS2_WRAPPER_FOLDER}/install/setup.bash ]; then \
        source ${ROS2_WRAPPER_FOLDER}/install/setup.bash; \
    fi && \
    colcon build --parallel-workers $(nproc) \
    --event-handlers console_direct+ \
    --cmake-args ' -DCMAKE_BUILD_TYPE=Release' \
    ' --no-warn-unused-cli'"

# Copy unified entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
