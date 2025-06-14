# Sublime asdf

A Sublime Text plugin that automatically configures your environment to use [asdf](https://asdf-vm.com/) version manager.

## Features

- Automatically loads tool versions from `.tool-versions` files
- Respects asdf's version resolution hierarchy
- Supports all asdf-managed tools (Go, Node.js, Ruby, Python, Elixir, Rust, etc.)
- Works with LSP (Language Server Protocol) plugins
- Per-window environment configuration
- Auto-reloads when `.tool-versions` files change

## Installation

### Via Package Control (Recommended)
1. Open Command Palette (`Cmd+Shift+P` on macOS, `Ctrl+Shift+P` on Windows/Linux)
2. Type "Package Control: Install Package"
3. Search for "sublime-asdf"
4. Press Enter to install

### Manual Installation
1. Clone this repository to your Sublime Text Packages directory:
   ```bash
   cd ~/Library/Application\ Support/Sublime\ Text/Packages/
   git clone https://github.com/cavi21/sublime-asdf.git