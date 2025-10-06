# Contributing to MicroK8s Cluster Orchestrator

Thank you for your interest in contributing to the MicroK8s Cluster Orchestrator! We welcome contributions from the community and are grateful for your help in making this project better.

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to uphold this code. Please read the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) file for details.

## How to Contribute

### Reporting Issues

Before creating an issue, please:

1. **Search existing issues** to avoid duplicates
2. **Use the issue templates** when available
3. **Provide detailed information**:
   - Operating system and version
   - Python version
   - Steps to reproduce the issue
   - Expected vs actual behavior
   - Relevant logs or error messages

### Suggesting Features

We welcome feature suggestions! Please:

1. **Check existing issues** to see if it's already been suggested
2. **Describe the use case** and why it would be valuable
3. **Consider the scope** - is it within the project's goals?
4. **Be open to discussion** and alternative approaches

### Contributing Code

#### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/microk8s-cluster-orchestrator.git
   cd microk8s-cluster-orchestrator
   ```

3. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up pre-commit hooks** (optional but recommended):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

#### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards:
   - Follow PEP 8 style guidelines
   - Add docstrings to new functions and classes
   - Include type hints where appropriate
   - Write tests for new functionality

3. **Test your changes**:
   ```bash
   # Run the test suite
   pytest
   
   # Run linting
   flake8
   
   # Run type checking
   mypy app/
   ```

4. **Update documentation** if needed:
   - Update docstrings
   - Add or update README sections
   - Update API documentation

#### Submitting Changes

1. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

2. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request**:
   - Use a descriptive title
   - Reference any related issues
   - Provide a clear description of changes
   - Include screenshots for UI changes

### Coding Standards

#### Python Code Style

- **Follow PEP 8** for code formatting
- **Use Black** for automatic code formatting
- **Use type hints** for function signatures
- **Write docstrings** for all public functions and classes
- **Keep functions small** and focused on a single responsibility

#### Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Example:
```
feat: add SSH key regeneration functionality

- Add regenerate-ssh-key endpoint to web interface
- Implement key cleanup before regeneration
- Add confirmation dialog for key regeneration
- Update documentation with new feature
```

#### Testing

- **Write tests** for new functionality
- **Maintain test coverage** above 80%
- **Test edge cases** and error conditions
- **Use descriptive test names** that explain what is being tested

### Documentation

#### Code Documentation

- **Add docstrings** to all public functions and classes
- **Use Google-style docstrings** for consistency
- **Include type hints** in function signatures
- **Document complex algorithms** with inline comments

#### User Documentation

- **Update README.md** for significant changes
- **Add examples** for new features
- **Update API documentation** if applicable
- **Keep installation instructions** up to date

### Review Process

1. **Automated checks** must pass (tests, linting, type checking)
2. **Code review** by maintainers
3. **Discussion** of any requested changes
4. **Approval** and merge

### Areas for Contribution

We particularly welcome contributions in these areas:

- **Bug fixes** and stability improvements
- **Performance optimizations**
- **Additional Ansible playbooks** for new functionality
- **UI/UX improvements** for the web interface
- **Documentation** improvements and examples
- **Test coverage** improvements
- **Security enhancements**

### Getting Help

If you need help or have questions:

1. **Check the documentation** in the `docs/` directory
2. **Search existing issues** for similar questions
3. **Create a new issue** with the "question" label
4. **Join our discussions** in the GitHub Discussions tab

### Recognition

Contributors will be recognized in:
- **CONTRIBUTORS.md** file (for significant contributions)
- **Release notes** for major contributions
- **GitHub contributors** page

Thank you for contributing to the MicroK8s Cluster Orchestrator! 🚀
