cmake_minimum_required(VERSION 3.16)
project(dm_bridge LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Threads REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBUSB REQUIRED libusb-1.0)

get_filename_component(REPO_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
set(BRIDGE_CORE_DIR "${REPO_ROOT}/vendor/damiao_core")

add_library(dm_bridge SHARED
    dm_bridge.cpp
    "${BRIDGE_CORE_DIR}/src/protocol/damiao.cpp"
    "${BRIDGE_CORE_DIR}/src/kinematics.cpp"
    "${BRIDGE_CORE_DIR}/src/gamepad.cpp"
)

target_include_directories(dm_bridge PRIVATE
    "${BRIDGE_CORE_DIR}/include"
    "${BRIDGE_CORE_DIR}/include/protocol"
    "${BRIDGE_CORE_DIR}/include/unit"
    ${LIBUSB_INCLUDE_DIRS}
)

target_link_libraries(dm_bridge PRIVATE
    Threads::Threads
    "${BRIDGE_CORE_DIR}/lib/libu2canfd.a"
    ${LIBUSB_LIBRARIES}
)
