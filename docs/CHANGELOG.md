# Changelog

All notable changes to the MicroK8s Cluster Orchestrator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Playbook Editor**: Comprehensive visual playbook creation and management system
  - **Visual Drag-and-Drop Interface**: Build Ansible playbooks without YAML knowledge
  - **Template Library**: Pre-built templates for common MicroK8s operations
  - **Target Selection System**: Flexible node targeting (all nodes, clusters, groups, individual)
  - **Real-time YAML Preview**: Live generation of Ansible YAML from visual components
  - **Execution Engine**: Background Ansible execution with real-time monitoring
  - **Template Management**: System and user templates with versioning and usage tracking
  - **Custom Playbooks**: User-created playbooks with visual configuration support
  - **Node Groups**: Custom node groupings for flexible targeting
  - **Execution History**: Complete audit trail with status tracking and output capture
  - **CLI Integration**: Full command-line interface for playbook management
  - **Web Interface**: Complete web-based playbook editor with modern UI
  - **API Endpoints**: RESTful API for all playbook operations
  - **System Templates**: Pre-built templates for MicroK8s installation, addon management, and health checks
  - **Real-time Monitoring**: Live execution progress with output streaming
  - **Error Handling**: Comprehensive error capture and reporting
  - **Security**: User isolation and permission-based access control

### Fixed
- **Template Uptime Display Error**: Fixed TypeError in hardware_report.html and node_hardware_report.html when calculating node uptime
  - Explicitly cast uptime_seconds to integer before division in Jinja2 templates
  - Prevents "unsupported operand type(s) for /: 'str' and 'int'" error
- **Ansible Callback Plugin Deprecation**: Fixed deprecated community.general.yaml callback plugin warnings
  - Updated ansible.cfg to use ansible.builtin.yaml instead of deprecated community.general.yaml
  - Resolved "community.general.yaml has been deprecated" warnings in Ansible output
- **Longhorn Prerequisites Status Integration**: Implemented complete Longhorn prerequisites status display and management
  - Added Longhorn prerequisites fields to Node model (prerequisites_met, status, missing_packages, etc.)
  - Updated orchestrator service to parse and store Longhorn check results in database
  - Added Longhorn status column to dashboard and nodes page with color-coded badges
  - Fixed parsing logic to handle both check and install operation output formats
  - Added support for missing wol_description property in Node model for WoL configuration
- **Operation Execution Issues**: Fixed operations getting stuck in pending status
  - Updated API endpoints to execute operations immediately instead of leaving them pending
  - Fixed check-longhorn-prerequisites, install-longhorn-prerequisites, and setup-new-node endpoints
  - Added proper error handling and success/failure responses
- **Wake-on-LAN Configuration**: Fixed WoL configuration functionality
  - Added missing wol_description property to Node model with human-readable descriptions
  - Resolved "'Node' object has no attribute 'wol_description'" error in WoL status endpoint
  - WoL configuration now works correctly in web interface
- **SQLAlchemy Model Conflicts**: Resolved database schema conflicts between CLI and web interface models
- **SSH Key Detection**: Improved SSH key scanning to properly detect existing keys
- **Database Schema Issues**: Added missing database columns and improved model compatibility
- **Web Interface Errors**: Fixed cluster page errors and improved error handling

### Enhanced
- **SSH Key Management**: Added manual SSH key selection from existing keys
- **SSH Key Scanning**: Enhanced to show all available keys with fingerprints and selection options
- **Web Interface**: Improved SSH key management UI with interactive key selection
- **Database Management**: Added new CLI command `python cli.py database path` to show database information
- **Error Handling**: Better error messages and recovery mechanisms throughout the application

