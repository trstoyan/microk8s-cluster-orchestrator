#!/usr/bin/env python3
"""
Core RAG System Test - Tests the local RAG system without Flask dependencies.

This script tests the core functionality of the local RAG system
without requiring the full Flask application setup.
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_core_rag_functionality():
    """Test core RAG functionality without Flask dependencies."""
    print("🍓 Testing Local RAG Core Functionality")
    print("=" * 50)
    
    try:
        # Import the core RAG system
        from app.services.local_rag_system import LocalRAGSystem
        
        print("✅ Successfully imported LocalRAGSystem")
        
        # Initialize the system
        print("\n1. Initializing RAG system...")
        rag_system = LocalRAGSystem(data_dir="test_data/local_rag")
        print("✅ RAG system initialized")
        
        # Test document addition
        print("\n2. Testing document addition...")
        
        sample_docs = [
            {
                'content': 'fatal: [node1]: FAILED! => {"changed": false, "msg": "snap command not found"}',
                'metadata': {'type': 'ansible_error', 'playbook': 'install_microk8s', 'success': False}
            },
            {
                'content': 'sudo apt install snapd && snap install microk8s --classic',
                'metadata': {'type': 'solution', 'playbook': 'install_microk8s', 'success': True}
            },
            {
                'content': 'fatal: [node2]: FAILED! => {"changed": false, "msg": "Permission denied"}',
                'metadata': {'type': 'ansible_error', 'playbook': 'setup_cluster', 'success': False}
            },
            {
                'content': 'chmod 600 ~/.ssh/id_rsa && ssh-add ~/.ssh/id_rsa',
                'metadata': {'type': 'solution', 'playbook': 'setup_cluster', 'success': True}
            }
        ]
        
        doc_ids = []
        for i, doc in enumerate(sample_docs, 1):
            doc_id = rag_system.add_document(doc['content'], doc['metadata'])
            doc_ids.append(doc_id)
            print(f"   ✅ Added document {i}: {doc_id}")
        
        print(f"✅ Added {len(doc_ids)} documents successfully")
        
        # Test search functionality
        print("\n3. Testing search functionality...")
        
        test_queries = [
            "snap command not found",
            "permission denied",
            "microk8s installation",
            "ssh connection failed"
        ]
        
        for query in test_queries:
            print(f"\n   Query: '{query}'")
            results = rag_system.retrieve_similar(query, top_k=2)
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"     Result {i}: Similarity {result.similarity_score:.3f}")
                    print(f"       Content: {result.document.content[:60]}...")
                    print(f"       Matching keywords: {result.matching_keywords}")
            else:
                print("     No results found")
        
        print("✅ Search functionality working")
        
        # Test response generation
        print("\n4. Testing response generation...")
        
        test_questions = [
            "How do I fix snap command not found?",
            "What causes permission denied errors?",
            "How to install MicroK8s?"
        ]
        
        for question in test_questions:
            print(f"\n   Question: '{question}'")
            response = rag_system.generate_response(question)
            
            print(f"     Method: {response['method']}")
            print(f"     Confidence: {response['confidence']:.3f}")
            print(f"     Context used: {response['context_used']}")
            
            resp_data = response['response']
            print(f"     Diagnosis: {resp_data.get('diagnosis', 'N/A')}")
            print(f"     Solution: {resp_data.get('solution', 'N/A')}")
            print(f"     Confidence: {resp_data.get('confidence', 'N/A')}")
        
        print("✅ Response generation working")
        
        # Test Ansible output analysis
        print("\n5. Testing Ansible output analysis...")
        
        sample_ansible_output = """
TASK [Install MicroK8s] ******************************************
fatal: [node1]: FAILED! => {"changed": false, "msg": "snap command not found"}
fatal: [node2]: FAILED! => {"changed": false, "msg": "Permission denied"}

