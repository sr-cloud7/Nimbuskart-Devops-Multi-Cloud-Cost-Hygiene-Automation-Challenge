# Network module variables
variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "owner" {
  type = string
}

variable "ssh_cidr" {
  type    = string
  default = "0.0.0.0/0"
}
