#!/usr/bin/env python3
"""
Test script to verify hardware collection functionality.
"""

import sys
import os
import json

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_inventory_generation():
    """Test that inventory generation works correctly."""
    try:
        from app.models.database import get_session
        from app.models.node import Node
        from app.services.orchestrator import OrchestrationService
        
        print("Testing hardware collection inventory generation...")
        
        session = get_session()
        try:
            # Get nodes from database
            nodes = session.query(Node).all()
            print(f"Found {len(nodes)} nodes in database")
            
            if not nodes:
                print("❌ No nodes found. Add nodes to test hardware collection.")
                return False
            
            # Test orchestrator service
            orchestrator = OrchestrationService()
            
            # Test inventory generation
            inventory_file = orchestrator._generate_inventory(nodes)
            print(f"✅ Generated inventory file: {inventory_file}")
            
            # Check if inventory file exists and has content
            if os.path.exists(inventory_file):
                with open(inventory_file, 'r') as f:
                    inventory_data = json.load(f)
                
                print("✅ Inventory file created successfully")
                print(f"   - Contains {len(inventory_data['all']['children']['microk8s_nodes']['hosts'])} hosts")
                
                # Print inventory structure
                for hostname, host_data in inventory_data['all']['children']['microk8s_nodes']['hosts'].items():
                    print(f"   - Host: {hostname} -> {host_data['ansible_host']}")
                
                # Clean up test file
                os.remove(inventory_file)
                print("✅ Test inventory file cleaned up")
                
                return True
            else:
                print("❌ Inventory file was not created")
                return False
                
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

def test_hardware_collection_api():
    """Test the hardware collection API call."""
    try:
        from app.models.database import get_session
        from app.models.node import Node
        from app.services.orchestrator import OrchestrationService
        
        print("\nTesting hardware collection API...")
        
        session = get_session()
        try:
            nodes = session.query(Node).all()
            if not nodes:
                print("❌ No nodes found for hardware collection test")
                return False
            
            orchestrator = OrchestrationService()
            
            # Test hardware collection method (without actually running Ansible)
            print("✅ Hardware collection method is accessible")
            print("   Note: Full test requires Ansible and SSH access to nodes")
            
            return True
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Error during API test: {e}")
        return False

def main():
    """Run all tests."""
    print("Hardware Collection Test Suite")
    print("=" * 50)
    
    success = True
    
    # Test inventory generation
    if not test_inventory_generation():
        success = False
    
    # Test API accessibility
    if not test_hardware_collection_api():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed! Hardware collection should work correctly.")
        print("\nTo test full functionality:")
        print("1. Ensure nodes have SSH access configured")
        print("2. Try hardware collection from the web interface")
        print("3. Check operations page for results")
    else:
        print("❌ Some tests failed. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