### Added
- **AI Assistant with Local RAG System**: Comprehensive AI-powered troubleshooting and analysis
  - **Local-Only Operation**: Runs entirely on local resources, no external dependencies
  - **Retrieval-Augmented Generation (RAG)**: Learns from Ansible outputs and operation logs
  - **Multiple Chat Sessions**: Separate conversations for different topics and issues
  - **Searchable Content**: Index and search through playbooks, documentation, and operation logs
  - **Operation Log Analysis**: Intelligent analysis of failed operations with recommendations
  - **Ansible Output Analysis**: Parse and explain complex Ansible execution results
  - **Health Insights**: AI-powered system health monitoring and recommendations
  - **Knowledge Base**: Automatically builds knowledge from successful and failed operations
  - **Privacy-First**: Configurable data retention and anonymization
  - **Raspberry Pi 5 Optimized**: Designed for resource-constrained environments
  - **Content Search Service**: Indexes and searches playbooks, docs, and operation logs
  - **Chat Session Manager**: Manages multiple chat sessions with persistent storage
  - **Enhanced Web Interface**: Integrated AI chat interface with sidebar navigation
  - **Configuration Management**: Comprehensive AI Assistant configuration options
  - **Local LLM Integration**: Support for Ollama and other local LLM providers

- **SSH Key Management System**: Comprehensive SSH key management with automatic generation
  - Automatic generation of unique RSA 2048-bit SSH key pairs for each node
  - Secure storage of private keys with proper file permissions (600)
  - Step-by-step setup instructions for adding public keys to target nodes
  - SSH connection testing with sudo access validation
  - Key regeneration capabilities for compromised or lost keys
  - Visual SSH key status indicators in the web interface
  - Integration with Ansible inventory generation
  - CLI commands for SSH key management (`test-ssh`, `ssh-status`, `regenerate-ssh-key`)

### Enhanced
- **Web Interface**: Enhanced with AI Assistant and improved user experience
  - **AI Chat Interface**: Integrated chat interface with thinking indicator in chat flow
  - **Sidebar Navigation**: Organized sidebar with chat sessions, content search, and operation logs
  - **Modal Improvements**: Replaced modal popups with inline chat indicators
  - **Enhanced Templates**: Updated assistant template with multiple chat sessions and log analysis
  - **SSH Key Management**: New SSH setup page for each node with detailed instructions
  - **SSH Key Status**: SSH key status column in the nodes list

- **System Management**: Enhanced with timezone configuration and improved restart functionality
  - **Timezone Setup**: Configure system timezone with timezone selection interface
  - **Robust Restart**: Improved system restart handling for different deployment scenarios
  - **Prerequisites Check**: Comprehensive system requirements validation
  - **Log Viewer**: Multi-log viewer with clear and refresh capabilities

- **Configuration System**: Enhanced with AI Assistant configuration options
  - **AI Configuration**: Comprehensive AI Assistant settings in configuration files
  - **Feature Toggles**: Enable/disable AI features and content types
  - **Privacy Controls**: Configurable data retention and anonymization settings
  - **Performance Settings**: Configurable timeouts, caching, and resource limits

- **Node Addition Workflow**: Streamlined node addition with automatic SSH key generation
  - Removed manual SSH key path requirement
  - Automatic redirect to SSH setup page after node creation
  - Clear setup instructions provided to users
  - Integration with existing node management workflow
  - Copy-to-clipboard functionality for public keys
  - Connection testing with real-time feedback
  - Key regeneration with confirmation dialogs

- **CLI Interface**: Extended with SSH key management commands
  - `node test-ssh <node_id>` - Test SSH connection to a node
  - `node ssh-status <node_id>` - Show detailed SSH key status
  - `node regenerate-ssh-key <node_id>` - Regenerate SSH key for a node
  - Enhanced `node add` command with automatic SSH key generation

- **AI Assistant Services**: New service modules for AI functionality
  - `ContentSearchService`: Indexes and searches playbooks, docs, and operation logs
  - `ChatSessionManager`: Manages multiple chat sessions with SQLite storage
  - `LocalRAGSystem`: Core RAG system with TF-IDF similarity and pattern matching
  - `AIConfigManager`: Centralized AI configuration management

