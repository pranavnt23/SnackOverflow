/**
 * TypeScript domain and API schema types for Snack Overflow.
 * Exactly matches backend models and Pydantic schemas.
 */

export type UserRole = 'admin' | 'member';

export type SnackCategory = 'sweet' | 'savoury' | 'drink' | 'healthy-ish';

export type SnackStatus = 'stocked' | 'running_low' | 'gone';

export type ActivityAction = 'restocked' | 'consumed';

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Snack {
  id: number;
  name: string;
  category: SnackCategory;
  quantity: number;
  low_stock_threshold: number;
  status: SnackStatus;
  vote_count: number;
  has_voted: boolean;
  created_at: string;
  updated_at: string;
}

export interface SnackSummary {
  stocked: number;
  running_low: number;
  gone: number;
  total: number;
  snack_of_the_week: Snack | null;
}

export interface PaginatedSnacks {
  items: Snack[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SnackFilterParams {
  category?: SnackCategory;
  status?: SnackStatus;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface SnackCreatePayload {
  name: string;
  category: SnackCategory;
  quantity: number;
  low_stock_threshold: number;
}

export interface SnackUpdatePayload {
  name?: string;
  category?: SnackCategory;
  low_stock_threshold?: number;
}

export interface ConsumePayload {
  amount: number;
}

export interface RestockPayload {
  amount: number;
}

export interface VoteStatusResponse {
  snack_id: number;
  vote_count: number;
  has_voted: boolean;
}

export interface Activity {
  id: number;
  user_id: number | null;
  snack_id: number | null;
  snack_name: string;
  action: ActivityAction;
  amount: number;
  quantity_after: number;
  created_at: string;
}

export interface ValidationErrorDetail {
  field?: string;
  message: string;
  type?: string;
}

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: ValidationErrorDetail[];
  };
}
