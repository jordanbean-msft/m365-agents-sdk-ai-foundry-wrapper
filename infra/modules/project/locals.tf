locals {
  project_id_guid = "${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 0, 8)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 8, 4)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 12, 4)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 16, 4)}-${substr(azapi_resource.ai_foundry_project.output.properties.internalId, 20, 12)}"

  # Extract Application Insights name from resource ID
  # Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Insights/components/{name}
  application_insights_name = var.application_insights_id != null ? element(split("/", var.application_insights_id), length(split("/", var.application_insights_id)) - 1) : null
}
