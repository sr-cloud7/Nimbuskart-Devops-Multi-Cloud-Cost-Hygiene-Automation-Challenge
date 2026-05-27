import json
import os
import sys

# Manipulation at top so imports work regardless of working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Configure AWS dummy environment variables before boto3 import
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ.pop("AWS_ENDPOINT_URL", None)

import boto3
import pytest
from moto import mock_aws

from janitor import (
    find_missing_tags,
    find_stopped_ec2,
    find_unattached_ebs,
    find_unused_eips,
    main,
)


@mock_aws
def test_finds_unattached_ebs():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    volume = ec2.create_volume(
        AvailabilityZone="us-east-1a",
        Size=20,
        TagSpecifications=[
            {
                "ResourceType": "volume",
                "Tags": [
                    {"Key": "Project", "Value": "nimbuskart"},
                    {"Key": "Environment", "Value": "staging"},
                    {"Key": "Owner", "Value": "devops-team"},
                ]
            }
        ]
    )
    result = find_unattached_ebs(ec2)
    assert len(result) == 1
    assert result[0]["resource_type"] == "ebs_volume"
    assert result[0]["resource_id"] == volume["VolumeId"]
    assert result[0]["estimated_monthly_cost_usd"] == 1.60


@mock_aws
def test_protected_volume_skipped():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    ec2.create_volume(
        AvailabilityZone="us-east-1a",
        Size=20,
        TagSpecifications=[
            {
                "ResourceType": "volume",
                "Tags": [
                    {"Key": "Protected", "Value": "true"},
                    {"Key": "Project", "Value": "nimbuskart"},
                ]
            }
        ]
    )
    result = find_unattached_ebs(ec2)
    assert result == []


@mock_aws
def test_finds_unused_eip():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    addr = ec2.allocate_address(Domain="vpc")
    result = find_unused_eips(ec2)
    assert len(result) == 1
    assert result[0]["resource_type"] == "elastic_ip"
    assert result[0]["resource_id"] == addr.get("AllocationId") or result[0]["resource_id"] == addr.get("PublicIp")


@mock_aws
def test_missing_tags_detected():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    ec2.run_instances(
        ImageId="ami-12345678",
        MinCount=1,
        MaxCount=1,
        InstanceType="t3.micro"
    )
    result = find_missing_tags(ec2)
    assert len(result) >= 1
    assert "missing_tags" in result[0]["reason"]


@mock_aws
def test_report_schema_valid(monkeypatch):
    ec2 = boto3.client("ec2", region_name="us-east-1")
    ec2.create_volume(AvailabilityZone="us-east-1a", Size=20)

    monkeypatch.setattr(sys, "argv", ["janitor.py", "--dry-run"])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1

    assert os.path.exists("report.json")
    with open("report.json", "r") as f:
        report = json.load(f)

    assert "scan_timestamp" in report
    assert "account_id" in report
    assert "region" in report
    assert "summary" in report
    assert "findings" in report

    summary = report["summary"]
    assert "total_orphans" in summary
    assert "estimated_monthly_waste_usd" in summary

    assert len(report["findings"]) >= 1
    finding = report["findings"][0]

    required_finding_keys = [
        "resource_id",
        "resource_type",
        "reason",
        "age_days",
        "estimated_monthly_cost_usd",
        "tags",
        "suggested_action",
        "safe_to_auto_delete",
    ]
    for key in required_finding_keys:
        assert key in finding
