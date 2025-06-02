# Contributing to YouTube Transcript Processor

Thank you for your interest in contributing to this project! We welcome contributions from the community.

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher
- FFmpeg installed on your system
- Git for version control
- A code editor of your choice

### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork locally**:
   ```bash
   git clone https://github.com/your-username/youtube-transcript-processor.git
   cd youtube-transcript-processor
   ```

3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate     # On Windows
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up configuration files**:
   ```bash
   cp config.yaml.example config.yaml
   cp .env.example .env
   # Edit these files with your API keys and settings
   ```

## 🛠️ How to Contribute

### Reporting Issues

Before creating an issue, please:
- Check if the issue already exists
- Search closed issues for potential solutions
- Include detailed information about your environment

When reporting bugs, include:
- **Python version** (`python --version`)
- **Operating system** and version
- **Error messages** and stack traces
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Log files** (`logs/app.log`) if relevant

### Suggesting Features

For feature requests:
- Describe the problem you're trying to solve
- Explain your proposed solution
- Consider the scope and complexity
- Discuss potential breaking changes

### Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b bugfix/issue-description
   ```

2. **Make your changes**:
   - Follow the existing code style
   - Add tests if applicable
   - Update documentation as needed
   - Keep commits focused and atomic

3. **Test your changes**:
   ```bash
   # Run the script to ensure it works
   python new_main.py
   
   # Check for any new warnings or errors
   # Test with different configurations
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   # or
   git commit -m "fix: resolve issue with specific component"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**:
   - Use a descriptive title
   - Explain what changes you made and why
   - Reference any related issues
   - Include screenshots if applicable

## 📝 Code Style Guidelines

### Python Code Style
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and under 50 lines when possible
- Use type hints where appropriate

### Example Function:
```python
def process_video_transcript(video_id: str, languages: list) -> str:
    """
    Extract and format transcript from a YouTube video.
    
    Args:
        video_id: YouTube video ID
        languages: List of preferred languages for transcript
        
    Returns:
        Formatted transcript text
        
    Raises:
        TranscriptNotAvailableError: If transcript is not available
    """
    # Implementation here
    pass
```

### Configuration Changes
- Update `config.yaml.example` for new configuration options
- Document new settings in README.md
- Provide sensible defaults

### Logging
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- Include context in log messages
- Don't log sensitive information (API keys, personal data)

## 🧪 Testing

### Manual Testing
- Test with different YouTube channels
- Verify all file types are generated correctly
- Check Google Drive upload functionality
- Test error handling scenarios

### Test Cases to Cover
- **Valid scenarios**: Normal video processing
- **Edge cases**: Videos without transcripts, rate limiting
- **Error handling**: Network issues, API failures
- **Configuration**: Different language settings, file naming

## 📋 Areas for Contribution

### High Priority
- **Error handling improvements**: Better retry logic, graceful failures
- **Performance optimization**: Parallel processing, faster uploads
- **Configuration validation**: Validate YAML config on startup
- **Documentation**: More examples, troubleshooting guides

### Medium Priority
- **Testing framework**: Unit tests, integration tests
- **Docker support**: Containerization for easy deployment
- **Web interface**: Simple web UI for configuration
- **Monitoring**: Progress bars, status indicators

### Low Priority
- **Additional formats**: Support for other video platforms
- **Advanced filtering**: Duration, view count filters
- **Notification system**: Email/Slack notifications on completion
- **Analytics**: Processing statistics, success rates

## 🔍 Code Review Checklist

Before submitting a PR, ensure:
- [ ] Code follows the style guidelines
- [ ] Functions have appropriate docstrings
- [ ] Error handling is implemented
- [ ] Logging is appropriate and helpful
- [ ] Configuration changes are documented
- [ ] No sensitive data is hardcoded
- [ ] Changes are tested manually
- [ ] README is updated if needed

## 🚨 Security Considerations

- **Never commit API keys** or credentials
- **Use environment variables** for sensitive data
- **Validate user inputs** to prevent injection attacks
- **Follow OAuth best practices** for Google APIs
- **Keep dependencies updated** for security patches

## 📚 Resources

### Documentation
- [YouTube Data API](https://developers.google.com/youtube/v3)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Google Cloud Text-to-Speech](https://cloud.google.com/text-to-speech/docs)
- [Google Drive API](https://developers.google.com/drive/api)

### Python Libraries
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)
- [scrapetube](https://github.com/dermasmid/scrapetube)
- [pydub](https://github.com/jiaaro/pydub)

## 🤝 Community Guidelines

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Follow the project's code of conduct
- Ask questions if something is unclear

## 📞 Getting Help

If you need help:
1. Check the [README.md](README.md) troubleshooting section
2. Search existing issues for solutions
3. Ask questions in issue discussions
4. Reach out to maintainers for guidance

## 🎉 Recognition

Contributors will be recognized in:
- Project README
- Release notes
- CHANGELOG.md
- GitHub contributors page

Thank you for contributing to making this project better! 🚀
