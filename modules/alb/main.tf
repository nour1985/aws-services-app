module "alb" {
  source  = "terraform-aws-modules/alb/aws"
  version = "~> 9.0"

  name = var.alb_name

  load_balancer_type = "application"
  internal           = var.internal


  vpc_id  = var.vpc_id
  subnets = var.public_subnets

  # Security Group
  create_security_group = true
  security_group_ingress_rules = {
    all_http = {
      from_port   = 80
      to_port     = 80
      ip_protocol = "tcp"
      description = "HTTP web traffic"
      cidr_ipv4   = "0.0.0.0/0"
    }
  }
  security_group_egress_rules = {
    all = {
      ip_protocol = "-1"
      cidr_ipv4   = "0.0.0.0/0"
    }
  }

  listeners = {
    http = {
      port     = 80
      protocol = "HTTP"

      forward = {
        target_group_key = "default-target-group"
      }
    }
  }

  target_groups = {
    default-target-group = {
      name_prefix      = "h1"
      protocol         = "HTTP"
      port             = 80
      target_type      = "ip"
      create_attachment = false
    }
  }
}
