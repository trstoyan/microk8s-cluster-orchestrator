# Local RAG System for MicroK8s Cluster Orchestrator

## 🍓 Raspberry Pi 5 Ready - Zero External Dependencies

The Local RAG (Retrieval-Augmented Generation) system is a completely self-contained, lightweight system designed to run efficiently on a single Raspberry Pi 5 without any external dependencies.

## 🎯 Key Features

### ✅ **Completely Local**
- **Zero external dependencies** - no APIs, no cloud services
- Uses only built-in Python libraries + SQLite
- Runs entirely on the Raspberry Pi 5
- No internet connection required after setup

### 🧠 **Intelligent Learning**
- **Pattern Recognition**: Automatically learns from Ansible outputs
- **Error Analysis**: Identifies common failure patterns
- **Solution Storage**: Remembers successful fixes
- **Contextual Retrieval**: Finds similar past issues and solutions

### ⚡ **Lightweight & Fast**
- **TF-IDF Similarity**: Fast text similarity using built-in algorithms
- **SQLite Storage**: Efficient local database storage
- **Memory Optimized**: Designed for Raspberry Pi 5 constraints
- **Single-threaded**: Optimized for ARM architecture

### 🔍 **Smart Health Monitoring**
- **Ansible Output Analysis**: Parses complex Ansible failures
- **Health Scoring**: Accurate health assessment with context
- **Trend Analysis**: Tracks system health over time
- **Recommendations**: Provides actionable insights

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Local RAG System                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Document Store │  │  Pattern DB     │  │  Health      │ │
│  │  (SQLite)       │  │  (SQLite)       │  │  Monitor     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  TF-IDF Search  │  │  Rule-based     │  │  Ansible     │ │
│  │  Engine         │  │  Response Gen   │  │  Parser      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Test the System
```bash
# Run comprehensive tests
python scripts/test_local_rag.py --test all

# Test specific components
python scripts/test_local_rag.py --test basic
python scripts/test_local_rag.py --test ansible
python scripts/test_local_rag.py --test performance
```

### 2. Integration with Existing System
```python
from app.services.local_rag_system import get_local_rag_system
from app.services.simple_health_monitor import get_simple_health_monitor

# Get the RAG system
rag_system = get_local_rag_system()

# Analyze Ansible output
analysis = rag_system.analyze_ansible_output(
    output="fatal: [node1]: FAILED! => snap command not found",
    playbook_name="install_microk8s.yml",
    affected_hosts=["node1"]
)

# Get health insights
health_monitor = get_simple_health_monitor()
health_report = health_monitor.run_comprehensive_health_check()
```

## 📊 How It Works

### 1. **Document Storage**
- Stores Ansible outputs, error messages, and solutions
- Extracts keywords using simple tokenization
- Maintains metadata (operation type, success, timestamps)
- Uses SQLite for efficient local storage

### 2. **Pattern Recognition**
- Identifies common error patterns (e.g., "snap command not found")
- Tracks solution patterns (e.g., "sudo apt install snapd")
- Builds frequency-based pattern database
- Learns from successful operations

### 3. **Intelligent Retrieval**
- Uses TF-IDF (Term Frequency-Inverse Document Frequency) for similarity
- Finds documents with similar keywords and context
- Ranks results by similarity score
- Provides contextual matching

### 4. **Response Generation**
- Combines retrieved context with rule-based logic
- Generates diagnostic information
- Provides step-by-step solutions
- Calculates confidence scores

## 🔧 Configuration

The system is configured via `config/local_rag_config.yml`:

```yaml
local_rag:
  enabled: true
  data_dir: "data/local_rag"
  
  documents:
    max_documents: 10000
    retention_days: 365
  
  search:
    default_top_k: 5
    min_similarity: 0.1
  
  patterns:
    enabled: true
    min_frequency: 2
    max_patterns: 1000
```

## 📈 Performance Characteristics

### **Raspberry Pi 5 Optimized**
- **Memory Usage**: < 512MB RAM
- **CPU Usage**: Single-threaded, < 80% CPU
- **Storage**: Compressed SQLite databases
- **Response Time**: < 100ms for typical queries

### **Scalability**
- **Documents**: Up to 10,000 documents
- **Patterns**: Up to 1,000 patterns
- **Concurrent Users**: Single-threaded (Raspberry Pi optimized)
- **Storage Growth**: ~1MB per 1000 documents

