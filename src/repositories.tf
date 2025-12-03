resource "github_repository" "create" {
  for_each = local.repositories

  name = each.key

  visibility  = each.value.visibility
  description = try(each.value.description, "")
  topics      = try(each.value.topics, [])
  has_issues  = true

  dynamic "pages" {
    for_each = try(each.value.pages, false) != false ? [each.value.pages] : []
    content {
      build_type = try(pages.value.build_type, "workflow")

      source {
        branch = try(pages.value.branch, "master")
        path   = try(pages.value.path, "/")
      }
    }
  }
}

resource "github_repository_collaborators" "users" {
  for_each = local.repositories

  repository = each.key

  dynamic "user" {
    for_each = try(each.value.permissions.users.pull, [])
    content {
      permission = "pull"
      username   = user.value
    }
  }

  dynamic "user" {
    for_each = try(each.value.permissions.users.push, [])
    content {
      permission = "push"
      username   = user.value
    }
  }

  dynamic "user" {
    for_each = try(each.value.permissions.users.maintain, [])
    content {
      permission = "maintain"
      username   = user.value
    }
  }

  dynamic "user" {
    for_each = try(each.value.permissions.users.triage, [])
    content {
      permission = "triage"
      username   = user.value
    }
  }

  dynamic "user" {
    for_each = try(each.value.permissions.users.admin, [])
    content {
      permission = "admin"
      username   = user.value
    }
  }

  dynamic "team" {
    for_each = try(each.value.permissions.teams.pull, [])
    content {
      permission = "pull"
      team_id    = team.value
    }
  }

  dynamic "team" {
    for_each = try(each.value.permissions.teams.push, [])
    content {
      permission = "push"
      team_id    = team.value
    }
  }

  dynamic "team" {
    for_each = try(each.value.permissions.teams.maintain, [])
    content {
      permission = "maintain"
      team_id    = team.value
    }
  }

  dynamic "team" {
    for_each = try(each.value.permissions.teams.triage, [])
    content {
      permission = "triage"
      team_id    = team.value
    }
  }

  dynamic "team" {
    for_each = try(each.value.permissions.teams.admin, [])
    content {
      permission = "admin"
      team_id    = team.value
    }
  }

  depends_on = [github_repository.create]
}
