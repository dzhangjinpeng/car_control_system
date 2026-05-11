#include "protocol/damiao.h"

#include <memory>
#include <string>
#include <vector>

namespace {

thread_local std::string g_last_error;

void set_error(const std::string& message) {
    g_last_error = message;
}

struct BridgeContext {
    std::vector<damiao::DmActData> init_data;
    std::shared_ptr<damiao::Motor_Control> control;
};

std::shared_ptr<damiao::Motor> get_motor(BridgeContext* ctx, uint16_t motor_id) {
    if (!ctx || !ctx->control) {
        return nullptr;
    }
    return ctx->control->getMotor(motor_id);
}

}  // namespace

extern "C" {

void* dm_bridge_open(const char* serial, uint32_t nom_baud, uint32_t dat_baud) {
    try {
        if (serial == nullptr || serial[0] == '\0') {
            set_error("serial number is empty");
            return nullptr;
        }

        auto* ctx = new BridgeContext();
        const uint16_t motor_ids[] = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08};
        const uint16_t master_ids[] = {0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18};

        for (int i = 0; i < 4; ++i) {
            damiao::DmActData item;
            item.motorType = damiao::DMH6215;
            item.mode = damiao::VEL_MODE;
            item.can_id = motor_ids[i];
            item.mst_id = master_ids[i];
            ctx->init_data.push_back(item);
        }
        for (int i = 4; i < 8; ++i) {
            damiao::DmActData item;
            item.motorType = damiao::DM8009;
            item.mode = damiao::POS_VEL_MODE;
            item.can_id = motor_ids[i];
            item.mst_id = master_ids[i];
            ctx->init_data.push_back(item);
        }

        ctx->control = std::make_shared<damiao::Motor_Control>(
            nom_baud, dat_baud, std::string(serial), &ctx->init_data);

        for (int i = 4; i < 8; ++i) {
            auto motor = ctx->control->getMotor(motor_ids[i]);
            if (motor) {
                ctx->control->switchControlMode(*motor, damiao::POS_VEL);
            }
        }

        for (int i = 0; i < 8; ++i) {
            uint16_t offset = (motor_ids[i] <= 0x04) ? damiao::VEL_MODE : damiao::POS_VEL_MODE;
            ctx->control->control_cmd(motor_ids[i] + offset, 0xFC);
        }

        set_error("");
        return ctx;
    } catch (const std::exception& e) {
        set_error(e.what());
        return nullptr;
    } catch (...) {
        set_error("unknown exception");
        return nullptr;
    }
}

void dm_bridge_close(void* handle) {
    auto* ctx = reinterpret_cast<BridgeContext*>(handle);
    delete ctx;
}

int dm_bridge_enable_all(void* handle) {
    try {
        auto* ctx = reinterpret_cast<BridgeContext*>(handle);
        if (!ctx || !ctx->control) {
            set_error("bridge is not open");
            return -1;
        }
        ctx->control->enable_all();
        return 0;
    } catch (const std::exception& e) {
        set_error(e.what());
        return -1;
    }
}

int dm_bridge_disable_all(void* handle) {
    try {
        auto* ctx = reinterpret_cast<BridgeContext*>(handle);
        if (!ctx || !ctx->control) {
            set_error("bridge is not open");
            return -1;
        }
        ctx->control->disable_all();
        return 0;
    } catch (const std::exception& e) {
        set_error(e.what());
        return -1;
    }
}

int dm_bridge_control_vel(void* handle, uint16_t motor_id, float velocity) {
    try {
        auto* ctx = reinterpret_cast<BridgeContext*>(handle);
        auto motor = get_motor(ctx, motor_id);
        if (!motor) {
            set_error("motor not found");
            return -1;
        }
        ctx->control->control_vel(*motor, velocity);
        return 0;
    } catch (const std::exception& e) {
        set_error(e.what());
        return -1;
    }
}

int dm_bridge_control_pos_vel(void* handle, uint16_t motor_id, float position, float velocity) {
    try {
        auto* ctx = reinterpret_cast<BridgeContext*>(handle);
        auto motor = get_motor(ctx, motor_id);
        if (!motor) {
            set_error("motor not found");
            return -1;
        }
        ctx->control->control_pos_vel(*motor, position, velocity);
        return 0;
    } catch (const std::exception& e) {
        set_error(e.what());
        return -1;
    }
}

int dm_bridge_switch_pos_vel(void* handle, uint16_t motor_id) {
    try {
        auto* ctx = reinterpret_cast<BridgeContext*>(handle);
        auto motor = get_motor(ctx, motor_id);
        if (!motor) {
            set_error("motor not found");
            return -1;
        }
        ctx->control->switchControlMode(*motor, damiao::POS_VEL);
        return 0;
    } catch (const std::exception& e) {
        set_error(e.what());
        return -1;
    }
}

int dm_bridge_set_zero_position(void* handle, uint16_t motor_id) {
    try {
        auto* ctx = reinterpret_cast<BridgeContext*>(handle);
        auto motor = get_motor(ctx, motor_id);
        if (!motor) {
            set_error("motor not found");
            return -1;
        }
        ctx->control->set_zero_position(*motor);
        return 0;
    } catch (const std::exception& e) {
        set_error(e.what());
        return -1;
    }
}

int dm_bridge_save_motor_param(void* handle, uint16_t motor_id) {
    try {
        auto* ctx = reinterpret_cast<BridgeContext*>(handle);
        auto motor = get_motor(ctx, motor_id);
        if (!motor) {
            set_error("motor not found");
            return -1;
        }
        ctx->control->save_motor_param(*motor);
        return 0;
    } catch (const std::exception& e) {
        set_error(e.what());
        return -1;
    }
}

int dm_bridge_get_position(void* handle, uint16_t motor_id, float* out_value) {
    auto* ctx = reinterpret_cast<BridgeContext*>(handle);
    auto motor = get_motor(ctx, motor_id);
    if (!motor || out_value == nullptr) {
        set_error("motor not found or output pointer is null");
        return -1;
    }
    *out_value = motor->Get_Position();
    return 0;
}

int dm_bridge_get_velocity(void* handle, uint16_t motor_id, float* out_value) {
    auto* ctx = reinterpret_cast<BridgeContext*>(handle);
    auto motor = get_motor(ctx, motor_id);
    if (!motor || out_value == nullptr) {
        set_error("motor not found or output pointer is null");
        return -1;
    }
    *out_value = motor->Get_Velocity();
    return 0;
}

int dm_bridge_get_tau(void* handle, uint16_t motor_id, float* out_value) {
    auto* ctx = reinterpret_cast<BridgeContext*>(handle);
    auto motor = get_motor(ctx, motor_id);
    if (!motor || out_value == nullptr) {
        set_error("motor not found or output pointer is null");
        return -1;
    }
    *out_value = motor->Get_tau();
    return 0;
}

const char* dm_bridge_last_error() {
    return g_last_error.c_str();
}

}  // extern "C"
