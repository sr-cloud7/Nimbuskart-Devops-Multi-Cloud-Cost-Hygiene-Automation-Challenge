terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region                      = var.region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  endpoints {
    ec2 = "http://localhost:4566"
    s3  = "http://localhost:4566"
  }
}

module "network" {
  source      = "./modules/network"
  project     = var.project
  environment = var.environment
  owner       = var.owner
}

resource "aws_instance" "web" {
  count         = 2
  ami           = "ami-00000000"
  instance_type = "t3.micro"
  subnet_id     = module.network.subnet_ids[count.index]
  tags = {
    Name        = "${var.project}-web-${count.index}"
    Project     = var.project
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "terraform"
    Tier        = "web"
  }
}

# INTENTIONAL ORPHAN — used by Cost Janitor as a known test case
resource "aws_ebs_volume" "orphan" {
  availability_zone = "us-east-1a"
  size              = 20
  type              = "gp3"
  tags = {
    Name        = "orphan-test-vol"
    Project     = var.project
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "terraform"
  }
  # No aws_volume_attachment — intentionally unattached
}

resource "aws_s3_bucket" "logs" {
  bucket = "${var.project}-${var.environment}-logs"
  tags = {
    Project     = var.project
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "terraform"
  }

  lifecycle_rule {
    id      = "expire-noncurrent"
    enabled = true

    noncurrent_version_expiration {
      days = 30
    }
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration { status = "Enabled" }
}
