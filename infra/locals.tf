locals {
  project_id_guid = "${substr(module.project.ai_foundry_project_internal_id, 0, 8)}-${substr(module.project.ai_foundry_project_internal_id, 8, 4)}-${substr(module.project.ai_foundry_project_internal_id, 12, 4)}-${substr(module.project.ai_foundry_project_internal_id, 16, 4)}-${substr(module.project.ai_foundry_project_internal_id, 20, 12)}"
}
