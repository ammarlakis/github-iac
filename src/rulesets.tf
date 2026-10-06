locals {
  repository_rulesets = merge({}, [
    for repository, repo in local.repositories : {
      for name, ruleset in try(repo.rulesets, {}) : "${repository}/${name}" => merge(ruleset, { repository = repository, name = name })
    }
  ]...)
}

resource "github_repository_ruleset" "policy" {
  for_each = local.repository_rulesets

  name        = each.value.name
  repository  = github_repository.create[each.value.repository].name
  target      = try(each.value.target, "branch")
  enforcement = try(each.value.enforcement, "active")

  conditions {
    ref_name {
      include = try(each.value.include, try(each.value.target, "branch") == "tag" ? ["~ALL"] : ["~DEFAULT_BRANCH"])
      exclude = try(each.value.exclude, [])
    }
  }

  dynamic "bypass_actors" {
    for_each = try(each.value.bypass_actors, [])
    content {
      actor_id    = try(bypass_actors.value.actor_id, null)
      actor_type  = bypass_actors.value.actor_type
      bypass_mode = bypass_actors.value.bypass_mode
    }
  }

  rules {
    creation                      = try(each.value.rules.creation, null)
    update                        = try(each.value.rules.update, null)
    deletion                      = try(each.value.rules.deletion, null)
    non_fast_forward              = try(each.value.rules.non_fast_forward, null)
    required_linear_history       = try(each.value.rules.required_linear_history, null)
    required_signatures           = try(each.value.rules.required_signatures, null)
    update_allows_fetch_and_merge = try(each.value.rules.update_allows_fetch_and_merge, null)

    dynamic "pull_request" {
      for_each = try(each.value.rules.pull_request, null) != null ? [each.value.rules.pull_request] : []
      content {
        dismiss_stale_reviews_on_push     = try(pull_request.value.dismiss_stale_reviews_on_push, null)
        require_code_owner_review         = try(pull_request.value.require_code_owner_review, null)
        require_last_push_approval        = try(pull_request.value.require_last_push_approval, null)
        required_review_thread_resolution = try(pull_request.value.required_review_thread_resolution, null)
        required_approving_review_count   = try(pull_request.value.required_approving_review_count, null)
        allowed_merge_methods             = try(pull_request.value.allowed_merge_methods, null)
      }
    }

    dynamic "merge_queue" {
      for_each = try(each.value.rules.merge_queue, null) != null ? [each.value.rules.merge_queue] : []
      content {
        check_response_timeout_minutes    = try(merge_queue.value.check_response_timeout_minutes, null)
        grouping_strategy                 = try(merge_queue.value.grouping_strategy, null)
        max_entries_to_build              = try(merge_queue.value.max_entries_to_build, null)
        max_entries_to_merge              = try(merge_queue.value.max_entries_to_merge, null)
        merge_method                      = try(merge_queue.value.merge_method, null)
        min_entries_to_merge              = try(merge_queue.value.min_entries_to_merge, null)
        min_entries_to_merge_wait_minutes = try(merge_queue.value.min_entries_to_merge_wait_minutes, null)
      }
    }

    dynamic "branch_name_pattern" {
      for_each = try(each.value.rules.branch_name_pattern, null) != null ? [each.value.rules.branch_name_pattern] : []
      content {
        name     = try(branch_name_pattern.value.name, null)
        negate   = try(branch_name_pattern.value.negate, null)
        operator = try(branch_name_pattern.value.operator, null)
        pattern  = try(branch_name_pattern.value.pattern, null)
      }
    }

    dynamic "tag_name_pattern" {
      for_each = try(each.value.rules.tag_name_pattern, null) != null ? [each.value.rules.tag_name_pattern] : []
      content {
        name     = try(tag_name_pattern.value.name, null)
        negate   = try(tag_name_pattern.value.negate, null)
        operator = try(tag_name_pattern.value.operator, null)
        pattern  = try(tag_name_pattern.value.pattern, null)
      }
    }

    dynamic "commit_message_pattern" {
      for_each = try(each.value.rules.commit_message_pattern, null) != null ? [each.value.rules.commit_message_pattern] : []
      content {
        name     = try(commit_message_pattern.value.name, null)
        negate   = try(commit_message_pattern.value.negate, null)
        operator = try(commit_message_pattern.value.operator, null)
        pattern  = try(commit_message_pattern.value.pattern, null)
      }
    }

    dynamic "commit_author_email_pattern" {
      for_each = try(each.value.rules.commit_author_email_pattern, null) != null ? [each.value.rules.commit_author_email_pattern] : []
      content {
        name     = try(commit_author_email_pattern.value.name, null)
        negate   = try(commit_author_email_pattern.value.negate, null)
        operator = try(commit_author_email_pattern.value.operator, null)
        pattern  = try(commit_author_email_pattern.value.pattern, null)
      }
    }

    dynamic "committer_email_pattern" {
      for_each = try(each.value.rules.committer_email_pattern, null) != null ? [each.value.rules.committer_email_pattern] : []
      content {
        name     = try(committer_email_pattern.value.name, null)
        negate   = try(committer_email_pattern.value.negate, null)
        operator = try(committer_email_pattern.value.operator, null)
        pattern  = try(committer_email_pattern.value.pattern, null)
      }
    }

    dynamic "required_deployments" {
      for_each = try(each.value.rules.required_deployments, null) != null ? [each.value.rules.required_deployments] : []
      content {
        required_deployment_environments = required_deployments.value
      }
    }

    dynamic "required_status_checks" {
      for_each = try(each.value.rules.required_status_checks, null) != null ? [each.value.rules.required_status_checks] : []
      content {
        strict_required_status_checks_policy = try(required_status_checks.value.strict_required_status_checks_policy, false)
        do_not_enforce_on_create             = try(required_status_checks.value.do_not_enforce_on_create, false)
        dynamic "required_check" {
          for_each = required_status_checks.value.required_checks
          content {
            context        = required_check.value.context
            integration_id = try(required_check.value.integration_id, null)
          }
        }
      }
    }
  }
}
