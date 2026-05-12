import type { MotorItem } from '../types';

interface MotorTableProps {
  motors: MotorItem[];
}

function errorClassName(motor: MotorItem) {
  const threshold = motor.unit === 'deg' ? 3 : 0.15;
  return Math.abs(motor.error) > threshold ? 'error-cell warn' : 'error-cell ok';
}

function MotorTable({ motors }: MotorTableProps) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>位置</th>
            <th>ID</th>
            <th>目标</th>
            <th>实测</th>
            <th>误差</th>
            <th>单位</th>
          </tr>
        </thead>
        <tbody>
          {motors.map((motor) => (
            <tr key={`${motor.role}-${motor.motor_id}`}>
              <td>{motor.role}</td>
              <td>{motor.motor_id}</td>
              <td className="mono">{motor.target.toFixed(3)}</td>
              <td className="mono">{motor.actual.toFixed(3)}</td>
              <td className={errorClassName(motor)}>{motor.error.toFixed(3)}</td>
              <td>{motor.unit}</td>
            </tr>
          ))}
          {motors.length === 0 && (
            <tr>
              <td colSpan={6} className="empty-row">
                暂无电机回显数据
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default MotorTable;
