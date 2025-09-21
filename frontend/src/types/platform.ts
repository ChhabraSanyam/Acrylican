export interface PlatformInfo {
  platform: string;
  name: string;
  description: string;
  integration_type: string;
  auth_method: string;
  enabled: boolean;
  connected: boolean;
  connection_status?: string;
  platform_username?: string;
  connected_at?: string;
  last_validated_at?: string;
  expires_at?: string;
  validation_error?: string;
  setup_required: boolean;
  setup_instructions?: string;
}

export interface ConnectionTestResult {
  platform: string;
  success: boolean;
  message: string;
  details?: Record<string, any>;
}

export interface SetupWizardStep {
  step: number;
  title: string;
  description: string;
  action: 'oauth' | 'form' | 'info' | 'test';
  required_fields: SetupField[];
}

export interface SetupField {
  name: string;
  label: string;
  type: string;
  placeholder?: string;
  help?: string;
}

export interface SetupWizardInfo {
  platform: string;
  platform_name: string;
  integration_type: string;
  auth_method: string;
  steps: SetupWizardStep[];
}

export interface PlatformPreferences {
  platform: string;
  enabled: boolean;
  auto_post: boolean;
  default_template?: string;
  posting_schedule?: Record<string, any>;
}