locals {
  repositories = {
    for file in fileset("${path.module}/../data/repositories", "*.yaml") :
    trimsuffix(file, ".yaml") => yamldecode(file("${path.module}/../data/repositories/${file}"))
  }
}
