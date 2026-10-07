locals {
  app_assignments = merge({}, [
    for repository, config in local.repositories : {
      for app in try(config.apps, []) : "${repository}/${app}" => {
        repository      = repository
        installation_id = local.apps[app].installation_id
      }
    }
  ]...)
}

resource "github_app_installation_repository" "app" {
  for_each = local.app_assignments

  installation_id = each.value.installation_id
  repository      = github_repository.create[each.value.repository].name
}
