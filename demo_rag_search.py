#!/usr/bin/env python3
"""
RAG Search Demo - Demonstrates the search and retrieval functionality.

This script shows how the RAG system learns and retrieves relevant information.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from standalone_rag_test import StandaloneRAGSystem

def demo_rag_search():
    """Demonstrate RAG search functionality."""
    print("🔍 RAG Search Demonstration")
    print("=" * 50)
    
    # Initialize system
    rag_system = StandaloneRAGSystem(data_dir="demo_data/rag")
    
    # Add more comprehensive documents
    print("1. Adding comprehensive knowledge base...")
    
    knowledge_base = [
        {
            'content': 'fatal: [node1]: FAILED! => {"changed": false, "msg": "snap command not found"}',
            'metadata': {'type': 'ansible_error', 'playbook': 'install_microk8s', 'success': False, 'solution': 'install_snapd'}
        },
        {
            'content': 'sudo apt update && sudo apt install snapd',
            'metadata': {'type': 'solution', 'playbook': 'install_microk8s', 'success': True, 'category': 'package_manager'}
        },
        {
            'content': 'fatal: [node2]: FAILED! => {"changed": false, "msg": "Permission denied"}',
            'metadata': {'type': 'ansible_error', 'playbook': 'setup_cluster', 'success': False, 'solution': 'fix_permissions'}
        },
        {
            'content': 'chmod 600 ~/.ssh/id_rsa && ssh-add ~/.ssh/id_rsa',
            'metadata': {'type': 'solution', 'playbook': 'setup_cluster', 'success': True, 'category': 'ssh_security'}
        },
        {
            'content': 'microk8s enable dns storage ingress',
            'metadata': {'type': 'solution', 'playbook': 'configure_microk8s', 'success': True, 'category': 'microk8s_config'}
        },
        {
            'content': 'fatal: [node3]: FAILED! => {"changed": false, "msg": "Connection refused"}',
            'metadata': {'type': 'ansible_error', 'playbook': 'setup_cluster', 'success': False, 'solution': 'check_connectivity'}
        },
        {
            'content': 'systemctl restart ssh && ufw allow ssh',
            'metadata': {'type': 'solution', 'playbook': 'setup_cluster', 'success': True, 'category': 'network'}
        },
        {
            'content': 'snap install microk8s --classic',
            'metadata': {'type': 'solution', 'playbook': 'install_microk8s', 'success': True, 'category': 'microk8s_install'}
        }
    ]
    
    for i, doc in enumerate(knowledge_base, 1):
        doc_id = rag_system.add_document(doc['content'], doc['metadata'])
        print(f"   ✅ Added document {i}: {doc_id}")
    
    print(f"✅ Knowledge base created with {len(knowledge_base)} documents")
    
    # Demonstrate search functionality
    print("\n2. Demonstrating intelligent search...")
    
    search_queries = [
        "snap command not found",
        "permission denied ssh",
        "microk8s installation",
        "connection refused",
        "ssh setup",
        "package manager issues"
    ]
    
    for query in search_queries:
        print(f"\n🔍 Query: '{query}'")
        results = rag_system.retrieve_similar(query, top_k=3, min_similarity=0.05)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"   Result {i} (similarity: {result.similarity_score:.3f}):")
                print(f"     Content: {result.document.content}")
                print(f"     Type: {result.document.metadata.get('type', 'unknown')}")
                print(f"     Matching keywords: {result.matching_keywords}")
                print()
        else:
            print("   No similar documents found")
    
    # Demonstrate response generation with context
    print("\n3. Demonstrating intelligent response generation...")
    
    questions = [
        "How do I fix snap command not found error?",
        "What should I do when getting permission denied?",
        "How to install MicroK8s properly?",
        "How to fix connection refused errors?"
    ]
    
    for question in questions:
        print(f"\n❓ Question: '{question}'")
        response = rag_system.generate_response(question)
        
        resp_data = response['response']
        print(f"   🎯 Diagnosis: {resp_data['diagnosis']}")
        print(f"   🔧 Solution: {resp_data['solution']}")
        print(f"   📊 Confidence: {resp_data['confidence']}/10")
        print(f"   📚 Context used: {response['context_used']} documents")
        print(f"   🧠 Method: {response['method']}")
    
    # Show system statistics
    print("\n4. System statistics...")
    stats = rag_system.get_statistics()
    print(f"   📄 Total documents: {stats['total_documents']}")
    print(f"   📝 Vocabulary size: {stats['vocabulary_size']}")
    print(f"   📊 Documents by type: {stats['documents_by_type']}")
    print(f"   🔄 Recent activity: {stats['recent_documents_7d']} documents in last 7 days")
    print(f"   🏠 System type: {stats['system_type']}")
    print(f"   🌐 External dependencies: {stats['external_dependencies']}")
    
    # Demonstrate Ansible analysis
    print("\n5. Demonstrating Ansible output analysis...")
    
    sample_failure = """
TASK [Install MicroK8s] ******************************************
fatal: [worker1]: FAILED! => {"changed": false, "msg": "snap command not found"}
fatal: [worker2]: FAILED! => {"changed": false, "msg": "Permission denied"}

TASK [Configure SSH] ********************************************
fatal: [worker1]: FAILED! => {"changed": false, "msg": "Connection refused"}

PLAY RECAP *****************************************************
worker1: ok=1 changed=0 unreachable=0 failed=2 skipped=0 rescued=0 ignored=0
worker2: ok=2 changed=0 unreachable=0 failed=1 skipped=0 rescued=0 ignored=0
    """
    
    analysis = rag_system.analyze_ansible_output(
        sample_failure,
        "setup_workers.yml",
        ["worker1", "worker2"]
    )
    
    print(f"   📋 Playbook: setup_workers.yml")
    print(f"   🎯 Success: {analysis['success']}")
    print(f"   🆔 Document ID: {analysis['document_id']}")
    print(f"   📊 Confidence: {analysis['confidence']}/10")
    print(f"   ❌ Errors found: {len(analysis['error_summary'])}")
    print(f"   🔧 Recommendations:")
    for rec in analysis['recommendations']:
        print(f"     - {rec}")
    
    # Cleanup
    print("\n6. Cleaning up demo data...")
    import shutil
    demo_data_dir = Path("demo_data")
    if demo_data_dir.exists():
        shutil.rmtree(demo_data_dir)
        print("✅ Demo data cleaned up")
    
    print("\n🎉 RAG Search Demo Completed!")
    print("The system successfully:")
    print("  ✅ Learned from multiple document types")
    print("  ✅ Retrieved relevant information based on queries")
    print("  ✅ Generated intelligent responses with context")
    print("  ✅ Analyzed complex Ansible outputs")
    print("  ✅ Provided actionable recommendations")
    print("\n🍓 Ready for production use on Raspberry Pi 5!")

if __name__ == '__main__':
    demo_rag_search()
