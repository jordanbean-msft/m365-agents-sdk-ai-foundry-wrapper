# Application Gateway Module

This module provisions an Azure Application Gateway v2 to expose the M365 Agents Container App to the internet.

## Features

- **Public Internet Access**: Application Gateway with a public IP allows external traffic to reach the Container App
- **Backend Integration**: Routes traffic to the internal Container App FQDN via HTTPS
- **Health Probes**: Monitors backend health with configurable intervals
- **Diagnostics**: Optional Log Analytics integration for monitoring and troubleshooting
- **Network Isolation**: Container App remains internal; only App Gateway has public exposure

## Architecture

```
Internet → Public IP → Application Gateway → Internal Container App (HTTPS)
```

The Application Gateway:

- Listens on port 80 (HTTP) on the public IP
- Routes traffic to the Container App backend on port 443 (HTTPS)
- Uses the Container App FQDN as the backend target
- Picks the hostname from the backend address for proper routing

## Requirements

### Subnet Requirements

The Application Gateway requires a dedicated subnet with the following properties:

- **Minimum size**: /26 (64 addresses) recommended; /24+ for production
- **Delegation**: None (Application Gateway does not use subnet delegation)
- **Service Endpoints**: None required, but can be added if needed
- **Existing resources**: Must be empty (Application Gateway requires exclusive use)

### Network Security Group (NSG)

An NSG can be attached to the Application Gateway subnet. Required rules:

- **Inbound**:
  - Allow TCP 80, 443 from Internet (for public access)
  - Allow TCP 65200-65535 from GatewayManager (for Azure infrastructure)
- **Outbound**:
  - Allow to VirtualNetwork (for backend communication)
  - Allow to Internet (for external dependencies)

See the `nsgs` module for NSG associations.

## Inputs

| Name                         | Description                                   | Type        | Required           |
| ---------------------------- | --------------------------------------------- | ----------- | ------------------ |
| `unique_suffix`              | Unique suffix for resource naming             | string      | Yes                |
| `resource_group_name`        | Name of the resource group                    | string      | Yes                |
| `location`                   | Azure region                                  | string      | Yes                |
| `subnet_id_app_gateway`      | Resource ID of the Application Gateway subnet | string      | Yes                |
| `container_app_fqdn`         | FQDN of the Container App backend             | string      | Yes                |
| `log_analytics_workspace_id` | Resource ID of Log Analytics workspace        | string      | Yes                |
| `common_tags`                | Common tags to apply to resources             | map(string) | No                 |
| `enable_diagnostics`         | Enable diagnostic settings                    | bool        | No (default: true) |

## Outputs

| Name                       | Description                                     |
| -------------------------- | ----------------------------------------------- |
| `application_gateway_id`   | Resource ID of the Application Gateway          |
| `application_gateway_name` | Name of the Application Gateway                 |
| `public_ip_address`        | Public IP address for accessing the application |
| `public_ip_fqdn`           | FQDN of the public IP (if configured)           |

## Dependencies

- Container Apps module (requires `container_app_fqdn` output)
- Dedicated subnet for Application Gateway
- NSG with appropriate rules (managed separately)

## Usage Notes

1. **Backend Protocol**: The Application Gateway uses HTTPS to communicate with the Container App backend
2. **Host Name Picking**: `pick_host_name_from_backend_address = true` ensures proper routing to Container Apps
3. **Health Probe**: Monitors the root path (`/`) on HTTPS; adjust as needed for your application
4. **SKU**: Uses Standard_v2 with autoscaling; capacity set to 2 for HA
5. **Public Access**: Only the Application Gateway has a public IP; Container App ingress should be internal-only

## Integration with Container Apps

When using this module, ensure the Container Apps ingress is configured as internal-only:

```hcl
ingress {
  external_enabled = false  # Internal only
  target_port      = 80
  ...
}
```

The Application Gateway will route public traffic to the internal Container App FQDN.

## Example

See `infra/main.tf` for a complete example of how this module is wired with other modules.

## Future Enhancements

- Add support for custom domains and SSL certificates
- Implement WAF (Web Application Firewall) policies
- Add additional listeners for HTTPS termination
- Support multiple backend pools for advanced routing scenarios
