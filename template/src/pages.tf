resource "github_repository_pages" "site" {
  for_each = {
    for name, repo in local.repositories : name => repo.pages
    if try(repo.pages, null) != null && try(repo.pages.enabled, true)
  }

  repository = github_repository.create[each.key].name
  build_type = try(each.value.build_type, "workflow")
  cname      = try(each.value.cname, "")

  dynamic "source" {
    for_each = try(each.value.build_type, "workflow") == "legacy" ? [each.value] : []
    content {
      branch = try(source.value.branch, "master")
      path   = try(source.value.path, "/")
    }
  }
}
