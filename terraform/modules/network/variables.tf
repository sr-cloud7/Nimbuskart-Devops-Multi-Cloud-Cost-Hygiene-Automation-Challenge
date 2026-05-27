variable "vpc_cidr" { default = "10.20.0.0/16" }
variable "project" { type = string }
variable "environment" { type = string }
variable "owner" { type = string }
variable "ssh_cidr" { default = "0.0.0.0/0" }
