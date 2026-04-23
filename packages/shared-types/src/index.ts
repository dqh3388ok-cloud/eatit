export type HealthStatus = {
  status: "ok";
  version: string;
};

export type AppVersion = {
  version: string;
};

export type CandidateAssetStatus =
  | "draft"
  | "ready_for_parse"
  | "parse_in_progress"
  | "analysis_ready"
  | "parse_failed";

export type ParseResultStatus = "pending" | "succeeded" | "failed";

export type InterviewStyle =
  | "friendly_guided"
  | "standard_professional"
  | "high_pressure_followup";

export type InterviewDirection =
  | "role_match"
  | "project_deep_dive"
  | "behavioral_comprehensive";

export type InterviewSessionStatus =
  | "created"
  | "session_started"
  | "turn_recording"
  | "turn_transcribing"
  | "turn_evaluating"
  | "turn_compressing"
  | "next_question_ready"
  | "paused"
  | "ended"
  | "exited_early"
  | "report_generating"
  | "report_ready"
  | "failed";

export type InterviewReportStatus = "pending" | "generating" | "ready" | "failed";

export type FrameworkStage = {
  name: string;
  goal: string;
  question_budget: number;
};

export type DirectionFramework = {
  style: InterviewStyle;
  direction: InterviewDirection;
  duration_minutes: number;
  stages: FrameworkStage[];
  focus_points: string[];
  risk_points: string[];
};

export type CompressedTurnSummary = {
  turn_index: number;
  question_tag: string;
  candidate_claims: string[];
  metrics_mentioned: string[];
  strengths: string[];
  weaknesses: string[];
  followup_candidates: string[];
  toxicity_or_risk: string[];
};

export type NormalizedQuestion = {
  turn_index: number;
  stage_name: string;
  question_tag: string;
  question_text: string;
};

export type NormalizedAnswer = {
  turn_index: number;
  transcript_text: string;
  cleaned_sentences: string[];
  key_points: string[];
};

export type NormalizedUserAssessment = {
  turn_index: number;
  strengths: string[];
  weaknesses: string[];
  risks: string[];
  suggestions: string[];
  evidence: string[];
  score_optional?: number | null;
};

export type ReferenceAnswer = {
  checkpoints: string[];
  expected_project_familiarity: string;
  expected_confidence: string;
  answer_script: string;
};

export type JobRequirement = {
  title: string;
  detail: string;
};

export type CandidateHighlight = {
  title: string;
  detail: string;
};

export type CandidateRisk = {
  title: string;
  detail: string;
};

export type ProjectHook = {
  project_name: string;
  reason: string;
  focus_points: string[];
};

export type ParseResultPayload = {
  job_requirements: JobRequirement[];
  candidate_highlights: CandidateHighlight[];
  candidate_risks: CandidateRisk[];
  project_hooks: ProjectHook[];
  match_summary: string;
};

export type ParseResultPreview = {
  match_summary: string;
  candidate_risk_count: number;
  project_hook_count: number;
};

export type TimestampedEntity = {
  id: string;
  created_at: string;
  updated_at: string;
};

export type AssetUploadRequest = {
  asset_bundle_id?: string | null;
};

export type AssetUploadResponse = TimestampedEntity & {
  asset_bundle_id: string;
  status: CandidateAssetStatus;
  uploaded_kind: "resume" | "jd" | string;
};

export type CandidateAssetResponse = TimestampedEntity & {
  user_id: string;
  status: CandidateAssetStatus;
  resume_filename?: string | null;
  jd_filename?: string | null;
  parse_preview?: ParseResultPreview | null;
};

export type ParseRequestResponse = {
  asset_bundle_id: string;
  status: ParseResultStatus | string;
  payload: ParseResultPayload;
};

export type ParseResultResponse = TimestampedEntity & {
  candidate_asset_id: string;
  status: ParseResultStatus | string;
  payload: ParseResultPayload;
};

export type InterviewConfigRequest = {
  style: InterviewStyle;
  direction: InterviewDirection;
  duration_minutes: number;
};

export type InterviewConfigResponse = TimestampedEntity & {
  interview_session_id: string;
  style: InterviewStyle;
  direction: InterviewDirection;
  duration_minutes: number;
};

export type CreateSessionRequest = {
  asset_bundle_id: string;
  config: InterviewConfigRequest;
};

export type CreateSessionResponse = {
  session_id: string;
  status: InterviewSessionStatus;
  direction_framework: DirectionFramework;
};

export type SessionListRequest = {
  page?: number;
  page_size?: number;
  status?: InterviewSessionStatus;
};

export type SessionSummary = TimestampedEntity & {
  user_id: string;
  candidate_asset_id: string;
  status: InterviewSessionStatus;
  started_at?: string | null;
  ended_at?: string | null;
  turn_count: number;
  config_snapshot: Record<string, unknown>;
};

export type SessionDetailResponse = SessionSummary & {
  config?: InterviewConfigResponse | null;
  direction_framework?: DirectionFramework | null;
};

export type SessionListResponse = {
  items: SessionSummary[];
  page: number;
  page_size: number;
  total: number;
};

export type EndSessionResponse = {
  session_id: string;
  status: InterviewSessionStatus;
  ended_at: string;
};

export type RoundReview = {
  question: NormalizedQuestion;
  answer: NormalizedAnswer;
  assessment: NormalizedUserAssessment;
};

export type ReportVerdict = "strong" | "solid" | "mixed" | "weak";

export type ReportReason = {
  aspect: string;
  verdict: ReportVerdict;
  evidence_turn_index: number;
  quote: string;
};

