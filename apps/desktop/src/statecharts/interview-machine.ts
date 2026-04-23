import { assign, createMachine } from "xstate";

export type GeneratedQuestion = {
  turn_index: number;
  question: string;
  intent: string;
  expected_depth: "surface" | "tactical" | "strategic";
  followup_hint: string | null;
  should_end: boolean;
};

export type TurnAssessmentSummary = {
  turn_index: number;
  summary: string;
  strengths: string[];
  weaknesses: string[];
};

export type InterviewContext = {
  sessionId: string | null;
  currentTurnIndex: number;
  currentQuestion: GeneratedQuestion | null;
  draftAnswer: string;
  lastAssessment: TurnAssessmentSummary | null;
  error: string | null;
};

export type InterviewEvent =
  | { type: "CONNECT"; sessionId: string }
  | { type: "WS_OPEN" }
  | { type: "SERVER_QUESTION"; payload: GeneratedQuestion }
  | { type: "UPDATE_ANSWER"; value: string }
  | { type: "SUBMIT_ANSWER" }
  | { type: "SERVER_ASSESSED"; payload: TurnAssessmentSummary }
  | { type: "END_SESSION" }
  | { type: "WS_ERROR"; message: string };

/**
 * Lifecycle:
 *   idle -> connecting (WS opens, session.init goes out)
 *        -> ready      (waiting for first question from server)
 *        -> user_answering (question delivered, user typing)
 *        -> scoring    (turn.end sent, waiting for assessment)
 *        -> next_question (waiting for the next server.question.generated)
 *        -> ended      (user or server ends; the page navigates to /report)
 *
 * Events originate either from WS messages (SERVER_*, WS_OPEN) or from UI
 * handlers (CONNECT, UPDATE_ANSWER, SUBMIT_ANSWER, END_SESSION). The
 * machine holds no WS reference; the React component owns the socket and
 * translates events in both directions.
 */
export const interviewMachine = createMachine({
  id: "interview",
  types: {} as {
    context: InterviewContext;
    events: InterviewEvent;
  },
  initial: "idle",
  context: {
    sessionId: null,
    currentTurnIndex: 0,
    currentQuestion: null,
    draftAnswer: "",
    lastAssessment: null,
    error: null,
  },
  states: {
    idle: {
      on: {
        CONNECT: {
          target: "connecting",
          actions: assign({
            sessionId: ({ event }) => event.sessionId,
            error: null,
          }),
        },
      },
    },
    connecting: {
      on: {
        WS_OPEN: "ready",
        WS_ERROR: {
          target: "idle",
          actions: assign({ error: ({ event }) => event.message }),
        },
      },
    },
    ready: {
      on: {
        SERVER_QUESTION: {
          target: "user_answering",
          actions: assign({
            currentQuestion: ({ event }) => event.payload,
            currentTurnIndex: ({ event }) => event.payload.turn_index,
            draftAnswer: "",
          }),
        },
        END_SESSION: "ended",
        WS_ERROR: {
          actions: assign({ error: ({ event }) => event.message }),
        },
      },
    },
    user_answering: {
      on: {
        UPDATE_ANSWER: {
          actions: assign({ draftAnswer: ({ event }) => event.value }),
        },
        SUBMIT_ANSWER: {
          target: "scoring",
          guard: ({ context }) => context.draftAnswer.trim().length > 0,
        },
        END_SESSION: "ended",
      },
    },
    scoring: {
      on: {
        SERVER_ASSESSED: {
          target: "next_question",
          actions: assign({
            lastAssessment: ({ event }) => event.payload,
          }),
        },
        SERVER_QUESTION: {
          target: "user_answering",
          actions: assign({
            currentQuestion: ({ event }) => event.payload,
            currentTurnIndex: ({ event }) => event.payload.turn_index,
            draftAnswer: "",
          }),
        },
        END_SESSION: "ended",
        WS_ERROR: {
          target: "user_answering",
          actions: assign({ error: ({ event }) => event.message }),
        },
      },
    },
    next_question: {
      on: {
        SERVER_QUESTION: [
          {
            target: "ended",
            guard: ({ event }) => event.payload.should_end,
            actions: assign({
              currentQuestion: ({ event }) => event.payload,
            }),
          },
          {
            target: "user_answering",
            actions: assign({
              currentQuestion: ({ event }) => event.payload,
              currentTurnIndex: ({ event }) => event.payload.turn_index,
              draftAnswer: "",
            }),
          },
        ],
        END_SESSION: "ended",
        WS_ERROR: {
          actions: assign({ error: ({ event }) => event.message }),
        },
      },
    },
    ended: {
      type: "final",
    },
  },
});
