## Overview

NimbusKart Cost Hygiene & Automation is a DevOps tool designed to identify and clean up orphaned or wasteful cloud resources. It leverages Terraform and LocalStack for local environment provisioning, utilizes a Python script to scan and detect cost leaks (stopped EC2 instances, unattached EBS volumes, unassociated EIPs, and missing tags), and runs inside a GitHub Actions pipeline to validate infrastructure PRs.

## How to run locally

```bash
git clone <repo>
cd <repo>
docker run --rm -d -p 4566:4566 --name localstack localstack/localstack
pip install terraform-local boto3
cd terraform && tflocal init && tflocal apply -auto-approve
cd ..
AWS_ENDPOINT_URL=http://localhost:4566 python janitor/janitor.py --dry-run
cat report.json
```

## Architecture

```text
GitHub PR → Actions → LocalStack → Terraform → EC2/EBS/S3
          → janitor.py → report.json + summary.md → PR comment
```

## Decisions & deviations

- SSH 0.0.0.0/0: spec requires it; flagged as unsafe; restrict in prod
- No KMS encryption on S3: LocalStack limitation; add in production
- Dummy AMI ID: LocalStack doesn't validate; use data source in prod
- Static cost constants: real impl would call AWS Pricing API
- No multi-account: out of scope for this assignment
- No Terraform remote state: LocalStack-only constraint
- Inline S3 Lifecycle Rule: Standalone aws_s3_bucket_lifecycle_configuration resource times out in LocalStack 3.8.0 S3 mock backend; resolved by using legacy inline lifecycle_rule block.

## Trade-offs

If given one more week to work on this project, we would prioritize:
1. Multi-account scanning via IAM assume-role chaining.
2. Integrating a concrete GCP provider for multi-cloud scanning.
3. Adding interactive notifications via Slack or PagerDuty.
4. Integrating the live AWS Pricing API rather than using static constants.
5. Implementing CloudTrail-based event history checking to determine stopped instance age.

## AI usage disclosure

- **AI tools used:** Gemini was used for code generation, test design structure, and workflow composition.
- **AI correction:** The AI initially set `--dry-run` action to `store_true` with `default=False`, which contradicted the specifications requiring a `default=True`. This was identified during code review and manual specification comparison.
- **Manual section:** The multi-cloud adapter design pattern and abstract base class specification were written manually without AI assistance:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Set

class CloudProvider(ABC):
    @abstractmethod
    def list_unattached_disks(self) -> List[Dict]:
        pass

    @abstractmethod
    def list_idle_compute(self, days: int) -> List[Dict]:
        pass

    @abstractmethod
    def list_unused_ips(self) -> List[Dict]:
        pass

    @abstractmethod
    def list_missing_tags(self, required: Set[str]) -> List[Dict]:
        pass

    @abstractmethod
    def delete_resource(self, resource_id: str) -> bool:
        pass
```


