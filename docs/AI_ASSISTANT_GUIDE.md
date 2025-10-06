# AI Assistant Guide

The MicroK8s Cluster Orchestrator includes an intelligent AI Assistant powered by a local Retrieval-Augmented Generation (RAG) system. This guide covers all AI Assistant features, configuration, and usage.

## Overview

The AI Assistant is designed to provide intelligent troubleshooting, analysis, and insights for MicroK8s cluster management. It operates entirely locally without external dependencies, making it perfect for Raspberry Pi 5 deployments and privacy-conscious environments.

### Key Features

- **Local-Only Operation**: No external APIs or cloud services required
- **Retrieval-Augmented Generation (RAG)**: Learns from your cluster's history
- **Multiple Chat Sessions**: Separate conversations for different topics
- **Searchable Content**: Index and search playbooks, docs, and logs
- **Operation Log Analysis**: Intelligent analysis of failed operations
- **Privacy-First**: Configurable data retention and anonymization

## Getting Started

### Accessing the AI Assistant

1. Navigate to the **AI Assistant** link in the main navigation
2. The interface opens with a chat window and sidebar
3. Start by asking questions about your cluster or pasting operation logs

### Basic Usage

#### Chat Interface
- Type your questions in the message input at the bottom
- The AI will respond with diagnoses, solutions, and confidence scores
- Use the quick action buttons for common queries

#### Sidebar Features
- **Chat Sessions**: Create and manage multiple conversations
- **Search Content**: Find relevant playbooks, documentation, and logs
- **Operation Logs**: View and analyze recent operations
- **Log Output Analyzer**: Paste logs directly for analysis

## Features in Detail

### 1. Chat Sessions Management

#### Creating New Sessions
- Click the **"New"** button in the Chat Sessions panel
- Enter a descriptive title for your session
- Switch between sessions using the sidebar list

#### Session Features
- **Persistent History**: Each session maintains its own message history
- **Session Metadata**: Track creation dates, message counts, and last activity
- **Search Sessions**: Find sessions by title or content
- **Delete Sessions**: Remove old or completed sessions

#### Use Cases
- **Separate Issues**: Create different sessions for different problems
- **Team Collaboration**: Share session IDs for collaborative troubleshooting
- **Historical Reference**: Keep sessions for recurring issues

### 2. Content Search

#### Searchable Content Types
- **Playbooks**: All Ansible playbooks in `ansible/playbooks/`
- **Documentation**: Markdown files in `docs/`
- **Operation Logs**: Historical operation outputs from the database

#### Search Features
- **Full-Text Search**: Search across content, titles, and keywords
- **Content Type Filtering**: Search specific types of content
- **Relevance Ranking**: Results ranked by relevance to your query
- **Preview**: See content snippets before opening full results

#### Indexing
- **Automatic Indexing**: Content is automatically indexed when added
- **Manual Reindexing**: Use the "Reindex" button to update the search index
- **Incremental Updates**: Only changed files are re-indexed

### 3. Operation Log Analysis

#### Viewing Recent Logs
- Click **"View Recent Logs"** to see the latest operations
- Logs are displayed with operation type, status, and timestamps
- Click on any log to get more details

#### Error Analysis
- Click **"Analyze Errors"** to automatically analyze failed operations
- The AI identifies patterns and provides recommendations
- Results include specific error types and suggested solutions

#### Log Output Analyzer
- **Paste Logs**: Use the text area to paste any operation logs
- **Analyze Logs**: Get technical analysis and recommendations
- **Explain Logs**: Get AI explanation of what the logs mean

### 4. Ansible Output Analysis

#### Analyzing Playbook Output
- Paste Ansible execution output into the analyzer
- Get structured analysis including:
  - Success/failure status
  - Error identification
  - Recommendations for fixes
  - Performance insights

#### Integration with Operations
- All Ansible operations are automatically analyzed
- Failed operations are flagged for review
- Successful operations contribute to the knowledge base

### 5. Health Insights

#### AI-Powered Health Monitoring
- Click **"Health Insights"** for intelligent system analysis
- Combines multiple data sources for comprehensive insights
- Provides confidence scores for recommendations

#### Insight Types
- **Performance Analysis**: CPU, memory, and storage optimization
- **Security Recommendations**: SSH, firewall, and access control
- **Configuration Issues**: MicroK8s and system configuration problems
- **Predictive Analysis**: Early warning of potential issues

## Configuration

### AI Assistant Settings

Access configuration through **AI Config** in the navigation menu.

#### Basic Settings
- **Enable/Disable**: Toggle AI Assistant features
- **RAG System**: Control the knowledge base functionality
- **Web Interface**: Configure chat interface options

#### Content Search Settings
- **Include Playbooks**: Index Ansible playbooks for search
- **Include Documentation**: Index documentation files
- **Include Operation Logs**: Index historical operation logs
- **Max Search Results**: Limit number of search results

#### Chat Session Settings
- **Multiple Chats**: Enable/disable multiple chat sessions
- **Session Retention**: How long to keep chat history
- **Auto-cleanup**: Automatically remove old sessions

#### Privacy Settings
- **Store Chat History**: Keep conversation history
- **Store Ansible Outputs**: Keep Ansible execution logs
- **Anonymize Data**: Remove sensitive information from stored data
- **Data Retention**: Configure how long to keep data

### Performance Settings

