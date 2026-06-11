export interface ParameterLimit {
  default: number;
  min: number;
  max: number;
  step: number;
}

export interface ChargerParameters {
  charger_id: string;
  enabled: boolean;
  target_voltage_v: number;
  current_limit_a: number;
  charge_current_limit_a: number;
  discharge_current_limit_a: number;
  requested_power_kw: number;
  charge_current_setpoint_a: number;
  active_power_setpoint_W: number;
  max_allowed_power_kw: number;
  applied_power_kw: number;
  voltage_min_v: number;
  voltage_max_v: number;
  parameter_limits: Record<string, ParameterLimit>;
  cc_cv_profile: Record<string, unknown>;
  updated_at: string;
}

export interface ChargerParametersUpdate {
  enabled?: boolean;
  target_voltage_v?: number;
  current_limit_a?: number;
  charge_current_limit_a?: number;
  discharge_current_limit_a?: number;
  requested_power_kw?: number;
  charge_current_setpoint_a?: number;
  active_power_setpoint_W?: number;
  voltage_min_v?: number;
  voltage_max_v?: number;
  cc_cv_profile?: Record<string, unknown>;
}