- **Database Schema**: Enhanced with AI Assistant and SSH key management
  - **SSH Key Fields**: Added to nodes table for SSH key management
    - `ssh_key_generated` - Boolean indicating if SSH key pair has been generated
    - `ssh_public_key` - Text field containing the public key content
    - `ssh_key_fingerprint` - String field for key fingerprint identification
    - `ssh_key_status` - String field for key status tracking
    - `ssh_connection_tested` - Boolean indicating if SSH connection has been tested
    - `ssh_connection_test_result` - Text field for last SSH connection test result
    - `ssh_setup_instructions` - Text field for setup instructions
  - **AI Knowledge Base**: New SQLite databases for AI functionality
    - Content index database for searchable content
    - Chat sessions database for multiple conversations
    - Messages database for chat history

- **API Endpoints**: New REST endpoints for AI Assistant functionality
  - `/api/assistant/chat`: Chat endpoint for AI conversations
  - `/api/assistant/search-content`: Search playbooks, docs, and logs
  - `/api/assistant/index-content`: Index searchable content
  - `/api/assistant/chat-sessions`: Manage multiple chat sessions
  - `/api/assistant/operation-logs`: Retrieve and analyze operation logs
  - `/api/assistant/health-insights`: Get AI-powered health insights
  - `/api/assistant/statistics`: Get AI system statistics

- **Configuration Files**: Enhanced with AI Assistant settings
  - Added `ai_assistant` section to production configuration
  - Support for local LLM integration (Ollama, OpenAI Local)
  - Configurable content search and privacy settings
  - Performance and timeout configurations

- **Ansible Integration**: Enhanced inventory generation with SSH key validation
  - SSH connection validation before running playbooks
  - Enhanced error reporting for SSH connection issues
  - Key fingerprint tracking in inventory files
  - Automatic exclusion of nodes with SSH connection issues

### Security
- **Enhanced SSH Security**: Improved SSH authentication security
  - Unique SSH key pairs per node prevent key sharing
  - Secure key storage with proper file permissions
  - Key fingerprinting for identification and verification
  - Connection validation with sudo access testing
  - Audit trail of SSH connection tests

### Documentation
- **AI Assistant Documentation**: Comprehensive AI Assistant documentation
  - Complete AI Assistant guide (`docs/AI_ASSISTANT_GUIDE.md`)
  - Updated documentation index with AI Assistant section
  - Detailed feature descriptions and usage examples
  - Configuration and troubleshooting guides

- **Comprehensive Documentation**: Added detailed SSH key management documentation
  - Complete SSH key management guide (`docs/SSH_KEY_MANAGEMENT.md`)
  - Updated README with SSH key management features
  - Migration guide for existing installations
  - Troubleshooting section with common issues and solutions
  - API reference for developers
  - Best practices for security and operations

### Migration
- **Database Migration**: Added migration script for existing installations
  - `migrations/add_ssh_key_fields.py` - Adds SSH key fields to existing databases
  - Rollback capability for safe migration management
  - Backward compatibility with existing installations

## [Previous Versions]

### [1.0.0] - 2024-01-XX

#### Added
- **Core System**: Initial release of MicroK8s Cluster Orchestrator
- **Node Management**: Add, remove, and monitor cluster nodes
- **Cluster Orchestration**: Automated cluster setup, configuration, and graceful shutdown
- **Ansible Integration**: Uses Ansible playbooks for all operations
- **SQLite Database**: Persistent storage for cluster state and history
- **Web Interface**: Modern web UI for cluster management
- **CLI Tool**: Command-line interface for automation and scripting
- **Operation Tracking**: Complete audit trail of all operations
- **Health Monitoring**: Automated health checks and status monitoring
- **Troubleshooting**: Built-in diagnostics and troubleshooting tools