export type InterviewReportPayload = {
  overall_summary: string;
  round_reviews: RoundReview[];
  strengths: string[];
  improvements: string[];
  next_actions: string[];
  pass_probability: number;
  reasons: ReportReason[];
};

export type TriggerReportRequest = {
  force_regenerate?: boolean;
};

export type TriggerReportResponse = {
  session_id: string;
  status: InterviewReportStatus;
  requested_at: string;
};

export type InterviewReportResponse = TimestampedEntity & {
  interview_session_id: string;
  status: InterviewReportStatus;
  requested_at?: string | null;
  generated_at?: string | null;
  payload: InterviewReportPayload;
};

export type ReportStatusResponse = {
  session_id: string;
  status: InterviewReportStatus;
  has_payload: boolean;
};

export type MetaReportStatus = "generating" | "ready" | "failed";

export type MetaReportVerdict = "weak" | "mixed" | "solid" | "strong";

export type RecurringWeakness = {
  aspect: string;
  occurrence_count: number;
  session_ids: string[];
  evidence_quotes: string[];
};

export type ImprovementSignal = {
  aspect: string;
  from_verdict: MetaReportVerdict;
  to_verdict: MetaReportVerdict;
  earlier_session_id: string;
  later_session_id: string;
};

export type PassProbabilityPoint = {
  session_id: string;
  session_created_at: string;
  pass_probability: number;
};

export type NextFocusArea = {
  aspect: string;
  reason: string;
  suggested_prep: string;
};

export type MetaReportPayload = {
  overall_trend_summary: string;
  recurring_weaknesses: RecurringWeakness[];
  improvement_signals: ImprovementSignal[];
  pass_probability_series: PassProbabilityPoint[];
  next_focus_areas: NextFocusArea[];
};

export type TriggerMetaReportRequest = {
  session_ids?: string[] | null;
};

export type TriggerMetaReportResponse = {
  id: string;
  task_id: string;
  status: MetaReportStatus;
  covered_session_ids: string[];
  created_at: string;
};

export type MetaReportFailurePayload = {
  detail: string;
};

export type MetaReportDetailResponse = {
  id: string;
  user_id: string;
  status: MetaReportStatus;
  covered_session_ids: string[];
  payload: MetaReportPayload | MetaReportFailurePayload | null;
  created_at: string;
  updated_at: string;
};

export type MetaReportListItem = {
  id: string;
  status: MetaReportStatus;
  covered_session_ids: string[];
  session_count: number;
  created_at: string;
};

export type MetaReportListResponse = {
  items: MetaReportListItem[];
  page: number;
  page_size: number;
  total: number;
};

export type ClientAudioChunkEvent = {
  event: "client.audio.chunk";
  content_type?: string | null;
};

export type LLMConfigPayload = {
  provider: string;
  api_key: string;
  model: string;
  base_url?: string | null;
};

export type ClientSessionInitEvent = {
  event: "client.session.init";
  config: LLMConfigPayload;
};

export type ClientTurnStartEvent = {
  event: "client.turn.start";
};

export type ClientTurnEndEvent = {
  event: "client.turn.end";
  turn_index: number;
  question: string;
  answer: string;
};

export type ClientSessionPauseEvent = {
  event: "client.session.pause";
};

export type ClientSessionResumeEvent = {
  event: "client.session.resume";
};

export type ClientSessionEndEvent = {
  event: "client.session.end";
};

export type ClientTextEvent =
  | ClientSessionInitEvent
  | ClientTurnStartEvent
  | ClientTurnEndEvent
  | ClientSessionPauseEvent
  | ClientSessionResumeEvent
  | ClientSessionEndEvent;

export type ClientEvent = ClientAudioChunkEvent | ClientTextEvent;

export type ServerTranscriptPartialEvent = {
  event: "server.transcript.partial";
  payload: {
    text: string;
  };
};

export type ServerTranscriptFinalizedEvent = {
  event: "server.transcript.finalized";
  payload: {
    text: string;
  };
};

export type ServerTurnAssessedEvent = {
  event: "server.turn.assessed";
  payload: {
    turn_index: number;
    summary: string;
    strengths: string[];
    weaknesses: string[];
  };
};

export type ServerTurnCompressedEvent = {
  event: "server.turn.compressed";
  payload: {
    summary: string;
    preserved_keywords: string[];
    open_threads: string[];
  };
};

export type ServerQuestionGeneratedEvent = {
  event: "server.question.generated";
  payload: {
    turn_index: number;
    question: string;
    intent: string;
    expected_depth: "surface" | "tactical" | "strategic";
    followup_hint: string | null;
    should_end: boolean;
  };
};

export type ServerReferenceReadyEvent = {
  event: "server.reference.ready";
  payload: {
    turn_index: number;
    answer_outline: string[];
    ideal_answer: string;
    key_evaluation_points: string[];
    common_pitfalls: string[];
  };
};

export type ServerSessionEndedEvent = {
  event: "server.session.ended";
  payload: {
    session_id: string;
    status: string;
  };
};

export type ServerErrorEvent = {
  event: "server.error";
  code: string;
  message: string;
  recoverable: boolean;
};

export type ServerEvent =
  | ServerTranscriptPartialEvent
  | ServerTranscriptFinalizedEvent
  | ServerTurnAssessedEvent
  | ServerTurnCompressedEvent
  | ServerQuestionGeneratedEvent
  | ServerReferenceReadyEvent
  | ServerSessionEndedEvent
  | ServerErrorEvent;
