#!/usr/bin/env python3
"""Check recent operations and SSH key status."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.database import db
from app.models.flask_models import Operation, Node
from sqlalchemy import desc

def main():
    app = create_app()
    
    with app.app_context():
        # Get recent operations
        operations = Operation.query.order_by(desc(Operation.created_at)).limit(10).all()
        print('Recent Operations:')
        print('=' * 50)
        for op in operations:
            print(f'ID: {op.id}')
            print(f'  Type: {op.operation_type}')
            print(f'  Status: {op.status}')
            print(f'  Success: {op.success}')
            print(f'  Created: {op.created_at}')
            if op.error_message:
                print(f'  Error: {op.error_message}')
            if op.output and len(op.output) > 200:
                print(f'  Output: {op.output[:200]}...')
            print()

        # Get nodes with SSH status
        nodes = Node.query.all()
        print('Nodes SSH Status:')
        print('=' * 50)
        for node in nodes:
            ssh_status = getattr(node, 'ssh_key_status', 'not_set')
            ssh_generated = getattr(node, 'ssh_key_generated', False)
            ssh_path = getattr(node, 'ssh_key_path', None)
            print(f'Node {node.id}: {node.hostname}')
            print(f'  SSH Status: {ssh_status}')
            print(f'  Generated: {ssh_generated}')
            print(f'  Key Path: {ssh_path}')
            if ssh_path and os.path.exists(ssh_path):
                print(f'  Key File Exists: Yes')
            else:
                print(f'  Key File Exists: No')
            print()

if __name__ == "__main__":
    main()