#### Local LLM Integration
- **Provider**: Choose between Ollama, OpenAI Local, or custom
- **Base URL**: API endpoint for local LLM
- **Model**: Specific model to use (e.g., llama2, codellama)
- **Timeout**: Request timeout in seconds
- **Max Tokens**: Maximum tokens per response
- **Temperature**: Response creativity (0.0-1.0)

#### Performance Optimization
- **Max Concurrent Requests**: Limit simultaneous AI requests
- **Response Timeout**: Maximum time to wait for responses
- **Cache Responses**: Cache frequent responses
- **Cache Duration**: How long to cache responses

## Advanced Usage

### Knowledge Base Management

#### Building Knowledge
- The AI Assistant automatically learns from:
  - Successful operations and their outcomes
  - Failed operations and their solutions
  - Manual corrections and fixes
  - User feedback and confirmations

#### Knowledge Sources
- **Ansible Playbooks**: Learn from playbook execution patterns
- **Operation Logs**: Understand common failure modes
- **Documentation**: Reference official guides and best practices
- **User Interactions**: Learn from chat conversations

### Troubleshooting Workflows

#### Systematic Approach
1. **Identify the Problem**: Use health insights to identify issues
2. **Search Knowledge Base**: Look for similar problems and solutions
3. **Analyze Logs**: Use operation log analysis for specific errors
4. **Create Chat Session**: Start a focused conversation about the issue
5. **Implement Solutions**: Follow AI recommendations step by step
6. **Learn and Improve**: Let the system learn from successful fixes

#### Common Use Cases
- **SSH Connection Issues**: Analyze connection failures and get setup guidance
- **MicroK8s Installation Problems**: Get step-by-step troubleshooting
- **Performance Issues**: Identify bottlenecks and optimization opportunities
- **Configuration Errors**: Understand and fix configuration problems

## Privacy and Security

### Data Handling
- **Local Processing**: All AI processing happens locally
- **No External APIs**: No data is sent to external services
- **Configurable Retention**: Control how long data is kept
- **Anonymization**: Option to remove sensitive information

### Security Features
- **Access Control**: AI Assistant respects user authentication
- **Audit Trail**: All interactions are logged for security
- **Data Encryption**: Sensitive data is encrypted at rest
- **Secure Storage**: All data stored in encrypted SQLite databases

## Troubleshooting

### Common Issues

#### AI Assistant Not Responding
- Check if AI Assistant is enabled in configuration
- Verify RAG system is properly initialized
- Check system logs for error messages
- Try reindexing content to refresh the knowledge base

#### Poor Response Quality
- Ensure content has been properly indexed
- Check if relevant documentation exists
- Verify operation logs are being stored
- Consider adjusting confidence thresholds

#### Performance Issues
- Reduce max concurrent requests
- Increase response timeout settings
- Enable response caching
- Check system resources (CPU, memory)

### Getting Help

#### Log Analysis
- Check application logs for AI Assistant errors
- Use the built-in log viewer in System Management
- Analyze operation logs for AI-related failures

#### Configuration Issues
- Verify configuration files are properly formatted
- Check AI Assistant configuration in web interface
- Reset to default settings if needed

#### Data Issues
- Reindex content if search results are poor
- Clear and rebuild knowledge base if needed
- Check database integrity

## Best Practices

### Effective Usage
1. **Be Specific**: Provide detailed information about problems
2. **Use Context**: Include relevant logs and error messages
3. **Follow Recommendations**: Implement AI suggestions systematically
4. **Provide Feedback**: Confirm when solutions work
5. **Organize Sessions**: Use multiple chat sessions for different topics

### Knowledge Base Optimization
1. **Regular Indexing**: Keep content search index updated
2. **Clean Data**: Remove outdated or irrelevant information
3. **Monitor Performance**: Watch for declining response quality
4. **Update Documentation**: Keep playbooks and docs current

### Privacy Management
1. **Review Settings**: Regularly check privacy configuration
2. **Data Cleanup**: Use automatic cleanup features
3. **Anonymization**: Enable for sensitive environments
4. **Access Control**: Monitor who has access to AI features

## Integration with Other Features

### SSH Key Management
- AI Assistant can help troubleshoot SSH connection issues
- Provides guidance on SSH server configuration
- Analyzes SSH key setup problems

### Hardware Monitoring
- Integrates with hardware reporting for system insights
- Correlates hardware issues with operational problems
- Provides recommendations for hardware optimization

### UPS Power Management
- Analyzes power-related issues and failures
- Provides guidance on power management configuration
- Helps troubleshoot UPS integration problems

### Wake-on-LAN
- Assists with WoL configuration and troubleshooting
- Analyzes network-related wake-up failures
- Provides network configuration guidance

## Future Enhancements

### Planned Features
- **Voice Interface**: Speech-to-text and text-to-speech capabilities
- **Advanced Analytics**: Deeper insights into cluster performance
- **Predictive Maintenance**: Proactive issue detection
- **Integration APIs**: External system integration capabilities
- **Mobile Interface**: Mobile-optimized chat interface

### Community Contributions
- **Custom Models**: Support for community-trained models
- **Plugin System**: Extensible AI capabilities
- **Knowledge Sharing**: Community knowledge base contributions
- **Translation Support**: Multi-language AI responses

## Conclusion

The AI Assistant provides powerful, privacy-focused intelligence for MicroK8s cluster management. By learning from your operations and providing contextual assistance, it helps reduce troubleshooting time and improves cluster reliability.

For more information, see the main [README](../README.md) and other documentation in the [docs/](.) directory.
