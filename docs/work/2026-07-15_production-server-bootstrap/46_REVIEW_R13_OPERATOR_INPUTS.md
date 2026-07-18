# 46_REVIEW_R13_OPERATOR_INPUTS — Required External Operator Inputs

This document lists the names and locations of required external operator inputs for private GitHub transport and source-readiness verification. Under no circumstances should actual secret values, private keys, or tokens be stored here.

## 1. Server-Side SSH Checkout Key (GitHub Read-Only Deploy Key)
- **Path on host:** `/home/astro/.ssh/solarsage_prod_server_ed25519` (Private Key)
- **Path on host:** `/home/astro/.ssh/solarsage_prod_server_ed25519.pub` (Public Key)
- **Ownership/Permissions:** `astro:astro` / `0600` (Private), `astro:astro` / `0644` (Public)
- **Role:** Allows the server to check out the repository via the SSH alias `github.com-solarsage-prod`.
- **GitHub Registration:** The public key must be manually registered in the GitHub repository settings under "Deploy Keys" with **read-only** permissions.

## 2. GitHub Actions Deployment SSH Key
- **Path on host:** `/etc/solarsage/keys/github-actions-deploy.pub` (Public Key only)
- **Ownership/Permissions:** `root:root` / `0644`
- **GitHub Environment Secret:** `PROD_SSH_PRIVATE_KEY` (Private Key value)
- **Role:** Allows GitHub Actions to connect to the production host via SSH.
- **Forced-Command Prefix:** The apply action configures this key in `/home/astro/.ssh/authorized_keys` prefixed with:
  `restrict,command="/usr/local/sbin/solarsage-github-deploy"`
  to prevent execution of arbitrary remote commands.

## 3. GitHub Environment Secrets
The `production` environment in GitHub must be configured with the following secrets (values not stored on the server or in code):
- `PROD_HOST`: Production server IP or hostname.
- `PROD_USER`: Target SSH user (`astro`).
- `PROD_SSH_PRIVATE_KEY`: Private SSH key matching the public key at `/etc/solarsage/keys/github-actions-deploy.pub`.
- `PROD_KNOWN_HOSTS`: SSH host keys of the production server.

## 4. Repository Visibility
- **State:** The repository must be manually changed to **Private** in the GitHub repository settings.
- **Verification:** The source-readiness check (`prod-github-access.sh --check`) queries the anonymous GitHub API and expects a `404 Not Found` to verify that the repository is indeed private.

## 5. Legacy Write Deploy Key
- **Role:** A legacy write deploy key may still exist in the GitHub repository settings.
- **Action:** This key must be manually reviewed and revoked by the repository owner/operator when no longer needed. The scripts do not automatically modify or delete this key.
