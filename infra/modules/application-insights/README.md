# Application Insights Module

Creates an Application Insights component optionally linked to a Log Analytics workspace.

## Inputs

| Name                | Description                           | Type        | Default |
| ------------------- | ------------------------------------- | ----------- | ------- |
| name                | Component name                        | string      | n/a     |
| location            | Azure region                          | string      | n/a     |
| resource_group_name | Target resource group                 | string      | n/a     |
| workspace_id        | Log Analytics workspace ID (optional) | string      | null    |
| application_type    | Application type (web/other)          | string      | web     |
| tags                | Tags applied to the component         | map(string) | {}      |

## Outputs

| Name                    | Description         |
| ----------------------- | ------------------- |
| application_insights_id | Resource ID         |
| app_id                  | Application ID      |
| instrumentation_key     | Instrumentation key |
| connection_string       | Connection string   |

## Notes

- Created only when root variable `application_insights_id` is null.
- If a workspace ID is provided (either existing or newly created), the component is linked to that workspace.
