data "jsonschema_validator" "defaults" {
  count    = fileexists("${path.module}/../data/defaults.yaml") ? 1 : 0
  document = "${path.module}/../data/defaults.yaml"
  schema   = "${path.module}/../schemas/repository-defaults.schema.json"
}

data "jsonschema_validator" "preset" {
  for_each = fileset("${path.module}/../data/presets", "*.yaml")
  document = "${path.module}/../data/presets/${each.key}"
  schema   = "${path.module}/../schemas/repository-preset.schema.json"
}

data "jsonschema_validator" "repository" {
  for_each = fileset("${path.module}/../data/repositories", "*.yaml")
  document = "${path.module}/../data/repositories/${each.key}"
  schema   = "${path.module}/../schemas/repository.schema.json"
}
