#ifndef KINEMATICS_H
#define KINEMATICS_H

struct KinematicsOutput {
    float wheel_speed[4];     // 顺序：右后,左后,左前,右前
    float wheel_angle_rad[4]; // 顺序同上
};

KinematicsOutput compute_kinematics(float half_wheelbase, float half_track, float wheel_radius,
                                    float raw_speed, float raw_angle_deg,
                                    const float current_angles[4]);

#endif