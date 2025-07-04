# Security Policy

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability in Watchtower, please follow these steps:

### 🔒 Private Disclosure

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them privately by:

1. **Email**: Send details to the repository maintainer via GitHub (check the repository for contact information)
2. **GitHub Security Advisories**: Use GitHub's private vulnerability reporting feature if available

### 📝 What to Include

When reporting a vulnerability, please include:

- **Description**: A clear description of the vulnerability
- **Impact**: What could an attacker do with this vulnerability?
- **Reproduction**: Step-by-step instructions to reproduce the issue
- **Environment**: Affected versions, operating systems, configurations
- **Suggested Fix**: If you have ideas for how to fix it

### ⏱️ Response Timeline

- **Initial Response**: We will acknowledge receipt within 48 hours
- **Investigation**: We will investigate and provide an initial assessment within 7 days
- **Resolution**: We aim to provide a fix within 30 days for high-severity issues

### 🛡️ Security Best Practices

When using Watchtower:

#### Configuration Security
- **Environment Variables**: Use `.env` files for sensitive configuration, never commit them to version control
- **API Keys**: Store API keys securely and rotate them regularly
- **Permissions**: Run Watchtower with minimal required permissions
- **Network**: Consider running in isolated network environments for production

#### Data Security
- **Local Storage**: Be aware that ETL pipelines store data locally in the `data/` directory
- **Logs**: Log files may contain sensitive information - secure the `logs/` directory appropriately
- **Cleanup**: Regularly clean up old data and logs to minimize exposure

#### Deployment Security
- **Dependencies**: Keep dependencies updated using `poetry update` or `pip update`
- **Container Security**: When using Docker, use minimal base images and keep them updated
- **Access Control**: Restrict access to the Streamlit dashboard in production environments

### 🔄 Security Updates

Security updates will be:
- Released as patch versions (e.g., 0.1.1 → 0.1.2)
- Documented in the [CHANGELOG.md](CHANGELOG.md)
- Announced in release notes

### 🙏 Recognition

We appreciate security researchers who help improve Watchtower's security. With your permission, we'll acknowledge your contribution in our security advisories and release notes.

---

Thank you for helping keep Watchtower secure!