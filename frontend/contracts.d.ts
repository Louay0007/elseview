// Request/error subset reviewed against backend/contracts/openapi.json.
// String bounds, UUID syntax, strict integers and cross-field rules remain
// server validated. This file does not claim unconstrained response schemas.
export type UUID = string;
export interface ErrorDetail { code: string; message: string }
export interface ErrorEnvelope { error: ErrorDetail; request_id: string }
export interface RegisterBody {
  email: string;
  password: string;
  display_name?: string;
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