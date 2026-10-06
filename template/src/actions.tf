resource "github_actions_repository_permissions" "policy" {
  for_each = { for name, repo in local.repositories : name => repo.actions if try(repo.actions, null) != null }

  repository           = github_repository.create[each.key].name
  enabled              = try(each.value.enabled, true)
  allowed_actions      = try(each.value.allowed_actions, null)
  sha_pinning_required = try(each.value.sha_pinning_required, null)

  dynamic "allowed_actions_config" {
    for_each = try(each.value.allowed_actions, null) == "selected" ? [each.value.allowed_actions_config] : []
    content {
      github_owned_allowed = allowed_actions_config.value.github_owned_allowed
      verified_allowed     = try(allowed_actions_config.value.verified_allowed, false)
      patterns_allowed     = try(allowed_actions_config.value.patterns_allowed, [])
    }
  }
}

resource "github_workflow_repository_permissions" "policy" {
  for_each = {
    for name, repo in local.repositories : name => repo.actions
    if try(repo.actions.default_workflow_permissions, null) != null || try(repo.actions.can_approve_pull_request_reviews, null) != null
  }

  repository                       = github_repository.create[each.key].name
  default_workflow_permissions     = try(each.value.default_workflow_permissions, null)
  can_approve_pull_request_reviews = try(each.value.can_approve_pull_request_reviews, null)
  depends_on                       = [github_actions_repository_permissions.policy]
}
