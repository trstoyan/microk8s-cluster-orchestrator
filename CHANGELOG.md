# Changelog

All notable changes to the MicroK8s Cluster Orchestrator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive hardware reporting system
- Detailed disk partition and filesystem information collection
- Docker and Kubernetes volume tracking
- LVM and RAID information detection
- Thermal sensor monitoring
- GPU detection and information
- Physical disk enumeration with accurate size calculation
- Mounted filesystem tracking
- Block device details and symbolic links
- MicroK8s and Kubernetes PVC/PV detection
- Storage class information
- Hardware report web interface with tabular data display

### Changed
- **BREAKING**: Database schema updated with new hardware fields
- Hardware data collection now uses SCP for large JSON transfers
- Disk total calculation now sums all physical disks instead of just root filesystem
- Improved data parsing with line-based extraction instead of regex patterns
- Enhanced error handling for hardware collection failures

### Fixed
- SCP connection issues with incorrect SSH user authentication
- JSON truncation problems with large hardware reports
- Disk total calculation showing incorrect values (441GB → 5296GB)
- Data extraction failures with regex pattern matching
- Template rendering issues with missing hardware data
- ORM caching problems preventing new database fields from being accessed

### Technical Improvements
- Added `calculate_disk_total.py` script for accurate disk space calculation
- Implemented proper SSH user handling in orchestrator service
- Enhanced Ansible playbook with comprehensive hardware collection tasks
- Improved database migration scripts for schema updates
- Added debug utilities for troubleshooting hardware collection issues

## [Previous Versions]

### v1.0.0 - Initial Release
- Basic node and cluster management
- Ansible integration
- Web interface
- CLI tool
- SQLite database
- Operation tracking
- Health monitoring
- Troubleshooting tools

---

## Hardware Reporting Features

### Data Collection
The hardware reporting system collects comprehensive information about:

#### System Information
- Hostname, IP address, OS version
- Kernel version and architecture
- Uptime and load averages

#### CPU Information
- CPU model and specifications
- Core count and usage statistics
- Temperature monitoring (when available)

#### Memory Information
- Total memory and swap space
- Memory usage statistics
- Detailed memory layout information

#### Storage Information
- **Physical Disks**: All physical storage devices with size, model, serial number
- **Partitions**: All disk partitions with filesystem types and mount points
- **Mounted Filesystems**: Complete list of mounted filesystems with options
- **LVM Information**: Logical Volume Manager details (VGs, LVs, PVs)
- **RAID Information**: RAID array status and configuration
- **Block Devices**: Symbolic links and device mappings

#### Container Storage
- **Docker Volumes**: All Docker-managed volumes
- **Podman Volumes**: Podman container volumes (when available)
- **Kubernetes PVCs**: Persistent Volume Claims across all namespaces
- **Kubernetes PVs**: Persistent Volumes and their status
- **Storage Classes**: Available storage classes and their configurations
- **MicroK8s Storage**: MicroK8s-specific storage components

#### Network Information
- Network interfaces and their configurations
- IP addresses and routing information
- Network performance metrics

#### GPU Information
- GPU detection and model information
- GPU usage statistics (when available)
- Driver information

#### Thermal Information
- Temperature sensors and readings
- Fan speeds and thermal management
- Hardware thermal status

### Web Interface
The hardware report is displayed in a comprehensive web interface with:
- Tabular display of all collected information
- Organized sections for different hardware categories
- Real-time data updates
- Responsive design for different screen sizes
- Detailed view for individual nodes

### Data Storage
Hardware information is stored in the SQLite database with:
- JSON-formatted detailed information
- Efficient querying and retrieval
- Historical data tracking
- Backup and restore capabilities

### API Integration
Hardware reports can be accessed via:
- Web interface at `/hardware-report/node/{id}`
- REST API endpoints for programmatic access
- CLI commands for automation
- Ansible integration for batch operations

---

## Migration Notes

### Database Migration
When upgrading from previous versions, run the migration scripts:

```bash
# Add hardware reporting fields
python scripts/migrate_disk_partitions_fields.py

# Add authentication fields (if upgrading from very old versions)
python scripts/migrate_auth.py
```

### Configuration Updates
No configuration changes are required for hardware reporting. The system automatically detects and collects available hardware information.

### Breaking Changes
- Database schema changes require migration scripts to be run
- Some CLI commands may have new options for hardware reporting
- Web interface has new hardware report pages

---

## Known Issues

### Hardware Collection
- Some hardware information may not be available on all systems
- Thermal sensors require specific drivers and may not be detected
- GPU information depends on proper driver installation
- LVM information is only available on systems with LVM configuration

### Performance
- Hardware collection can take 30-60 seconds on complex systems
- Large JSON files are transferred via SCP which may be slower than direct parsing
- Database queries may be slower with large amounts of hardware data

### Compatibility
- Tested on Ubuntu 20.04+ and similar Linux distributions
- Requires Python 3.8+ on target systems for hardware collection
- Ansible 2.15+ required for playbook execution
- SSH access required for all hardware collection operations

---

## Future Enhancements

### Planned Features
- Hardware trend analysis and historical tracking
- Hardware alerting and threshold monitoring
- Hardware-based capacity planning
- Integration with monitoring systems (Prometheus, Grafana)
- Hardware inventory management
- Automated hardware health checks

### Technical Improvements
- Performance optimization for large-scale deployments
- Enhanced error handling and retry mechanisms
- Improved data compression for storage efficiency
- Real-time hardware monitoring capabilities
- Hardware change detection and notifications
