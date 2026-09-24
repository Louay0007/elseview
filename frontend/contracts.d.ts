// Request/error and explicit auth success subset reviewed against
// backend/contracts/openapi.json. String bounds, UUID syntax, strict integers
// and cross-field rules remain server validated. Other untyped responses
// are not claimed as covered by this file.
export type UUID = string;
export interface ErrorDetail { code: string; message: string }
export interface ErrorEnvelope { error: ErrorDetail; request_id: string }
export interface AuthInstructionsResponse {
  message: 'If the request is eligible, instructions will be delivered.';
}
export interface AuthStatusResponse { status: 'ok' }
export interface AuthUserResponse { id: UUID; email: string; display_name: string }
export interface AuthLoginResponse {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
  csrf_token: string;
  family_id: UUID;
}
// The refresh capability is deliberately absent: it remains an HttpOnly cookie.
export interface RegisterBody {
  email: string;
  password: string;
  display_name?: string;
}
export type ExperienceCategory = 'software' | 'design' | 'research' | 'business' |
  'education' | 'healthcare' | 'finance' | 'manufacturing' | 'retail' | 'hospitality';
export type ExperienceLevel = 'beginner' | 'intermediate' | 'advanced';
export interface RecruitingExperience {
  version: '1';
  categories: Partial<Record<ExperienceCategory, ExperienceLevel>>;
}
// Fetch the targeting vocabulary; country/city syntax and 1–10 categories are
// server validated. These self-reported fields never grant qualifications.
export interface RecruitingTargetingAttributes {
  country_id?: string | null;
  city_id?: string | null;
  experience?: RecruitingExperience | null;
}
export interface PrivateTargetingConsent {
  version: '1';
  purpose: 'private_panel_targeting';
  confirmed: true;
  presented_digest: string;
  document_digest: string;
}
export interface StudyBody {
  title: string;
  retention_policy_id: UUID;
  ai_policy?: 'human_only' | 'assisted';
}
// Study creation requires Idempotency-Key in addition to bearer authorization.
export interface StudyCreateHeaders { 'Idempotency-Key': string }
export interface DecisionBody {
  command_key: UUID;
  verdict: 'accepted' | 'rejected';
  rationale: string;
  evidence?: string[];
}
export type Operation = 'study_helper' | 'themes' | 'failure_clustering' |
  'translation' | 'report_writer' | 'research_qa' | 'quality_suggestion' |
  'campaign_clarity' | 'sentiment_suggestion';
export interface RunBody {
  study_id: UUID;
  snapshot_id?: UUID | null;
  operation: Operation;
  instruction?: string;
  command_key: string;
  researcher_text_approved?: boolean;
}
export interface AnswerBody {
  version_id?: UUID | null;
  occurrence_id?: UUID | null;
  schema_version: 1;
  expected_revision: number;
  client_event_id: UUID;
  occurrence?: 0;
  status: 'responded' | 'skipped' | 'unable';
  value: Record<string, unknown> | null;
  reason_code?: 'technical' | 'accessibility' | 'declined' | 'other' | null;
}
export interface EventBody {
  block_key: string;
  event: Record<string, unknown>;
}
export interface BatchBody { version_id: UUID; events: EventBody[] }
export interface SubmitBody {
  version_id: UUID;
  occurrence_id?: UUID | null;
  expected_revision: number;
}
export interface CollectionHeaders { 'X-Session-Token': string }
// Report GET and AI status GET have path IDs and no request body.
export interface ReportPath { workspace_id: UUID; report_id: UUID }
export interface AIRunPath { workspace_id: UUID; run_id: UUID }