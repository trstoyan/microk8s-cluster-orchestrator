#!/usr/bin/env python3
import re
import subprocess
import sys

def calculate_disk_total():
    try:
        # Get disk sizes using lsblk
        result = subprocess.run([
            'lsblk', '-d', '-o', 'NAME,SIZE'
        ], capture_output=True, text=True, check=True)
        
        total = 0.0
        for line in result.stdout.split('\n'):
            # Look for lines starting with sda, sdb, etc. (physical disks)
            if re.match(r'^s[a-z]+\s+', line):
                parts = line.split()
                if len(parts) >= 2:
                    size_str = parts[1]
                    
                    # Skip 0B entries
                    if size_str == '0B':
                        continue
                    
                    # Parse different size formats
                    if re.match(r'^([0-9.]+)G$', size_str):
                        total += float(re.match(r'^([0-9.]+)G$', size_str).group(1))
                    elif re.match(r'^([0-9.]+)T$', size_str):
                        total += float(re.match(r'^([0-9.]+)T$', size_str).group(1)) * 1024
                    elif re.match(r'^([0-9.]+)M$', size_str):
                        total += float(re.match(r'^([0-9.]+)M$', size_str).group(1)) / 1024
        
        print(f'{total:.1f}')
        return 0
    except Exception as e:
        print(f'0.0', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(calculate_disk_total())
