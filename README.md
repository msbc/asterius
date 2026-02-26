# Asterius

Asterius is a tool for file information and comparison. It allows you to list file size, modification time, and SHA-256 checksum, as well as compare two directories recursively to report differences.

## Usage

To list file information:

```bash
asterius <directory>
```

To compare two directories:

```bash
asterius --diff <directory1> <directory2>
```

## Installation

Asterius only uses the Python standard library, so you can simply download the repository and run it with Python 3.
