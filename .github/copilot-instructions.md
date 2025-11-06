# Copilot Instructions for AI Foundry Terraform Infrastructure

## Project Overview

This repository provisions a secure, modular Azure infrastructure for AI Foundry agent-based applications using Terraform. The design emphasizes network isolation, least-privilege access, and modularity for maintainability and clarity.

## Architecture & Modules

- **Modules are in `infra/modules/`**. Each subfolder is a logical unit (e.g., `storage`, `ai-foundry`, `container-apps`, `logic-apps`).
- **Data flow:**
  - `foundation` → `storage`/`ai-foundry`/`identity`/`acr` → `networking` → `project`/`container-apps`/`logic-apps`
  - `nsgs` module is independent (attaches NSGs to existing subnets) and can be modified safely without impacting resource creation order.
- **Key cross-module dependencies** are managed via outputs and explicit input variables (see each module's `variables.tf` and `outputs.tf`).
- **All resources are private**: Public network access is disabled for storage, Logic Apps, and Container Apps. Access is via private endpoints and VNet integration only.

## Developer Workflows

- **Terraform root is `infra/`**. Run all Terraform commands from this directory.
- **Required pre-step: build & push container image BEFORE Terraform plan/apply**
  - Always build the Docker image for the container app first so the tag exists when Terraform updates the revision.
  - Use linux/amd64 platform flag (Container Apps scheduling requirement already documented below).
  - Example sequence (adjust repo/tag as needed):
    - `docker buildx build --platform linux/amd64 -t <acr-login-server>/<repo>:<tag> .`
    - `docker push <acr-login-server>/<repo>:<tag>`
  - Only after the image is pushed should you run Terraform so the new revision can pull successfully.
- **Standard workflow (single reusable plan file):**
  1. `terraform fmt -recursive`
  2. `terraform init`
  3. `terraform validate`
  4. `terraform plan -out tfplan` ← Always overwrite `tfplan` (do not create ad-hoc filenames)
  5. Review plan output if needed
  6. `terraform apply tfplan` (must apply the exact plan you just generated)
  - Re-run steps 4–6 for subsequent changes; the previous `tfplan` is intentionally overwritten to avoid stale plans.
- **Rationale for single `tfplan` file:**
  - Prevents accumulation of outdated plan artifacts.
  - Ensures you always apply what you just reviewed.
  - Simplifies CI scripts and local workflows.
- **Variables:**
  - All environment-specific values are set in `infra/terraform.tfvars`.
  - Subnet IDs must reference pre-existing subnets in your VNet (see module READMEs for required properties).
  - `common_tags` map applied to all tag-supporting resources (propagated explicitly through modules). Add new standard tags here only.
- **Module composition:**
  - The root `main.tf` wires modules together, passing outputs as needed.
  - Example: `module.project` depends on outputs from `module.networking`, `module.storage`, and `module.ai_foundry`.

## Patterns & Conventions

- **Resource naming:**
  - All resources use a `unique_suffix` from the `foundation` module for global uniqueness.
  - Example: `project${unique_suffix}`
- **Identity:**
  - User-assigned managed identities are used for all compute resources.
  - Container Apps use user-assigned identities for secure ACR pulls and Azure resource access.
- **RBAC:**
  - Role assignments are explicit and scoped to the minimum required resources.
  - Data plane and control plane roles are assigned after resource creation, with `time_sleep` resources to ensure propagation.
- **Secrets:**
  - Sensitive values (e.g., client secrets) are passed as Terraform variables and stored as secrets in Azure resources, not as environment variables.
- **Networking:**
  - All resources are deployed into a VNet with private endpoints.
  - Logic Apps and Container Apps have VNet integration for secure outbound access.
  - NSGs (`nsgs` module) are attached per subnet: agent, private endpoints, logic-apps, container-apps. Default rules (deny inbound except VirtualNetwork) currently in effect; add explicit rules inside that module only.
  - No public IPs are assigned; public network access disabled on all services.
  - Tag consistency is enforced via `common_tags` variable rather than provider default tags (azapi resources require explicit tagging).
- **Private Endpoints:**
  - All private endpoint resources must include a lifecycle block that ignores changes to `private_dns_zone_group`.
  - This prevents Terraform from attempting to manage DNS zone groups that may be created/managed externally or through Azure policies.
  - Example:
    ```hcl
    lifecycle {
      ignore_changes = [
        private_dns_zone_group
      ]
    }
    ```

## Integration Points

- **AI Foundry:**
  - The `ai-foundry` and `project` modules provision the AI Foundry account, project, and connect to Cosmos DB, Storage, and AI Search.
  - The `container-apps` module configures environment variables for agent integration (see its README for details).
- **Logic Apps:**
  - Fully network-isolated, with private endpoints and VNet integration. Use the Azure Portal or VS Code extension for workflow development.
- **Container Apps:**
  - Deployed with VNet integration, private ACR, and managed identities. Ingress is internal-only by default.

## Container Image Architecture Requirement

Azure Container Apps currently schedules workloads on linux/amd64. All Docker images referenced via the `container_image` Terraform variable MUST be built for `linux/amd64`. If you are on an arm64 development machine (Apple Silicon, newer ARM laptops, etc.), always force the platform during builds:

```
docker buildx build --platform linux/amd64 -t <acr-login-server>/<repo>:<tag> .
```

or

```
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build -t <acr-login-server>/<repo>:<tag> .
```

Failing to do this can result in startup failures or crash loops in the Container App revision. Keep this requirement documented whenever adding new build automation.

## Examples

- **Adding a new environment:** Copy and adjust `terraform.tfvars` for the new environment. Ensure all required subnets exist.
- **Referencing module outputs:**
  ```hcl
  output_from_other_module = module.other_module.output_name
  ```
- **Granting access:**
  - After deployment, grant managed identities access to required Azure resources as needed.

## Key Files

- `infra/main.tf`: Root Terraform configuration, wires modules together
- `infra/terraform.tfvars`: Environment-specific variables
- `infra/modules/*/README.md`: Module-specific documentation and requirements
- `infra/modules/nsgs/`: Network Security Groups + subnet associations (do not duplicate elsewhere)

---

**For AI agents:**

- Always read module READMEs before modifying or adding modules.
- Maintain strict network isolation and least-privilege access patterns. Add/modify NSG rules only in `modules/nsgs` to keep security centralized.
- Use outputs and variables to connect modules—avoid hardcoding resource IDs.
- Document any new patterns or workflows in the appropriate module README.
- If you deploy code using the Azure CLI, those changes need to be reflected in Terraform to avoid drift. This includes Docker image versions, configuration changes, and role assignments.
- When creating private endpoints, always include the lifecycle block to ignore changes to `private_dns_zone_group` to prevent drift issues.
- Follow the established naming conventions and tagging strategies to ensure consistency across resources.
