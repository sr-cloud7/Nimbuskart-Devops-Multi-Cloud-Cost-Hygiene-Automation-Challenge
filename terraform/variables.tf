# Root Terraform variables
variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "nimbuskart"
}

variable "environment" {
  type    = string
  default = "staging"
}

variable "owner" {
  type    = string
  default = "devops-team"
}
