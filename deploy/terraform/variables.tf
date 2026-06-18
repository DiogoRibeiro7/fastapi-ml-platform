variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "eu-west-1"
}

variable "project" {
  description = "Name prefix for created resources."
  type        = string
  default     = "fraud-api"
}

variable "app_env" {
  description = "Application environment profile (staging or production)."
  type        = string
  default     = "production"
}

variable "vpc_id" {
  description = "Existing VPC to deploy into."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnets for the load balancer."
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnets for the ECS tasks and database."
  type        = list(string)
}

variable "container_image" {
  description = "Full image reference (e.g. <account>.dkr.ecr.<region>.amazonaws.com/fraud-api:<sha>)."
  type        = string
}

variable "container_port" {
  description = "Port the app listens on."
  type        = number
  default     = 8000
}

variable "desired_count" {
  description = "Number of ECS tasks. Use 1 when relying on the in-process scheduler."
  type        = number
  default     = 1
}

variable "task_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Fargate task memory (MiB)."
  type        = number
  default     = 1024
}

variable "db_username" {
  description = "RDS master username."
  type        = string
  default     = "fraud"
}

variable "db_password" {
  description = "RDS master password."
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "Database name."
  type        = string
  default     = "fraud"
}

variable "api_key" {
  description = "Service-to-service API key."
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "Secret used to sign JWT access tokens."
  type        = string
  sensitive   = true
}

variable "bootstrap_admin_password" {
  description = "Initial admin password seeded on startup."
  type        = string
  sensitive   = true
}
