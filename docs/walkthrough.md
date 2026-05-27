# Reviewer Walkthrough: NimbusKart Cost Janitor

This walkthrough guides you through running and verifying the Cost Janitor project. The project is designed to run against a local AWS endpoint simulated by LocalStack, so no real AWS credentials or charges will be incurred.

## Prerequisites

Ensure you have the following installed on your machine:
- Docker
- Python 3.10+
- pip
- Terraform (v1.5.0+)

## Step-by-Step Execution

### 1. Spin up LocalStack
LocalStack simulates the AWS cloud APIs (specifically EC2 and S3) locally on port 4566. Start it in the background using Docker:
```bash
docker run --rm -d -p 4566:4566 --name localstack localstack/localstack
```

### 2. Install Python Tools & Dependencies
Install the required dependencies, including `terraform-local` (a wrapper around Terraform that automatically redirects commands to LocalStack's endpoint):
```bash
pip install terraform-local boto3
```

### 3. Deploy Local Infrastructure
Navigate to the `terraform/` directory, initialize, and deploy the infrastructure configuration:
```bash
cd terraform
tflocal init
tflocal apply -auto-approve
cd ..
```
This provisions:
- A custom VPC with 2 public subnets
- 2 running EC2 instances
- 1 unattached EBS volume (our intentional orphan resource)
- 1 S3 bucket with lifecycle and versioning configured

### 4. Run the Cost Janitor
Execute the janitor script pointing to the LocalStack endpoint:
```bash
AWS_ENDPOINT_URL=http://localhost:4566 python janitor/janitor.py --dry-run
```
Since the janitor will identify the unattached EBS volume as an orphan resource, it will write `report.json` and `summary.md` and exit with status code `1` (indicating orphans were found, which is expected in dry-run mode).

### 5. Inspect the Results
Verify the generated files:
```bash
cat report.json
cat summary.md
```
`report.json` contains detailed resource attributes, while `summary.md` provides a clean Markdown breakdown suitable for pipeline notifications or PR comments.

### 6. Clean Up Local Resources
Stop the LocalStack container:
```bash
docker stop localstack
```
