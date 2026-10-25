# ADR 0002: Closed built-in tool registry

Status: accepted for the first milestone.

The model can suggest steps, but the runtime accepts only validated tool IDs and arguments. The initial tools are deterministic text transforms and a transactional, approval-gated local memory write. No shell, arbitrary file access, or network tool exists. This limits demonstration scope but makes authorization and restart behavior verifiable before introducing broader capabilities.

