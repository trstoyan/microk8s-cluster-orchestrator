#!/usr/bin/env python3
"""
MicroK8s Cluster Orchestrator - Logo Display Utility
Displays ASCII art logos for the application
"""

import os
from pathlib import Path

# Color codes for terminal
COLORS = {
    'reset': '\033[0m',
    'bold': '\033[1m',
    'cyan': '\033[96m',
    'green': '\033[92m',
    'blue': '\033[94m',
    'magenta': '\033[95m',
    'yellow': '\033[93m',
    'red': '\033[91m',
}

LOGO_COMPACT = """
   ╔════════════════════════════════════════════════╗
   ║  ███╗   ███╗██╗  ██╗ █████╗ ███████╗          ║
   ║  ████╗ ████║██║ ██╔╝██╔══██╗██╔════╝          ║
   ║  ██╔████╔██║█████╔╝ ╚█████╔╝███████╗          ║
   ║  ██║╚██╔╝██║██╔═██╗ ██╔══██╗╚════██║          ║
   ║  ██║ ╚═╝ ██║██║  ██╗╚█████╔╝███████║          ║
   ║  ╚═╝     ╚═╝╚═╝  ╚═╝ ╚════╝ ╚══════╝          ║
   ║   Cluster Orchestrator   ⎈                    ║
   ║                                                ║
   ║     [π]━━[π]━━[π]  Ansible • Python • K8s     ║
   ║      ↓    ↓    ↓                              ║
   ║     [∞]  [∞]  [∞]  AI-Powered Management      ║
   ╚════════════════════════════════════════════════╝
"""

LOGO_MINIMAL = """
    ┌─────────────────────────────────────┐
    │     ⎈  MicroK8s Orchestrator  ⎈    │
    │                                     │
    │    [π]──[π]──[π]  Cluster Nodes    │
    │     ││  ││  ││                     │
    │     ╰───╰───╯  Ansible Automation  │
    │         │                           │
    │        [🤖]  AI Assistant           │
    │         │                           │
    │    ⚡ Fast • 🔒 Secure • 🎯 Smart   │
    └─────────────────────────────────────┘
"""

LOGO_BANNER = """
    ███╗   ███╗██╗  ██╗ █████╗ ███████╗  
    ████╗ ████║██║ ██╔╝██╔══██╗██╔════╝  
    ██╔████╔██║█████╔╝ ╚█████╔╝███████╗  
    ██║╚██╔╝██║██╔═██╗ ██╔══██╗╚════██║  
    ██║ ╚═╝ ██║██║  ██╗╚█████╔╝███████║  
    ╚═╝     ╚═╝╚═╝  ╚═╝ ╚════╝ ╚══════╝  
      Cluster Orchestrator ⎈
"""


def colorize(text, color='cyan'):
    """Add color to text"""
    if color in COLORS:
        return f"{COLORS[color]}{text}{COLORS['reset']}"
    return text


def print_logo(style='compact', colored=True):
    """
    Print the MicroK8s Orchestrator logo
    
    Args:
        style: 'compact', 'minimal', or 'banner'
        colored: Whether to apply colors (default: True)
    """
    logo_map = {
        'compact': LOGO_COMPACT,
        'minimal': LOGO_MINIMAL,
        'banner': LOGO_BANNER,
    }
    
    logo = logo_map.get(style, LOGO_COMPACT)
    
    if colored:
        # Colorize different elements
        lines = logo.split('\n')
        colored_lines = []
        for line in lines:
            # Color the boxes/borders
            line = line.replace('╔', colorize('╔', 'cyan'))
            line = line.replace('╗', colorize('╗', 'cyan'))
            line = line.replace('╚', colorize('╚', 'cyan'))
            line = line.replace('╝', colorize('╝', 'cyan'))
            line = line.replace('║', colorize('║', 'cyan'))
            line = line.replace('═', colorize('═', 'cyan'))
            line = line.replace('┌', colorize('┌', 'cyan'))
            line = line.replace('┐', colorize('┐', 'cyan'))
            line = line.replace('└', colorize('└', 'cyan'))
            line = line.replace('┘', colorize('┘', 'cyan'))
            line = line.replace('│', colorize('│', 'cyan'))
            line = line.replace('─', colorize('─', 'cyan'))
            
            # Color the Kubernetes symbol
            line = line.replace('⎈', colorize('⎈', 'blue'))
            
            # Color Raspberry Pi symbols
            line = line.replace('[π]', colorize('[π]', 'magenta'))
            
            # Color infinity symbols
            line = line.replace('[∞]', colorize('[∞]', 'green'))
            
            # Color tech stack
            if 'Ansible' in line or 'Python' in line or 'K8s' in line:
                line = line.replace('Ansible', colorize('Ansible', 'red'))
                line = line.replace('Python', colorize('Python', 'yellow'))
                line = line.replace('K8s', colorize('K8s', 'blue'))
            
            colored_lines.append(line)
        
        print('\n'.join(colored_lines))
    else:
        print(logo)


def print_startup_message(version="1.0.0"):
    """Print a nice startup message with the logo"""
    print_logo('compact', colored=True)
    print(f"\n   {colorize('Version:', 'cyan')} {colorize(version, 'green')}")
    print(f"   {colorize('🔧 Infrastructure as Code, Management as Art', 'yellow')}\n")


if __name__ == '__main__':
    # For testing
    import sys
    
    style = sys.argv[1] if len(sys.argv) > 1 else 'compact'
    
    if style == 'all':
        print("\n=== COMPACT ===")
        print_logo('compact')
        print("\n=== MINIMAL ===")
        print_logo('minimal')
        print("\n=== BANNER ===")
        print_logo('banner')
    elif style == 'startup':
        print_startup_message("1.0.0")
    else:
        print_logo(style)

