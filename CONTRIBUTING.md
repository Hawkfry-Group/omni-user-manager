# Contributing to Omni User Manager

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Hawkfry-Group/omni-user-manager.git
   cd omni-user-manager
   ```

2. Create a virtual environment and install:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .
   ```

## Development Process

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following these guidelines:
   - Place source code in `src/omni_sync/`
   - Update example files in `data/` if needed
   - Keep environment variables in `.env` (not committed)

## Pull Request Process

1. Ensure your changes:
   - Pass all tests
   - Follow the existing code style
   - Include necessary documentation
   - Don't expose sensitive data

2. Create a PR with:
   - Clear description of changes
   - Reference to any related issues
   - Updated documentation if needed

## Code Style

- Use type hints
- Write docstrings for public functions
- Keep functions focused and small
- Use meaningful variable names

## Documentation

- Update README.md for new features
- Keep docstrings current
- Document any new environment variables
- Update example files if needed

## Questions?

- Open an issue for bugs
- Use discussions for questions
- Tag maintainers for urgent issues

Thank you for your contribution! 