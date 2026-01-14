resource "aws_resourcegroups_group" "this" {
  name = var.group_name

  resource_query {
    query = jsonencode({
      ResourceTypeFilters = ["AWS::AllSupported"]
      TagFilters = [
        {
          Key    = "Project"
          Values = [var.project_name]
        },
        {
          Key    = "Environment"
          Values = [var.environment_name]
        }
      ]
    })
  }

  tags = {
    Name = var.group_name
    Environment = var.environment_name
    Project = var.project_name
  }
}
