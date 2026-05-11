#ifndef GAMEPAD_H
#define GAMEPAD_H

#include <string>
#include <vector>

class Gamepad {
public:
    Gamepad(const std::string& device_path = "/dev/input/js0");
    ~Gamepad();

    bool open();
    void update();                     // 读取最新状态
    float getAxis(int index) const;
    int getButton(int index) const;
    bool isOpen() const { return fd_ >= 0; }
    int getNumAxes() const { return axes_.size(); }
    int getNumButtons() const { return buttons_.size(); }
    void printStatus() const;

    // ========== 新增：摇杆处理（直接返回角度、速度等） ==========
    // 处理左摇杆 (A0, A1)，返回角度(度)、模长、线速度(m/s)
    void getLeftStick(float& angle_deg, float& magnitude, float& speed_mps);
    // 处理右摇杆 (A2, A3)
    void getRightStick(float& angle_deg, float& magnitude, float& speed_mps);
    // 仅获取左摇杆角度（最常用）
    float getLeftAngle();
    float getLeftMagnitude();
    float getLeftSpeed();

private:
    int fd_;
    std::vector<float> axes_;
    std::vector<int> buttons_;
    std::string device_path_;

    // 内部处理函数
    void processStick(float x, float y, float& angle_deg, float& magnitude, float& speed_mps);
};

#endif // GAMEPAD_H