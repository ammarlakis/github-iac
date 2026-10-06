resource "github_repository" "create" {
  for_each = local.repositories

  name = each.key

  visibility  = each.value.visibility
  description = try(each.value.description, "")
  topics      = try(each.value.topics, [])
  has_issues  = try(each.value.has_issues, true)

  has_projects           = try(each.value.has_projects, null)
  has_wiki               = try(each.value.has_wiki, null)
  allow_auto_merge       = try(each.value.allow_auto_merge, null)
  allow_merge_commit     = try(each.value.allow_merge_commit, null)
  allow_rebase_merge     = try(each.value.allow_rebase_merge, null)
  allow_squash_merge     = try(each.value.allow_squash_merge, null)
  delete_branch_on_merge = try(each.value.delete_branch_on_merge, null)
  homepage_url           = try(each.value.homepage_url, null)

  fork         = try(each.value.fork, null) != null
  source_owner = try(each.value.fork.owner, null)
  source_repo  = try(each.value.fork.repository, null)

  dynamic "pages" {
    for_each = try(each.value.pages, false) != false ? [each.value.pages] : []
    content {
      build_type = try(pages.value.build_type, "workflow")
      cname      = try(pages.value.cname, "")

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
