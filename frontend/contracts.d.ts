// Request/error and explicit auth, collection, history, report-index and delivery
// success subsets reviewed against
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
export interface LanguageAssessmentConsentGrant {
  id: UUID;
  document_version: string;
  created_at: string;
  withdrawn_at: string | null;
}
export interface LanguageAssessmentConsentPage {
  items: LanguageAssessmentConsentGrant[];
  next_offset: number | null;
}
export interface ParticipantHistoryPage<T> { items: T[]; next_offset: number | null }
export interface ParticipantHistoryWorkspace { workspace_id: UUID }
export interface ParticipantResponseHistory {
  session_id: UUID;
  version_id: UUID;
  occurrence_id: UUID | null;
  locale: string;
  submitted_at: string | null;
  review_state: 'pending' | 'accepted' | 'rejected' | 'disputed' | 'appealed' | 'erased';
  appeal_state: 'open' | 'upheld' | 'overturned' | null;
}
export interface ParticipantRewardHistory {
  id: UUID;
  amount_millimes: number;
  currency: 'TND';
  state: 'earned' | 'paid';
  created_at: string;
  settled_at: string | null;
  manual_record_only: true;
}
export interface ParticipantPaymentHistory {
  id: UUID;
  state: 'recorded' | 'failed' | 'reversed';
  created_at: string;
  manual_record_only: true;
}
export interface ParticipantAttendanceHistory {
  id: UUID;
  version_id: UUID;
  state: 'booked' | 'cancelled';
  attendance: 'unknown' | 'attended' | 'absent';
  attendance_at: string | null;
  starts_at: string;
  ends_at: string;
  timezone: string;
}
export interface NotificationPreferenceBody {
  reminders: boolean;
  email_reminders?: boolean | null; // Omitted/null preserves the existing email choice.
}
export interface NotificationPreferenceResponse { reminders: boolean; email_reminders: boolean }
export interface RecruitmentInvitationBody {
  source_kind: 'public' | 'private';
  source_id: UUID;
  expires_seconds?: number;
  delivery?: 'manual' | 'email'; // Defaults to manual; hashed-only contacts cannot receive email.
}
export type RecruitmentInvitationResponse = {
  invitation_id: UUID;
  candidate_id: UUID;
  expires_at: string;
} & (
  { delivery: 'manual'; invitation_token: string } |
  { delivery: 'queued'; invitation_token: null }
);
export interface InvitationDeliveryResponse { status: 'queued' }
export interface ReportIndexItem { id: UUID; revision: number; state: 'draft' | 'approved' | 'invalidated' }
export interface ReportIndexResponse { items: ReportIndexItem[]; has_more: boolean }
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
export type AIDepth = 'quick' | 'standard' | 'deep';
export interface AIEstimateBody {
  study_id: UUID;
  snapshot_id?: UUID | null;
  operation: Operation;
  instruction?: string;
  researcher_text_approved?: boolean;
  depth?: AIDepth; // Defaults to standard; all current profiles use one call.
}
export interface RunBody extends AIEstimateBody {
  command_key: string;
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
export interface SessionResponse {
  session_id: UUID;
  occurrence_id: UUID | null;
  locale: string; // Pinned to original consented participation; not selected at recovery.
  version_id: UUID;
  state: 'active' | 'submitted' | 'withdrawn' | 'erased';
  revision: number;
  saved: true;
  last_sequence: number;
  block: Record<string, unknown> | null;
  answers: Record<string, { revision: number; answer: Record<string, unknown> }>;
  complete: boolean;
  submitted_at: string | null;
}
export interface DiaryStartBody { capability: string }
export interface DiaryRecoverBody extends DiaryStartBody {
  expected_revision: number; // Listed session_revision; exact replay retains the same capability.
}
export interface DiaryOccurrence {
  id: UUID;
  base_session_id: UUID;
  ordinal: number;
  opens_at: string;
  due_at: string;
  grace_at: string;
  timezone: string;
  state: 'submitted' | 'early' | 'missed' | 'grace' | 'open';
  session_id: UUID | null;
  session_revision: number | null;
  late: boolean;
}
export interface PrepareExposureBody {
  protocol_version: 2;
  version_id: UUID;
  capability: string; // 43–128 base64url characters; memory-only, not a URL parameter.
}
export interface StartExposureBody extends PrepareExposureBody { attempt_id: UUID }
export interface ExposureAssetHeaders extends CollectionHeaders { 'X-Exposure-Token': string }
export interface ExportBody {
  format: 'json' | 'csv' | 'pdf' | 'xlsx';
  scope?: 'summary' | 'raw'; // Defaults to summary; raw requires separate server authorization.
}
export interface AuthCsrfHeaders { 'X-CSRF-Token': string }
// Report GET and AI status GET have path IDs and no request body.
export interface ReportPath { workspace_id: UUID; report_id: UUID }
export interface AIRunPath { workspace_id: UUID; run_id: UUID }