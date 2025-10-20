## Data source for Application Insights (if provided)
## This fetches the connection string from the Application Insights resource
##
data "azurerm_application_insights" "existing" {
  count               = var.application_insights_id != null ? 1 : 0
  name                = element(split("/", var.application_insights_id), length(split("/", var.application_insights_id)) - 1)
  resource_group_name = element(split("/", var.application_insights_id), 4)

  provider = azurerm.workload_subscription
}
