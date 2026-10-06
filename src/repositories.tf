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

  dynamic "security_and_analysis" {
    for_each = length(setintersection(toset(keys(try(each.value.security, {}))), toset(["advanced_security", "code_security", "secret_scanning", "secret_scanning_push_protection", "secret_scanning_ai_detection", "secret_scanning_non_provider_patterns"]))) > 0 ? [each.value.security] : []
    content {
      dynamic "advanced_security" {
        for_each = try(security_and_analysis.value.advanced_security, null) != null ? [security_and_analysis.value.advanced_security] : []
        content {
          status = advanced_security.value ? "enabled" : "disabled"
        }
      }
      dynamic "code_security" {
        for_each = try(security_and_analysis.value.code_security, null) != null ? [security_and_analysis.value.code_security] : []
        content {
          status = code_security.value ? "enabled" : "disabled"
        }
      }
      dynamic "secret_scanning" {
        for_each = try(security_and_analysis.value.secret_scanning, null) != null ? [security_and_analysis.value.secret_scanning] : []
        content {
          status = secret_scanning.value ? "enabled" : "disabled"
        }
      }
      dynamic "secret_scanning_push_protection" {
        for_each = try(security_and_analysis.value.secret_scanning_push_protection, null) != null ? [security_and_analysis.value.secret_scanning_push_protection] : []
        content {
          status = secret_scanning_push_protection.value ? "enabled" : "disabled"
        }
      }
      dynamic "secret_scanning_ai_detection" {
        for_each = try(security_and_analysis.value.secret_scanning_ai_detection, null) != null ? [security_and_analysis.value.secret_scanning_ai_detection] : []
        content {
          status = secret_scanning_ai_detection.value ? "enabled" : "disabled"
        }
      }
      dynamic "secret_scanning_non_provider_patterns" {
        for_each = try(security_and_analysis.value.secret_scanning_non_provider_patterns, null) != null ? [security_and_analysis.value.secret_scanning_non_provider_patterns] : []
        content {
          status = secret_scanning_non_provider_patterns.value ? "enabled" : "disabled"
        }
      }
    }
  }

  lifecycle {
    # Pages is managed by github_repository_pages.site.
    ignore_changes = [pages]

    precondition {
      condition     = each.value.visibility != "public" || try(each.value.security.advanced_security, null) == null
      error_message = "Advanced Security is always enabled for public repositories; omit security.advanced_security."
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