#### Hardware Reporting System
- **Automatic Detection**: Discovers all hardware components automatically
- **Detailed Information**: Collects comprehensive data about CPUs, memory, storage, network, and more
- **Real-time Updates**: Hardware information is collected on-demand or scheduled
- **Web Interface**: Beautiful, responsive web interface for viewing hardware reports
- **API Access**: REST API endpoints for programmatic access to hardware data

#### UPS Power Management System
- **USB UPS Detection**: Automatically detects and configures USB-connected UPS devices
- **NUT Integration**: Uses Network UPS Tools (NUT) for UPS communication and control
- **Power Event Monitoring**: Monitors power loss, low battery, and power restoration events
- **Automated Cluster Management**: Executes configurable actions on clusters based on power events
- **Real-time Status Monitoring**: Tracks battery charge, voltage, load, and temperature
- **Rule-based Configuration**: Flexible power management rules with priority-based execution
- **Web Interface**: Complete web-based management interface for UPS devices and rules
- **CLI and API Support**: Full command-line and REST API access to all UPS functions

#### Features
- **Wake-on-LAN Support**: Configure and manage Wake-on-LAN for cluster nodes
- **Hardware Information Collection**: Comprehensive hardware reporting system
- **Network Topology Visualization**: Visual representation of network connections
- **Router/Switch Management**: Integration with network infrastructure
- **Power Management**: UPS integration for Raspberry Pi deployments
- **Privilege Management**: Automated setup of required system privileges
- **Configuration Management**: Flexible YAML-based configuration system

#### Security
- **SQLite Database**: Excluded from version control for security
- **SSH Key Management**: Secure storage of SSH keys with proper permissions
- **Configuration Security**: Environment-specific settings support
- **Data Encryption**: Support for encrypting sensitive data in the database

#### Development
- **Modular Architecture**: Clear separation of concerns with modular design
- **Turing Complete**: Fully programmable and extensible system
- **Infrastructure Agnostic**: Works with any infrastructure that supports SSH
- **Persistent State**: All state and history stored in SQLite database

---

## Version History

### Version 1.1.0 (Unreleased)
- **Major Feature**: SSH Key Management System
- **Enhancement**: Streamlined node addition workflow
- **Security**: Enhanced SSH authentication security
- **Documentation**: Comprehensive SSH key management documentation

### Version 1.0.0 (Initial Release)
- **Core System**: Complete MicroK8s cluster orchestration system
- **Hardware Reporting**: Comprehensive hardware information collection
- **UPS Management**: Power management for Raspberry Pi deployments
- **Web Interface**: Modern web UI for cluster management
- **CLI Tools**: Command-line interface for automation

---

## Migration Guide

### From Version 1.0.0 to 1.1.0

#### Database Migration
Run the migration script to add SSH key management fields:

```bash
python migrations/add_ssh_key_fields.py
```

#### Configuration Updates
No configuration changes required. The system will automatically use the new SSH key management features.

#### Breaking Changes
- **Node Addition**: The `--key-path` parameter is no longer required for `node add` command
- **SSH Key Storage**: SSH keys are now stored in the `ssh_keys/` directory instead of user-specified locations

#### New Features
- **Automatic SSH Key Generation**: SSH keys are now generated automatically when adding nodes
- **SSH Setup Instructions**: Users receive detailed setup instructions for each node
- **Connection Testing**: Built-in SSH connection testing and validation
- **Key Regeneration**: Easy key regeneration for compromised keys

---

## Support

For support with the SSH Key Management System:

1. **Check Documentation**: Review `docs/SSH_KEY_MANAGEMENT.md` for detailed information
2. **Run Migration**: Ensure database migration has been completed
3. **Check Logs**: Review operation logs for detailed error information
4. **Test Connections**: Use the built-in connection testing tools
5. **Regenerate Keys**: If issues persist, regenerate SSH keys for affected nodes

For general support:
- Check operation logs for detailed error information
- Review the troubleshooting playbooks
- Create issues in the repository for bugs or feature requests