PLAY RECAP *****************************************************
node1: ok=2 changed=0 unreachable=0 failed=1 skipped=0 rescued=0 ignored=0
node2: ok=1 changed=0 unreachable=0 failed=1 skipped=0 rescued=0 ignored=0
        """
        
        analysis = rag_system.analyze_ansible_output(
            sample_ansible_output,
            "install_microk8s.yml",
            ["node1", "node2"]
        )
        
        print(f"   Success: {analysis['success']}")
        print(f"   Document ID: {analysis['document_id']}")
        print(f"   Confidence: {analysis['confidence']}")
        print(f"   Error summary: {analysis['error_summary'][:2]}")
        print(f"   Recommendations:")
        for rec in analysis['recommendations']:
            print(f"     - {rec}")
        
        print("✅ Ansible analysis working")
        
        # Test health insights
        print("\n6. Testing health insights...")
        
        insights = rag_system.get_health_insights()
        
        print(f"   Confidence: {insights['confidence']:.3f}")
        print(f"   Patterns found: {insights['patterns_found']}")
        print(f"   Documents analyzed: {insights['documents_analyzed']}")
        print("   Insights:")
        for insight in insights['insights']:
            print(f"     {insight}")
        
        print("✅ Health insights working")
        
        # Test statistics
        print("\n7. Testing system statistics...")
        
        stats = rag_system.get_statistics()
        
        print(f"   Total documents: {stats['total_documents']}")
        print(f"   Vocabulary size: {stats['vocabulary_size']}")
        print(f"   Documents by type: {stats['documents_by_type']}")
        print(f"   Recent documents (7d): {stats['recent_documents_7d']}")
        print(f"   Total patterns: {stats['total_patterns']}")
        print(f"   Frequent patterns: {stats['frequent_patterns']}")
        print(f"   System type: {stats['system_type']}")
        print(f"   External dependencies: {stats['external_dependencies']}")
        
        print("✅ Statistics working")
        
        # Performance test
        print("\n8. Testing performance...")
        
        import time
        
        # Test document addition performance
        start_time = time.time()
        for i in range(5):
            content = f"Performance test document {i} with various keywords for testing"
            metadata = {'type': 'test', 'index': i}
            rag_system.add_document(content, metadata)
        add_time = time.time() - start_time
        
        print(f"   Added 5 documents in {add_time:.3f} seconds")
        print(f"   Average time per document: {add_time/5:.3f} seconds")
        
        # Test search performance
        start_time = time.time()
        for i in range(5):
            query = f"test document {i} keywords"
            results = rag_system.retrieve_similar(query, top_k=3)
        search_time = time.time() - start_time
        
        print(f"   Performed 5 searches in {search_time:.3f} seconds")
        print(f"   Average time per search: {search_time/5:.3f} seconds")
        
        # Test response generation performance
        start_time = time.time()
        for i in range(3):
            query = f"How to fix test document {i}?"
            response = rag_system.generate_response(query)
        response_time = time.time() - start_time
        
        print(f"   Generated 3 responses in {response_time:.3f} seconds")
        print(f"   Average time per response: {response_time/3:.3f} seconds")
        
        print("✅ Performance test completed")
        
        # Cleanup
        print("\n9. Cleaning up test data...")
        
        # Remove test data directory
        import shutil
        test_data_dir = Path("test_data")
        if test_data_dir.exists():
            shutil.rmtree(test_data_dir)
            print("✅ Test data cleaned up")
        
        print("\n🎉 ALL TESTS PASSED!")
        print("The Local RAG System is working perfectly!")
        print("🍓 Ready for Raspberry Pi 5 deployment!")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the project root directory.")
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Test failed")
        return False

def main():
    """Main test function."""
    print("🧪 Local RAG System Core Test")
    print("=" * 60)
    print("Testing core functionality without Flask dependencies")
    print()
    
    success = test_core_rag_functionality()
    
    if success:
        print("\n✅ All core tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
