resource "github_repository_vulnerability_alerts" "policy" {
  for_each = { for name, repo in local.repositories : name => repo.security.vulnerability_alerts if try(repo.security.vulnerability_alerts, null) != null }

  repository = github_repository.create[each.key].name
  enabled    = each.value
}

resource "github_repository_dependabot_security_updates" "policy" {
  for_each = { for name, repo in local.repositories : name => repo.security.dependabot_security_updates if try(repo.security.dependabot_security_updates, null) != null }

  repository = github_repository.create[each.key].name
  enabled    = each.value
  depends_on = [github_repository_vulnerability_alerts.policy]

  lifecycle {
    precondition {
      condition     = !each.value || try(local.repositories[each.key].security.vulnerability_alerts, true)
      error_message = "Dependabot security updates require vulnerability alerts."
    }
  }
}
