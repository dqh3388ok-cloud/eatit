import { createMachine } from "xstate";

export const interviewMachine = createMachine({
  id: "interview",
  initial: "idle",
  states: {
    idle: {
      on: {
        START: "recording",
      },
    },
    recording: {
      on: {
        STOP: "processing",
      },
    },
    processing: {
      on: {
        RESET: "idle",
      },
    },
  },
});
