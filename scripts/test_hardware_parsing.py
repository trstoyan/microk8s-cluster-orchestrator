#!/usr/bin/env python3
"""
Test script to verify hardware data parsing logic.
"""

import sys
import os
import json

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_hardware_parsing():
    """Test the hardware data parsing logic with sample output."""
    try:
        from app.services.orchestrator import OrchestrationService
        
        print("Testing hardware data parsing logic...")
        
        # Sample Ansible output with our new format
        sample_output = """
PLAY [Collect comprehensive hardware and resource information] *****************

TASK [Gathering Facts] *********************************************************
ok: [test-node-1]

TASK [Install required packages for hardware detection] ***********************
ok: [test-node-1]

TASK [Output structured hardware data for orchestrator] ***********************
ok: [test-node-1] => {
    "msg": "HARDWARE_REPORT_JSON: {\\"hostname\\": \\"test-node-1\\", \\"cpu_info\\": {\\"cores\\": 4, \\"usage_percent\\": 25}, \\"memory_info\\": {\\"total_gb\\": 8, \\"usage_percent\\": 60}, \\"disk_info\\": {\\"total_gb\\": 100, \\"usage_percent\\": 45}}"
}

PLAY RECAP *********************************************************************
test-node-1                : ok=3    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
"""
        
        orchestrator = OrchestrationService()
        
        # Test parsing
        hardware_data = orchestrator._parse_hardware_results(sample_output, [])
        
        print(f"✅ Parsing completed")
        print(f"   - Found data for {len(hardware_data)} hosts")
        
        for hostname, data in hardware_data.items():
            print(f"   - Host: {hostname}")
            print(f"     - CPU cores: {data.get('cpu_info', {}).get('cores', 'N/A')}")
            print(f"     - Memory: {data.get('memory_info', {}).get('total_gb', 'N/A')}GB")
            print(f"     - Disk: {data.get('disk_info', {}).get('total_gb', 'N/A')}GB")
        
        if hardware_data:
            print("✅ Hardware parsing test passed!")
            return True
        else:
            print("❌ No hardware data was parsed from sample output")
            return False
            
    except Exception as e:
        print(f"❌ Error during parsing test: {e}")
        return False

def main():
    """Run the test."""
    print("Hardware Data Parsing Test")
    print("=" * 40)
    
    if test_hardware_parsing():
        print("\n✅ Test passed! Hardware data parsing should work correctly.")
        print("\nNext steps:")
        print("1. Restart the Flask application")
        print("2. Try hardware collection from the web interface")
        print("3. Check that data appears in hardware reports")
    else:
        print("\n❌ Test failed. Check the parsing logic.")
        sys.exit(1)

if __name__ == "__main__":
    main()
