from setuptools import setup, find_packages

# Parse requirements.txt for base requirements
with open('requirements.txt') as f:
    requirements = []
    dev_requirements = []
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if 'extra == ' in line:
            if 'dev' in line:
                dev_requirements.append(line.split(';')[0].strip())
        else:
            requirements.append(line)

setup(
    name="checkmate",
    version="0.1.0",
    description="Meshtastic private channel monitor and radio check responder",
    author="Meshtastic Team",
    author_email="info@meshtastic.org",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
    },
    entry_points={
        "console_scripts": [
            "check-mate=checkmate.main:main",
        ],
    },
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)