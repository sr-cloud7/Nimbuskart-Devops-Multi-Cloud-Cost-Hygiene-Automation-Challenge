"""
NimbusKart Cost Janitor
Scans cloud environment for orphan resources and generates cost reports.
"""
import argparse
import datetime
import json
import os
import re
import sys
from typing import Any, Dict, List

import boto3

from constants import (
    DEFAULT_EBS_SIZE_GB,
    EBS_GP3_PER_GB_MONTH,
    EC2_HOURS_PER_MONTH,
    EC2_T3_MICRO_PER_HOUR,
    EIP_HOURS_PER_MONTH,
    EIP_IDLE_PER_HOUR,
    STOPPED_DAYS_THRESHOLD,
)

REQUIRED_TAGS = {"Project", "Environment", "Owner"}


def get_client(service: str, region: str) -> Any:
    endpoint = os.environ.get("AWS_ENDPOINT_URL")
    kwargs: Dict[str, Any] = {"region_name": region}
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.client(service, **kwargs)


def find_unattached_ebs(ec2: Any) -> List[Dict[str, Any]]:
    findings = []
    response = ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])
    for volume in response.get("Volumes", []):
        tags_list = volume.get("Tags", [])
        tags = {tag["Key"]: tag["Value"] for tag in tags_list}

        if tags.get("Protected", "").lower() == "true":
            continue

        create_time = volume["CreateTime"]
        now = datetime.datetime.now(datetime.timezone.utc)
        age_days = (now - create_time).days

        size_gb = volume.get("Size", DEFAULT_EBS_SIZE_GB)
        cost = size_gb * EBS_GP3_PER_GB_MONTH

        findings.append({
            "resource_id": volume["VolumeId"],
            "resource_type": "ebs_volume",
            "reason": "unattached",
            "age_days": age_days,
            "estimated_monthly_cost_usd": round(cost, 2),
            "tags": {k: tags.get(k) for k in REQUIRED_TAGS},
            "suggested_action": "delete",
            "safe_to_auto_delete": False
        })
    return findings


def find_stopped_ec2(ec2: Any, days_threshold: int) -> List[Dict[str, Any]]:
    findings = []
    response = ec2.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}])
    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            tags_list = instance.get("Tags", [])
            tags = {tag["Key"]: tag["Value"] for tag in tags_list}

            if tags.get("Protected", "").lower() == "true":
                continue

            reason = instance.get("StateTransitionReason", "")
            match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", reason)

            parsed_successfully = False
            age_days = 0
            if match:
                try:
                    stopped_dt = datetime.datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
                    now = datetime.datetime.now(datetime.timezone.utc)
                    age_days = (now - stopped_dt).days
                    parsed_successfully = True
                except Exception:
                    pass

            if parsed_successfully:
                if age_days < days_threshold:
                    continue
            else:
                age_days = 0

            cost = EC2_T3_MICRO_PER_HOUR * EC2_HOURS_PER_MONTH

            findings.append({
                "resource_id": instance["InstanceId"],
                "resource_type": "ec2_instance",
                "reason": f"stopped_{age_days}_days",
                "age_days": age_days,
                "estimated_monthly_cost_usd": round(cost, 2),
                "tags": {k: tags.get(k) for k in REQUIRED_TAGS},
                "suggested_action": "terminate",
                "safe_to_auto_delete": False
            })
    return findings


def find_unused_eips(ec2: Any) -> List[Dict[str, Any]]:
    findings = []
    response = ec2.describe_addresses()
    for address in response.get("Addresses", []):
        if "AssociationId" in address:
            continue

        tags_list = address.get("Tags", [])
        tags = {tag["Key"]: tag["Value"] for tag in tags_list}

        if tags.get("Protected", "").lower() == "true":
            continue

        cost = EIP_IDLE_PER_HOUR * EIP_HOURS_PER_MONTH

        findings.append({
            "resource_id": address.get("AllocationId", address.get("PublicIp")),
            "resource_type": "elastic_ip",
            "reason": "unassociated",
            "age_days": 0,
            "estimated_monthly_cost_usd": round(cost, 2),
            "tags": {k: tags.get(k) for k in REQUIRED_TAGS},
            "suggested_action": "release",
            "safe_to_auto_delete": True
        })
    return findings


def find_missing_tags(ec2: Any) -> List[Dict[str, Any]]:
    findings = []
    response = ec2.describe_instances()
    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            tags_list = instance.get("Tags", [])
            tags = {tag["Key"]: tag["Value"] for tag in tags_list}

            if tags.get("Protected", "").lower() == "true":
                continue

            missing = [t for t in REQUIRED_TAGS if t not in tags or not tags[t]]
            if not missing:
                continue

            findings.append({
                "resource_id": instance["InstanceId"],
                "resource_type": "ec2_instance",
                "reason": "missing_tags:" + ",".join(sorted(missing)),
                "age_days": 0,
                "estimated_monthly_cost_usd": 0.0,
                "tags": {k: tags.get(k) for k in REQUIRED_TAGS},
                "suggested_action": "add_tags",
                "safe_to_auto_delete": False
            })
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description="NimbusKart Cost Janitor")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Dry run mode")
    parser.add_argument("--delete", action="store_true", default=False, help="Delete orphans")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--days", type=int, default=STOPPED_DAYS_THRESHOLD, help="Stopped days threshold")

    args = parser.parse_args()

    ec2 = get_client("ec2", args.region)
    findings = []
    findings += find_unattached_ebs(ec2)
    findings += find_stopped_ec2(ec2, args.days)
    findings += find_unused_eips(ec2)
    findings += find_missing_tags(ec2)

    total_waste = sum(f["estimated_monthly_cost_usd"] for f in findings)
    report = {
        "scan_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "account_id": "000000000000",
        "region": args.region,
        "summary": {
            "total_orphans": len(findings),
            "estimated_monthly_waste_usd": round(total_waste, 2)
        },
        "findings": findings
    }

    with open("report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    with open("summary.md", "w") as f:
        f.write("# Cost Janitor Report\n\n")
        f.write(f"**Orphans found:** {len(findings)}\n\n")
        f.write(f"**Estimated monthly waste:** ${total_waste:.2f}\n\n")
        f.write("## Findings\n\n")
        for finding in findings:
            f.write(f"- `{finding['resource_id']}` ({finding['resource_type']}): "
                    f"{finding['reason']} — ${finding['estimated_monthly_cost_usd']:.2f}/mo\n")

    if args.delete:
        for finding in findings:
            if not finding["safe_to_auto_delete"]:
                continue
            if finding["tags"].get("Protected", "") == "true":
                continue
            rid = finding["resource_id"]
            rtype = finding["resource_type"]
            if rtype == "elastic_ip":
                ec2.release_address(AllocationId=rid)
            print(f"[DELETE] {rid}")

    if findings and not args.delete:
        print(f"[janitor] {len(findings)} orphan(s) found. See report.json for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
