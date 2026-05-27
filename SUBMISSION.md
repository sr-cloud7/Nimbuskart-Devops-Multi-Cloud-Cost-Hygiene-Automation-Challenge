# Submission — DevOps Engineer Assignment

**Candidate name:** Shivam
**Email:** imshivam7890@gmail.com
**Date submitted:** May 24, 2026
**Hours spent (approximate):** 9

## Deliverables checklist
- [x] Part A: Terraform code under /terraform applies cleanly on LocalStack
- [x] Part A: `terraform validate` and `terraform fmt -check` both pass
- [x] Part B: Janitor script runs in --dry-run mode and produces report.json
- [x] Part B: GitHub Actions workflow runs green on a fresh PR
- [x] Part B: --delete mode respects Protected=true tag
- [x] Part C: DESIGN.md is present and within 2 pages

## Walkthrough video
Link: [TO BE ADDED]
Length: max 5 minutes

## Sample report
Path: samples/report.example.json

## Known limitations
- Static cost estimates (not real AWS Pricing API)
- No multi-account scanning
- GCP/Azure providers not implemented (interface is ready)
- Stopped EC2 age detection relies on StateTransitionReason string parsing
- S3 lifecycle configuration defined inline in aws_s3_bucket to prevent LocalStack mock API timeout

## AI usage disclosure
- **AI tools used:** Gemini was used for code generation, test design structure, and workflow composition.
- **AI correction:** The AI initially set `--dry-run` action to `store_true` with `default=False`, which contradicted the specifications requiring a `default=True`. This was identified during code review and manual specification comparison.
- **Manual section:** The multi-cloud adapter design pattern and abstract base class specification were written manually without AI assistance.
