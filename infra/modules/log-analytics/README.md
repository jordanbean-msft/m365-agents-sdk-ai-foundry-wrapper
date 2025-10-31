# Log Analytics Workspace Module

Provisions an Azure Log Analytics workspace when one is not supplied externally.

## Inputs

| Name                | Description                   | Type        | Default |
| ------------------- | ----------------------------- | ----------- | ------- |
| name                | Workspace name                | string      | n/a     |
| location            | Azure region                  | string      | n/a     |
| resource_group_name | Target resource group         | string      | n/a     |
| retention_in_days   | Data retention period         | number      | 30      |
| tags                | Tags applied to the workspace | map(string) | {}      |

## Outputs

| Name           | Description                  |
| -------------- | ---------------------------- |
| workspace_id   | Resource ID of the workspace |
| workspace_name | Name of the workspace        |

## Notes

- SKU is fixed to `PerGB2018`.
- Retention defaults to 30 days; adjust via `retention_in_days`.
- Created only when root variable `log_analytics_workspace_id` is null.