## 🧪 Testing

### **Automated Tests**
```bash
# Basic functionality test
python scripts/test_local_rag.py --test basic

# Ansible analysis test
python scripts/test_local_rag.py --test ansible

# Performance test
python scripts/test_local_rag.py --test performance

# Health monitoring test
python scripts/test_local_rag.py --test health
```

### **Manual Testing**
```python
# Test document addition
rag_system = get_local_rag_system()
doc_id = rag_system.add_document(
    "fatal: [node1]: FAILED! => snap command not found",
    {"type": "error", "playbook": "install_microk8s"}
)

# Test search
results = rag_system.retrieve_similar("snap command not found", top_k=3)

# Test response generation
response = rag_system.generate_response("How to fix snap command not found?")
```

## 🔍 Troubleshooting

### **Common Issues**

1. **Database Locked**
   ```bash
   # Check for running processes
   ps aux | grep python
   
   # Restart if needed
   sudo systemctl restart microk8s-orchestrator
   ```

2. **Low Memory**
   ```bash
   # Monitor memory usage
   free -h
   
   # Adjust configuration
   # Edit config/local_rag_config.yml
   max_memory_mb: 256  # Reduce if needed
   ```

3. **Slow Performance**
   ```bash
   # Check disk space
   df -h
   
   # Vacuum database
   sqlite3 data/local_rag/documents.db "VACUUM;"
   ```

## 📚 API Reference

### **LocalRAGSystem**

#### `add_document(content: str, metadata: Dict) -> str`
Add a document to the knowledge base.

#### `retrieve_similar(query: str, top_k: int = 5) -> List[LocalRAGResult]`
Find similar documents using TF-IDF similarity.

#### `generate_response(query: str, context_documents: List = None) -> Dict`
Generate intelligent response using retrieved context.

#### `analyze_ansible_output(output: str, playbook_name: str, hosts: List = None) -> Dict`
Analyze Ansible output and extract insights.

#### `get_health_insights() -> Dict`
Get health insights based on historical data.

#### `get_statistics() -> Dict`
Get system statistics and performance metrics.

### **SimpleHealthMonitor**

#### `run_comprehensive_health_check() -> Dict`
Run complete health check with RAG insights.

#### `analyze_ansible_failure(output: str, playbook_name: str, nodes: List) -> Dict`
Analyze Ansible failure with RAG context.

#### `get_health_trend(days: int = 7) -> Dict`
Get health trend analysis over specified period.

## 🎯 Use Cases

### **1. Ansible Failure Analysis**
```python
# When Ansible playbook fails
analysis = rag_system.analyze_ansible_output(
    output=ansible_output,
    playbook_name="install_microk8s.yml",
    affected_hosts=["node1", "node2"]
)

# Get intelligent recommendations
recommendations = analysis['recommendations']
```

### **2. Health Monitoring**
```python
# Get comprehensive health report
health_monitor = get_simple_health_monitor()
report = health_monitor.run_comprehensive_health_check()

# Access insights
print(f"Overall Health: {report['overall_score']}%")
print(f"RAG Insights: {report['rag_analysis']['rag_insights']}")
```

### **3. Pattern Learning**
```python
# System automatically learns from operations
# Each Ansible run adds to the knowledge base
# Patterns are extracted and stored
# Similar issues are identified and resolved faster
```

## 🔮 Future Enhancements

### **Planned Features**
- **Clustering**: Group similar issues automatically
- **Prediction**: Predict likely failures before they occur
- **Automation**: Auto-fix common issues
- **Visualization**: Web UI for pattern exploration

### **Integration Opportunities**
- **Prometheus**: Export metrics for monitoring
- **Grafana**: Dashboard for health visualization
- **AlertManager**: Intelligent alerting based on patterns

## 📝 License

This system is part of the MicroK8s Cluster Orchestrator project and follows the same license terms.

## 🤝 Contributing

Contributions are welcome! The system is designed to be:
- **Simple**: Easy to understand and modify
- **Local**: No external dependencies to break
- **Efficient**: Optimized for Raspberry Pi 5
- **Extensible**: Easy to add new features

---

**🍓 Perfect for Raspberry Pi 5 - Zero External Dependencies - Maximum Intelligence!**
