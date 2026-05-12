import type { DriverInput } from '../types';

interface InputDisplayProps {
  input: DriverInput;
}

function formatAxis(value: number) {
  return value.toFixed(2);
}

function formatButton(pressed: boolean) {
  return pressed ? '按下' : '释放';
}

function InputDisplay({ input }: InputDisplayProps) {
  return (
    <div className="input-grid">
      <section className="mini-panel">
        <h4>摇杆状态</h4>
        <div className="kv-grid">
          <span>左摇杆 X</span>
          <strong>{formatAxis(input.left_x)}</strong>
          <span>左摇杆 Y</span>
          <strong>{formatAxis(input.left_y)}</strong>
          <span>右摇杆 X</span>
          <strong>{formatAxis(input.right_x)}</strong>
          <span>右摇杆 Y</span>
          <strong>{formatAxis(input.right_y)}</strong>
        </div>
      </section>
      <section className="mini-panel">
        <h4>按键状态</h4>
        <div className="kv-grid">
          <span>模式切换</span>
          <strong>{formatButton(input.mode_button)}</strong>
          <span>转向锁定</span>
          <strong>{formatButton(input.steering_lock_button)}</strong>
          <span>前进/倒车</span>
          <strong>{formatButton(input.drive_direction_button)}</strong>
          <span>急停</span>
          <strong className={input.emergency_stop_button ? 'danger-text' : undefined}>
            {formatButton(input.emergency_stop_button)}
          </strong>
        </div>
      </section>
    </div>
  );
}

export default InputDisplay;
