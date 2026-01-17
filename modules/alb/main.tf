module "alb" {
  source  = "terraform-aws-modules/alb/aws"
  version = "~> 9.0"

  name = var.alb_name

  load_balancer_type = "application"
  internal           = var.internal

  enable_deletion_protection = false


  vpc_id  = var.vpc_id
  subnets = var.public_subnets

  # Security Group
  create_security_group = true
  security_group_name = "${var.alb_name}-sg"
  security_group_tags = merge(
    var.tags,
    {
      Name = "${var.alb_name}-sg"
    }
  )
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

  tags = merge(
    var.tags,
    {
      Name = var.alb_name
    }
  )

  target_groups = {
    default-target-group = {
      name                  = var.target_group_name # Use explicit name if provided
      name_prefix           = var.target_group_name == null ? "h1" : null
      protocol              = "HTTP"
      port                  = var.target_group_port
      target_type           = "ip"
      create_attachment     = false
      deregistration_delay  = 30
      
      health_check = {
        enabled             = true
        interval            = 15
        path                = "/"
        port                = "traffic-port"
        healthy_threshold   = 2
        unhealthy_threshold = 2
        timeout             = 5
        protocol            = "HTTP"
        matcher             = "200-299"
      }
    }
  }
}
