#include "gamepad.h"
#include <fcntl.h>
#include <unistd.h>
#include <linux/joystick.h>
#include <iostream>
#include <cstring>
#include <iomanip>
#include <cmath>
#include <algorithm>

const float MAX_SPEED = 0.5f;     // 最大线速度 (m/s)，可根据需要调整
const float DEADZONE = 0.05f;

Gamepad::Gamepad(const std::string& device_path)
    : fd_(-1), device_path_(device_path) {}

Gamepad::~Gamepad() {
    if (fd_ >= 0) close(fd_);
}

bool Gamepad::open() {
    fd_ = ::open(device_path_.c_str(), O_RDONLY | O_NONBLOCK);
    if (fd_ < 0) {
        std::cerr << "无法打开设备 " << device_path_ << std::endl;
        return false;
    }

    char name[128];
    if (ioctl(fd_, JSIOCGNAME(sizeof(name)), name) < 0)
        strcpy(name, "Unknown");
    std::cout << "手柄已打开: " << name << std::endl;

    __u8 axes, buttons;
    if (ioctl(fd_, JSIOCGAXES, &axes) < 0) axes = 0;
    if (ioctl(fd_, JSIOCGBUTTONS, &buttons) < 0) buttons = 0;
    axes_.resize(axes, 0.0f);
    buttons_.resize(buttons, 0);

    std::cout << "  轴数量: " << (int)axes << ", 按键数量: " << (int)buttons << std::endl;
    return true;
}

void Gamepad::update() {
    if (fd_ < 0) return;

    struct js_event ev;
    while (read(fd_, &ev, sizeof(ev)) == sizeof(ev)) {
        ev.type &= ~JS_EVENT_INIT;
        if (ev.type == JS_EVENT_AXIS) {
            if (ev.number < axes_.size()) {
                axes_[ev.number] = ev.value / 32768.0f; // 归一化到 -1..1
            }
        } else if (ev.type == JS_EVENT_BUTTON) {
            if (ev.number < buttons_.size()) {
                buttons_[ev.number] = ev.value;
            }
        }
    }
}

float Gamepad::getAxis(int index) const {
    if (index >= 0 && index < (int)axes_.size())
        return axes_[index];
    return 0.0f;
}

int Gamepad::getButton(int index) const {
    if (index >= 0 && index < (int)buttons_.size())
        return buttons_[index];
    return 0;
}

void Gamepad::printStatus() const {
    for (size_t i = 0; i < axes_.size(); ++i) {
        std::cout << "A" << i << ":" << std::fixed << std::setprecision(4) << axes_[i] << " ";
    }
    for (size_t i = 0; i < buttons_.size(); ++i) {
        std::cout << "B" << i << ":" << buttons_[i] << " ";
    }
}

// 内部处理函数（与测试程序中一致）
void Gamepad::processStick(float x, float y, float& angle_deg, float& magnitude, float& speed_mps) {
    if (std::abs(x) < DEADZONE) x = 0.0f;
    if (std::abs(y) < DEADZONE) y = 0.0f;

    magnitude = std::hypot(x, y);
    if (magnitude > 1.0f) magnitude = 1.0f;
    if (magnitude < DEADZONE) magnitude = 0.0f;

    // 角度映射：右0°，上-90°，下90°，左180°
    float angle_rad = (magnitude == 0.0f) ? 0.0f : std::atan2(-y, x);
    angle_deg = angle_rad * 180.0f / M_PI;

    speed_mps = MAX_SPEED * magnitude;
}

void Gamepad::getLeftStick(float& angle_deg, float& magnitude, float& speed_mps) {
    float x = getAxis(0);
    float y = getAxis(1);
    processStick(x, y, angle_deg, magnitude, speed_mps);
}

void Gamepad::getRightStick(float& angle_deg, float& magnitude, float& speed_mps) {
    float x = getAxis(2);
    float y = getAxis(3);
    processStick(x, y, angle_deg, magnitude, speed_mps);
}

float Gamepad::getLeftAngle() {
    float angle, mag, speed;
    getLeftStick(angle, mag, speed);
    return angle;
}

float Gamepad::getLeftMagnitude() {
    float angle, mag, speed;
    getLeftStick(angle, mag, speed);
    return mag;
}

float Gamepad::getLeftSpeed() {
    float angle, mag, speed;
    getLeftStick(angle, mag, speed);
    return speed;
}