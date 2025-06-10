from setuptools import setup, find_packages

setup(
    name="omni-user-manager",
    version="0.1.3",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "omni-user-manager=omni_sync.cli:main",
            "omni-um=omni_sync.cli:main",
        ],
    },
    python_requires=">=3.7",
    author="Jamie Fry",
    author_email="jamie@hawkfry.com",
    description="Omni User Manager - Sync users and groups with Omni",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Hawkfry-Group/omni-user-manager",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
) 