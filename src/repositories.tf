resource "github_repository" "create" {
  for_each = local.repositories

  name = each.key

  visibility  = each.value.visibility
  description = each.value.description
  topics      = each.value.topics
}
