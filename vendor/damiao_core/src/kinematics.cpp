// // kinematics.cpp
// #include "kinematics.h"
// #include <cmath>

// #ifndef M_PI
// #define M_PI 3.14159265358979323846
// #endif

// static float deg_to_rad(float deg) {
//     return deg * M_PI / 180.0f;
// }

// // 角度映射（处理倒车）
// static float map_angle_to_forward(float angle_deg, int& forward_flag) {
//     if (angle_deg > 90 && angle_deg <= 180) {
//         forward_flag = -1;
//         return angle_deg - 180;
//     } else if (angle_deg >= -180 && angle_deg < -90) {
//         forward_flag = -1;
//         return angle_deg + 180;
//     } else {
//         forward_flag = 1;
//         return angle_deg;
//     }
// }

// // 最短路径优化
// static float arc_decide(float target_angle, float current_angle) {
//     float d = target_angle - current_angle;
//     if (d > M_PI) d -= 2.0f * M_PI;
//     if (d < -M_PI) d += 2.0f * M_PI;
//     return current_angle + d;
// }

// KinematicsOutput compute_kinematics(float half_wheelbase, float half_track, float wheel_radius,
//                                     float raw_speed, float raw_angle_deg,
//                                     const float current_angles[4]) {
//     // 角度映射，确定前进标志
//     int forward_flag = 1;
//     float mapped_deg = map_angle_to_forward(raw_angle_deg, forward_flag);
//     float slant_rad = deg_to_rad(mapped_deg);
    
//     // 整车速度指令（车体系）
//     float vx_cmd = raw_speed * cos(slant_rad);
//     float vy_cmd = raw_speed * sin(slant_rad);
//     float w_cmd = 0.0f;   // 斜向运动无自转
    
//     // 轮子坐标（顺序：右后,左后,左前,右前）
//     float rx[4] = {-half_wheelbase, -half_wheelbase,  half_wheelbase,  half_wheelbase};
//     float ry[4] = {-half_track,      half_track,      half_track,     -half_track};
    
//     KinematicsOutput out;
//     for (int i = 0; i < 4; i++) {
//         // 轮心速度（车体系）
//         float vx_wheel = vx_cmd - w_cmd * ry[i];
//         float vy_wheel = vy_cmd + w_cmd * rx[i];
//         float linear_speed = sqrtf(vx_wheel * vx_wheel + vy_wheel * vy_wheel);
//         float yaw_wheel = atan2f(vy_wheel, vx_wheel);
        
//         // 轮速 (rad/s) = 线速度 / 轮半径，再乘以前进标志（倒车时速度取反）
//         out.wheel_speed[i] = (linear_speed / wheel_radius) * forward_flag;
        
//         // 转角优化（最短路径）
//         out.wheel_angle_rad[i] = arc_decide(yaw_wheel, current_angles[i]);
//     }
//     return out;
// }

#include "kinematics.h"
#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static float deg_to_rad(float deg) {
    return deg * M_PI / 180.0f;
}

static float map_angle_to_forward(float angle_deg, int& forward_flag) {
    if (angle_deg > 90 && angle_deg <= 180) {
        forward_flag = -1;
        return angle_deg - 180;
    } else if (angle_deg >= -180 && angle_deg < -90) {
        forward_flag = -1;
        return angle_deg + 180;
    } else {
        forward_flag = 1;
        return angle_deg;
    }
}

static float arc_decide(float target_angle, float current_angle) {
    float d = target_angle - current_angle;
    if (d > M_PI) d -= 2.0f * M_PI;
    if (d < -M_PI) d += 2.0f * M_PI;
    return current_angle + d;
}

KinematicsOutput compute_kinematics(float half_wheelbase, float half_track, float wheel_radius,
                                    float raw_speed, float raw_angle_deg,
                                    const float current_angles[4]) {
    int forward_flag = 1;
    float mapped_deg = map_angle_to_forward(raw_angle_deg, forward_flag);
    float slant_rad = deg_to_rad(mapped_deg);
    float vx_cmd = raw_speed * cos(slant_rad);
    float vy_cmd = raw_speed * sin(slant_rad);
    if (forward_flag == -1) {
        vx_cmd = -vx_cmd;
        vy_cmd = -vy_cmd;
    }
    float w_cmd = 0.0f;

    float rx[4] = {-half_wheelbase, -half_wheelbase,  half_wheelbase,  half_wheelbase};
    float ry[4] = {-half_track,      half_track,      half_track,     -half_track};

    KinematicsOutput out;
    for (int i = 0; i < 4; ++i) {
        float vx_wheel = vx_cmd - w_cmd * ry[i];
        float vy_wheel = vy_cmd + w_cmd * rx[i];
        float linear_speed = sqrtf(vx_wheel * vx_wheel + vy_wheel * vy_wheel);
        float yaw_wheel = atan2f(vy_wheel, vx_wheel);
        out.wheel_speed[i] = (linear_speed / wheel_radius) * forward_flag;
        out.wheel_angle_rad[i] = arc_decide(yaw_wheel, current_angles[i]);
    }
    return out;
}