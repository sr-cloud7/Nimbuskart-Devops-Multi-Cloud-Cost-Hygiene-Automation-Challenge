## Multi-cloud design

To support a multi-cloud strategy, NimbusKart Cost Janitor is designed with an extensible, provider-based architecture. We define a standard interface that each cloud provider must implement.

We define a `CloudProvider` abstract base class (ABC) with these methods:
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

The resulting folder structure is:
```text
janitor/
  providers/
    __init__.py
    base.py        # CloudProvider ABC
    aws.py         # AWSProvider(CloudProvider)
    gcp.py         # GCPProvider(CloudProvider) — stub
    azure.py       # AzureProvider(CloudProvider) — stub
```

Adding a new provider like GCP is simple: implement `GCPProvider` inheriting from `CloudProvider`, and register it in a central providers registry dictionary. The core execution engine is decoupled, requiring zero changes to the core janitor logic.

## IAM permissions

The NimbusKart Cost Janitor follows the principle of least privilege.

Below is the minimal IAM policy required for read-only scan mode:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVolumes",
        "ec2:DescribeInstances",
        "ec2:DescribeAddresses",
        "ec2:DescribeTags",
        "s3:ListAllMyBuckets",
        "s3:GetBucketTagging"
      ],
      "Resource": "*"
    }
  ]
}
```

For delete mode, the following actions are added: `ec2:DeleteVolume`, `ec2:ReleaseAddress`, and `ec2:TerminateInstances`. To protect critical resources, we scope these actions using an IAM Condition block so that resources tagged with `Protected=true` cannot be deleted:
```json
{
  "Effect": "Allow",
  "Action": [
    "ec2:DeleteVolume",
    "ec2:ReleaseAddress",
    "ec2:TerminateInstances"
  ],
  "Resource": "*",
  "Condition": {
    "StringNotEquals": {
      "ec2:ResourceTag/Protected": "true"
    }
  }
}
```

## Safety nets

Automated resource cleanup carries inherent risks. We address two primary failure modes:

### Failure mode 1 — Reboot race condition
An instance may temporarily report as stopped during an active OS reboot or maintenance window.
- **Guardrail:** Require `age_days >= 7` before flagging stopped instances.
- **Notification:** Send an SNS alert to the engineering team 24 hours before any automated deletion occurs.
- **Override:** An operator can apply a `Protected=true` tag to the resource at any point to exempt it.

### Failure mode 2 — Legitimate batch job
A scheduled batch workload may stop instances during off-peak times (e.g. overnight or on weekends).
- **Guardrail:** Require a `Schedule` tag containing the execution window.
- **Override:** If the tag is missing but the instance represents batch infrastructure, flag it for human review; never auto-delete.

## Observability

We track metrics to monitor cost efficiency and tool operation. Metrics are published using `boto3.client("cloudwatch").put_metric_data()` to the custom CloudWatch namespace `NimbusKart/CostJanitor`.

| Metric name | Source | Alert threshold |
|---|---|---|
| `orphans_found` | `janitor.py` | > 0 |
| `waste_usd` | `janitor.py` | > $50/month |
| `scan_duration_sec` | CloudWatch Logs | > 120s |
| `resources_deleted` | `janitor.py` | > 0 (notify always) |
| `scan_errors` | `janitor.py` | >= 1 |

## What I did not build

This current initial implementation is built to run locally and test against LocalStack. It does not include:
- Multi-account assume-role credentials chaining.
- Concrete GCP or Azure provider implementations (the interfaces are ready).
- Slack or PagerDuty alerting integration.
- Cost trend analysis over time.
- Orphan detection for RDS snapshots, Lambda functions, or ECS task definitions.

These items represent the highest-priority additions for the next phase.
